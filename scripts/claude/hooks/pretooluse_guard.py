#!/usr/bin/env python3
import json
import os
import re
import shlex
import subprocess
import sys

def _load():
    try:
        return json.load(sys.stdin)
    except Exception as e:
        print(f"[guard] invalid hook input: {e}", file=sys.stderr)
        return {}

def _block(msg: str, raw: str):
    print(f"[guard] {msg}\ncommand: {raw}", file=sys.stderr)
    sys.exit(2)

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

# --- git checkout/restore on a file with uncommitted worktree changes 防止 ---
# トークナイズは shlex.split()（クォート対応）で行う。素朴な str.split() だと
# `git checkout -- "my file.py"` のような空白パスを取りこぼし黙って素通し（データ消失）する。
_SHELL_OPS = ("&&", "||", "|", ";")

def _segments(cmd: str) -> list:
    """コマンドをクォート対応で分割し、shell 演算子区切りごとのトークン列リストを返す。
    クォート不整合（実シェルでもエラー）の場合は素朴分割にフォールバック。"""
    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = cmd.split()
    segs, seg = [], []
    for t in toks:
        if t in _SHELL_OPS:
            if seg:
                segs.append(seg)
                seg = []
        else:
            seg.append(t)
    if seg:
        segs.append(seg)
    return segs

def _worktree_dirty(path: str) -> bool:
    """<path>（'.' 可）にワークツリー変更があれば True。untracked('??')は除外。
    git 不在/失敗は False（fail-open＝既存方針と同じ）。"""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "--", path],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            return False
        for line in r.stdout.splitlines():
            if len(line) >= 2 and line[:2] != "??" and line[1] != " ":
                return True
        return False
    except Exception:
        return False

def _revert_targets(sub: str, args: list) -> list:
    """checkout/restore のうちワークツリーを破壊し得る pathspec を返す。破壊しない形は []。"""
    if sub == "checkout" and any(a in ("-b", "-B", "--orphan") for a in args):
        return []  # ブランチ作成
    if sub == "restore":
        has_staged = ("--staged" in args) or ("-S" in args)
        has_worktree = ("--worktree" in args) or ("-W" in args)
        if has_staged and not has_worktree:
            return []  # index のみ・ワークツリー非破壊
    cand = args[args.index("--") + 1:] if "--" in args else args
    return [a for a in cand if not a.startswith("-")]

def _git_revert_target_on_dirty(cmd: str):
    """複合コマンドを分割し、git checkout/restore の pathspec が dirty なら最初の該当パスを返す。"""
    for toks in _segments(cmd):
        if "git" not in toks:
            continue
        rest = toks[toks.index("git") + 1:]
        if not rest or rest[0] not in ("checkout", "restore"):
            continue
        for t in _revert_targets(rest[0], rest[1:]):
            if _worktree_dirty(t):
                return t
    return None

# --- git push の保護ブランチ宛先判定（I080） ---
PROTECTED_BRANCHES = ("develop", "main")

def _current_branch():
    """現ブランチ名を返す。git 不在/失敗は None（fail-open＝既存 HEAD チェックと同方針）。"""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

def _norm_push_dest(token: str, cur_branch):
    """push 宛先トークンを正規化して宛先ブランチ名を返す（判定不能は None）。
    'src:dst' なら dst 採用 → force-shorthand '+'（先頭/dst 側いずれも）除去 →
    'refs/heads/' 接頭辞除去 → 'HEAD' は現ブランチ解決。"""
    t = token
    if ":" in t:
        t = t.split(":", 1)[1]          # 'src:dst' の dst を採用
    t = t.lstrip("+")                    # force-shorthand '+'（先頭 / dst 側）を除去
    if t.startswith("refs/heads/"):
        t = t[len("refs/heads/"):]
    if t == "HEAD":
        return cur_branch               # None 可（detached/fail-open）
    return t or None

def _push_protected_target(cmd: str):
    """git push が protected ブランチを名前/refspec で宛先にするなら宛先名を返す。非該当は None。
    複合コマンドは _segments(I081)で分割して各セグメントを判定。
    --all/--mirror・--repo は positional を持たない/前提を崩すため main() 側の独立チェックで扱う。"""
    for toks in _segments(cmd):
        if "git" not in toks or "push" not in toks:
            continue
        after = toks[toks.index("push") + 1:]
        positionals = [a for a in after if not a.startswith("-")]
        refspecs = positionals[1:] if positionals else []   # [0]=remote、以降=refspec
        cur = None
        if not refspecs:                                     # 宛先明示なし → 現ブランチが宛先
            cur = _current_branch()
            if cur in PROTECTED_BRANCHES:
                return cur
            continue
        for rs in refspecs:
            if cur is None:
                cur = _current_branch()
            dest = _norm_push_dest(rs, cur)
            if dest in PROTECTED_BRANCHES:
                return dest
    return None

# --- git push force フラグ判定（_segments ベース・I083 欠陥2/F1） ---
_FORCE_LONG = ("--force", "--force-with-lease", "--force-if-includes")

def _is_force_flag(tok: str) -> bool:
    """push の force 系フラグなら True。--push-option=force 等の非 force 用法は False。"""
    if tok.startswith("--"):
        return tok.split("=", 1)[0] in _FORCE_LONG
    if tok.startswith("-") and len(tok) > 1:          # 単一ダッシュ短縮クラスタ（-f/-uf/-fu）
        # 単一ダッシュで 'f' を含む全クラスタを force として扱う（git push の短縮フラグで 'f' は -f のみ）。
        # 注: '-rf' 等の非実在フラグも True になるが、push セグメント内で '-rf' は無効構文＝実害なし。
        return "f" in tok[1:]
    return False

