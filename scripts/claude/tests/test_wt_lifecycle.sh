#!/usr/bin/env bash
# I096/I179: wt-remove.sh の撤去（データ判定・安全策）を決定論検証する。
# 実行: bash scripts/claude/tests/test_wt_lifecycle.sh
#
# 隔離方針: 実 git worktree は temp repo（bare origin + clone の primary 役）に `git worktree add` で作り、
# docker は PATH スタブに差し替えて Docker デーモン非依存にする（実 volume/コンテナは触らない）。0=正常 / 2=明示エラー停止。
# スタブは STUB_CONTAINERS / STUB_VOLUMES を `docker ps -a -q ...` / `docker volume ls -q ...` の出力として返し、
# DOCKER_FAIL_ON に一致する呼び出しは exit 1。呼び出しはすべて DOCKER_LOG に記録する。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WT_REMOVE="$REPO_ROOT/scripts/claude/wt-remove.sh"
BASH_BIN="$(command -v bash)"

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
ckhas() { if printf '%s' "$2" | grep -qF -- "$3"; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
          else printf 'FAIL %s (missing substring: %s)\n' "$1" "$3"; fail=$((fail+1)); fi; }
cknot() { if printf '%s' "$2" | grep -qF -- "$3"; then printf 'FAIL %s (unexpected substring: %s)\n' "$1" "$3"; fail=$((fail+1));
          else printf 'PASS %s\n' "$1"; pass=$((pass+1)); fi; }

# 新しい隔離環境を構築（globals: TMP BIN NODOCKER DOCKER_LOG ORIGIN PRIMARY）
# usage: new_env [primary ディレクトリ名（既定 primary）] [named＝develop の compose に最上位 name: を入れる]
new_env() {
  local pname="${1:-primary}" named="${2:-}" SRC c
  TMP="$(mktemp -d)"; ALL_TMP+=("$TMP")
  BIN="$TMP/bin"; mkdir -p "$BIN"
  DOCKER_LOG="$TMP/docker.log"; : > "$DOCKER_LOG"
  # docker スタブ: 呼出を記録・down 時に対象 WT の存在（順序）を記録・失敗注入・ps/volume ls の出力差し替え
  cat > "$BIN/docker" <<'STUB'
#!/usr/bin/env bash
echo "docker $*" >> "$DOCKER_LOG"
case "$*" in
  *down*)
    if [ -n "${STUB_WT:-}" ] && [ -e "$STUB_WT/.git" ]; then echo "down present=yes" >> "$DOCKER_LOG";
    else echo "down present=no" >> "$DOCKER_LOG"; fi ;;
esac
if [ -n "${DOCKER_FAIL_ON:-}" ] && printf '%s' "$*" | grep -q -- "$DOCKER_FAIL_ON"; then exit 1; fi
case "$1 ${2:-}" in
  "ps -a")     [ -n "${STUB_CONTAINERS:-}" ] && printf '%s\n' "$STUB_CONTAINERS" ;;
  "volume ls") [ -n "${STUB_VOLUMES:-}" ]    && printf '%s\n' "$STUB_VOLUMES" ;;
esac
exit 0
STUB
  chmod +x "$BIN/docker"
  # docker が無い PATH（R1d 用）: wt-remove.sh が使うコマンドだけを置く
  NODOCKER="$TMP/nodocker"; mkdir -p "$NODOCKER"
  for c in git sed head basename tr grep; do ln -s "$(command -v "$c")" "$NODOCKER/$c"; done
  # source repo: develop に only-develop-file・.env と公式ワークツリー置き場は gitignore（実 .gitignore と揃える）
  SRC="$TMP/src"
  git init -q -b main "$SRC"
  git -C "$SRC" config user.email t@example.com
  git -C "$SRC" config user.name tester
  mkdir -p "$SRC/backend" "$SRC/e2e"
  printf 'backend/.env\ne2e/.env.e2e\n.env\n*.env\n.claude/worktrees/\n' > "$SRC/.gitignore"
  printf 'keep\n' > "$SRC/backend/.gitkeep"
  printf 'keep\n' > "$SRC/e2e/.gitkeep"
  printf 'services: {}\n' > "$SRC/docker-compose.yml"
  git -C "$SRC" add -A; git -C "$SRC" commit -qm "main commit"
  git -C "$SRC" checkout -q -b develop
  printf 'develop-only\n' > "$SRC/only-develop-file.txt"
  [ "$named" = "named" ] && printf 'name: x\nservices: {}\n' > "$SRC/docker-compose.yml"
  git -C "$SRC" add -A; git -C "$SRC" commit -qm "develop commit"
  git -C "$SRC" checkout -q main
  # bare origin + primary clone
  ORIGIN="$TMP/origin.git"; git clone -q --bare "$SRC" "$ORIGIN"
  PRIMARY="$TMP/$pname"; git clone -q "$ORIGIN" "$PRIMARY"
  git -C "$PRIMARY" config user.email t@example.com
  git -C "$PRIMARY" config user.name tester
  git -C "$PRIMARY" checkout -q develop
  printf 'SECRET=stub\n' > "$PRIMARY/backend/.env"
}

