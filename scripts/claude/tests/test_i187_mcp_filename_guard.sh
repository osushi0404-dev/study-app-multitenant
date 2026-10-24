#!/usr/bin/env bash
# I187: Playwright MCP の操作がファイルを書ける先を .evidence/I###/ に限る見張りの判定を決定論検証する。
# 実行: bash scripts/claude/tests/test_i187_mcp_filename_guard.sh
# 期待値: 2 = 止める（exit 2）・0 = 通す。ケースは docs/tests/open/I187_auto_test.md の TC-25（F1〜F11）と対応する。
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# $1=見張り $2=操作名 $3=filename（空なら入力に入れない）
run() {
  python3 -c '
import json, sys
inp = {"url": "http://localhost:3000/"} if sys.argv[1].endswith("navigate") else {}
if sys.argv[2]:
    inp["filename"] = sys.argv[2]
print(json.dumps({"tool_name": sys.argv[1], "tool_input": inp}))' "$2" "$3" | python3 "$1" >/dev/null 2>&1
  echo $?
}

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

P=mcp__playwright__
ck "F1 .evidence/I187/ の画像"            0 "$(run "$GUARD" ${P}browser_take_screenshot .evidence/I187/login-a-1.png)"
ck "F2 ファイル名なし"                    0 "$(run "$GUARD" ${P}browser_take_screenshot '')"
ck "F3 backend/.env"                      2 "$(run "$GUARD" ${P}browser_take_screenshot backend/.env)"
ck "F4 .. で外へ出る"                     2 "$(run "$GUARD" ${P}browser_take_screenshot .evidence/I187/../../backend/.env)"
ck "F5 絶対パス"                          2 "$(run "$GUARD" ${P}browser_take_screenshot /tmp/x.png)"
ck "F6 イシューのフォルダなし"            2 "$(run "$GUARD" ${P}browser_take_screenshot .evidence/x.png)"
ck "F7 snapshot で settings.json"         2 "$(run "$GUARD" ${P}browser_snapshot .claude/settings.json)"
ck "F8 console_messages を .evidence へ"  0 "$(run "$GUARD" ${P}browser_console_messages .evidence/I187/console.txt)"
ck "F9 network_requests で .env.e2e"      2 "$(run "$GUARD" ${P}browser_network_requests e2e/.env.e2e)"
ck "F10 フォルダの入れ子"                 2 "$(run "$GUARD" ${P}browser_find .evidence/I187/sub/x.txt)"
ck "F11 navigate（ファイル名なし）"       0 "$(run "$GUARD" ${P}browser_navigate '')"

# false-green の確認: 見張りの複製から mcp__playwright__ の分岐を外すと F3 が素通し（0）になる
BROKEN="$TMP/guard_no_mcp_playwright.py"
sed 's/if str(tool_name or "").startswith("mcp__playwright__"):/if False:/' "$GUARD" > "$BROKEN"
ck "G1 複製に置換が入った"                YES "$( (! cmp -s "$GUARD" "$BROKEN") && echo YES || echo NO)"
ck "G2 分岐を外すと backend/.env が素通し" 0 "$(run "$BROKEN" ${P}browser_take_screenshot backend/.env)"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
