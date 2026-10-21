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
ckhas() { if grep -qF -- "$3" <<<"$2"; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
          else printf 'FAIL %s (missing substring: %s)\n' "$1" "$3"; fail=$((fail+1)); fi; }
cknot() { if grep -qF -- "$3" <<<"$2"; then printf 'FAIL %s (unexpected substring: %s)\n' "$1" "$3"; fail=$((fail+1));
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
echo "cwd=$(pwd -P)" >> "$DOCKER_LOG"   # どのフォルダで実行されたか（down -v が撤去対象で走ることの検証用）
case "$*" in
  *down*)
    if [ -n "${STUB_WT:-}" ] && [ -e "$STUB_WT/.git" ]; then echo "down present=yes" >> "$DOCKER_LOG";
    else echo "down present=no" >> "$DOCKER_LOG"; fi ;;
esac
if [ -n "${DOCKER_FAIL_ON:-}" ] && printf '%s' "$*" | grep -q -- "$DOCKER_FAIL_ON"; then exit 1; fi
case "$1 ${2:-}" in
  "ps -a")
    if [ -n "${STUB_CONTAINERS:-}" ]; then
      case "$*" in
        *--format*) printf '%s\n' "${STUB_WORKDIR-$(cd "$STUB_WT" && pwd -P)}" ;;   # working_dir ラベル（コンテナごとに 1 行・空も可）
        *)          printf '%s\n' "$STUB_CONTAINERS" ;;
      esac
    fi ;;
  "volume ls") [ -n "${STUB_VOLUMES:-}" ]    && printf '%s\n' "$STUB_VOLUMES" ;;
  "volume inspect") printf '%s\n' "2026-10-01T09:00:00Z" ;;   # 作成日時（volume だけのときの表示の検証用）
esac
exit 0
STUB
  chmod +x "$BIN/docker"
  # docker が無い PATH（R1d 用）: wt-remove.sh が使うコマンドだけを置く
  NODOCKER="$TMP/nodocker"; mkdir -p "$NODOCKER"
  for c in git sed head basename tr grep awk ps; do ln -s "$(command -v "$c")" "$NODOCKER/$c"; done
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
ckhas "R1 バックアップ: -p で起動" "$OUT" "docker compose -p 'wt-app' up -d db"
ckhas "R1 バックアップ: -p でダンプ" "$OUT" "docker compose -p 'wt-app' exec -T db pg_dump"
ckhas "R1 バックアップ: 空でないこと" "$OUT" "test -s backup_wt-app_"
ckhas "R1 再実行の案内は bash 付き" "$OUT" "DANGER_OK=1 bash "
cknot "R1 down 非実行"         "$(cat "$DOCKER_LOG")" "down"
ckhas "R1 worktree 残存"       "$(wl)" "/wt-app"

# --- TC-R1b: volume のみあり・DANGER_OK なし → 停止 ---
new_env; make_wt
STUB_VOLUMES=wt-app_postgres_data run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1b exit2"               2    "$RC"
cknot "R1b down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckhas "R1b worktree 残存"      "$(wl)" "/wt-app"
# --- TC-R1b2: volume のみ → 持ち主を確かめられない旨と volume 名・作成日時・バックアップ手順を表示 ---
ckhas "R1b2 確かめられない案内" "$OUT" "機械で確かめられません"
ckhas "R1b2 volume 名と作成日時" "$OUT" "wt-app_postgres_data（作成: 2026-10-01T09:00:00Z）"
ckhas "R1b2 バックアップ手順"  "$OUT" "test -s backup_wt-app_"
# --- TC-R1b3: volume のみ・DANGER_OK=1 → 許可どおり -p 付きで down -v（撤去対象の中で 1 回だけ） ---
new_env; make_wt
STUB_VOLUMES=wt-app_postgres_data DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1b3 exit0"              0    "$RC"
ck   "R1b3 down -v は 1 回"    1    "$(grep -c 'compose -p wt-app down -v' "$DOCKER_LOG")"
ckhas "R1b3 撤去対象の中で実行" "$(grep -A1 'compose -p wt-app down -v' "$DOCKER_LOG")" "cwd=$(cd "$TMP" && pwd -P)/wt-app"

