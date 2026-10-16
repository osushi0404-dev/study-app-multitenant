#!/usr/bin/env python3
import functools
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

# --- I174: 危険操作・外部送信の判定（書き出しに依存せず「実際に何をするか」で判定する） ---
# 判定はトークン列（_segments）に対して行い、コマンド行の文字列全体には当てない
# （grep の検索文字列・ヒアドキュメント本文への誤反応を防ぐ）。
_MAX_WRAP_DEPTH = 3                 # sh -c の入れ子を展開する深さの上限
_MAX_SCRIPT_BYTES = 1_000_000       # 中身を読む実行ファイルの大きさの上限
# コンテナ内パス → リポジトリ相対パス（docker-compose.yml の backend/celery の volumes に合わせる。
# マウントを変えたらここも更新する）。長い接頭辞から順に照合する。
_CONTAINER_MOUNTS = (("/app/docs/", "docs/"), ("/app/", "backend/"))
_CONTAINER_WORKDIR = "/app/"
_DOCKER_CLIS = ("docker", "docker-compose")
_PYTHON_RE = re.compile(r"^python(\d+(\.\d+)?)?$")
_MANAGE_DB_WIPE = ("flush", "sqlflush", "reset_db")
_MIGRATE_VALUE_OPTS = ("--database", "--settings", "--pythonpath", "-v", "--verbosity")
_REDIRECT_RE = re.compile(r"^\d*[<>]|&")   # 2>&1・>out・<in などの位置引数でないトークン

# 実行される Python コードに対する判定（manage.py shell -c / python -c / 実行ファイルの中身）
_CODE_DANGER = (
    (r"\.delete\(", "データ削除（.delete()）"),
    (r"\bobjects\b[^;\n]*\.update\(", "QuerySet の一括更新（.update()）"),
    (r"\.bulk_update\(", "一括更新（bulk_update）"),
    (r"call_command\(\s*['\"](flush|sqlflush|reset_db)['\"]", "管理コマンドによる DB 全消去"),
    (r"call_command\(\s*['\"]migrate['\"][^)]*['\"]zero['\"]", "管理コマンドによるマイグレーション巻き戻し"),
)
_CODE_EXTERNAL = (
    (r"\b(send_mail|send_mass_mail|mail_admins|mail_managers)\(", "メール送信"),
    (r"\bEmail(Message|MultiAlternatives)\b", "メール送信"),
    (r"\.(delay|apply_async)\(", "celery タスクの起動"),
    (r"\bsend_study_reminders_task\b", "学習リマインダー送信タスク"),
    (r"auth/register/", "登録 API（確認メールを送信）"),
    (r"auth/password-reset/", "パスワード再設定依頼 API（メールを送信）"),
    (r"\bAIQuestionGenerator\b|problems/generate_(ai|adaptive)/|\bopenai\.", "OpenAI への送信"),
)

_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

def _strip_env(toks: list) -> list:
    """先頭の環境変数の代入（`FOO=1 cmd ...` の `FOO=1`）を除いたトークン列を返す。"""
    i = 0
    while i < len(toks) and _ENV_ASSIGN_RE.match(toks[i]):
        i += 1
    return toks[i:]

def _is_container_seg(toks: list) -> bool:
    """docker / docker-compose の exec・run でコンテナ内に渡すセグメントなら True。"""
    toks = _strip_env(toks)
    return bool(toks) and os.path.basename(toks[0]) in _DOCKER_CLIS and \
        ("exec" in toks or "run" in toks)

def _expand_segments(cmd: str, in_container: bool = False, depth: int = 0) -> list:
    """(トークン列, コンテナ内か) のリストを返す。sh/bash -c と eval の中身も再帰で展開する。"""
    out = []
    for toks in _segments(cmd):
        ctr = in_container or _is_container_seg(toks)
        out.append((toks, ctr))
        if depth >= _MAX_WRAP_DEPTH:
            continue
        for i, t in enumerate(toks):
            if os.path.basename(t) in _WRAP_SHELLS and i + 2 < len(toks) and toks[i + 1] == "-c":
                out += _expand_segments(toks[i + 2], ctr, depth + 1)
        head = _strip_env(toks)
        if head and head[0] == "eval" and len(head) > 1:
            out += _expand_segments(" ".join(head[1:]), ctr, depth + 1)
    return out

