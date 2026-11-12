#!/usr/bin/env bash
# I444: 見張りに残る役目の取りこぼし（環境変数の表示・コンテナ内の書き先・psql の WHERE なしの UPDATE）と、
# 縮めた許可リスト（危ない語が当たっても通す形）・corpus diff の作業記録の探し方を決定論で確かめる。
# 実行: bash scripts/claude/tests/test_i444_guard_gaps.sh
#
# 見張りに JSON を渡して判定だけを見る（コマンドは実行しない）。期待値: 2＝停止・ASK＝確認・0＝通す。
# ケースは docs/tests/open/I444_auto_test.md の TC-01〜TC-05 と 1 対 1。0=全 PASS / 1=FAIL あり。
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
DIFF_PY="$REPO_ROOT/scripts/claude/tests/guard_corpus_diff.py"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
b() {  # b <コマンド> [見張り]
  local out code
  out=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1" \
        | python3 "${2:-$GUARD}" 2>/dev/null); code=$?
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

# ---- TC-01 環境変数をまとめて表示する形は確認（ホストとコンテナ） ----
ck 01a ASK "$(b "$D export")"
ck 01b ASK "$(b "$D declare")"
ck 01c ASK "$(b "$D typeset")"
ck 01d ASK "$(b "$D env -0")"
ck 01e ASK "$(b "$D env -u X")"
ck 01f ASK "$(b "$D env FOO=1")"
ck 01g ASK "$(b "$D ps auxe")"
ck 01h ASK "$(b 'export')"
ck 01i ASK "$(b 'env -u X')"
ck 01j ASK "$(b 'set')"
ck 01k ASK "$(b 'declare -p')"
ck 01l ASK "$(b 'ps e')"
ck 01m 0   "$(b "$D export FOO=1")"
ck 01n 0   "$(b "$D declare -i x=1")"
ck 01o 0   "$(b 'set -euo pipefail')"
ck 01p 0   "$(b 'ps aux')"
ck 01q 0   "$(b 'ps -eo etimes,pcpu,args --sort=-etimes')"
ck 01r 0   "$(b 'env FOO=1 python3 -V')"
ck 01s 0   "$(b "$D env -u X python -V")"
ck 01t ASK "$(b "$D ps aux e")"
# fix-loop 3（台帳 F3・F4）: オプションの値・代入つきの -x は表示ではない。表示する形は確認のまま
ck 01u 0   "$(b 'ps -C node')"
ck 01v 0   "$(b 'ps -u postgres')"
ck 01w 0   "$(b 'ps -p 1 -o etime')"
ck 01x 0   "$(b 'declare -x FOO=1')"
ck 01y ASK "$(b 'ps -u postgres e')"
ck 01z ASK "$(b 'declare -x')"
ck 01za ASK "$(b 'declare -p FOO')"
fg FG-01 0 '                and (all(a.startswith(("-", "+")) for a in toks[1:]) or any(a in ("-p", "-px", "-xp") for a in toks[1:]))):
        r.append("環境変数（秘密情報を含む）の表示")' \
  '                and (all(a.startswith(("-", "+")) for a in toks[1:]) or any(a in ("-p", "-px", "-xp") for a in toks[1:]))):
        pass' "$D export"
fg FG-01b ASK ' and not _PS_VALUE_OPT_RE.fullmatch(p)' '' 'ps -C node'

# ---- TC-02 コンテナの /tmp/ 以外への書き込み（書き先の指定・移動元）は確認 ----
ck 02a ASK "$(b "$D cp -t /app/x /tmp/y")"
ck 02b ASK "$(b "$D cp --target-directory=/app/x /tmp/y")"
ck 02c ASK "$(b "$D cp -vt /app/x /tmp/y")"
ck 02d ASK "$(b "$D mv /app/x /tmp/y")"
ck 02h ASK "$(b "$D mv -t /app/x /tmp/y")"
ck 02i ASK "$(b "$D install -t /app/x /tmp/y")"
ck 02j ASK "$(b "$D rsync -avt /tmp/a /app/b")"
ck 02e 0   "$(b "$D mv /tmp/a /tmp/b")"
ck 02f 0   "$(b "$D cp /app/a /tmp/b")"
ck 02g 0   "$(b "$D cp -t /tmp/d /app/a")"
fg FG-02a 0 'T = ("-t", "--target-directory")' 'T = ("--target-directory",)' "$D cp -t /app/x /tmp/y"
fg FG-02b 0 '        return tdir + guess + pos' '        return pos[-1:]' "$D mv /app/x /tmp/y"

