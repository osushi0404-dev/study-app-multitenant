#!/usr/bin/env bash
# I096: wt-new.sh / wt-remove.sh の worktree lifecycle を決定論検証する。
# 実行: bash scripts/claude/tests/test_wt_lifecycle.sh
#
# 隔離方針: 実 git worktree は temp repo（bare origin + clone）に作り、docker は PATH スタブに
# 差し替えて Docker デーモン非依存にする（実 volume/コンテナは触らない）。0=正常 / 2=明示エラー停止。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WT_NEW="$REPO_ROOT/scripts/claude/wt-new.sh"
WT_REMOVE="$REPO_ROOT/scripts/claude/wt-remove.sh"
RUNBOOK="$REPO_ROOT/docs/runbooks/worktree.md"

ALL_TMP=()
cleanup() { local d; for d in "${ALL_TMP[@]:-}"; do [ -n "$d" ] && rm -rf "$d"; done; }
trap cleanup EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
# ckt: 続く test コマンドが成功(exit 0)すれば PASS。$? を条件から拾う SC2319 回避も兼ねる。
ckt() { local name="$1"; shift
        if "$@"; then printf 'PASS %s\n' "$name"; pass=$((pass+1));
        else printf 'FAIL %s\n' "$name"; fail=$((fail+1)); fi; }
ckhas() { if printf '%s' "$2" | grep -q -- "$3"; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
          else printf 'FAIL %s (missing substring: %s)\n' "$1" "$3"; fail=$((fail+1)); fi; }
cknot() { if printf '%s' "$2" | grep -q -- "$3"; then printf 'FAIL %s (unexpected substring: %s)\n' "$1" "$3"; fail=$((fail+1));
          else printf 'PASS %s\n' "$1"; pass=$((pass+1)); fi; }

# 新しい隔離環境を構築（globals: TMP BIN DOCKER_LOG ORIGIN PRIMARY）。$1=primary ディレクトリ名（既定 primary）
new_env() {
  local pname="${1:-primary}" SRC
  TMP="$(mktemp -d)"; ALL_TMP+=("$TMP")
  BIN="$TMP/bin"; mkdir -p "$BIN"
  DOCKER_LOG="$TMP/docker.log"; : > "$DOCKER_LOG"
  # docker スタブ: 呼出を記録・down 時に対象 WT の存在（順序）を記録・失敗注入対応
  cat > "$BIN/docker" <<'STUB'
#!/usr/bin/env bash
echo "docker $*" >> "$DOCKER_LOG"
case "$*" in
  *down*)
    if [ -n "${STUB_WT:-}" ] && [ -e "$STUB_WT/.git" ]; then echo "down present=yes" >> "$DOCKER_LOG";
    else echo "down present=no" >> "$DOCKER_LOG"; fi ;;
esac
if [ -n "${DOCKER_FAIL_ON:-}" ] && printf '%s' "$*" | grep -q -- "$DOCKER_FAIL_ON"; then exit 1; fi
exit 0
STUB
  chmod +x "$BIN/docker"
  # source repo: main に only-main-file / develop に only-develop-file・.env は gitignore
  SRC="$TMP/src"
  git init -q -b main "$SRC"
  git -C "$SRC" config user.email t@example.com
  git -C "$SRC" config user.name tester
  mkdir -p "$SRC/backend" "$SRC/e2e"
  # 実 .gitignore と揃える。root .env / *.env を無視（I097: wt-new が生成する直下 .env が
  # dirty 扱いにならず、wt-remove の未コミット変更チェックが実運用と同じ挙動になる）。
  printf 'backend/.env\ne2e/.env.e2e\n.env\n*.env\n' > "$SRC/.gitignore"
  printf 'keep\n' > "$SRC/backend/.gitkeep"
  printf 'keep\n' > "$SRC/e2e/.gitkeep"
  printf 'services: {}\n' > "$SRC/docker-compose.yml"
  printf 'main-only\n' > "$SRC/only-main-file.txt"
  git -C "$SRC" add -A; git -C "$SRC" commit -qm "main commit"
  git -C "$SRC" checkout -q -b develop
  git -C "$SRC" rm -q only-main-file.txt
  printf 'develop-only\n' > "$SRC/only-develop-file.txt"
  git -C "$SRC" add -A; git -C "$SRC" commit -qm "develop commit"
  git -C "$SRC" checkout -q main
  # bare origin + primary clone
  ORIGIN="$TMP/origin.git"; git clone -q --bare "$SRC" "$ORIGIN"
  PRIMARY="$TMP/$pname"; git clone -q "$ORIGIN" "$PRIMARY"
  git -C "$PRIMARY" config user.email t@example.com
  git -C "$PRIMARY" config user.name tester
  git -C "$PRIMARY" checkout -q develop
  # 作業ツリーの env source（gitignore 対象＝dirty 判定に出ない）
  printf 'SECRET=stub\n' > "$PRIMARY/backend/.env"
  printf 'E2E=stub\n'    > "$PRIMARY/e2e/.env.e2e"
}

