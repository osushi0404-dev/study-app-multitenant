#!/bin/bash
# I113 決定論テスト: pr-base-sync.sh の分岐網羅（T1〜T26）
# 実 GitHub / 実 git に依存せず、gh・git・sleep のスタブを PATH 先頭に挿して全分岐を検証する。
# テスト対象は TARGET_SCRIPT で差し替え可能。失敗の注入 FG1・FG2 は、壊した写しを CASE_SCRIPT で 1 ケースずつ流す。
# I530: final の CI 待ちは code-review.sh の wait_ci（同じフォルダの code-review.sh を読む）。
#   スタブは wait_ci の呼び方（pr checks --json・headRefOid・git rev-parse HEAD）に合わせ、ジョブ名は CI_WORKFLOWS の一時の yml から読む（PyYAML が要る）
set -u

cd "$(git rev-parse --show-toplevel)" || exit 1
TARGET_SCRIPT="${TARGET_SCRIPT:-scripts/claude/pr-base-sync.sh}"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
STUB_DIR="$WORK/bin"
mkdir -p "$STUB_DIR"

# gh スタブ: mergeStateStatus はキュー（STATE_FILE）から返す（残り1行になったら以後その値を返し続ける）。
# GH_FAIL=1 のときは mergeStateStatus 照会のみ失敗させる（T15/T16）。
# pr checks は --json の有無とも CHECKS_FILE（`<bucket>\t<name>` の行）を返す（wait_ci の --jq の結果と同じ形）
cat > "$STUB_DIR/gh" <<'EOF'
#!/bin/bash
case "$*" in
  *isCrossRepository*)
    # I146: cross-repo 判定。GH_FAIL_CROSS=1 で照会失敗（T19）。
    [ "${GH_FAIL_CROSS:-0}" = "1" ] && exit 1
    # 対象 PR（219）への照会にだけ CROSS_VALUE を返し、それ以外の PR・識別子なしは自前（false）と答える
    # （「別の PR を照会して素通し」を tautology で見逃さないため）。
    if [ "$1 $2 $3" = "pr view 219" ]; then
      printf '%s\n' "${CROSS_VALUE-false}"
    else
      printf 'false\n'
    fi
    ;;
  *mergeStateStatus*)
    [ "${GH_FAIL:-0}" = "1" ] && exit 1
    if [ "$(wc -l < "$STATE_FILE")" -gt 1 ]; then
      head -1 "$STATE_FILE"
      tail -n +2 "$STATE_FILE" > "$STATE_FILE.tmp"
      mv "$STATE_FILE.tmp" "$STATE_FILE"
    else
      head -1 "$STATE_FILE"
    fi
    ;;
  *baseRefName*) echo "develop" ;;
  *"--json number"*) echo "42" ;;
  *headRefOid*) printf '%s\n' "${PR_HEAD-$FAKE_HEAD}" ;;
  *checks*) cat "$CHECKS_FILE" ;;
  *) exit 0 ;;
esac
EOF

# git スタブ: 呼び出し引数を GIT_LOG に記録。MERGE_FAIL=1 で merge（--abort 以外）を失敗させる（T11）。
# rev-parse HEAD は FAKE_HEAD（wait_ci が PR の最新のコミットと比べる）
cat > "$STUB_DIR/git" <<'EOF'
#!/bin/bash
echo "$*" >> "$GIT_LOG"
case "$*" in
  "rev-parse HEAD") printf '%s\n' "$FAKE_HEAD" ;;
  "merge --abort"*) exit 0 ;;
  merge\ *) [ "${MERGE_FAIL:-0}" = "1" ] && exit 1; exit 0 ;;
  diff\ *) echo "conflict-file.txt" ;;
esac
exit 0
EOF
printf '#!/bin/bash\nexit 0\n' > "$STUB_DIR/sleep"
chmod +x "$STUB_DIR/gh" "$STUB_DIR/git" "$STUB_DIR/sleep"
WF="$WORK/wf.yml"
printf 'jobs:\n  build:\n    runs-on: x\n  test:\n    runs-on: x\n' > "$WF"
export FAKE_HEAD="fake-local-head"   # wait_ci は文字列の一致だけを見る

PASS=0
NG=0