def _opt_value(toks: list, names: tuple):
    """toks から `-c X` / `--command X` / `--command=X` 形式の値を返す（無ければ None）。"""
    for i, t in enumerate(toks):
        if t in names and i + 1 < len(toks):
            return toks[i + 1]
        for n in names:
            if n.startswith("--") and t.startswith(n + "="):
                return t[len(n) + 1:]
    return None

def _stdin_file(toks: list):
    """`< FILE` / `<FILE` の FILE を返す（ヒアドキュメント `<<` は除く）。無ければ None。"""
    for i, t in enumerate(toks):
        if t == "<" and i + 1 < len(toks):
            return toks[i + 1]
        if t.startswith("<") and not t.startswith("<<") and len(t) > 1:
            return t[1:]
    return None

def _sql_is_destructive(sql: str) -> bool:
    """SQL（; 区切りの複数文可）に DROP/TRUNCATE/ALTER TABLE/WHERE なし UPDATE・DELETE があれば True。"""
    for stmt in sql.split(";"):
        s = stmt.lower()
        if re.search(r"\b(drop|truncate)\b", s) or re.search(r"\balter\s+table\b", s):
            return True
        has_where = re.search(r"\bwhere\b", s)
        if re.search(r"\bupdate\b", s) and re.search(r"\bset\b", s) and not has_where:
            return True
        if re.search(r"\bdelete\s+from\b", s) and not has_where:
            return True
    return False

def _code_reasons(code: str) -> tuple:
    """実行される Python コードの (危険操作の理由, 外部送信の理由) を返す。"""
    danger = [why for pat, why in _CODE_DANGER if re.search(pat, code)]
    if any(_sql_is_destructive(lit) for _q, lit in re.findall(r"(['\"])(.*?)\1", code, re.S)):
        danger.append("文字列中の破壊的 SQL")
    external = [why for pat, why in _CODE_EXTERNAL if re.search(pat, code)]
    return danger, external

def _resolve_exec_file(path: str, in_container: bool):
    """実行ファイルのホスト上のパスを返す。読み替えできなければ None。"""
    root = _current_worktree_root()
    if in_container:
        p = path if path.startswith("/") else _CONTAINER_WORKDIR + path
        for cpre, hpre in _CONTAINER_MOUNTS:
            if p.startswith(cpre) and root:
                return os.path.join(root, hpre + p[len(cpre):])
        return None
    return os.path.abspath(path)

def _exec_files(toks: list, in_container: bool) -> list:
    """セグメントで実行されるファイル（中身を判定する対象）を (パス, コンテナ内か) で返す。"""
    files = []
    for i, t in enumerate(toks):
        base = os.path.basename(t)
        if base == "manage.py" and i + 1 < len(toks) and toks[i + 1] == "shell":
            f = _stdin_file(toks[i + 2:])
            if f:
                files.append((f, False))          # `<` はホストのシェルが処理する
        elif _PYTHON_RE.match(base):
            rest = toks[i + 1:]
            if "-m" in rest or "-c" in rest:
                continue
            pos = [a for a in rest if not a.startswith("-")]
            if pos and pos[0].endswith(".py"):
                files.append((pos[0], in_container))
        elif in_container and base in ("sh", "bash") and "-c" not in toks[i + 1:]:
            pos = [a for a in toks[i + 1:] if not a.startswith("-")]
            if pos:
                files.append((pos[0], True))
    return files

@functools.lru_cache(maxsize=None)
def _file_reasons(path: str, in_container: bool) -> tuple:
    """実行ファイルの中身の (危険操作の理由, 外部送信の理由)。読めなければ stderr に出して ([], [])。
    危険操作と外部送信の両方の判定から呼ばれるため、1 回の実行の中では結果を使い回す。"""
    if os.path.basename(path) == "manage.py":
        return [], []
    host = _resolve_exec_file(path, in_container)
    root = _current_worktree_root()
    if host and root and os.path.realpath(host).startswith(
            os.path.join(os.path.realpath(root), "scripts", "claude") + os.sep):
        return [], []                             # ハーネス自身のコード（判定パターンを文字列で含む）
    try:
        if not host or os.path.getsize(host) > _MAX_SCRIPT_BYTES:
            raise OSError("unresolvable or too large")
        with open(host, encoding="utf-8") as fh:
            code = fh.read()
    except (OSError, UnicodeDecodeError):
        print(f"[guard] 実行ファイルの中身を確認できませんでした（判定を省略）: {path}", file=sys.stderr)
        return [], []
    d, e = _code_reasons(code)
    return [f"{why}（{path}）" for why in d], [f"{why}（{path}）" for why in e]

