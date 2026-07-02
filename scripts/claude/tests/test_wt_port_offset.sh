#!/usr/bin/env bash
# I097: wt-new.sh のポートオフセット/衝突ロジックを決定論検証する（docker 非依存）。
# 実行: bash scripts/claude/tests/test_wt_port_offset.sh
#
# 隔離方針: 実 git worktree を temp repo（bare origin + clone）に作る。docker は使わない（--up しない）。
# temp repo の .gitignore に .env / *.env を含め（I097）、wt-new 生成の直下 .env が dirty 扱いにならない
# 実運用と同じ環境で検証する。0=正常 / 2=明示エラー停止。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WT_NEW="$REPO_ROOT/scripts/claude/wt-new.sh"
RUNBOOK="$REPO_ROOT/docs/runbooks/worktree.md"
COMMON="$REPO_ROOT/docs/runbooks/common-commands.md"

ALL_TMP=()
cleanup() { local d; for d in "${ALL_TMP[@]:-}"; do [ -n "$d" ] && rm -rf "$d"; done; }
trap cleanup EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
ckt() { local name="$1"; shift
        if "$@"; then printf 'PASS %s\n' "$name"; pass=$((pass+1));
        else printf 'FAIL %s\n' "$name"; fail=$((fail+1)); fi; }
ckhas() { if printf '%s' "$2" | grep -q -- "$3"; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
          else printf 'FAIL %s (missing substring: %s)\n' "$1" "$3"; fail=$((fail+1)); fi; }
cknot() { if printf '%s' "$2" | grep -q -- "$3"; then printf 'FAIL %s (unexpected substring: %s)\n' "$1" "$3"; fail=$((fail+1));
          else printf 'PASS %s\n' "$1"; pass=$((pass+1)); fi; }

# 隔離環境（globals: TMP ORIGIN PRIMARY）
new_env() {
  local SRC
  TMP="$(mktemp -d)"; ALL_TMP+=("$TMP")
  SRC="$TMP/src"
  git init -q -b main "$SRC"
  git -C "$SRC" config user.email t@example.com
  git -C "$SRC" config user.name tester
  mkdir -p "$SRC/backend"
  # 実 .gitignore と揃える（.env / *.env を無視＝生成 .env が dirty 扱いにならない）
  printf 'backend/.env\ne2e/.env.e2e\n.env\n*.env\n' > "$SRC/.gitignore"
  printf 'keep\n' > "$SRC/backend/.gitkeep"
  printf 'services: {}\n' > "$SRC/docker-compose.yml"
  git -C "$SRC" add -A; git -C "$SRC" commit -qm "main"
  git -C "$SRC" checkout -q -b develop
  printf 'develop\n' > "$SRC/only-develop-file.txt"
  git -C "$SRC" add -A; git -C "$SRC" commit -qm "develop"
  git -C "$SRC" checkout -q main
  ORIGIN="$TMP/origin.git"; git clone -q --bare "$SRC" "$ORIGIN"
  PRIMARY="$TMP/primary"; git clone -q "$ORIGIN" "$PRIMARY"
  git -C "$PRIMARY" config user.email t@example.com
  git -C "$PRIMARY" config user.name tester
  git -C "$PRIMARY" checkout -q develop
  printf 'SECRET=stub\n' > "$PRIMARY/backend/.env"
}

# wt-new を primary で実行（globals: OUT RC）
run_new() { OUT="$( cd "$PRIMARY" && bash "$WT_NEW" "$@" 2>&1 )"; RC=$?; }
wl() { ( cd "$PRIMARY" && git worktree list --porcelain ); }
envval() { sed -n "s/^$2=\([0-9]\{1,\}\).*/\1/p" "$1" | head -1; }

# ===================== 自動割当（既定） =====================
# --- TC-P1: 既存なし → offset=10 で .env 生成 ---
new_env; run_new app 101 x
ck   "P1 exit0"            0    "$RC"
ckt  "P1 .env 生成"       test -f "$TMP/wt-app/.env"
ck   "P1 DB=5442"         5442 "$(envval "$TMP/wt-app/.env" DB_PORT)"
ck   "P1 REDIS=6389"      6389 "$(envval "$TMP/wt-app/.env" REDIS_PORT)"
ck   "P1 BACKEND=8010"    8010 "$(envval "$TMP/wt-app/.env" BACKEND_PORT)"
ck   "P1 FRONTEND=3010"   3010 "$(envval "$TMP/wt-app/.env" FRONTEND_PORT)"