# run_case <名前> <mode> <状態キュー(カンマ区切り)> <checks内容> <MERGE_FAIL> <GH_FAIL> <LOOP_MAX> <期待exit>
# 実行後、直近の GIT_LOG は $LAST_LOG、出力は $LAST_OUT で参照できる（副作用・出力のアサーション用）
run_case() {
  local name="$1" mode="$2" states="$3" checks="$4" merge_fail="$5" gh_fail="$6" loop_max="$7" expect="$8"
  local state_file="$WORK/state.$name" checks_file="$WORK/checks.$name" rc
  LAST_LOG="$WORK/gitlog.$name"
  LAST_OUT="$WORK/out.$name"
  echo "$states" | tr ',' '\n' > "$state_file"
  if [ -n "$checks" ]; then printf '%b\n' "$checks" > "$checks_file"; else : > "$checks_file"; fi
  : > "$LAST_LOG"
  STATE_FILE="$state_file" CHECKS_FILE="$checks_file" GIT_LOG="$LAST_LOG" \
    MERGE_FAIL="$merge_fail" GH_FAIL="$gh_fail" \
    CROSS_VALUE="${CROSS_VALUE-false}" GH_FAIL_CROSS="${GH_FAIL_CROSS:-0}" \
    PR_HEAD="${PR_HEAD-$FAKE_HEAD}" CI_WORKFLOWS="$WF" \
    PBS_RETRY_INTERVAL=0 CI_WAIT_TIMEOUT=1 CI_POLL_INTERVAL=1 PBS_LOOP_MAX="$loop_max" \
    PATH="$STUB_DIR:$PATH" timeout 60 bash "${CASE_SCRIPT:-$TARGET_SCRIPT}" "$mode" 219 > "$LAST_OUT" 2>&1
  rc=$?
  if [ "$rc" -eq "$expect" ]; then
    echo "OK: $name (exit=$rc)"
    PASS=$((PASS+1))
  else
    echo "NG: $name (expect=$expect actual=$rc)"
    NG=$((NG+1))
  fi
}

# 副作用アサーション: 直近ケースの GIT_LOG に対する grep（あり/なし）
log_has() {
  if grep -qF -- "$1" "$LAST_LOG"; then
    echo "OK: $2"; PASS=$((PASS+1))
  else
    echo "NG: $2"; NG=$((NG+1))
  fi
}
log_not() {
  if grep -qF -- "$1" "$LAST_LOG"; then
    echo "NG: $2"; NG=$((NG+1))
  else
    echo "OK: $2"; PASS=$((PASS+1))
  fi
}
# 出力アサーション: 直近ケースの出力に文字列がある
out_has() {
  if grep -qF -- "$1" "$LAST_OUT"; then
    echo "OK: $2"; PASS=$((PASS+1))
  else
    echo "NG: $2"; NG=$((NG+1))
  fi
}

CHECKS_GREEN='pass\tbuild\npass\ttest'
CHECKS_FAIL='fail\tbuild'
CHECKS_PARTIAL='pass\tbuild'
CHECKS_NONE=''

# --- sync モード ---
run_case "T1 sync CLEAN=続行"                sync  "CLEAN"          "$CHECKS_GREEN" 0 0 3 0
log_not  "merge"                             "T1 副作用なし（merge が呼ばれない）"
run_case "T2 sync BEHIND=取り込みのみ"        sync  "BEHIND"         "$CHECKS_GREEN" 0 0 3 0
log_has  "fetch origin develop"              "T2 fetch origin develop 実行"
log_has  "merge origin/develop --no-edit"    "T2 merge origin/develop 実行"
log_not  "push"                              "T2 push しない（step 3 相乗り）"
run_case "T3 sync DIRTY=STOP"                sync  "DIRTY"          "$CHECKS_GREEN" 0 0 3 1
run_case "T4 sync DRAFT=正常続行"             sync  "DRAFT"          "$CHECKS_GREEN" 0 0 3 0
run_case "T5 sync UNKNOWN継続=ユーザー確認"   sync  "UNKNOWN"        "$CHECKS_GREEN" 0 0 3 2
run_case "T6 sync UNKNOWN→BEHIND=リトライ"    sync  "UNKNOWN,BEHIND" "$CHECKS_GREEN" 0 0 3 0
log_has  "merge origin/develop --no-edit"    "T6 リトライ後に merge 実行"

# --- final モード ---
run_case "T7 final CLEAN=合格"                final "CLEAN"          "$CHECKS_GREEN" 0 0 3 0
run_case "T8 final BLOCKED+CI緑=Approve待ち合格" final "BLOCKED"     "$CHECKS_GREEN" 0 0 3 0
run_case "T9 final UNSTABLE+CI fail=STOP"     final "UNSTABLE"       "$CHECKS_FAIL"  0 0 3 1
out_has  "⛔ CI 失敗"                          "T9 出力に ⛔ CI 失敗"
run_case "T10 final BEHIND→追従→合格"          final "BEHIND,BLOCKED" "$CHECKS_GREEN" 0 0 3 0
log_has  "push"                              "T10 push 実行（フルモード）"
run_case "T11 final BEHIND+コンフリクト=STOP"  final "BEHIND"         "$CHECKS_GREEN" 1 0 3 1
log_has  "merge --abort"                     "T11 作業ツリー復元（merge --abort）"
run_case "T12 final DRAFT継続=STOP"           final "DRAFT"          "$CHECKS_GREEN" 0 0 3 1
run_case "T13 final BEHIND連続=上限STOP"      final "BEHIND"         "$CHECKS_GREEN" 0 0 1 1
run_case "T14 final 未知値=STOP"              final "HOGE"           "$CHECKS_GREEN" 0 0 3 1

# --- 取得失敗の fail-closed（plan review Blocker 再発防止） ---
run_case "T15 sync 照会失敗=STOP"             sync  "CLEAN"          "$CHECKS_GREEN" 0 1 3 1
run_case "T16 final 照会失敗=STOP"            final "CLEAN"          "$CHECKS_GREEN" 0 1 3 1

