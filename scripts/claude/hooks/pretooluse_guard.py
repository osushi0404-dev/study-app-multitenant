#!/usr/bin/env python3
import json
import re
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

def main():
    data = _load()
    if data.get("tool_name") != "Bash":
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