# 撤去対象のワークツリーを origin/develop 基点で作る（HEAD=origin/develop tip＝push 済み扱い）。globals: WT WT_BRANCH
# usage: make_wt [パス（既定 $TMP/wt-app）] [ブランチ（既定 feature/I001-my-feature）]
make_wt() {
  WT="${1:-$TMP/wt-app}"; WT_BRANCH="${2:-feature/I001-my-feature}"
  git -C "$PRIMARY" worktree add -q "$WT" -b "$WT_BRANCH" origin/develop
  cp "$PRIMARY/backend/.env" "$WT/backend/.env"
}
# wt-remove を実行（globals: OUT RC）。usage: run_rm <cwd> <script> [引数...]（環境変数は呼び出し側で export せず前置する）
run_rm() { local cwd="$1" script="$2"; shift 2
           OUT="$( cd "$cwd" && PATH="$BIN:$PATH" DOCKER_LOG="$DOCKER_LOG" STUB_WT="$WT" bash "$script" "$@" 2>&1 )"; RC=$?; }
wl() { ( cd "$PRIMARY" && git worktree list --porcelain ); }   # worktree 一覧（判定用）

# ===================== データ判定 =====================

# --- TC-R0: データ無し・DANGER_OK なし → down せず撤去 ---
new_env; make_wt
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R0 exit0"                0    "$RC"
cknot "R0 worktree 撤去済"     "$(wl)" "/wt-app"
cknot "R0 down 非実行"         "$(cat "$DOCKER_LOG")" "compose down"
ckhas "R0 プロジェクト名=フォルダ名" "$(cat "$DOCKER_LOG")" "label=com.docker.compose.project=wt-app"
# --- TC-R10: 撤去後もブランチが残り、完了メッセージに出る ---
ckt  "R10 ブランチ残存"        git -C "$PRIMARY" show-ref --verify --quiet "refs/heads/$WT_BRANCH"
ckhas "R10 ブランチ案内"       "$OUT" "ブランチ $WT_BRANCH は残っています"

# --- TC-R1: コンテナあり・DANGER_OK なし → 停止 ---
new_env; make_wt
STUB_CONTAINERS=c1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1 exit2"                2    "$RC"
ckhas "R1 破壊的操作の案内"    "$OUT" "破壊的操作"
cknot "R1 down 非実行"         "$(cat "$DOCKER_LOG")" "down"
ckhas "R1 worktree 残存"       "$(wl)" "/wt-app"

# --- TC-R1b: volume のみあり・DANGER_OK なし → 停止 ---
new_env; make_wt
STUB_VOLUMES=wt-app_postgres_data run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1b exit2"               2    "$RC"
cknot "R1b down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckhas "R1b worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R1c: 判定失敗（docker ps が失敗）→ 停止 ---
new_env; make_wt
DOCKER_FAIL_ON="ps -a" run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1c exit2"               2    "$RC"
ckhas "R1c 判定不能の案内"     "$OUT" "判定できません"
cknot "R1c down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckhas "R1c worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R1d: 判定失敗（PATH に docker が無い）→ 停止 ---
new_env; make_wt
OUT="$( cd "$PRIMARY" && PATH="$NODOCKER" "$BASH_BIN" "$WT_REMOVE" "$WT" 2>&1 )"; RC=$?
ck   "R1d exit2"               2    "$RC"
ckhas "R1d 判定不能の案内"     "$OUT" "判定できません"
ckhas "R1d worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R1e / C1: 判定失敗（COMPOSE_PROJECT_NAME あり）・データ無し → 停止・警告 ---
new_env; make_wt
COMPOSE_PROJECT_NAME=foo run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1e exit2"               2    "$RC"
ckhas "R1e worktree 残存"      "$(wl)" "/wt-app"
ckhas "C1 警告出力"            "$OUT" "COMPOSE_PROJECT_NAME=foo が設定されています"

# --- TC-R1f: 判定失敗（compose に最上位 name:）・データ無し → 停止 ---
new_env primary named; make_wt
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1f exit2"               2    "$RC"
ckhas "R1f 判定不能の案内"     "$OUT" "判定できません"
ckhas "R1f worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R2/R3: データあり・DANGER_OK=1 → down -v → remove の順序 ---
new_env; make_wt
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R2 exit0"                0    "$RC"
ckhas "R2 down -v 呼出"        "$(cat "$DOCKER_LOG")" "compose down -v"
cknot "R2 worktree 撤去済"     "$(wl)" "/wt-app"
ckhas "R3 down→remove 順序(present=yes)" "$(cat "$DOCKER_LOG")" "present=yes"

# ===================== 既存の安全策 =====================

# --- TC-R4: 未コミット変更 → 中止 ---
new_env; make_wt
printf 'dirty\n' >> "$WT/only-develop-file.txt"
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R4 exit2"                2    "$RC"
ckhas "R4 未コミット中止"      "$OUT" "未コミット変更あり"
cknot "R4 down 非実行"         "$(cat "$DOCKER_LOG")" "down"