# --- I146: cross-repo（fork）PR ガード（sync/final 共通・fail-closed） ---
# T17/T18 は BEHIND を与える（ガードが無ければ merge/push まで進む状態＝副作用アサーションが意味を持つ）
CROSS_VALUE=true run_case "T17 sync cross-repo=STOP"   sync  "BEHIND" "$CHECKS_GREEN" 0 0 3 1
log_not  "merge"                              "T17 副作用なし（merge が呼ばれない）"
CROSS_VALUE=true run_case "T18 final cross-repo=STOP"  final "BEHIND" "$CHECKS_GREEN" 0 0 3 1
log_not  "push"                               "T18 副作用なし（push が呼ばれない）"
GH_FAIL_CROSS=1  run_case "T19 sync 照会失敗=STOP"      sync  "CLEAN" "$CHECKS_GREEN" 0 0 3 1
CROSS_VALUE=""   run_case "T20 sync 空値=STOP"          sync  "CLEAN" "$CHECKS_GREEN" 0 0 3 1
CROSS_VALUE=hoge run_case "T21 sync 想定外値=STOP"      sync  "CLEAN" "$CHECKS_GREEN" 0 0 3 1

# --- I530: CI がそろうまで合格にしない（wait_ci）・NOT_PUSHED・sync は code-review.sh を読まない ---
run_case "T22 final BLOCKED+チェック無し=STOP"  final "BLOCKED" "$CHECKS_NONE"    0 0 3 1
out_has  "⚠️ CI タイムアウト（1秒）"             "T22 出力に ⚠️ CI タイムアウト（1秒）"
run_case "T23 final BLOCKED+一部だけ登録=STOP"  final "BLOCKED" "$CHECKS_PARTIAL" 0 0 3 1
run_case "T24 final CLEAN+チェック無し=STOP"    final "CLEAN"   "$CHECKS_NONE"    0 0 3 1
PR_HEAD=deadbeef run_case "T25 final PR の最新のコミットが手元と違う=STOP" final "BLOCKED" "$CHECKS_GREEN" 0 0 3 1
out_has  "NOT_PUSHED"                          "T25 出力に NOT_PUSHED"
T26_DIR="$WORK/t26"; mkdir -p "$T26_DIR"; cp "$TARGET_SCRIPT" "$T26_DIR/pr-base-sync.sh"
CASE_SCRIPT="$T26_DIR/pr-base-sync.sh" run_case "T26 sync は code-review.sh が無くても続行" sync "CLEAN" "$CHECKS_GREEN" 0 0 3 0

# --- I530 失敗の注入: 壊した写しに T22〜T24 と同じ入力を与え、exit 0（＝穴が開く）になることを確かめる ---
# 本物の T22〜T24 は exit 1 を求めるので、同じ壊し方が本物に入れば T22〜T24 が NG になる（本物のファイルは書き換えない）
# fg_copy <名前> <sed の式>: 写しのフォルダを作り pr-base-sync.sh を壊して、写しのパスを出す。壊し方が効いていなければ失敗
fg_copy() {
  local d="$WORK/$1"; mkdir -p "$d"
  cp "$TARGET_SCRIPT" "$d/pr-base-sync.sh"
  cp "$(dirname "$TARGET_SCRIPT")/code-review.sh" "$d/code-review.sh"
  sed -i "$2" "$d/pr-base-sync.sh"
  ! cmp -s "$d/pr-base-sync.sh" "$TARGET_SCRIPT" && echo "$d/pr-base-sync.sh"
}
# FG1: run_wait_ci の中身を古い判定（チェックの一覧に fail が無ければ合格）に置き換える
# shellcheck disable=SC2016  # 単一引用符の中は写しに書き込むコードの文字どおり
if FG=$(fg_copy FG1 '/^run_wait_ci() {$/a\  local out; out=$(gh pr checks "$PR_NUM" 2>\&1 || true); if echo "$out" | grep -q fail; then exit 1; fi; return 0'); then
  CASE_SCRIPT="$FG" run_case "FG1 古い判定の写しは T22 の入力で合格してしまう" final "BLOCKED" "$CHECKS_NONE"    0 0 3 0
  CASE_SCRIPT="$FG" run_case "FG1 古い判定の写しは T23 の入力で合格してしまう" final "BLOCKED" "$CHECKS_PARTIAL" 0 0 3 0
else echo "NG: FG1 の壊し方が効かない"; NG=$((NG+1)); fi
# FG2: CLEAN|HAS_HOOKS の行から run_wait_ci を消す
if FG=$(fg_copy FG2 '/^ *CLEAN|HAS_HOOKS)/s/run_wait_ci; //'); then
  CASE_SCRIPT="$FG" run_case "FG2 CLEAN で待たない写しは T24 の入力で合格してしまう" final "CLEAN" "$CHECKS_NONE" 0 0 3 0
else echo "NG: FG2 の壊し方が効かない"; NG=$((NG+1)); fi

echo "---"
if [ "$NG" -gt 0 ]; then
  echo "RESULT: NG (${NG} 件 / pass ${PASS})"
  exit 1
fi
echo "RESULT: OK (26 cases, ${PASS} assertions)"