def _push_has_force(cmd: str) -> bool:
    """push を含むセグメントの push 以降トークンに force 系フラグがあれば True。
    複合コマンド・短縮結合形に頑健（_segments でセグメント分割）。protected 宛先の force は
    _push_protected_target が先に block するため、ここで捕捉する漏れは非保護宛に限定される。"""
    for toks in _segments(cmd):
        if "git" in toks and "push" in toks:
            after = toks[toks.index("push") + 1:]
            if any(_is_force_flag(t) for t in after):
                return True
    return False

# --- 動的・不透明 push 判定（ask degrade・I083 欠陥1/R5） ---
_WRAP_SHELLS = ("sh", "bash", "dash", "zsh")

def _push_is_dynamic(cmd: str) -> bool:
    """静的に宛先を確定できない push なら True（ask に degrade する対象）。
    (i) 直接 push の push 以降引数に動的メタ文字（宛先トークン分離に依存しない）。
    (ii) 構造的に不透明なラッパー（eval/sh -c/bash -c/git -c alias.）が push を隠蔽。
    脅威モデル=事故。push トークンが完全隠蔽される eval "$VAR" 形は対象外（既知の限界）。"""
    if not (re.search(r"\bgit\b", cmd) and re.search(r"\bpush\b", cmd)):
        return False
    for toks in _segments(cmd):
        if not toks:                       # _segments は空セグメントを返さないが防御的に
            continue
        # (i) 直接 push: push 以降の引数領域に動的メタ文字（$(...) の空白で shlex が壊れてもすり抜けない）
        if "git" in toks and "push" in toks:
            after = " ".join(toks[toks.index("push") + 1:])
            if any(ch in after for ch in "$`{("):
                return True
        # (ii) 構造的に不透明なラッパー（先頭トークンで判定＝branch/remote 名の偶然一致を排除）
        head = toks[0]
        if head == "eval" and any("push" in t for t in toks[1:]):
            return True
        if head in _WRAP_SHELLS and "-c" in toks:
            ci = toks.index("-c")
            wrapped = toks[ci + 1] if ci + 1 < len(toks) else ""
            if "push" in wrapped:
                return True
        if head == "git":
            for i, t in enumerate(toks[:-1]):
                if t == "-c" and toks[i + 1].startswith("alias.") and "push" in toks[i + 1]:
                    return True
    return False

# 高リスク Edit/Write パス（リポジトリルート相対で照合）。
# 価値判断寄り（依存/スキーマ/インフラ）のため、編集時に ask（プロンプト）を出す。
# 注: ハードブロック(exit 2)ではなく ask。承認すれば編集可（I079 案D）。
HIGH_RISK_EDIT_PATTERNS = [
    r"(?:^|/)(?:backend|frontend)/Dockerfile(?:\.dev)?$",   # コンテナ定義
    r"(?:^|/)frontend/nginx\.conf$",                        # 配信設定
    r"(?:^|/)backend/requirements[^/]*\.txt$",              # 依存マニフェスト
    r"(?:^|/)backend/pyproject\.toml$",                     # 依存/ビルド設定
    r"(?:^|/)frontend/package(?:-lock)?\.json$",            # 依存/ロックファイル
    r"(?:^|/)[^/]+/migrations/[^/]*\.py$",                  # DBマイグレーション(手書き)
    r"(?:^|/)backend/init-db\.sql$",                        # DB初期化SQL
]

def _repo_relative(path: str) -> str:
    """file_path を可能ならリポジトリルート相対に正規化する（絶対/相対・`./`・OS差を吸収）。"""
    p = path.replace("\\", "/")
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            root = r.stdout.strip().replace("\\", "/")
            if root and p.startswith(root + "/"):
                p = p[len(root) + 1:]
    except Exception:
        pass  # git 不在環境では生のパスで照合
    while p.startswith("./"):
        p = p[2:]
    return p

# --- worktree 横断書込のブロック（I095） ---
# 別トラック（別 worktree）の作業ツリーへの直接書込を技術強制で禁止する（worktree.md §9）。
# 読み取りは許可・書込のみブロック。fail-safe（境界確定不能はブロック）・エスケープ無し（DANGER_OK 非解除）。
_REDIR_OPS = (">>", ">|", ">")   # 長いものから判定（">>" を ">" より先に）

def _worktree_roots():
    """全 worktree ルート（realpath 正規化）のリストを返す。git 失敗/非ゼロは None（fail-safe 対象）。"""
    try:
        r = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            return None
        roots = []
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                roots.append(os.path.realpath(line[len("worktree "):].strip()))
        return roots
    except Exception:
        return None

def _current_worktree_root():
    """現 worktree ルート（realpath 正規化）。失敗は None。"""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True
        )
        return os.path.realpath(r.stdout.strip()) if r.returncode == 0 else None
    except Exception:
        return None

def _cross_worktree(path):
    """path が別 worktree 配下なら True / どの別 worktree 配下でもなければ False /
    境界を確定できなければ None（fail-safe 対象）。境界一致は realpath＋末尾 os.sep 接頭辞で
    行い、兄弟ディレクトリ名の部分一致（<root>-foo）を誤判定しない。"""
    if not path or not isinstance(path, str):
        return None
    roots = _worktree_roots()
    cur = _current_worktree_root()
    if roots is None or cur is None:
        return None
    ap = os.path.realpath(os.path.abspath(path))
    for root in roots:
        if root == cur:
            continue
        if ap == root or ap.startswith(root + os.sep):
            return True
    return False

def _edit_path(data: dict) -> str:
    """書込ツールの対象パス（Edit/Write/MultiEdit=file_path, NotebookEdit=notebook_path）。"""
    ti = data.get("tool_input") or {}
    p = ti.get("file_path") or ti.get("notebook_path") or ""
    return p if isinstance(p, str) else ""

def _split_redir_target(tok: str):
    """リダイレクト演算子が埋め込まれたトークンの右側（宛先候補）を返す。無ければ None。
    例: '>>/p'→'/p'・'>|/p'→'/p'・'>/p'→'/p'・'x>/p'→'/p'・'2>/p'→'/p'。'>' 単体は None。"""
    for op in _REDIR_OPS:
        idx = tok.find(op)
        if idx != -1:
            rhs = tok[idx + len(op):]
            return rhs or None
    return None

