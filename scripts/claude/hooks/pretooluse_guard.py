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
    print(f"[guard] 別 worktree（{x_root}）への{kind}は禁止です。"
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
    # no silent caps: 書込語はあるが絶対パス宛先を抽出できない経路（cd/変数越し等）は限界を明示。
    if not _wt_targets and _has_write_intent(cmd):
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
        if _push_is_dynamic(cmd):
            _ask("動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。")

    sys.exit(0)

if __name__ == "__main__":
    main()