# --- TC-R1c: 判定失敗（docker ps が失敗）→ 停止 ---
new_env; make_wt
DOCKER_FAIL_ON="ps -a" run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1c exit2"               2    "$RC"
ckhas "R1c 判定不能の案内"     "$OUT" "判定できません"
cknot "R1c down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckhas "R1c worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R1c2: docker はあるが判定が失敗・DANGER_OK=1 → down せず中止（DANGER_OK では先へ進まない） ---
new_env; make_wt
STUB_CONTAINERS=c1 DOCKER_FAIL_ON="ps -a" DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1c2 exit2"              2    "$RC"
cknot "R1c2 down 非実行"       "$(cat "$DOCKER_LOG")" "down"
ckhas "R1c2 worktree 残存"     "$(wl)" "/wt-app"

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
ckhas "R1f 判定不能の案内"     "$OUT" "プロジェクト名を確定できません"
ckhas "R1f worktree 残存"      "$(wl)" "/wt-app"
# --- TC-R25: 戻り値 2 の案内は「コミットして push」と、元の名前のデータの片付け先 ---
ckhas "R25 push まで案内"      "$OUT" "コミットし push"
ckhas "R25 元の名前のデータ"   "$OUT" "取り残しの発見と削除"

# --- TC-R2/R3: データあり・DANGER_OK=1 → down -v → remove の順序 ---
new_env; make_wt
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R2 exit0"                0    "$RC"
ckhas "R2 down -v 呼出（-p で固定）" "$(cat "$DOCKER_LOG")" "compose -p wt-app down -v"
cknot "R2 worktree 撤去済"     "$(wl)" "/wt-app"
ckhas "R3 down→remove 順序(present=yes)" "$(cat "$DOCKER_LOG")" "present=yes"
# down -v は撤去対象のフォルダで実行される（呼び出し元＝primary で走ると primary の volume が消える）
ckhas "R3b down は撤去対象の中で実行" "$(grep -A1 'down -v' "$DOCKER_LOG")" "cwd=$TMP/wt-app"

# --- TC-R1g: 判定失敗（docker volume ls が失敗）→ 停止 ---
new_env; make_wt
DOCKER_FAIL_ON="volume ls" run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1g exit2"               2    "$RC"
ckhas "R1g worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R1h: 判定失敗（直下 .env に export 付きの COMPOSE_PROJECT_NAME）→ 停止 ---
new_env; make_wt
printf 'export COMPOSE_PROJECT_NAME = study\n' > "$WT/.env"
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1h exit2"               2    "$RC"
ckhas "R1h 名前を確定できない" "$OUT" "プロジェクト名を確定できません"
ckhas "R1h worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R1i: 判定失敗（直下 .env の COMPOSE_FILE）→ 停止 ---
new_env; make_wt
printf '  COMPOSE_FILE=other.yml\n' > "$WT/.env"   # 行頭に空白がある書き方も
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1i exit2"               2    "$RC"
ckhas "R1i worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R1j: 判定失敗（compose.yaml・override に最上位 name:）→ 停止 ---
for cf in compose.yaml compose.yml docker-compose.yaml docker-compose.yml \
          compose.override.yaml compose.override.yml docker-compose.override.yaml docker-compose.override.yml; do
  new_env; make_wt
  printf 'name : study\nservices: {}\n' > "$WT/$cf"   # コロンの前に空白がある書き方も
  git -C "$WT" add "$cf"; git -C "$WT" commit -qm "add $cf"; git -C "$WT" push -q origin "HEAD:refs/heads/tmp-$cf" 2>/dev/null
  git -C "$WT" fetch -q origin
  run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
  ck   "R1j $cf exit2"         2    "$RC"
  ckhas "R1j $cf 名前を確定できない" "$OUT" "プロジェクト名を確定できません"
done

# --- TC-R1k: 判定失敗（フォルダ名からプロジェクト名が作れない＝空）→ 停止 ---
new_env; make_wt "$TMP/___" feature/I003-x
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R1k exit2"               2    "$RC"
ckt  "R1k worktree 残存"       test -d "$TMP/___"

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

# ===================== ロック（公式 claude --worktree のセッションロック） =====================
# 存在しない pid（pid_max を超える値）＝終了済みセッション / テストを動かしているシェルの pid＝使用中セッション
DEAD_PID=99999999

# --- TC-R13: 終了済みセッションのロック・データ無し → ロックを外して撤去 ---
new_env; make_wt
git -C "$PRIMARY" worktree lock --reason "claude session app (pid $DEAD_PID start 1)" "$WT"
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R13 exit0"               0    "$RC"
cknot "R13 worktree 撤去済"    "$(wl)" "/wt-app"
ckhas "R13 ロック解除の案内"   "$OUT" "ロックを解除しました"