def _bash_write_targets(cmd: str) -> list:
    """Bash コマンドから書込先の絶対パスのみを抽出する（ヒューリスティック）。
    対象: リダイレクト（>/>>/>| の単体・付着・語中埋め込み）・tee・cp/mv の宛先・sed -i の対象。
    src 側（読み取り）は対象外・相対/変数越しは対象外（絶対パスのみ）。"""
    targets = []
    for toks in _segments(cmd):
        if not toks:
            continue
        # リダイレクト（全コマンド共通）
        i, n = 0, len(toks)
        while i < n:
            t = toks[i]
            if t in _REDIR_OPS:                 # 演算子単体 → 次トークンが宛先
                if i + 1 < n:
                    targets.append(toks[i + 1])
            elif any(op in t for op in _REDIR_OPS):   # 付着/語中埋め込み
                rhs = _split_redir_target(t)
                if rhs:
                    targets.append(rhs)
            i += 1
        # コマンド別の宛先
        head = os.path.basename(toks[0]) if toks[0] else ""
        rest = toks[1:]
        if head == "tee":
            targets += [a for a in rest if not a.startswith("-")]
        elif head in ("cp", "mv"):
            if "-t" in rest:                    # cp/mv -t <dir> src...
                ti = rest.index("-t")
                if ti + 1 < len(rest):
                    targets.append(rest[ti + 1])
            else:
                positional = [a for a in rest if not a.startswith("-")]
                if len(positional) >= 2:
                    targets.append(positional[-1])   # 末尾＝宛先（src は対象外）
        elif head == "sed":
            if any(a == "-i" or a.startswith("-i") or a.startswith("--in-place") for a in rest):
                targets += [a for a in rest if not a.startswith("-")]   # in-place 対象（絶対パスのみ後段で選別）
    # 絶対パスのみ（相対 src・sed script 等を除外）
    return [t for t in targets if t.startswith("/")]

def _has_write_intent(cmd: str) -> bool:
    """Bash に書込語（リダイレクト・tee・cp・mv・sed -i）が含まれるか（未カバー警告の判定用）。"""
    for toks in _segments(cmd):
        if not toks:
            continue
        for t in toks:
            if t in _REDIR_OPS or any(op in t for op in _REDIR_OPS):
                return True
        head = os.path.basename(toks[0]) if toks[0] else ""
        if head in ("tee", "cp", "mv"):
            return True
        if head == "sed" and any(a == "-i" or a.startswith("-i") or a.startswith("--in-place")
                                 for a in toks[1:]):
            return True
    return False

def _bash_uncovered_risk(cmd: str) -> bool:
    """絶対パス宛先の抽出では捕捉できない書込リスク（`cd` 後の相対書込・変数/コマンド置換・
    不透明ラッパー越しの宛先）があるか。no-silent-caps 警告用。
    読み取り（例: `cp /other/src ./dest`）や単純な相対書込では False（誤警告しない）。"""
    if not _has_write_intent(cmd):
        return False
    for toks in _segments(cmd):
        if not toks:
            continue
        head = os.path.basename(toks[0]) if toks[0] else ""
        if head == "cd":                                   # cwd が変わる → 相対宛先を分類できない
            return True
        if head == "eval" or (head in _WRAP_SHELLS and "-c" in toks):   # 不透明ラッパー
            return True
        if any(("$" in t) or ("`" in t) for t in toks):    # 変数/コマンド置換越しの宛先
            return True
    return False

def _block_cross_worktree(kind: str, path: str):
    """別 worktree への書込／判定不能を exit 2 でブロックする（DANGER_OK でも解除しない）。"""
    roots = _worktree_roots()
    cur = _current_worktree_root()
    if not path or roots is None or cur is None:
        reason = "対象パスを取得できない" if not path else "worktree 境界を確定できない"
        print(f"[guard] {reason}ため{kind}をブロックしました（fail-safe）。"
              f"git の状態/入力を確認してください: {path!r}", file=sys.stderr)
        sys.exit(2)
    ap = os.path.realpath(os.path.abspath(path))
    x_root = next((r for r in roots if r != cur and (ap == r or ap.startswith(r + os.sep))), None)
    where = f"別 worktree（{x_root}）" if x_root else "別 worktree"
    print(f"[guard] {where}への{kind}は禁止です。"
          f"トラック境界を越える変更は worktree.md §9 のファイル経由で引き継いでください: {path}",
          file=sys.stderr)
    sys.exit(2)