def _rm_rf_targets(cmd: str) -> list:
    """再帰＋強制の rm の対象トークンを返す（該当なしは []）。ヒアドキュメント本文（<< 以降）は見ない。"""
    targets = []
    for toks, _ctr in _expand_segments(cmd.split("<<", 1)[0]):
        for i, t in enumerate(toks):
            if os.path.basename(t) != "rm":
                continue
            args = toks[i + 1:]
            flags = [a for a in args if a.startswith("-")]
            short = "".join(a[1:] for a in flags if not a.startswith("--"))
            rec = any(c in short for c in "rR") or "--recursive" in flags
            force = "f" in short or "--force" in flags
            if rec and force:
                targets += [a for a in args if not a.startswith("-")]
    return targets

def _segment_danger(toks: list, in_container: bool) -> list:
    """1 セグメントのコンテナ内／DB 系の危険操作の理由（書き出しに依存しない）。"""
    reasons = []
    for i, t in enumerate(toks):
        base = os.path.basename(t)
        rest = toks[i + 1:]
        if base == "manage.py" and rest:
            sub, args = rest[0], rest[1:]
            if sub in _MANAGE_DB_WIPE:
                reasons.append(f"DB 全消去（manage.py {sub}）requires DANGER_OK=1")
            elif sub == "loaddata":
                reasons.append("既存データの上書き（manage.py loaddata）requires DANGER_OK=1")
            elif sub == "migrate":
                pos, skip = [], False
                for a in args:
                    if skip:
                        skip = False
                        continue
                    if a in _MIGRATE_VALUE_OPTS:
                        skip = True
                    elif not a.startswith("-") and not _REDIRECT_RE.search(a):
                        pos.append(a)
                if len(pos) >= 2:
                    reasons.append("マイグレーションの巻き戻し（migrate <app> <移動先>）requires DANGER_OK=1")
            elif sub == "shell":
                code = _opt_value(args, ("-c", "--command"))
                if code:
                    reasons += [f"{why}（manage.py shell）requires DANGER_OK=1" for why in _code_reasons(code)[0]]
        elif _PYTHON_RE.match(base) and "-c" in rest:
            code = _opt_value(rest, ("-c",))
            if code:
                reasons += [f"{why}（python -c）requires DANGER_OK=1" for why in _code_reasons(code)[0]]
        elif base == "psql":
            sql = _opt_value(rest, ("-c", "--command"))
            if sql and _sql_is_destructive(sql):
                reasons.append("destructive SQL requires DANGER_OK=1")
            if _opt_value(rest, ("-f", "--file")) or _stdin_file(rest):
                reasons.append("ダンプ・SQL ファイルの流し込み（psql -f / <）requires DANGER_OK=1")
        elif base == "dropdb":
            reasons.append("データベースの削除（dropdb）requires DANGER_OK=1")
        elif base == "pg_restore" and ("--clean" in rest or "-c" in rest):
            reasons.append("既存データを消して復元（pg_restore --clean）requires DANGER_OK=1")
        elif base == "redis-cli" and any(a.upper() in ("FLUSHALL", "FLUSHDB") for a in rest):
            reasons.append("Redis の全消去（FLUSHALL/FLUSHDB）requires DANGER_OK=1")
    return reasons

def _danger_reasons(cmd: str) -> list:
    """DANGER_OK=1 で人の承認に切り替わる危険操作の理由を集める（該当なしは []）。"""
    reasons = []
    dest = _push_protected_target(cmd)
    if dest:
        reasons.append(f"push to protected branch '{dest}' is forbidden "
                       f"(release/hotfix は計画書明記＋danger-approved＋DANGER_OK=1 のみ)")
    if re.search(r"\bgit\s+push\b.*\s(--all|--mirror)\b", cmd, re.I):
        reasons.append("git push --all/--mirror pushes all refs incl. protected; requires DANGER_OK=1")
    # vestigial --repo flag sets the remote without a positional arg, which evades the
    # positional-based protected detector（security-review/I080）。
    if re.search(r"\bgit\s+push\b.*\s--repo(\s|=)", cmd, re.I):
        reasons.append("git push --repo can evade protected-branch detection and is unused here; requires DANGER_OK=1")
    # I083: pure _segments ベース。protected 宛先は上で先に理由化済み。
    if _push_has_force(cmd):
        reasons.append("force push requires DANGER_OK=1")
    if re.search(r"\bgit\s+reset\b.*--hard\b", cmd, re.I):
        reasons.append("git reset --hard requires DANGER_OK=1")
    if re.search(r"\bdocker(\s+compose|\-compose)\s+down\b.*\s(-v|--volumes)\b", cmd, re.I):
        reasons.append("docker compose down -v/--volumes requires DANGER_OK=1")
    if _rm_rf_targets(cmd):
        reasons.append("rm -rf requires DANGER_OK=1")
    target = _git_revert_target_on_dirty(cmd)
    if target:
        reasons.append(f"git checkout/restore would discard uncommitted changes in '{target}'. "
                       f"Edit で戻すか、どうしても必要なら DANGER_OK=1 を前置してください。")
    for toks, ctr in _expand_segments(cmd):
        reasons += _segment_danger(toks, ctr)
        for path, fctr in _exec_files(toks, ctr):
            reasons += [f"{why} requires DANGER_OK=1" for why in _file_reasons(path, fctr)[0]]
    return list(dict.fromkeys(reasons))           # 重複（入れ子展開で同じ理由）を順序を保って除く