# wt-app を作成し removable にする（HEAD=origin/develop tip）。globals: OUT RC EXPECT_WT
make_wt() {
  OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" bash "$WT_NEW" app 001 my-feature 2>&1 )"; RC=$?
  EXPECT_WT="$(cd "$PRIMARY" && git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)"
  EXPECT_WT="$(dirname "$EXPECT_WT")/wt-app"
}
wl() { ( cd "$PRIMARY" && git worktree list --porcelain ); }   # worktree 一覧（判定用）

# ===================== wt-new =====================

# --- TC-N1〜N3: happy path（作成・基点 origin/develop・.env コピー） ---
new_env; make_wt
ck   "N1 happy exit0"          0    "$RC"
ckhas "N1 wt-app 作成"         "$(wl)" "/wt-app"
ckt  "N2 基点develop(only-develop在)" test -f "$EXPECT_WT/only-develop-file.txt"
ckt  "N2 基点develop(only-main無)"    test ! -f "$EXPECT_WT/only-main-file.txt"
ckt  "N3 .env コピー一致"             cmp -s "$PRIMARY/backend/.env" "$EXPECT_WT/backend/.env"

# --- TC-N4: .env source 欠落 → add 前に停止・orphan 非作成 ---
new_env; rm -f "$PRIMARY/backend/.env"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" bash "$WT_NEW" app 002 x 2>&1 )"; RC=$?
ck   "N4 exit2"                2    "$RC"
ckhas "N4 メッセージ"          "$OUT" ".env source が存在しません"
cknot "N4 worktree 非作成"     "$(wl)" "/wt-app"

# --- TC-N5: 既定 up なし → docker 未呼出 ---
new_env
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" bash "$WT_NEW" app 003 x 2>&1 )"; RC=$?
ck   "N5 exit0"                0    "$RC"
cknot "N5 up 未呼出"           "$(cat "$DOCKER_LOG")" "up"

# --- TC-N6: --up → docker compose up -d 呼出 ---
new_env
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" bash "$WT_NEW" app 004 x --up 2>&1 )"; RC=$?
ck   "N6 exit0"                0    "$RC"
ckhas "N6 up 呼出"             "$(cat "$DOCKER_LOG")" "compose up -d"

# --- TC-N7: 引数検証（数字/許可文字/空白） ---
new_env
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" bash "$WT_NEW" app abc x 2>&1 )"; ck "N7a 番号非数字 exit2" 2 "$?"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" bash "$WT_NEW" app 005 "a b" 2>&1 )"; ck "N7b 概要に空白 exit2" 2 "$?"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" bash "$WT_NEW" a/b 006 x 2>&1 )"; ck "N7c trackにスラッシュ exit2" 2 "$?"
cknot "N7 worktree 非作成"     "$(wl)" "/wt-"

# --- TC-N8: branch 既存衝突 ---
new_env
git -C "$PRIMARY" branch feature/I007-dup >/dev/null 2>&1
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" bash "$WT_NEW" app 007 dup 2>&1 )"; RC=$?
ck   "N8 exit2"                2    "$RC"
ckhas "N8 メッセージ"          "$OUT" "branch が既に存在"

# --- TC-N9: worktree path 既存衝突 ---
new_env; mkdir -p "$TMP/wt-app"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" bash "$WT_NEW" app 008 x 2>&1 )"; RC=$?
ck   "N9 exit2"                2    "$RC"
ckhas "N9 メッセージ"          "$OUT" "worktree path が既に存在"

# --- TC-N10: --env-source 値なし（shift 2 範囲外の無言 exit を防ぐ・W2 回帰） ---
new_env
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" bash "$WT_NEW" app 010 x --env-source 2>&1 )"; RC=$?
ck   "N10 exit2"               2    "$RC"
ckhas "N10 メッセージ"         "$OUT" "--env-source に値がありません"

# ===================== wt-remove =====================

# --- TC-R1: DANGER_OK 未設定 → down 非実行・非撤去 ---
new_env; make_wt
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" STUB_WT="$EXPECT_WT" bash "$WT_REMOVE" app 2>&1 )"; RC=$?
ck   "R1 exit2"                2    "$RC"
ckhas "R1 破壊的操作の案内"    "$OUT" "破壊的操作"
cknot "R1 down 非実行"         "$(cat "$DOCKER_LOG")" "down"
ckhas "R1 worktree 残存"       "$(wl)" "/wt-app"

# --- TC-R2/R3: DANGER_OK=1 → down -v → remove の順序 ---
new_env; make_wt
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" STUB_WT="$EXPECT_WT" DANGER_OK=1 bash "$WT_REMOVE" app 2>&1 )"; RC=$?
ck   "R2 exit0"                0    "$RC"
ckhas "R2 down -v 呼出"        "$(cat "$DOCKER_LOG")" "compose down -v"
cknot "R2 worktree 撤去済"     "$(wl)" "/wt-app"
ckhas "R3 down→remove 順序(present=yes)" "$(cat "$DOCKER_LOG")" "present=yes"

