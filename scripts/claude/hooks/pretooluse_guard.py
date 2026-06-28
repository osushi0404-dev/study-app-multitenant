#!/usr/bin/env python3
import json
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
    if tool_name in ("Edit", "Write"):
        _check_edit_write(data)  # 高リスクなら ask、非該当は exit 0
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

    if not danger_ok:
        # force push requires explicit ack
        if re.match(r"git\s+push\b.*--force", cmd, re.I):
            _block("force push requires DANGER_OK=1", raw)

        # push to protected branches is forbidden
        if re.match(r"git\s+push\b.*\borigin\b\s+(develop|main)\b", cmd, re.I):
            _block("direct push to develop/main is forbidden", raw)

        # git push ... HEAD on develop/main is forbidden
        if re.match(r"git\s+push\b.*\bHEAD\b", cmd, re.I):
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip() in ("develop", "main"):
                    _block(
                        f"push via HEAD to protected branch '{result.stdout.strip()}' is forbidden",
                        raw
                    )
            except Exception:
                pass  # git が利用できない環境ではスキップ

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

    sys.exit(0)

if __name__ == "__main__":
    main()