def _external_reasons(cmd: str) -> list:
    """外部送信（メール・celery の起動・OpenAI）の理由を集める。実行されるコードと構造だけを見る。"""
    reasons = []
    for toks, ctr in _expand_segments(cmd):
        for i, t in enumerate(toks):
            base = os.path.basename(t)
            rest = toks[i + 1:]
            if base == "manage.py" and rest[:1] == ["generate_ai_problems"]:
                reasons.append("OpenAI への送信（manage.py generate_ai_problems）")
            elif base == "manage.py" and rest[:1] == ["shell"]:
                code = _opt_value(rest[1:], ("-c", "--command"))
                if code:
                    reasons += _code_reasons(code)[1]
            elif _PYTHON_RE.match(base) and "-c" in rest:
                code = _opt_value(rest, ("-c",))
                if code:
                    reasons += _code_reasons(code)[1]
            elif base == "celery" and "call" in rest:
                reasons.append("celery タスクの起動（celery call）")
        for path, fctr in _exec_files(toks, ctr):
            reasons += _file_reasons(path, fctr)[1]
    return list(dict.fromkeys(reasons))

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
    if tool_name != "Bash":
        sys.exit(0)
    tool_input = data.get("tool_input") or {}
    raw = tool_input.get("command") or ""
    if not isinstance(raw, str) or not raw.strip():
        sys.exit(0)

    danger_ok = raw.lstrip().startswith("DANGER_OK=1 ")
    # I174: 判定は DANGER_OK=1 を外したコマンドで行う（先頭トークンで判定する eval / sh -c 等を
    # DANGER_OK=1 の前置で見逃さないため。DANGER_OK=1 の扱いは danger_ok で別に決める）。
    cmd = re.sub(r"^DANGER_OK=1\s+", "", _norm(raw))

    # hard-block（DANGER_OK=1 でも解除しない）。I174: rm -rf はルート（/・/*）だけをここで止め、
    # それ以外の rm -rf は下の危険操作（DANGER_OK=1 で人の承認）で扱う。
    if any(t in ("/", "/*") for t in _rm_rf_targets(cmd)):
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

    # 危険操作（danger-ops.md）。I174: DANGER_OK=1 は素通しではなく人の承認（ask）に切り替える。
    # settings.json の ask ルールに頼らず、決定論的に人の承認を求める（CLAUDE.md 絶対ルール 4）。
    reasons = _danger_reasons(cmd)
    if reasons:
        if danger_ok:
            _ask("DANGER_OK=1 付きの危険操作です。内容を確認して承認してください: " + " / ".join(reasons))
        _block(reasons[0], raw)

    # I174: 外部送信（メール・celery の起動・OpenAI）はデータを壊さないが外へ出るため人の確認にする。
    external = _external_reasons(cmd)
    if external:
        _ask("外部への送信を伴う操作です。確認してください: " + " / ".join(external))

    # I083 欠陥1: 動的・不透明な宛先の push は静的に安全と断言できないため ask に degrade する。
    # 危険操作の判定の後に置くことで、rm -rf 等の同居 danger-op を ask で先食いしない。
    # I174: DANGER_OK=1 でも ask にする（宛先が保護ブランチに解決し得るため）。
    if _push_is_dynamic(cmd):
        _ask("動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。")

    sys.exit(0)

if __name__ == "__main__":
    main()