# --- TC-R4: 未コミット変更 → 中止 ---
new_env; make_wt
printf 'dirty\n' >> "$EXPECT_WT/only-develop-file.txt"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" STUB_WT="$EXPECT_WT" DANGER_OK=1 bash "$WT_REMOVE" app 2>&1 )"; RC=$?
ck   "R4 exit2"                2    "$RC"
ckhas "R4 未コミット中止"      "$OUT" "未コミット変更あり"
cknot "R4 down 非実行"         "$(cat "$DOCKER_LOG")" "down"

# --- TC-R5: 未 push コミット → 中止 ---
new_env; make_wt
printf 'more\n' >> "$EXPECT_WT/only-develop-file.txt"
git -C "$EXPECT_WT" commit -aqm "local unpushed"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" STUB_WT="$EXPECT_WT" DANGER_OK=1 bash "$WT_REMOVE" app 2>&1 )"; RC=$?
ck   "R5 exit2"                2    "$RC"
ckhas "R5 未push中止"          "$OUT" "HEAD が未 push"
cknot "R5 down 非実行"         "$(cat "$DOCKER_LOG")" "down"

# --- TC-R6: primary 保護（clone 先を wt-primary にして WT_PATH==PRIMARY を成立） ---
new_env "wt-primary"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" DANGER_OK=1 bash "$WT_REMOVE" primary 2>&1 )"; RC=$?
ck   "R6 exit2"                2    "$RC"
ckhas "R6 primary 保護"        "$OUT" "primary checkout は撤去できません"
cknot "R6 down 非実行"         "$(cat "$DOCKER_LOG")" "down"

# --- TC-R7: 撤去対象 WT の内側から実行 → 中止（W1 回帰） ---
new_env; make_wt
OUT="$( cd "$EXPECT_WT" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" STUB_WT="$EXPECT_WT" DANGER_OK=1 bash "$WT_REMOVE" app 2>&1 )"; RC=$?
ck   "R7 exit2"                2    "$RC"
ckhas "R7 内側実行の案内"      "$OUT" "内側からは実行できません"
cknot "R7 down 非実行"         "$(cat "$DOCKER_LOG")" "down"
ckhas "R7 worktree 残存"       "$(wl)" "/wt-app"

# --- TC-R8: down -v 失敗 → remove せず案内（W4 回帰） ---
new_env; make_wt
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" STUB_WT="$EXPECT_WT" DOCKER_FAIL_ON=down DANGER_OK=1 bash "$WT_REMOVE" app 2>&1 )"; RC=$?
ck   "R8 exit2"                2    "$RC"
ckhas "R8 down 失敗の案内"     "$OUT" "docker compose down -v が失敗しました"
ckhas "R8 worktree 残存"       "$(wl)" "/wt-app"

# --- TC-C1: COMPOSE_PROJECT_NAME 警告（軽微・処理継続） ---
new_env
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" COMPOSE_PROJECT_NAME=foo bash "$WT_NEW" app 009 x 2>&1 )"; RC=$?
ck   "C1 exit0（警告のみ）"    0    "$RC"
ckhas "C1 警告出力"            "$OUT" "COMPOSE_PROJECT_NAME"

# ===================== false-green 注入 =====================

# --- TC-FG1: DANGER_OK ゲート除去複製では未設定でも down される（実体の停止要因がゲートである反証） ---
new_env; make_wt
BROKEN_RM="$TMP/wt-remove-broken.sh"
# shellcheck disable=SC2016  # 単一引用は意図的（${DANGER_OK:-} を展開せず sed パターンに渡す）
sed 's/"${DANGER_OK:-}" = "1"/true/' "$WT_REMOVE" > "$BROKEN_RM"
ck   "FG1 注入成立(if [ true ])" 0 "$(grep -q '\[ true \]' "$BROKEN_RM"; echo $?)"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" STUB_WT="$EXPECT_WT" bash "$BROKEN_RM" app 2>&1 )"; RC=$?
ckhas "FG1 除去複製=未設定でも down" "$(cat "$DOCKER_LOG")" "compose down -v"

# --- TC-FG2: .env 検証除去複製では欠落でも add へ進む（実体の停止要因が .env 検証である反証） ---
new_env; rm -f "$PRIMARY/backend/.env"
BROKEN_NEW="$TMP/wt-new-broken.sh"
sed '/\.env source が存在しません/d' "$WT_NEW" > "$BROKEN_NEW"
ck   "FG2 注入成立(guard 除去)" 1 "$(grep -q '.env source が存在しません' "$BROKEN_NEW"; echo $?)"
OUT="$( cd "$PRIMARY" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" bash "$BROKEN_NEW" app 011 x 2>&1 )"; RC=$?
ckhas "FG2 除去複製=worktree 作成へ進む" "$(wl)" "/wt-app"
cknot "FG2 除去複製=停止メッセージ無し"  "$OUT" ".env source が存在しません"

# ===================== runbook =====================
ck "D1 runbook に wt-new"    0 "$(grep -q 'wt-new' "$RUNBOOK"; echo $?)"
ck "D2 runbook に wt-remove" 0 "$(grep -q 'wt-remove' "$RUNBOOK"; echo $?)"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