# --- TC-R14: 使用中セッションのロック・データあり・DANGER_OK=1 → down せず中止 ---
new_env; make_wt
git -C "$PRIMARY" worktree lock --reason "claude session app (pid $$ start 1)" "$WT"
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R14 exit2"               2    "$RC"
ckhas "R14 使用中の案内"       "$OUT" "使用中の Claude セッション"
cknot "R14 down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckhas "R14 worktree 残存"      "$(wl)" "/wt-app"
ckhas "R14 ロック維持"         "$(wl)" "locked claude session app"

# --- TC-R15: Claude 以外の理由のロック → down せず中止 ---
new_env; make_wt
git -C "$PRIMARY" worktree lock --reason "on usb drive" "$WT"
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R15 exit2"               2    "$RC"
ckhas "R15 ロックの案内"       "$OUT" "ロックされています（理由: on usb drive）"
cknot "R15 down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckhas "R15 worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R16: ps が無い環境でのロック → 生存を確認できないので中止 ---
new_env; make_wt
git -C "$PRIMARY" worktree lock --reason "claude session app (pid $DEAD_PID start 1)" "$WT"
NOPS="$TMP/nops"; mkdir -p "$NOPS"
for c in git sed head basename tr grep awk find bash env; do ln -s "$(command -v "$c")" "$NOPS/$c"; done
ln -s "$BIN/docker" "$NOPS/docker"
OUT="$( cd "$PRIMARY" && PATH="$NOPS" DOCKER_LOG="$DOCKER_LOG" "$BASH_BIN" "$WT_REMOVE" "$WT" 2>&1 )"; RC=$?
ck   "R16 exit2"               2    "$RC"
ckhas "R16 確認できない案内"   "$OUT" "ps が無いため"
ckhas "R16 worktree 残存"      "$(wl)" "/wt-app"

# ===================== 入れ子・名前の重なり・docker 不在 =====================

# --- TC-R17: 中に登録済みの入れ子ワークツリー（未コミット変更あり）→ 中止・入れ子の中身が残る ---
new_env; make_wt
git -C "$WT" worktree add -q "$WT/.claude/worktrees/agent-x" -b worktree-agent-x origin/develop
printf 'precious\n' > "$WT/.claude/worktrees/agent-x/work.txt"
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R17 exit2"               2    "$RC"
ckhas "R17 入れ子の案内"       "$OUT" "中に別のワークツリー"
cknot "R17 down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckt  "R17 入れ子の中身が残る"  test -f "$WT/.claude/worktrees/agent-x/work.txt"

# --- TC-R18: 中に未登録の git（prunable の残骸・入れ子 clone）→ 中止 ---
new_env; make_wt
mkdir -p "$WT/.claude/worktrees/stale"; printf 'gitdir: /nowhere\n' > "$WT/.claude/worktrees/stale/.git"
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R18 exit2"               2    "$RC"
ckhas "R18 入れ子の案内"       "$OUT" "中に別のワークツリー"
ckhas "R18 worktree 残存"      "$(wl)" "/wt-app"

# --- TC-R19: Compose プロジェクト名が別のワークツリー（primary）と同じ・データあり・DANGER_OK=1 → down せず中止 ---
new_env; make_wt "$TMP/other/primary" feature/I004-x
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R19 exit2"               2    "$RC"
ckhas "R19 名前の重なりの案内" "$OUT" "別のワークツリーと同じです"
cknot "R19 down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckt  "R19 worktree 残存"       test -d "$TMP/other/primary"
ckhas "R24 同名で止まってもバックアップ手順" "$OUT" "test -s backup_primary_"
# --- TC-R19b: 名前が重なってもデータが無ければ撤去できる ---
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R19b exit0"              0    "$RC"

# --- TC-R20: docker が無い・DANGER_OK=1 → down せずに撤去（警告） ---
new_env; make_wt
OUT="$( cd "$PRIMARY" && PATH="$NODOCKER" DANGER_OK=1 "$BASH_BIN" "$WT_REMOVE" "$WT" 2>&1 )"; RC=$?
ck   "R20a DANGER_OK=1 だけでは exit2" 2  "$RC"
ckhas "R20a KEEP_DATA の案内"  "$OUT" "KEEP_DATA=1"
ckhas "R20a worktree 残存"     "$(wl)" "/wt-app"
OUT="$( cd "$PRIMARY" && PATH="$NODOCKER" KEEP_DATA=1 "$BASH_BIN" "$WT_REMOVE" "$WT" 2>&1 )"; RC=$?
ck   "R20 KEEP_DATA=1 exit0"   0    "$RC"
ckhas "R20 警告"               "$OUT" "down -v を実行せずに撤去します（KEEP_DATA=1）"
cknot "R20 worktree 撤去済"    "$(wl)" "/wt-app"
# --- TC-R20c: docker が使える（データあり）ときは KEEP_DATA=1 でも down せず中止（KEEP_DATA は docker 不在専用） ---
new_env; make_wt
STUB_CONTAINERS=c1 KEEP_DATA=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R20c exit2"              2    "$RC"
cknot "R20c down 非実行"       "$(cat "$DOCKER_LOG")" "down"
ckhas "R20c worktree 残存"     "$(wl)" "/wt-app"

