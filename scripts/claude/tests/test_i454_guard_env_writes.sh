#!/usr/bin/env bash
# I454: 見張りの環境変数の表示（ps -A e の後退 F10・F11・F12）・コンテナの /tmp/ 以外への書き込み（くっつけた -t・
# sed の式の付着形・通す形の --opt=/絶対パス）・別ワークツリーへの書き込みの停止（書き先の見分け方を 1 つに）を決定論で確かめる。
# 実行: bash scripts/claude/tests/test_i454_guard_env_writes.sh
#
# 見張りに JSON を渡して判定だけを見る（コマンドは実行しない）。期待値: 2＝停止・ASK＝確認・0＝通す。
# ケースは docs/tests/open/I454_auto_test.md の TC-01〜TC-04 と 1 対 1。0=全 PASS / 1=FAIL あり。
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# TC-04 用: 一時リポジトリ（＝今のワークツリーの代役）に別ワークツリー W を作る（test_pretooluse_worktree_guard.sh と同じ）。
# 見張りはこの一時リポジトリの中から呼ぶ
MAIN="$TMP/main"
mkdir -p "$MAIN"
git -C "$MAIN" init -q
git -C "$MAIN" -c user.email=t@example.com -c user.name=tester commit -q --allow-empty -m init
git -C "$MAIN" branch -q other
W="$TMP/other-wt"
git -C "$MAIN" worktree add -q "$W" other

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
D='docker compose exec -T backend'

# ---- TC-01 環境変数をまとめて表示する形（F10・F11・F12） ----
ck 01a ASK "$(b 'ps -A e')"
ck 01b ASK "$(b 'ps -ef e')"
ck 01c ASK "$(b "$D ps -A e")"
ck 01d ASK "$(b 'ps -o pid e')"
ck 01e ASK "$(b 'ps -u root e')"
ck 01f 0   "$(b 'ps o etime')"
ck 01g 0   "$(b 'ps U user')"
ck 01h 0   "$(b 'ps --sort etime')"
ck 01i ASK "$(b 'declare +x')"
ck 01j ASK "$(b 'typeset +x')"
ck 01k 0   "$(b 'declare +x FOO')"
fg FG-01 0 'not _PS_VALUE_OPT_RE.fullmatch(p)' 'not p.startswith("-")' 'ps -A e'
fg FG-01b 0 'all(a.startswith(("-", "+")) for a in toks[1:])' 'all(a.startswith("-") for a in toks[1:])' 'declare +x'

# ---- TC-02 コンテナの /tmp/ 以外への書き込み（くっつけた -t・sed の式の付着形） ----
ck 02a ASK "$(b "$D cp -vt/app/x /tmp/y")"
ck 02b ASK "$(b "$D cp -t/app/x /tmp/y")"
ck 02c 0   "$(b "$D install -d /app/newdir")"
ck 02d 0   "$(b "$D cp -vt/tmp/x /app/y")"
ck 02e ASK "$(b "$D sed -i -es/a/b/ /app/x")"
ck 02f 0   "$(b "$D sed -i -e s/a/b/ /tmp/x")"
ck 02g ASK "$(b "$D install -m 644 /tmp/a /app/b")"
fg FG-02 0 '(j == 0 or body[:j].isalpha())' 'j == 0' "$D cp -vt/app/x /tmp/y"

# ---- TC-03 通す形でも /tmp/ 以外への書き込みは確認（危ない語の理由と書き込みの理由を分ける） ----
ck 03a ASK "$(b "$D pytest --junitxml=/app/r.xml -k x")"
ck 03b 0   "$(b "$D pytest --junitxml=/tmp/r.xml -k delete")"
ck 03c 0   "$(b "$D pytest -k delete")"
ck 03d ASK "$(b "$D sh -c \"pytest -k delete > /app/out.txt\"")"
ck 03e 0   "$(b "$D sh -c \"pytest -k delete > /tmp/out.txt\"")"
ck 03f 0   "$(b "$D grep -rn foo /app/apps > out.txt")"
fg FG-03 0 'if any(not _in_scratch(t) for t in c["write_to"] + _write_targets(c["toks"]) + vals):' \
  'if not _container_safe(c) and any(not _in_scratch(t) for t in c["write_to"] + _write_targets(c["toks"]) + vals):' \
  "$D pytest --junitxml=/app/r.xml -k x"

# ---- TC-04 別ワークツリーへの書き込みの停止（書き先の見分け方を 1 つに） ----
ck 04a 2 "$(b "cp -vt$W/x /tmp/y")"
ck 04b 2 "$(b "cp --target-directory=$W/x /tmp/y")"
ck 04c 2 "$(b "install /tmp/y $W/x")"
ck 04d 2 "$(b "ln -s /tmp/y $W/x")"
ck 04e 2 "$(b "rsync -a /tmp/y $W/x")"
ck 04f 2 "$(b "mv $W/x /tmp/y")"
ck 04g 2 "$(b "cp /tmp/y $W/x")"
ck 04h 2 "$(b "cp -t $W/x /tmp/y")"
ck 04i 2 "$(b "sed -i s/a/b/ $W/x")"
ck 04j 2 "$(b "tee $W/x")"
ck 04k 2 "$(b "echo x > $W/x")"
ck 04l 0 "$(b "cp $W/x /tmp/y")"
ck 04m 0 "$(b "ln -s $W/x /tmp/y")"
ck 04n 0 "$(b "install -d $W/newdir")"
ck 04o 0 "$(b "sed -n p $W/x")"
fg FG-04 0 '        targets += _write_targets(toks)' '        targets += []' "cp -vt$W/x /tmp/y"

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
