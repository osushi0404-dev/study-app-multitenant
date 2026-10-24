#!/usr/bin/env bash
# I187: Playwright MCP の設定（.mcp.json）と、その操作の許可・見張りの登録（.claude/settings.json）を決定論検証する。
# 実行: bash scripts/claude/tests/test_i187_frontend_verify_config.sh
# ケースは docs/tests/open/I187_auto_test.md の TC-03 ①〜⑦ と対応する。
# 別のファイルに当てるとき: MCP_JSON=... SETTINGS_JSON=... bash scripts/claude/tests/test_i187_frontend_verify_config.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
MCP_JSON="${MCP_JSON:-$REPO_ROOT/.mcp.json}"
SETTINGS_JSON="${SETTINGS_JSON:-$REPO_ROOT/.claude/settings.json}"

python3 - "$MCP_JSON" "$SETTINGS_JSON" <<'PY'
import json
import sys

mcp_path, settings_path = sys.argv[1], sys.argv[2]
passed = failed = 0


def ck(name, ok):
    global passed, failed
    if ok:
        print(f"PASS {name}")
        passed += 1
    else:
        print(f"FAIL {name}")
        failed += 1


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print(f"FAIL 読めない: {path}: {e}")
        return None


mcp = load(mcp_path) or {}
settings = load(settings_path) or {}
servers = mcp.get("mcpServers", {})
pw = servers.get("playwright", {})

# ① playwright の起動方法（計画 5-2-1 の 12 語と順番まで一致）
EXPECTED_ARGS = [
    "-y", "@playwright/mcp@0.0.83",
    "--browser", "chromium",
    "--headless",
    "--isolated",
    "--allowed-origins", "http://localhost:*;http://127.0.0.1:*",
    "--output-dir", ".evidence",
    "--secrets", "e2e/.env.e2e",
]
ck("①a playwright の command が npx", pw.get("command") == "npx")
ck("①b playwright の args が計画と完全一致", pw.get("args") == EXPECTED_ARGS)

# ② github は変えていない
gh = servers.get("github", {})
ck("② github の args が変わっていない",
   gh.get("args") == ["-y", "@modelcontextprotocol/server-github@2025.4.8"])

allow = settings.get("permissions", {}).get("allow", [])
deny = settings.get("permissions", {}).get("deny", [])

# ③ 許可する 20 個
ALLOWED = [
    "browser_navigate", "browser_navigate_back", "browser_snapshot", "browser_find",
    "browser_take_screenshot", "browser_click", "browser_hover", "browser_drag",
    "browser_type", "browser_fill_form", "browser_select_option", "browser_press_key",
    "browser_wait_for", "browser_handle_dialog", "browser_tabs", "browser_resize",
    "browser_emulate_media", "browser_close", "browser_console_messages",
    "browser_network_requests",  # 複数形 = 通信の一覧だけ
]
missing = [t for t in ALLOWED if f"mcp__playwright__{t}" not in allow]
ck(f"③ 許可する 20 個がすべて allow にある（不足: {missing}）", len(ALLOWED) == 20 and not missing)

# ④ 許可しないもの（単数形 browser_network_request = ヘッダー・本文を返す。複数形と 1 文字違い）
NOT_ALLOWED = [
    "browser_run_code_unsafe", "browser_evaluate", "browser_file_upload", "browser_drop",
    "browser_network_request",
]
present = [t for t in NOT_ALLOWED if f"mcp__playwright__{t}" in allow]
ck(f"④a 許可しない 5 個が allow に無い（あった: {present}）", not present)
wide = [r for r in allow if r.startswith("mcp__playwright") and r[len("mcp__playwright__"):] not in ALLOWED]
ck(f"④b サーバー全体・ワイルドカードの許可が無い（あった: {wide}）", not wide)

# ⑤ Bash の許可
ck("⑤a docker compose port が allow にある", "Bash(docker compose port *)" in allow)
# e2e の実行は、依存先の backend を今の環境で作り直すため、回数制限を切るときは実行コマンド自体に前置する（計画変更記録 2）
E2E_ALLOW = [
    f"Bash({pre}docker compose --profile e2e run --rm e2e{tail})"
    for pre in ("", "RATELIMIT_ENABLE=false ")
    for tail in ("", " npx playwright test *")
]
missing5 = [r for r in E2E_ALLOW if r not in allow]
ck(f"⑤b e2e サービスの実行（既定コマンドと npx playwright test・前置きなし・あり）が allow にある（無い: {missing5}）", not missing5)
# 見張りは npm test・npx jest・e2e-init などを判断せずに通すため、末尾を何でも受ける許可は置かない（敵対的レビュー 1 周目）
wide5 = [r for r in allow if "run --rm e2e" in r and r not in E2E_ALLOW]
ck(f"⑤b' e2e の実行で上の 4 つ以外の許可が無い（あった: {wide5}）", not wide5)
ck("⑤c 効かない RATELIMIT_ENABLE=false docker compose up の許可が無い",
   "Bash(RATELIMIT_ENABLE=false docker compose up *)" not in allow)

# ⑥ .env.e2e の読み取り禁止が残っている
ck("⑥ deny の Read(**/.env.e2e) が残っている", "Read(**/.env.e2e)" in deny)

# ⑦ MCP の書き先の見張り（/security-review）
GUARD_CMD = 'python3 "$CLAUDE_PROJECT_DIR"/scripts/claude/hooks/pretooluse_guard.py'
entries = settings.get("hooks", {}).get("PreToolUse", [])
ok7 = any(
    e.get("matcher") == "mcp__playwright__.*"
    and any(h.get("type") == "command" and h.get("command") == GUARD_CMD for h in e.get("hooks", []))
    for e in entries
)
ck("⑦ PreToolUse に matcher mcp__playwright__.* で見張りが登録されている", ok7)

print(f"---\npass={passed} fail={failed}")
sys.exit(0 if failed == 0 else 1)
PY
