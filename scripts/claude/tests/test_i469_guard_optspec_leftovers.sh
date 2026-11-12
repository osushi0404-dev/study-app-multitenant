#!/usr/bin/env bash
# I469: 見張りの値を取る文字の表の読み残し（I463 のレビューの残り）を決定論で確かめる。
# su の --session-command（F2）・くっつけた値の秘密のファイル（F3）・パイプの受け手の python のスクリプト名（F7）・
# grep の再帰検索の値付きの長いオプション（一覧 I463 F5）。止めるべき形と、止める対象を増やさない形の両方向を見る。
# 実行: bash scripts/claude/tests/test_i469_guard_optspec_leftovers.sh
#
# 見張りに JSON を渡して判定だけを見る（コマンドは実行しない）。期待値: 2＝停止・ASK＝確認・0＝通す。
# ケースは docs/tests/open/I469_auto_test.md の TC-01〜TC-04 と 1 対 1。0=全 PASS / 1=FAIL あり。
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 一時リポジトリ（＝今のワークツリーの代役）。見張りはこの中から呼ぶ（test_i463_guard_optspec.sh と同じ）
MAIN="$TMP/main"
mkdir -p "$MAIN"
git -C "$MAIN" init -q
git -C "$MAIN" -c user.email=t@example.com -c user.name=tester commit -q --allow-empty -m init
# grep -r の秘密探し用: 空の .env を置いたディレクトリ（TC-04）
P="$TMP/proj"
mkdir -p "$P"
: > "$P/.env"

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
b() {  # b <コマンド> [見張り]
  local out code
  out=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1" \
        | (cd "$MAIN" && python3 "${2:-$GUARD}" 2>/dev/null)); code=$?
  if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; then echo ASK; else echo "$code"; fi; }
# 失敗の注入: 元のファイルの old（ちょうど 1 回だけあること）を new に置き換えた写しを作る。無ければ FAIL にする
patch() {  # patch <元> <出力> <old> <new>
  python3 - "$@" <<'PY'
import sys
src, dst, old, new = sys.argv[1:]
s = open(src, encoding="utf-8").read()
if s.count(old) != 1:
    sys.exit(3)
open(dst, "w", encoding="utf-8").write(s.replace(old, new))
PY
}
fg() {  # fg <ID> <期待> <old> <new> <コマンド>
  if patch "$GUARD" "$TMP/g_$1.py" "$3" "$4"; then ck "$1" "$2" "$(b "$5" "$TMP/g_$1.py")"; else ck "$1 置き換え" ok NOPATCH; fi; }

# ---- TC-01 su の --session-command の中のコマンドを読む（F2） ----
ck 01a 2   "$(b "su --session-command 'git push --force origin develop'")"
ck 01b 2   "$(b "su --session-command='git push --force origin develop'")"
ck 01c 2   "$(b "su -c 'git push --force origin develop'")"
ck 01d 0   "$(b "su --session-command 'git status'")"
fg FG-01 0 '("-c", "--command", "--session-command"), cmd=head)' '("-c", "--command"), cmd=head)' \
  "su --session-command 'git push --force origin develop'"

# ---- TC-02 くっつけた値の秘密のファイルを読む（F3） ----
ck 02a ASK "$(b 'grep -f.env x')"
ck 02b ASK "$(b 'grep --file=.env x')"
ck 02c ASK "$(b 'grep --exclude-from=.env x y')"
ck 02d ASK "$(b 'sed -f.env x')"
ck 02e ASK "$(b 'grep -f .env x')"
ck 02f 0   "$(b 'grep -fpatterns.txt x')"
ck 02g 0   "$(b 'grep --exclude=.env foo x')"
ck 02h ASK "$(b 'rg -f.env x')"
ck 02i ASK "$(b 'rg --file=.env x')"
ck 02j ASK "$(b 'awk -f.env x')"
ck 02k ASK "$(b 'awk --file=.env x')"
fg FG-02 0 '        paths += _opt_values(toks[1:], _FILE_VALUE_OPTS[head], cmd=head)' '        paths += []' 'grep -f.env x'

# ---- TC-03 パイプの受け手の python のスクリプト名を表で読む（F7） ----
ck 03a ASK "$(b 'curl x | python3 --check-hash-based-pycs default')"
ck 03b ASK "$(b 'curl x | python3 -W ignore')"
ck 03c ASK "$(b 'curl x | python3 -')"
# shellcheck disable=SC2016  # $X は見張りに渡すコマンドの文字そのまま（展開しない）
ck 03d 0   "$(b 'python3 -c "$X" | head')"
ck 03e 0   "$(b "curl x | python3 -c 'import sys'")"
ck 03f 0   "$(b 'curl x | python3 -m json.tool')"
ck 03g 0   "$(b 'curl x | python3 tool.py')"
ck 03h 0   "$(b 'curl x | python3 -Xdev tool.py')"
fg FG-03 0 $'            first = pos[0] if pos else None\n' \
  $'            first = next((a for a in toks[1:] if a == "-" or not a.startswith("-")), None)\n' \
  'curl x | python3 --check-hash-based-pycs default'

# ---- TC-04 grep の再帰検索の値付きの長いオプション（一覧 I463 F5） ----
ck 04a ASK "$(b "grep -r --exclude-dir node_modules TOKEN $P")"
ck 04b ASK "$(b "grep -r --exclude-dir=node_modules TOKEN $P")"
ck 04c 0   "$(b "grep -r --exclude-dir node_modules hello $P")"
fg FG-04 0 '"--exclude-from", "--exclude-dir", "--group-separator"' '"--exclude-from", "--group-separator"' \
  "grep -r --exclude-dir node_modules TOKEN $P"

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