# ---- TC-03 psql の WHERE なしの UPDATE は停止（コンテナ内・ホスト） ----
ck 03a 2 "$(b "docker compose exec -T db psql -U postgres -c 'UPDATE users SET is_active=false'")"
ck 03b 2 "$(b "psql -U postgres -h localhost -c 'UPDATE users SET is_active=false'")"
ck 03c 0 "$(b "docker compose exec -T db psql -U postgres -c 'UPDATE users SET is_active=false WHERE id=1'")"
fg FG-03 0 'if re.search(r"\bupdate\b", s) and re.search(r"\bset\b", s) and not has_where:' 'if False:' \
  "docker compose exec -T db psql -U postgres -c 'UPDATE users SET is_active=false'"

# ---- TC-04 危ない語が当たっても通す形（I200 の普通の操作は通る） ----
ck 04a 0   "$(b "$D pytest -k delete")"
ck 04b 0   "$(b "$D python -m pytest -k delete")"
ck 04c 0   "$(b "$D python manage.py test apps.problems.tests.test_delete")"
ck 04d 0   "$(b 'docker compose run --rm e2e npx playwright test --grep delete')"
ck 04e 0   "$(b 'docker compose exec -T frontend npx jest src/password')"
ck 04f 0   "$(b "$D ruff check apps/accounts/password_reset.py")"
ck 04g 0   "$(b "$D pip show openai")"
ck 04h 0   "$(b "$D python manage.py shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/password-reset-confirm/', {})\"")"
ck 04i 0   "$(b "docker compose exec -T db psql -U postgres -c \"select 'drop' as x\"")"
ck 04j 0   "$(b "$D curl -fsS http://localhost:8000/health/")"
ck 04k 0   "$(b "$D sh -c \"pytest -k delete | tail -20\"")"
ck 04l ASK "$(b "$D sh -c \"pytest -k delete | sort -o /app/x\"")"
ck 04o 0   "$(b "$D sh -c \"pytest -k delete | grep -o FAILED\"")"
ck 04m 0  "$(b "$D ruff format --check apps/accounts/password_reset.py")"
ck 04n ASK "$(b "$D ruff format apps/accounts/password_reset.py")"
fg FG-04 ASK '    head, rest = os.path.basename(toks[0]), toks[1:]
    if c["piped"]:' '    return False
    if c["piped"]:' "$D pytest -k delete"

# ---- TC-05 corpus diff が primary とワークツリーの作業記録を見つける ----
dirs_of() {  # dirs_of <guard_corpus_diff.py> <HOME>
  HOME="$2" python3 - "$1" <<'PY'
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("gcd", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(",".join(os.path.basename(d) for d in m._project_dirs("/x/app.y")))
PY
}
H="$TMP/home"; mkdir -p "$H/.claude/projects/-x-app-y" "$H/.claude/projects/-x-app-y--claude-worktrees-w1" "$H/.claude/projects/-x-app-yz"
ck 05a "-x-app-y,-x-app-y--claude-worktrees-w1" "$(dirs_of "$DIFF_PY" "$H")"
E="$TMP/empty"; mkdir -p "$E"
out=$(HOME="$E" python3 "$DIFF_PY" 2>&1); code=$?
skip=no; printf '%s' "$out" | grep -q '^SKIP: 作業記録が無い環境です' && skip=yes
ck 05b "0 yes" "$code $skip"
if patch "$DIFF_PY" "$TMP/gcd_fg.py" 're.sub(r"[^A-Za-z0-9]", "-", primary)' 'primary.replace("/", "-")'; then
  ck FG-05 "" "$(dirs_of "$TMP/gcd_fg.py" "$H")"
else ck "FG-05 置き換え" ok NOPATCH; fi

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