# --- TC-P2: --port-offset 20 ---
new_env; run_new app 102 x --port-offset 20
ck   "P2 exit0"           0    "$RC"
ck   "P2 DB=5452"         5452 "$(envval "$TMP/wt-app/.env" DB_PORT)"
ck   "P2 REDIS=6399"      6399 "$(envval "$TMP/wt-app/.env" REDIS_PORT)"
ck   "P2 BACKEND=8020"    8020 "$(envval "$TMP/wt-app/.env" BACKEND_PORT)"
ck   "P2 FRONTEND=3020"   3020 "$(envval "$TMP/wt-app/.env" FRONTEND_PORT)"

# --- TC-P4: 自動割当が使用済みを避ける（app=10 → api=20） ---
new_env; run_new app 105 x
run_new api 106 y
ck   "P4 exit0"           0    "$RC"
ck   "P4 api BACKEND=8020" 8020 "$(envval "$TMP/wt-api/.env" BACKEND_PORT)"

# ===================== 衝突検出（決定論ゲート） =====================
# --- TC-P3: 既存 offset=10 に --port-offset 10 → 衝突 fail ---
new_env; run_new app 103 x            # offset 10
run_new api 104 y --port-offset 10    # 衝突
ck   "P3 exit2"           2    "$RC"
ckhas "P3 衝突メッセージ" "$OUT" "既存 worktree と衝突"
cknot "P3 wt-api 非作成"  "$(wl)" "/wt-api"

# --- TC-P6: --port-offset 0 → primary 既定ポートと衝突 fail ---
new_env; run_new app 108 x --port-offset 0
ck   "P6 exit2"           2    "$RC"
ckhas "P6 衝突メッセージ" "$OUT" "既存 worktree と衝突"
cknot "P6 wt-app 非作成"  "$(wl)" "/wt-app"

# ===================== 引数検証 =====================
# --- TC-P5: --port-offset 非整数 → exit2 ---
new_env; run_new app 107 x --port-offset abc
ck   "P5 exit2"           2    "$RC"
ckhas "P5 メッセージ"     "$OUT" "--port-offset は数字"
# --- TC-P5b: --port-offset 値なし → exit2 ---
new_env; run_new app 107 x --port-offset
ck   "P5b exit2"          2    "$RC"
ckhas "P5b メッセージ"    "$OUT" "--port-offset に値がありません"

# ===================== AC4: COMPOSE_PROJECT_NAME 不在 =====================
# --- TC-P9: 生成 .env に COMPOSE_PROJECT_NAME が混入しない ---
new_env; run_new app 109 x
cknot "P9 COMPOSE_PROJECT_NAME 不在" "$(cat "$TMP/wt-app/.env")" "COMPOSE_PROJECT_NAME"

# ===================== 回帰（既存挙動の無改変・具体） =====================
# --- TC-P8: backend/.env コピー一致・基点 develop・exit0 ---
new_env; run_new app 110 x
ck   "P8 exit0"           0    "$RC"
ckt  "P8 backend/.env コピー一致" cmp -s "$PRIMARY/backend/.env" "$TMP/wt-app/backend/.env"
ckt  "P8 基点develop(only-develop在)" test -f "$TMP/wt-app/only-develop-file.txt"

# ===================== false-green 注入 =====================
# --- TC-FG-P1: 衝突ガード除去複製では衝突しても作成される（実体の停止要因が衝突ガードである反証） ---
new_env; run_new app 111 x            # offset 10
BROKEN="$TMP/wt-new-broken.sh"
# shellcheck disable=SC2016  # 単一引用は意図的（$np/$ep を展開せず sed パターンに渡す）
sed 's/\[ "$np" = "$ep" \]/false/' "$WT_NEW" > "$BROKEN"
ck   "FG-P1 注入成立(if false)" 0 "$(grep -q 'if false; then' "$BROKEN"; echo $?)"
OUT="$( cd "$PRIMARY" && bash "$BROKEN" api 112 y --port-offset 10 2>&1 )"; RC=$?
ckhas "FG-P1 除去複製=衝突でも作成" "$(wl)" "/wt-api"

# ===================== runbook 整合（TC-DOC1） =====================
ck "DOC1a §6 同時起動言及"        0 "$(grep -q '同時' "$RUNBOOK"; echo $?)"
ck "DOC1b BACKEND_PORT 記載"      0 "$(grep -q 'BACKEND_PORT' "$RUNBOOK"; echo $?)"
ck "DOC1c §3 コマンド例に port-offset" 0 "$(grep -q 'port-offset' "$RUNBOOK"; echo $?)"
cknot "DOC1d 旧記述除去(1スタックずつ)" "$(cat "$RUNBOOK")" "1 スタックずつ"
ck "DOC1e common-commands にポート変数" 0 "$(grep -q 'BACKEND_PORT' "$COMMON"; echo $?)"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
