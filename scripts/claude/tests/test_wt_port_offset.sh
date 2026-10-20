#!/usr/bin/env bash
# I097/I179: wt-ports.sh のポートオフセット/衝突ロジックを決定論検証する（docker 非依存）。
# 実行: bash scripts/claude/tests/test_wt_port_offset.sh
#
# 隔離方針: 実 git worktree を temp repo（bare origin + clone の primary 役）に `git worktree add` で作り、
# そのワークツリーを cwd にして wt-ports.sh を実行する。docker は使わない。
# temp repo の .gitignore は実物と揃える（.env / *.env / .claude/worktrees/）。0=正常 / 2=明示エラー停止。
# runbook の文言検査（旧 DOC1）は test_i179_worktree_docs.sh へ移した。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WT_PORTS="$REPO_ROOT/scripts/claude/wt-ports.sh"

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
  printf 'backend/.env\ne2e/.env.e2e\n.env\n*.env\n.claude/worktrees/\n' > "$SRC/.gitignore"
  printf 'keep\n' > "$SRC/backend/.gitkeep"
  printf 'services: {}\n' > "$SRC/docker-compose.yml"
  git -C "$SRC" add -A; git -C "$SRC" commit -qm "main"
  git -C "$SRC" checkout -q -b develop
  git -C "$SRC" checkout -q main
  ORIGIN="$TMP/origin.git"; git clone -q --bare "$SRC" "$ORIGIN"
  PRIMARY="$TMP/primary"; git clone -q "$ORIGIN" "$PRIMARY"
  git -C "$PRIMARY" config user.email t@example.com
  git -C "$PRIMARY" config user.name tester
  git -C "$PRIMARY" checkout -q develop
  printf 'SECRET=stub\n' > "$PRIMARY/backend/.env"
}

# ワークツリーを origin/develop 基点で作り、backend/.env を置く（.worktreeinclude のコピー相当）
# usage: add_wt <path> <branch> [noenv]
add_wt() {
  git -C "$PRIMARY" worktree add -q "$1" -b "$2" origin/develop
  [ "${3:-}" = "noenv" ] || cp "$PRIMARY/backend/.env" "$1/backend/.env"
}
# wt-ports を指定ワークツリーで実行（globals: OUT RC）。usage: run_ports <wt> [args...]
run_ports() { local wt="$1"; shift; OUT="$( cd "$wt" && bash "$WT_PORTS" "$@" 2>&1 )"; RC=$?; }
envval() { sed -n "s/^$2=\([0-9]\{1,\}\).*/\1/p" "$1" | head -1; }

# ===================== 自動割当（既定） =====================
# --- TC-P1: 他に割当なし → offset=10 ---
new_env; add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app"
ck   "P1 exit0"            0    "$RC"
ckt  "P1 .env 生成"       test -f "$TMP/wt-app/.env"
ck   "P1 DB=5442"         5442 "$(envval "$TMP/wt-app/.env" DB_PORT)"
ck   "P1 REDIS=6389"      6389 "$(envval "$TMP/wt-app/.env" REDIS_PORT)"
ck   "P1 BACKEND=8010"    8010 "$(envval "$TMP/wt-app/.env" BACKEND_PORT)"
ck   "P1 FRONTEND=3010"   3010 "$(envval "$TMP/wt-app/.env" FRONTEND_PORT)"

# --- TC-P2: --port-offset 20 ---
new_env; add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app" --port-offset 20
ck   "P2 exit0"           0    "$RC"
ck   "P2 DB=5452"         5452 "$(envval "$TMP/wt-app/.env" DB_PORT)"
ck   "P2 REDIS=6399"      6399 "$(envval "$TMP/wt-app/.env" REDIS_PORT)"
ck   "P2 BACKEND=8020"    8020 "$(envval "$TMP/wt-app/.env" BACKEND_PORT)"
ck   "P2 FRONTEND=3020"   3020 "$(envval "$TMP/wt-app/.env" FRONTEND_PORT)"

# --- TC-P4: 自動割当が使用済みを避ける（app=10 → api=20） ---
new_env; add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app"
add_wt "$TMP/wt-api" b2; run_ports "$TMP/wt-api"
ck   "P4 exit0"           0    "$RC"
ck   "P4 api BACKEND=8020" 8020 "$(envval "$TMP/wt-api/.env" BACKEND_PORT)"

# --- TC-P7: 入れ子配置の割当済みワークツリーも走査される ---
new_env; add_wt "$PRIMARY/.claude/worktrees/a" b1; run_ports "$PRIMARY/.claude/worktrees/a"
ck   "P7 入れ子 BACKEND=8010" 8010 "$(envval "$PRIMARY/.claude/worktrees/a/.env" BACKEND_PORT)"
add_wt "$TMP/wt-b" b2; run_ports "$TMP/wt-b"
ck   "P7 exit0"           0    "$RC"
ck   "P7 b BACKEND=8020"  8020 "$(envval "$TMP/wt-b/.env" BACKEND_PORT)"

# ===================== 衝突検出（決定論ゲート） =====================
# --- TC-P3: 既存 offset=10 に --port-offset 10 → 衝突 fail ---
new_env; add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app"     # offset 10
add_wt "$TMP/wt-api" b2; run_ports "$TMP/wt-api" --port-offset 10
ck   "P3 exit2"           2    "$RC"
ckhas "P3 衝突メッセージ" "$OUT" "既存 worktree と衝突"
ckt  "P3 .env 非作成"     test ! -e "$TMP/wt-api/.env"