def _ask(reason: str):
    """PreToolUse の permissionDecision=ask を返す（プロンプト化）。"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)

def _check_edit_write(data: dict):
    """Edit/Write の対象が高リスクパスなら ask を返す。非該当は素通り(exit 0)。"""
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not isinstance(path, str) or not path.strip():
        sys.exit(0)
    rel = _repo_relative(path)
    for pat in HIGH_RISK_EDIT_PATTERNS:
        if re.search(pat, rel):
            _ask(f"高リスクファイル（依存/スキーマ/インフラ）の編集です。確認してください: {rel}")
    sys.exit(0)

# --- I146: cross-repo（fork）PR への取り込み系操作の防止 ---
# 判定の単一ソースは `gh pr view <識別子> --json isCrossRepository`。
# block = 不可逆かつ方針上ありえない操作（外部コードが develop に入る）。
# ask   = 取り込み方向だが可逆な操作。close/comment/read-only は素通し
#         （外部 PR を断るのに必要な操作を塞いではならない）。
# checkout も block: fork のブランチを checkout すると `.claude/settings.json` と hook 本体が
# 相手の版に置き換わり、次のツール呼び出しでそのコードが実行される（R10・2026-10-16 承認）。
# 対象サブコマンドと種別は下の _GH_PR_SPECS に集約する（R8: 追加は 1 エントリ）。

_MCP_PR_BLOCK_TOOLS = ("mcp__github__merge_pull_request",)
_MCP_PR_ASK_TOOLS = (
    "mcp__github__update_pull_request_branch",
    "mcp__github__create_pull_request_review",
)

_GH_TIMEOUT = 5  # 秒。ハーネスを長く止めない（超過時は ask に降格）


_CROSS_CACHE = {}


def _pr_is_cross_repo(ident, repo=None):
    """同一 (ident, repo) の照会は 1 回にまとめる（hook は 1 回の呼び出しごとに起動するため安全）。"""
    key = (ident, repo)
    if key not in _CROSS_CACHE:
        _CROSS_CACHE[key] = _pr_is_cross_repo_uncached(ident, repo)
    return _CROSS_CACHE[key]


def _pr_is_cross_repo_uncached(ident, repo=None):
    """(cross, head) を返す。cross は fork 由来 True / 自前 False / 判定不能 None（＝ask 降格）。
    head は "owner/repo" 形式の head リポジトリ名（取れなければ None）。
    ident が None のときはカレントブランチの PR を解決させる（gh の既定挙動）。
    head も同一クエリで取得するため照会回数は 1 回のまま。"""
    argv = ["gh", "pr", "view"]
    if ident:
        argv.append(ident)
    if repo:
        argv += ["--repo", repo]
    argv += ["--json", "isCrossRepository,headRepositoryOwner,headRepository"]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=_GH_TIMEOUT)
    except Exception:
        return None, None
    if r.returncode != 0:
        return None, None
    try:
        d = json.loads(r.stdout)
    except Exception:
        return None, None
    v = d.get("isCrossRepository")
    owner = (d.get("headRepositoryOwner") or {}).get("login")
    name = (d.get("headRepository") or {}).get("name")
    head = f"{owner}/{name}" if owner and name else None
    if v is True:
        return True, head
    if v is False:
        return False, head
    return None, head


# gh pr サブコマンドごとのフラグ表（gh 2.88 の `gh pr <verb> --help` 準拠）。
# (kind, 値を取る long, 値を取る short, 値を取らない long, 値を取らない short)
# 表にないフラグは推測せず ambiguous（ask 降格）にする。値の有無を取り違えると識別子を誤認し、
# 別の PR を検査して素通しするため（例: merge の -m は値なし、edit の -m は値あり）。
# kind="approve" は review 用（--approve/-a があるときだけ ask 対象）。
_GH_PR_SPECS = {
    "merge": ("block",
              ("--body", "--body-file", "--subject", "--match-head-commit", "--author-email", "--repo"),
              "bFtAR",
              ("--merge", "--rebase", "--squash", "--delete-branch", "--admin", "--auto",
               "--disable-auto", "--help"),
              "mrsdh"),
    "checkout": ("block",
                 ("--branch", "--repo"), "bR",
                 ("--recurse-submodules", "--force", "--detach", "--help"), "fh"),
    "ready": ("ask", ("--repo",), "R", ("--undo", "--help"), "h"),
    "edit": ("ask",
             ("--title", "--body", "--body-file", "--base", "--milestone", "--add-assignee",
              "--remove-assignee", "--add-label", "--remove-label", "--add-project",
              "--remove-project", "--add-reviewer", "--remove-reviewer", "--repo"),
             "tbFBmR",
             ("--remove-milestone", "--help"), "h"),
    "update-branch": ("ask", ("--repo",), "R", ("--rebase", "--help"), "h"),
    "review": ("approve", ("--body", "--body-file", "--repo"), "bFR",
               ("--approve", "--comment", "--request-changes", "--help"), "acrh"),
}
_GH_PUNCT = "();<>|&`"
_FD_RE = re.compile(r"(?:(?<=^)|(?<=[\s;&|()`]))\d+(?=[<>])", re.M)
_WORD_BREAK = " \t\n;&|()<>"
# 安全網（_gh_coarse_count）: 精密判定（下の _gh_pr_target）が取りこぼした「gh pr の取り込み系操作の記述」を数える粗い検出。
# 「実行される部分」（_shell_code(keep_quoted=False)＝引用符の中身・ヒアドキュメント本文・コメントを除いた文字列）に掛け、
# 精密判定の件数と一致しなければ「判定しきれない記述がある」とみなして ask にする
# （精密判定の穴を黙った素通しではなく確認に倒す fail-safe。block はしない）。
# 引数として渡す文字列データ（`run 'gh pr merge 257'`・`python3 -c "…"`）には反応しない（I174 と同じ方針）。
_GH_COARSE_VERBS = ("merge", "checkout", "ready", "edit", "update-branch")


def _gh_coarse_count(text: str) -> int:
    """安全網の粗い検出: `gh … pr … <取り込み系 verb>`・`gh … co`・`gh … pr … review … --approve/-a` の
    記述を数える（区切り `\n ; & | ` ( )` ごとに空白で単語に分け、gh ごとに次の gh までを見る線形走査）。
    正規表現の入れ子の遅延一致は入力によって 3 乗の時間がかかり hook のタイムアウト＝素通しを招くため使わない。"""
    count = 0
    for seg in re.split(r"[\n;&|`()]", text):
        words = seg.split()
        idxs = [k for k, w in enumerate(words) if os.path.basename(w) in ("gh", "gh.exe")]
        for a, k in enumerate(idxs):
            rest = words[k + 1:idxs[a + 1] if a + 1 < len(idxs) else len(words)]
            if "co" in rest:
                count += 1
                continue
            if "pr" not in rest:
                continue
            after = rest[rest.index("pr") + 1:]
            if any(w in _GH_COARSE_VERBS for w in after):
                count += 1
            elif "review" in after and any(
                    w.startswith("--approve") or re.match(r"^-[crh]*a", w) for w in after):
                count += 1
    return count