# --- TC-R5: 未 push コミット → 中止 ---
new_env; make_wt
printf 'more\n' >> "$WT/only-develop-file.txt"
git -C "$WT" commit -aqm "local unpushed"
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R5 exit2"                2    "$RC"
ckhas "R5 未push中止"          "$OUT" "HEAD が未 push"
cknot "R5 down 非実行"         "$(cat "$DOCKER_LOG")" "down"

# --- TC-R6: primary を指定 → 拒否 ---
new_env; WT="$PRIMARY"
DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$PRIMARY"
ck   "R6 exit2"                2    "$RC"
ckhas "R6 primary 保護"        "$OUT" "primary checkout は撤去できません"
cknot "R6 down 非実行"         "$(cat "$DOCKER_LOG")" "down"

# --- TC-R7: 撤去対象 WT の内側から実行 → 中止 ---
new_env; make_wt
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$WT" "$WT_REMOVE" "$WT"
ck   "R7 exit2"                2    "$RC"
ckhas "R7 内側実行の案内"      "$OUT" "内側からは実行できません"
cknot "R7 down 非実行"         "$(cat "$DOCKER_LOG")" "down"
ckhas "R7 worktree 残存"       "$(wl)" "/wt-app"

# --- TC-R8: down -v 失敗 → remove せず案内 ---
new_env; make_wt
STUB_CONTAINERS=c1 DOCKER_FAIL_ON=down DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R8 exit2"                2    "$RC"
ckhas "R8 down 失敗の案内"     "$OUT" "docker compose down -v が失敗しました"
ckhas "R8 worktree 残存"       "$(wl)" "/wt-app"

# ===================== 指定方法 =====================

# --- TC-R9 / R10: 公式配置（<primary>/.claude/worktrees/app2）・データ無し → 撤去・ブランチ残存 ---
new_env; make_wt "$PRIMARY/.claude/worktrees/app2" worktree-app2
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R9 exit0"                0    "$RC"
cknot "R9 worktree 撤去済"     "$(wl)" "/.claude/worktrees/app2"
ckhas "R9 プロジェクト名=app2" "$(cat "$DOCKER_LOG")" "label=com.docker.compose.project=app2"
ckt  "R10 公式配置のブランチ残存" git -C "$PRIMARY" show-ref --verify --quiet "refs/heads/worktree-app2"

# --- TC-R9b: フォルダ名は Compose の既定と同じ規則で変換（大文字→小文字・. を除去） ---
new_env; make_wt "$TMP/Wt.App" feature/I002-x
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R9b exit0"               0    "$RC"
ckhas "R9b プロジェクト名=wtapp" "$(cat "$DOCKER_LOG")" "label=com.docker.compose.project=wtapp"

# --- TC-R11: git worktree list に無いフォルダ → 拒否・フォルダ残存 ---
new_env; WT="$TMP/plain"; mkdir -p "$WT"
DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R11 exit2"               2    "$RC"
ckhas "R11 登録外の案内"       "$OUT" "登録されたワークツリーではありません"
ckt  "R11 フォルダ残存"        test -d "$WT"
cknot "R11 down 非実行"        "$(cat "$DOCKER_LOG")" "down"

# --- TC-R12: 引数なし → Usage ---
new_env; WT=""
run_rm "$PRIMARY" "$WT_REMOVE"
ckt  "R12 exit 非ゼロ"         test "$RC" -ne 0
ckhas "R12 Usage 表示"         "$OUT" "Usage"

# ===================== false-green 注入 =====================

# --- TC-FG1: DANGER_OK ゲート除去複製では R1 の条件でも down される（実体の停止要因がゲートである反証） ---
new_env; make_wt
BROKEN_RM="$TMP/wt-remove-broken.sh"
# shellcheck disable=SC2016  # 単一引用は意図的（${DANGER_OK:-} を展開せず sed パターンに渡す）
sed 's/"${DANGER_OK:-}" = "1"/true/' "$WT_REMOVE" > "$BROKEN_RM"
ck   "FG1 注入成立(if [ true ])" 0 "$(grep -q '\[ true \]' "$BROKEN_RM"; echo $?)"
STUB_CONTAINERS=c1 run_rm "$PRIMARY" "$BROKEN_RM" "$WT"
ckhas "FG1 除去複製=未設定でも down" "$(cat "$DOCKER_LOG")" "compose down -v"

# --- TC-FG3: データ判定を常に「無し」にした複製では R1 の条件でも DANGER_OK なしで撤去される ---
new_env; make_wt
BROKEN_DD="$TMP/wt-remove-nodata.sh"
sed 's/^detect_data() {.*/&\n  return 0  # FG3/' "$WT_REMOVE" > "$BROKEN_DD"
ck   "FG3 注入成立"            0    "$(grep -q 'return 0  # FG3' "$BROKEN_DD"; echo $?)"
STUB_CONTAINERS=c1 run_rm "$PRIMARY" "$BROKEN_DD" "$WT"
ck   "FG3 除去複製=exit0"      0    "$RC"
cknot "FG3 除去複製=撤去済"    "$(wl)" "/wt-app"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