# --- TC-P6: --port-offset 0 → primary 既定ポートと衝突 fail ---
new_env; add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app" --port-offset 0
ck   "P6 exit2"           2    "$RC"
ckhas "P6 衝突メッセージ" "$OUT" "既存 worktree と衝突"
ckt  "P6 .env 非作成"     test ! -e "$TMP/wt-app/.env"

# --- TC-P14: primary の .env にポート以外の行しか無い → 既定ポート扱いで --port-offset 0 は衝突 ---
new_env; printf 'SOME_VAR=1\n' > "$PRIMARY/.env"
add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app" --port-offset 0
ck   "P14 exit2"          2    "$RC"
ckhas "P14 衝突メッセージ" "$OUT" "既存 worktree と衝突"
ckt  "P14 .env 非作成"    test ! -e "$TMP/wt-app/.env"

# ===================== 引数検証 =====================
# --- TC-P5: --port-offset 非整数 / 値なし → exit2 ---
new_env; add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app" --port-offset abc
ck   "P5 exit2"           2    "$RC"
ckhas "P5 メッセージ"     "$OUT" "--port-offset は数字"
run_ports "$TMP/wt-app" --port-offset
ck   "P5b exit2"          2    "$RC"
ckhas "P5b メッセージ"    "$OUT" "--port-offset に値がありません"

# ===================== 冪等・既存行・primary・backend/.env =====================
# --- TC-P8: 2 回目は何も変えない ---
new_env; add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app"
cp "$TMP/wt-app/.env" "$TMP/env.first"
run_ports "$TMP/wt-app"
ck   "P8 exit0"           0    "$RC"
ckt  "P8 .env 不変(cmp)"  cmp -s "$TMP/env.first" "$TMP/wt-app/.env"
ckhas "P8 割当済み表示"   "$OUT" "割当済み"

# --- TC-P9: 生成 .env に COMPOSE_PROJECT_NAME が混入しない ---
cknot "P9 COMPOSE_PROJECT_NAME 不在" "$(cat "$TMP/wt-app/.env")" "COMPOSE_PROJECT_NAME"

# --- TC-P10: primary で実行 → exit2・.env 非作成 ---
new_env; run_ports "$PRIMARY"
ck   "P10 exit2"          2    "$RC"
ckhas "P10 メッセージ"    "$OUT" "primary は既定ポート"
ckt  "P10 primary .env 非作成" test ! -e "$PRIMARY/.env"

# --- TC-P11: backend/.env が無い → exit2・.env 非作成 ---
new_env; add_wt "$TMP/wt-app" b1 noenv; run_ports "$TMP/wt-app"
ck   "P11 exit2"          2    "$RC"
ckhas "P11 メッセージ"    "$OUT" "backend/.env がありません"
ckt  "P11 .env 非作成"    test ! -e "$TMP/wt-app/.env"

# --- TC-P12: ポート以外の行だけがある .env（末尾改行なし）→ 残して追記 ---
new_env; add_wt "$TMP/wt-app" b1; printf 'FOO=1' > "$TMP/wt-app/.env"; run_ports "$TMP/wt-app"
ck   "P12 exit0"          0    "$RC"
ck   "P12 FOO=1 残存"     0    "$(grep -qx 'FOO=1' "$TMP/wt-app/.env"; echo $?)"
ck   "P12 ポート 4 行"    4    "$(grep -Ec '^(DB|REDIS|BACKEND|FRONTEND)_PORT=[0-9]+$' "$TMP/wt-app/.env")"

# --- TC-P13: COMPOSE_PROJECT_NAME 設定時は警告して続行 ---
new_env; add_wt "$TMP/wt-app" b1
OUT="$( cd "$TMP/wt-app" && COMPOSE_PROJECT_NAME=foo bash "$WT_PORTS" 2>&1 )"; RC=$?
ck   "P13 exit0"          0    "$RC"
ckhas "P13 警告"          "$OUT" "COMPOSE_PROJECT_NAME"

# ===================== false-green 注入 =====================
# --- TC-FG-P1: 衝突ガード除去複製では P3 の条件でも .env が作られる ---
new_env; add_wt "$TMP/wt-app" b1; run_ports "$TMP/wt-app"     # offset 10
add_wt "$TMP/wt-api" b2
BROKEN="$TMP/wt-ports-broken.sh"
# shellcheck disable=SC2016  # 単一引用は意図的（$np/$ep を展開せず sed パターンに渡す）
sed 's/\[ "$np" = "$ep" \]/false/' "$WT_PORTS" > "$BROKEN"
ck   "FG-P1 注入成立(if false)" 0 "$(grep -q 'if false; then' "$BROKEN"; echo $?)"
OUT="$( cd "$TMP/wt-api" && bash "$BROKEN" --port-offset 10 2>&1 )"; RC=$?
ck   "FG-P1 除去複製=exit0" 0 "$RC"
ckt  "FG-P1 除去複製=.env 作成" test -f "$TMP/wt-api/.env"

# --- TC-FG-P2: backend/.env 検査除去複製では P11 の条件でも exit0 ---
new_env; add_wt "$TMP/wt-app" b1 noenv
BROKEN2="$TMP/wt-ports-broken2.sh"
# shellcheck disable=SC2016
sed 's/^\[ -f "\$WT\/backend\/.env" \] || {$/true || {/' "$WT_PORTS" > "$BROKEN2"
ck   "FG-P2 注入成立"     0    "$(grep -q '^true || {$' "$BROKEN2"; echo $?)"
OUT="$( cd "$TMP/wt-app" && bash "$BROKEN2" 2>&1 )"; RC=$?
ck   "FG-P2 除去複製=exit0" 0 "$RC"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