def _shell_code(raw: str, keep_quoted: bool = True) -> str:
    """bash と同じ規則で、実行されない部分を取り除いた文字列を返す（gh pr 判定専用）。
    - CRLF を LF に揃え、クォート外の行継続（\\<改行>）を連結する
    - クォート外の語頭の `#` から行末までのコメントを除く（語中の `#`・クォート内の `#` は文字のまま）
    - クォート外・算術式外の `<<WORD`（`<<<` を除く）をヒアドキュメント開始とみなし、本文行と終端行を除く。
      終端語はクォート・バックスラッシュを除いた語全体（`'END-OF-MSG'`・`\\EOF`・`EO"F"` → END-OF-MSG/EOF/EOF）。
      終端行が見つからない場合は除かない（後続の実コマンドを隠さない fail-safe）。
    - 二重引用符の中の `$( … )`・`` ` … ` `` は実行される部分として入れ子で追う（中の引用符で状態を取り違えない）。
      ANSI-C 引用 `$'…'` は、直前の `$` が引用・エスケープされておらず `$$` の 2 文字目でもないときだけ認める。
    keep_quoted=False のときは引用符の中身（データ）を空白に置き換える（コマンド置換の中身は実行されるので残す）。
    安全網はこの「実行される部分だけ」の文字列に掛ける（I174 と同じ方針: 引数の文字列・ヒアドキュメント本文に反応しない）。"""
    s = raw.replace("\r\n", "\n")
    out, pending, i, n = [], [], 0, len(s)
    stack = ["top"]   # top / sq / dq / ansi / subst / bt
    depth = []        # subst ごとの括弧の深さ
    bare_dollar = False  # 直前に出力したのが「引用・エスケープされていない単独の $」か

    def emit(text, data=False):
        if data and not keep_quoted:
            out.append(" ")
        else:
            out.append(text)

    while i < n:
        ch, ctx = s[i], stack[-1]
        if ctx == "sq":
            if ch == "'":
                stack.pop()
                emit("'", data=True)
            else:
                emit(ch, data=True)
            i += 1
            continue
        if ctx == "ansi":
            if ch == "\\" and i + 1 < n:
                emit(s[i:i + 2], data=True)
                i += 2
                continue
            if ch == "'":
                stack.pop()
            emit(ch, data=True)
            i += 1
            continue
        if ctx == "dq":
            if ch == "\\" and i + 1 < n:
                emit(s[i:i + 2], data=True)
                i += 2
            elif ch == '"':
                stack.pop()
                emit('"', data=True)
                i += 1
            elif s.startswith("$(", i) and not s.startswith("$((", i):
                stack.append("subst")
                depth.append(0)
                emit("$(")
                i += 2
            elif ch == "`":
                stack.append("bt")
                emit("`")
                i += 1
            else:
                emit(ch, data=True)
                i += 1
            bare_dollar = False
            continue
        # クォート外（top / subst / bt）
        prev_bare = bare_dollar
        bare_dollar = False
        if ch == "\\" and i + 1 < n:
            if s[i + 1] != "\n":  # 行継続は連結（出力しない）
                out.append(s[i:i + 2])
            i += 2
            continue
        if s.startswith("$((", i):  # 算術式（中の << はシフト演算）
            end = s.find("))", i)
            end = n if end < 0 else end + 2
            out.append(s[i:end])
            i = end
            continue
        if ch == "$":
            # `$$` の 2 文字目は展開の開始ではない
            bare_dollar = not prev_bare
            out.append(ch)
            i += 1
            if s.startswith("$(", i - 1) and not s.startswith("$((", i - 1):
                stack.append("subst")
                depth.append(0)
                out.append("(")
                i += 1
                bare_dollar = False
            continue
        if ch == "'":
            stack.append("ansi" if prev_bare else "sq")
            emit("'", data=True)
            i += 1
            continue
        if ch == '"':
            stack.append("dq")
            emit('"', data=True)
            i += 1
            continue
        if ch == "`":
            if ctx == "bt":
                stack.pop()
            else:
                stack.append("bt")
            out.append("`")
            i += 1
            continue
        if ctx == "subst" and ch in "()":
            if ch == "(":
                depth[-1] += 1
            elif depth[-1] == 0:
                stack.pop()
                depth.pop()
            else:
                depth[-1] -= 1
            out.append(ch)
            i += 1
            continue
        if ch == "#" and (not out or out[-1][-1:] in _WORD_BREAK):
            while i < n and s[i] != "\n":
                i += 1
            continue
        if s.startswith("((", i) and (not out or out[-1][-1:] in _WORD_BREAK):
            end = s.find("))", i)
            end = n if end < 0 else end + 2
            out.append(s[i:end])
            i = end
            continue
        if s.startswith("<<<", i):  # here-string（ヒアドキュメントではない）
            out.append("<<<")
            i += 3
            continue
        if s.startswith("<<", i):
            j = i + 2
            dash = j < n and s[j] == "-"
            j += 1 if dash else 0
            while j < n and s[j] in " \t":
                j += 1
            k, word = j, []
            while k < n and s[k] not in _WORD_BREAK:
                if s[k] == "\\" and k + 1 < n:
                    word.append(s[k + 1])
                    k += 2
                    continue
                if s[k] in "'\"":
                    q = s[k]
                    e = s.find(q, k + 1)
                    e = n if e < 0 else e
                    word.append(s[k + 1:e])
                    k = e + 1
                    continue
                word.append(s[k])
                k += 1
            if word:
                pending.append(("".join(word), dash))
            out.append(s[i:k])
            i = k
            continue
        if ch == "\n" and pending:
            out.append(ch)
            pos = i + 1
            for word, dash in pending:
                p, found = pos, False
                while p <= n:
                    e = s.find("\n", p)
                    e = n if e < 0 else e
                    line = s[p:e]
                    if (line.lstrip("\t") if dash else line) == word:
                        found = True
                        pos = e  # 終端行の末尾（改行の手前）
                        break
                    if e >= n:
                        break
                    p = e + 1
                if not found:
                    break  # 終端なし: 以降は除かない
            pending = []
            i = pos if pos > i + 1 else i + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _gh_tokens(code: str) -> list:
    """`_shell_code` 済みの文字列を (token, is_op) の列にする（gh pr 判定専用。既存 `_segments` は無改変）。
    改行は区切りとして扱う。fd 番号付きリダイレクト（`2>&1`）の番号は除く。クォート不整合は素朴分割で fail-safe。"""
    s = _FD_RE.sub("", code).replace("\n", " ; ")
    try:
        lx = shlex.shlex(s, posix=True, punctuation_chars=_GH_PUNCT)
        lx.whitespace = " \t\r\n"
        lx.whitespace_split = True
        lx.commenters = ""  # コメントは _shell_code で bash の規則どおり除去済み
        toks = list(lx)
    except ValueError:
        toks = [t for t in re.split(r"([();<>|&`]+)|\s+", s) if t]
    return [(t, bool(t) and set(t) <= set(_GH_PUNCT)) for t in toks]