# --- TC-R21: コンテナの作業フォルダ（ラベル）が撤去対象と違う・DANGER_OK=1 → down せず中止 ---
new_env; make_wt
STUB_CONTAINERS=c1 STUB_WORKDIR="$PRIMARY" DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R21 exit2"               2    "$RC"
ckhas "R21 作業フォルダの案内" "$OUT" "作業フォルダが撤去対象と違います"
cknot "R21 down 非実行"        "$(cat "$DOCKER_LOG")" "down"
ckhas "R21e 戻り値 4 でもバックアップ手順" "$OUT" "test -s backup_wt-app_"
# --- TC-R21b: コンテナ 2 件のうち 2 件目だけが別の場所（先頭行だけの照合では見逃す） ---
new_env; make_wt
STUB_CONTAINERS=c1 STUB_WORKDIR="$(cd "$WT" && pwd -P)"$'\n'"$PRIMARY" DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R21b exit2"              2    "$RC"
cknot "R21b down 非実行"       "$(cat "$DOCKER_LOG")" "down"
# --- TC-R21c: 作業フォルダのラベルが空（古い compose 等）→ 中止 ---
new_env; make_wt
STUB_CONTAINERS=c1 STUB_WORKDIR="" DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R21c exit2"              2    "$RC"
cknot "R21c down 非実行"       "$(cat "$DOCKER_LOG")" "down"
# --- TC-R21d: 作業フォルダのラベルが symlink 経由の同じ場所 → 同じとみなして撤去できる（pwd -P で実パス化） ---
new_env; make_wt
ln -s "$WT" "$TMP/wt-link"
STUB_CONTAINERS=c1 STUB_WORKDIR="$TMP/wt-link" DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R21d exit0"              0    "$RC"
ckhas "R21d down 実行"         "$(cat "$DOCKER_LOG")" "compose -p wt-app down -v"
# --- TC-R22c: 名前を確定できない（.env の指定）・docker 不在・KEEP_DATA=1 → 中止（KEEP_DATA は戻り値 3 専用） ---
new_env; make_wt
printf 'COMPOSE_PROJECT_NAME=x\n' > "$WT/.env"
OUT="$( cd "$PRIMARY" && PATH="$NODOCKER" KEEP_DATA=1 "$BASH_BIN" "$WT_REMOVE" "$WT" 2>&1 )"; RC=$?
ck   "R22c exit2"              2    "$RC"
ckhas "R22c worktree 残存"     "$(wl)" "/wt-app"

# --- TC-R22: 名前を確定できない（COMPOSE_PROJECT_NAME あり）・DANGER_OK=1 → down せず中止 ---
new_env; make_wt
STUB_CONTAINERS=c1 COMPOSE_PROJECT_NAME="$(basename "$PRIMARY")" DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R22 exit2"               2    "$RC"
ckhas "R22 確定できない案内"   "$OUT" "DANGER_OK=1 でも撤去しません"
cknot "R22 down 非実行"        "$(cat "$DOCKER_LOG")" "down"
# --- TC-R22b: .env にコロン区切りの COMPOSE_PROJECT_NAME → 確定できない ---
new_env; make_wt
printf 'COMPOSE_PROJECT_NAME: prim\n' > "$WT/.env"
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R22b exit2"              2    "$RC"
cknot "R22b down 非実行"       "$(cat "$DOCKER_LOG")" "down"

# --- TC-R23: 中の入れ子の登録がフォルダごと消えている（prunable）だけなら撤去できる ---
new_env; make_wt
git -C "$WT" worktree add -q "$WT/.claude/worktrees/agent-y" -b worktree-agent-y origin/develop
# shellcheck disable=SC2016  # 単一引用は意図的（展開せずに渡す）
"$BASH_BIN" -c 'cd "$1" && find .claude/worktrees/agent-y -mindepth 1 -delete && rmdir .claude/worktrees/agent-y' _ "$WT"
BEFORE_R23="$(wl)"
run_rm "$PRIMARY" "$WT_REMOVE" "$WT"
ck   "R23 exit0"               0    "$RC"
LIST_R23="$(wl)"
ckt  "R23 worktree 撤去済"     test -z "$(grep -x "worktree $TMP/wt-app" <<<"$LIST_R23")"
ckt  "R23 撤去前は登録されていた（判定の前提）" test -n "$(grep -x "worktree $TMP/wt-app" <<<"$BEFORE_R23")"

