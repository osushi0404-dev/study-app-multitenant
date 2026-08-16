#!/bin/bash
# I113 決定論テスト: pr-base-sync.sh の分岐網羅（T1〜T16）
# 実 GitHub / 実 git に依存せず、gh・git のスタブを PATH 先頭に挿して全分岐を検証する。
# テスト対象は TARGET_SCRIPT で差し替え可能（TC-02 の false-green 注入用・I114 の I114_TEST_SKILL と同方式）。
set -u

cd "$(git rev-parse --show-toplevel)" || exit 1
TARGET_SCRIPT="${TARGET_SCRIPT:-scripts/claude/pr-base-sync.sh}"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
STUB_DIR="$WORK/bin"
mkdir -p "$STUB_DIR"

# gh スタブ: mergeStateStatus はキュー（STATE_FILE）から返す（残り1行になったら以後その値を返し続ける）。
# GH_FAIL=1 のときは mergeStateStatus 照会のみ失敗させる（T15/T16）。
cat > "$STUB_DIR/gh" <<'EOF'
#!/bin/bash
case "$*" in
  *isCrossRepository*)
    # I146: cross-repo 判定。GH_FAIL_CROSS=1 で照会失敗（T19）。
    [ "${GH_FAIL_CROSS:-0}" = "1" ] && exit 1
    printf '%s\n' "${CROSS_VALUE-false}"
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
  *checks*) cat "$CHECKS_FILE" ;;
  *) exit 0 ;;
esac
EOF

# git スタブ: 呼び出し引数を GIT_LOG に記録。MERGE_FAIL=1 で merge（--abort 以外）を失敗させる（T11）。
cat > "$STUB_DIR/git" <<'EOF'
#!/bin/bash
echo "$*" >> "$GIT_LOG"
case "$*" in
  "merge --abort"*) exit 0 ;;
  merge\ *) [ "${MERGE_FAIL:-0}" = "1" ] && exit 1; exit 0 ;;
  diff\ *) echo "conflict-file.txt" ;;
esac
exit 0
EOF
chmod +x "$STUB_DIR/gh" "$STUB_DIR/git"

PASS=0
NG=0

# run_case <名前> <mode> <状態キュー(カンマ区切り)> <checks内容> <MERGE_FAIL> <GH_FAIL> <LOOP_MAX> <期待exit>
# 実行後、直近の GIT_LOG は $LAST_LOG で参照できる（副作用アサーション用）
run_case() {
  local name="$1" mode="$2" states="$3" checks="$4" merge_fail="$5" gh_fail="$6" loop_max="$7" expect="$8"
  local state_file="$WORK/state.$name" checks_file="$WORK/checks.$name" rc
  LAST_LOG="$WORK/gitlog.$name"
  echo "$states" | tr ',' '\n' > "$state_file"
  printf '%s\n' "$checks" > "$checks_file"
  : > "$LAST_LOG"
  STATE_FILE="$state_file" CHECKS_FILE="$checks_file" GIT_LOG="$LAST_LOG" \
    MERGE_FAIL="$merge_fail" GH_FAIL="$gh_fail" \
    CROSS_VALUE="${CROSS_VALUE-false}" GH_FAIL_CROSS="${GH_FAIL_CROSS:-0}" \
    PBS_RETRY_INTERVAL=0 PBS_CI_INTERVAL=0 PBS_CI_TIMEOUT=0 PBS_LOOP_MAX="$loop_max" \
    PATH="$STUB_DIR:$PATH" bash "$TARGET_SCRIPT" "$mode" 219 >/dev/null 2>&1
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

CHECKS_GREEN="build	pass	1m30s
test	pass	2m10s"
CHECKS_FAIL="build	fail	1m30s"

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

echo "---"
if [ "$NG" -gt 0 ]; then
  echo "RESULT: NG (${NG} 件 / pass ${PASS})"
  exit 1
fi
echo "RESULT: OK (21/21 cases, ${PASS} assertions)"