def _gh_pr_target(cmd: str):
    """`gh pr <verb> ...` をすべて検出して [(kind, ident, repo, ambiguous), ...] を返す（非該当は空）。
    cmd は生コマンド（改行を潰す前）。`gh` はコマンド中のどの位置でも検出する
    （then/do/{/!/リダイレクト・ラッパー越しでも取りこぼさないため）。gh 既定エイリアス `co` は checkout と同一視する
    （利用者定義のエイリアスは対象外＝計画書「設計上の限界」）。
    識別子（番号・URL・ブランチ名）は解釈せず gh へそのまま渡す。`-R/--repo`・`GH_REPO=` は照会側へ渡す。
    次は ambiguous（照会せず ask）: 表にないフラグ・位置引数が複数・識別子がなく gh の前に別コマンドがある
    （xargs 等で識別子が外から渡る）。"""
    toks = _gh_tokens(_shell_code(cmd))
    targets = []
    for idx, (tok, is_op) in enumerate(toks):
        if is_op or os.path.basename(tok) not in ("gh", "gh.exe"):
            continue
        in_backquote = sum(1 for t, op in toks[:idx] if op and t == "`") % 2 == 1
        # 同じ区切り内で gh より前にあるもの（GH_REPO= と、別コマンドの有無）
        k, env_repo, prefixed = idx - 1, None, False
        while k >= 0 and not (toks[k][1] and not re.search(r"[<>]", toks[k][0])):
            t = toks[k][0]
            if t.startswith("GH_REPO="):
                env_repo = t.split("=", 1)[1] or None
            elif not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
                prefixed = True
            k -= 1
        # gh より後ろ（区切り演算子まで）。リダイレクトは演算子と行き先を除く
        # プロセス置換 `<(`・クォートなしのコマンド置換 `$(`/`` ` `` が引数にあると識別子を確定できない → ambiguous
        args, j, subst = [], idx + 1, False
        while j < len(toks):
            t, op = toks[j]
            if op and t == "`" and in_backquote:
                break  # 閉じのバッククォート
            if op and ("(" in t or "`" in t):
                subst = True
                break
            if op and re.search(r"[<>]", t):
                j += 2
                continue
            if op:
                break
            if t != "$":
                args.append(t)
            j += 1
        repo = env_repo
        verb, seen_pr, i = None, False, 0
        while i < len(args):  # gh / pr の後ろ・verb の前のフラグ（`gh -R o/r pr --repo o/r merge`）
            a = args[i]
            if a in ("-R", "--repo"):
                repo = args[i + 1] if i + 1 < len(args) else repo
                i += 2
            elif a.startswith("--repo="):
                repo = a.split("=", 1)[1]
                i += 1
            elif a.startswith("-R") and len(a) > 2:
                repo = a[2:]
                i += 1
            elif a.startswith("-"):
                i += 1
            elif not seen_pr:
                if a == "co":  # gh 既定エイリアス `co: pr checkout`
                    verb = "checkout"
                    i += 1
                    break
                if a != "pr":
                    break
                seen_pr = True
                i += 1
            else:
                verb = a
                i += 1
                break
        spec = _GH_PR_SPECS.get(verb)
        if not spec:
            continue  # view/checks/diff/list/close/comment は対象外
        kind, vlong, vshort, blong, bshort = spec
        rest = args[i:]
        positionals, approve, ambiguous, j = [], False, False, 0
        while j < len(rest):
            a = rest[j]
            if a == "--":
                positionals += rest[j + 1:]
                break
            if a.startswith("--"):
                name, eq, val = a.partition("=")
                if name in vlong:
                    if not eq:
                        val = rest[j + 1] if j + 1 < len(rest) else ""
                        j += 1
                    if name == "--repo" and val:
                        repo = val
                elif name in blong:
                    if name == "--approve" and not (eq and val.lower() in ("false", "0")):
                        approve = True
                else:
                    ambiguous = True
            elif a.startswith("-") and len(a) > 1:
                cluster = a[1:]
                for c, ch in enumerate(cluster):
                    if ch in vshort:
                        val = cluster[c + 1:]
                        if not val:
                            val = rest[j + 1] if j + 1 < len(rest) else ""
                            j += 1
                        if ch == "R" and val:
                            repo = val
                        break
                    if ch in bshort:
                        if kind == "approve" and ch == "a":
                            approve = True
                        continue
                    ambiguous = True
                    break
            else:
                positionals.append(a)
            j += 1
        # 識別子なし＝カレントブランチの PR。照会は hook の作業ディレクトリで走るため、
        # gh の前に別コマンド（xargs 等）や cd/pushd があると実際の対象と食い違い得る → ask
        moved = any(not op and t in ("cd", "pushd") for t, op in toks[:idx])
        # 引用符の外のブレース展開（`{x,257}`）は bash が複数の語に展開するため、値と識別子の対応を確定できない
        braced = any(re.search(r"\{[^{}]*,[^{}]*\}", a) for a in rest)
        if subst or braced or len(positionals) > 1 or (not positionals and (prefixed or moved)):
            ambiguous = True
        if kind == "approve":  # ambiguous 判定の後に評価する（位置引数の異常で ask を消さない）
            if not approve and not ambiguous:
                continue  # review --comment / --request-changes は対象外
            kind = "ask"
        targets.append((kind, positionals[0] if positionals else None, repo, ambiguous))
    return targets