# ===================== false-green 注入 =====================

# --- TC-FG5: down -v の前の cd を外した複製では R3b が落ちる（cwd 検証が実際に効く証明） ---
new_env; make_wt
BROKEN_CD="$TMP/wt-remove-nocd.sh"
# shellcheck disable=SC2016
sed 's/( cd "\$WT_PATH" && docker compose -p "\$PROJECT" down -v )/( docker compose -p "$PROJECT" down -v )/' "$WT_REMOVE" > "$BROKEN_CD"
# shellcheck disable=SC2016  # 単一引用は意図的（展開せずに渡す）
ck   "FG5 注入成立"            0    "$(grep -q '^    ( docker compose -p "\$PROJECT" down -v )' "$BROKEN_CD"; echo $?)"
STUB_CONTAINERS=c1 DANGER_OK=1 run_rm "$PRIMARY" "$BROKEN_CD" "$WT"
cknot "FG5 除去複製=撤去対象の外で down" "$(grep -A1 'down -v' "$DOCKER_LOG")" "cwd=$TMP/wt-app"

# --- TC-FG6: 入れ子の検査を除去した複製では R17 の条件で入れ子の中身が消える ---
new_env; make_wt
git -C "$WT" worktree add -q "$WT/.claude/worktrees/agent-x" -b worktree-agent-x origin/develop
printf 'precious\n' > "$WT/.claude/worktrees/agent-x/work.txt"
BROKEN_NS="$TMP/wt-remove-nonest.sh"
# shellcheck disable=SC2016  # 単一引用は意図的（$NESTED を展開せず sed パターンに渡す）
sed 's/^if \[ -n "\$NESTED" \]; then$/if false; then/' "$WT_REMOVE" > "$BROKEN_NS"
ck   "FG6 注入成立"            0    "$(grep -q '^if false; then$' "$BROKEN_NS"; echo $?)"
run_rm "$PRIMARY" "$BROKEN_NS" "$WT"
ckt  "FG6 除去複製=入れ子の中身が消える" test ! -e "$WT/.claude/worktrees/agent-x/work.txt"

# --- TC-FG4: 使用中判定を除去した複製では R14 の条件でも撤去される（実体の停止要因が使用中判定である反証） ---
new_env; make_wt
git -C "$PRIMARY" worktree lock --reason "claude session app (pid $$ start 1)" "$WT"
BROKEN_LK="$TMP/wt-remove-nolive.sh"
# shellcheck disable=SC2016  # 単一引用は意図的（$LOCK_PID を展開せず sed パターンに渡す）
sed 's/if \[ -e "\/proc\/$LOCK_PID" \] || ps -p "$LOCK_PID" >\/dev\/null 2>&1; then/if false; then/' "$WT_REMOVE" > "$BROKEN_LK"
ck   "FG4 注入成立"            0    "$(grep -q '^  if false; then' "$BROKEN_LK"; echo $?)"
run_rm "$PRIMARY" "$BROKEN_LK" "$WT"
ck   "FG4 除去複製=exit0"      0    "$RC"
cknot "FG4 除去複製=撤去済"    "$(wl)" "/wt-app"

# --- TC-FG1: DANGER_OK ゲート除去複製では R1 の条件でも down される（実体の停止要因がゲートである反証） ---
new_env; make_wt
BROKEN_RM="$TMP/wt-remove-broken.sh"
# shellcheck disable=SC2016  # 単一引用は意図的（${DANGER_OK:-} を展開せず sed パターンに渡す）
sed 's/if \[ "${DANGER_OK:-}" != "1" \]; then/if false; then/' "$WT_REMOVE" > "$BROKEN_RM"
ck   "FG1 注入成立(if false)"  0    "$(grep -q '^    if false; then' "$BROKEN_RM"; echo $?)"
STUB_CONTAINERS=c1 run_rm "$PRIMARY" "$BROKEN_RM" "$WT"
ckhas "FG1 除去複製=未設定でも down" "$(cat "$DOCKER_LOG")" "compose -p wt-app down -v"

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