def _mcp_pr_target(tool_name: str, tool_input: dict):
    """対象 MCP ツールなら (kind, ident, repo) を返す。非該当は None。
    create_pull_request_review は event=APPROVE のときのみ対象にする。
    キー名は対象 3 ツールのスキーマ実測値: owner / repo / pull_number（スネークケース・全て required）。
    別実装の MCP サーバに備えてキャメルケースも読むが、正は snake_case。"""
    if tool_name in _MCP_PR_BLOCK_TOOLS:
        kind = "block"
    elif tool_name in _MCP_PR_ASK_TOOLS:
        if tool_name.endswith("create_pull_request_review") and \
                str(tool_input.get("event", "")).upper() != "APPROVE":
            return None
        kind = "ask"
    else:
        return None
    num = tool_input.get("pull_number")
    if num is None:
        num = tool_input.get("pullNumber")
    owner = tool_input.get("owner")
    repo = tool_input.get("repo")
    ident = str(num) if num is not None else None
    full = f"{owner}/{repo}" if owner and repo else None
    return kind, ident, full


def _cross_decision(kind: str, ident, repo, require_ident: bool = False):
    """cross-repo 判定に応じて ("block", 理由) / ("ask", 理由) / None（素通し）を返す。判定不能は ask（fail-safe）。
    require_ident=True（MCP 経路）で識別子が取れない場合は照会せず ask する。
    MCP はカレントブランチという概念を持たず、ident=None のまま照会すると
    「別の PR（カレントブランチの PR）を検査して素通しする」誤判定になり得るため。"""
    if require_ident and not ident:
        return ("ask", "対象 PR の番号を特定できませんでした（tool_input に pull_number がない）。"
                       "外部（fork）由来の PR でないか確認してください。")
    cross, head = _pr_is_cross_repo(ident, repo)
    label = f"PR {ident}" if ident else "カレントブランチの PR"
    origin = f"（head: {head}）" if head else ""
    if cross is None:
        return ("ask", f"{label} が自前のものか判定できませんでした（gh 照会失敗/タイムアウト）。"
                       f"外部（fork）由来の PR でないか確認してください。")
    if cross is False:
        return None  # 自前 PR → 従来どおり素通し
    if kind == "block":
        return ("block",
                f"{label} は fork（外部リポジトリ）由来です{origin}。外部からのコード寄稿は受け付けていません"
                f"（CONTRIBUTING.md）。マージ・checkout せず、方針コメント付きで close してください。"
                f"中身の確認は gh pr diff / gh pr view で行えます（checkout すると相手の .claude/ と hook が"
                f"次の操作で実行されます）。どうしても必要なら DANGER_OK=1 を前置してください。")
    return ("ask", f"{label} は fork（外部リポジトリ）由来です{origin}。取り込み方向の操作になります。"
                   f"CONTRIBUTING.md の方針（外部からのコード寄稿は受け付けない）を確認してください。")


def _guard_cross_repo(kind: str, ident, repo, raw: str, require_ident: bool = False):
    """単一対象（MCP 経路）の判定を適用する。
    注: `_ask()` / `_block()` は内部で sys.exit する（呼び出し後は戻らない）。"""
    d = _cross_decision(kind, ident, repo, require_ident)
    if d and d[0] == "block":
        _block(d[1], raw)
    if d:
        _ask(d[1])


def _guard_gh_pr_targets(targets: list, raw: str):
    """Bash 経路で検出した全 `gh pr` 対象を判定する。1 件でも fork への block 種別があれば block、
    それ以外に ask 理由が 1 件でもあれば ask（先頭の自前 PR で後続の fork PR を見逃さないため）。"""
    asks = []
    for kind, ident, repo, ambiguous in targets:
        if ambiguous:
            asks.append("gh pr の対象 PR を一意に特定できませんでした（未知のフラグ・位置引数が複数・"
                        "識別子なしで前に別コマンドや cd がある）。外部（fork）由来の PR でないか確認してください。")
            continue
        d = _cross_decision(kind, ident, repo)
        if d and d[0] == "block":
            _block(d[1], raw)
        if d:
            asks.append(d[1])
    # 安全網: 判定しきれない「gh pr の取り込み系操作の記述」が残っていれば ask
    if _gh_coarse_count(_shell_code(raw, keep_quoted=False)) != len(targets):
        asks.append("判定しきれない形で gh pr の取り込み系操作（merge/checkout/ready/edit/update-branch/"
                    "review --approve）が書かれています（クォート内・置換内・未知の書き方など）。"
                    "外部（fork）由来の PR への操作でないか確認してください。")
    if asks:
        _ask(asks[0])


def main():
    data = _load()
    tool_name = data.get("tool_name")
    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        # I095: 別 worktree 配下への書込は禁止（パス未取得/境界不能も fail-safe で block）
        path = _edit_path(data)
        x = _cross_worktree(path) if path else None
        if x is True or x is None:
            _block_cross_worktree("編集", path)
        if tool_name in ("Edit", "Write"):
            _check_edit_write(data)  # 既存の高リスク ask は Edit/Write のみ（現状維持）
        sys.exit(0)
    # I146: MCP 経由の PR 取り込み操作（Bash を通らない経路）
    if str(tool_name or "").startswith("mcp__github__"):
        t = _mcp_pr_target(tool_name, data.get("tool_input") or {})
        if t:
            _guard_cross_repo(t[0], t[1], t[2], tool_name, require_ident=True)
        sys.exit(0)
    if tool_name != "Bash":
        sys.exit(0)
    tool_input = data.get("tool_input") or {}
    raw = tool_input.get("command") or ""
    if not isinstance(raw, str) or not raw.strip():
        sys.exit(0)

    cmd = _norm(raw)
    danger_ok = raw.lstrip().startswith("DANGER_OK=1 ")

    # hard-block
    if re.search(r"\brm\s+-rf\s+/\b", cmd, re.I):
        _block("rm -rf / is forbidden", raw)
    if re.search(r"\bmkfs(\.|\s)", cmd, re.I):
        _block("mkfs is forbidden", raw)
    if re.search(r"\bdd\b", cmd, re.I):
        _block("dd is forbidden", raw)
    if re.search(r"\bshred\b", cmd, re.I):
        _block("shred is forbidden", raw)

    # I095: worktree 横断書込のブロック（DANGER_OK でも解除しない＝danger_ok ゲートの外）。
    _wt_targets = _bash_write_targets(cmd)
    for _tgt in _wt_targets:
        x = _cross_worktree(_tgt)
        if x is True or x is None:
            _block_cross_worktree("Bash 書込", _tgt)
    # no silent caps: 絶対パス宛先を抽出できないが cd/変数/ラッパー越しで別 worktree を
    # 指し得る経路のみ限界を明示（読み取り・単純な相対書込では誤警告しない）。
    if not _wt_targets and _bash_uncovered_risk(cmd):
        print("[guard] worktree ガードは絶対パス宛先のみ検査します（cd/変数展開越しの宛先は非対象）",
              file=sys.stderr)

    if not danger_ok:
        # push to a protected branch by name/refspec — danger-op:
        # release/hotfix のローカル push のみ DANGER_OK=1 で解除可（danger-ops.md 枠組み）。
        # 明示名・引数なし(保護ブランチ上)・refspec <src>:develop|main・+develop・
        # refs/heads/develop・HEAD:refs/heads/main を宛先正規化＋完全一致で一括網羅。
        dest = _push_protected_target(cmd)
        if dest:
            _block(
                f"push to protected branch '{dest}' is forbidden "
                f"(release/hotfix は計画書明記＋danger-approved＋DANGER_OK=1 のみ)",
                raw,
            )

        # bulk push of all refs (includes protected) — danger-op
        if re.search(r"\bgit\s+push\b.*\s(--all|--mirror)\b", cmd, re.I):
            _block("git push --all/--mirror pushes all refs incl. protected; requires DANGER_OK=1", raw)

        # vestigial --repo flag sets the remote without a positional arg, which evades the
        # positional-based protected detector → block outright (security-review/I080).
        if re.search(r"\bgit\s+push\b.*\s--repo(\s|=)", cmd, re.I):
            _block("git push --repo can evade protected-branch detection and is unused here; requires DANGER_OK=1", raw)

        # force push to non-protected (protected 宛先は上で先に block)
        # I083: pure _segments ベース。-f/-uf/--force-with-lease/--force-if-includes・複合コマンドに頑健。
        # 旧 re.match(r"git\s+push\b.*--force") の潜在誤 block（後続 echo の --force まで貪欲一致）も根治。
        if _push_has_force(cmd):
            _block("force push requires DANGER_OK=1", raw)

        # reset --hard requires explicit ack
        if re.search(r"\bgit\s+reset\b.*--hard\b", cmd, re.I):
            _block("git reset --hard requires DANGER_OK=1", raw)

        # docker volume wipe requires explicit ack
        if re.search(r"\bdocker(\s+compose|\-compose)\s+down\b.*\s(-v|--volumes)\b", cmd, re.I):
            _block("docker compose down -v/--volumes requires DANGER_OK=1", raw)

        # rm -rf anywhere requires explicit ack
        if re.search(r"\brm\s+-rf\b", cmd, re.I):
            _block("rm -rf requires DANGER_OK=1", raw)

        # git checkout/restore on a file with uncommitted worktree changes would discard them
        target = _git_revert_target_on_dirty(cmd)
        if target:
            _block(
                f"git checkout/restore would discard uncommitted changes in '{target}'. "
                f"Edit で戻すか、どうしても必要なら DANGER_OK=1 を前置してください。",
                raw,
            )

        # heuristics for psql -c "...": block destructive SQL unless explicit ack
        m = re.search(r"\bpsql\b.*\s-c\s+\"([^\"]+)\"", raw, re.I)
        if m:
            sql = _norm(m.group(1)).lower()
            if " update " in sql and " where " not in sql:
                _block("UPDATE without WHERE is forbidden (requires DANGER_OK=1 + plan/rollback)", raw)
            if " delete from " in sql and " where " not in sql:
                _block("DELETE without WHERE is forbidden (requires DANGER_OK=1 + plan/rollback)", raw)
            if any(k in sql for k in [" drop ", " truncate ", " alter table "]):
                _block("destructive SQL requires DANGER_OK=1", raw)

        # I083 欠陥1: 動的・不透明な宛先の push は静的に安全と断言できないため ask に degrade する。
        # 全 hard-block の後に置くことで、rm -rf 等の同居 danger-op を ask で先食いしない
        # （静的 protected/force は上で先に exit 2 block 済み・DANGER_OK=1 時はこのブロックに来ない）。
        # I146: cross-repo PR ガード。既存 hard-block の後に置き、danger-op 同居時に
        # ask で先食いしない（I083 で確立した順序方針を踏襲）。
        # 改行を区切りとして扱うため _norm 前の生コマンドを渡す
        _guard_gh_pr_targets(_gh_pr_target(raw) or [], raw)

        if _push_is_dynamic(cmd):
            _ask("動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。")

    sys.exit(0)

if __name__ == "__main__":
    main()
