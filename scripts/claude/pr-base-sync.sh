#!/bin/bash
# I113: /close 用 base 追従チェック（mergeStateStatus 単一ソース・fail-closed）
# 使い方: bash scripts/claude/pr-base-sync.sh <sync|final> [PR番号]
#   sync  = /close step 0 用: BEHIND なら origin/<base> を merge するだけ（push/CI なし）
#   final = gh pr ready 直後用: BEHIND なら merge→push→CI 待機。
#           合格条件は「BEHIND/DIRTY でない ＋ CI のジョブが全部そろって合格」（CLEAN は要求しない＝Approve 待ちの BLOCKED は正常）。
#           CI の判定は code-review.sh の wait_ci の 1 か所（I530）
# 終了コード: 0=続行OK / 1=STOP（コンフリクト・CI fail・DRAFT 残留・未知値） / 2=UNKNOWN 上限（続行可否をユーザー確認）
set -u

MODE="${1:?Usage: pr-base-sync.sh <sync|final> [PR番号]}"
case "$MODE" in sync|final) ;; *) echo "⚠️ MODE は sync / final のみ: $MODE"; exit 1 ;; esac
PR_NUM="${2:-}"
if [ -z "$PR_NUM" ]; then
  PR_NUM=$(gh pr view --json number -q .number) || { echo "⚠️ PR を特定できません"; exit 1; }
fi

RETRY_INTERVAL="${PBS_RETRY_INTERVAL:-5}"   # UNKNOWN/DRAFT 再取得間隔（秒）＝イシュー確定値
RETRY_MAX="${PBS_RETRY_MAX:-6}"             # 再取得回数（計30秒）＝イシュー確定値
LOOP_MAX="${PBS_LOOP_MAX:-3}"               # final の BEHIND 追従再チェック上限
# CI 待ちの判定・上限・間隔は code-review.sh の wait_ci（CI_WAIT_TIMEOUT・CI_POLL_INTERVAL）の 1 か所（I498・I530）
CR_SCRIPT="$(dirname "${BASH_SOURCE[0]}")/code-review.sh"

# I146: cross-repo（fork）PR ガード。MODE 分岐より前＝sync/final 共通で必ず走る。
# 自前でない PR に base 追従・push をしない（fail-closed: 取得失敗・空値・想定外値も STOP）。
CROSS=$(gh pr view "$PR_NUM" --json isCrossRepository -q .isCrossRepository) \
  || { echo "⛔ isCrossRepository の取得に失敗しました。STOP してユーザーに報告"; exit 1; }
case "$CROSS" in
  false) ;;   # 自前 PR → 続行
  true)
    echo "⛔ PR #${PR_NUM} は fork（外部リポジトリ）由来です。base 追従・push・CI 対応はしません。"
    echo "   外部からのコード寄稿は受け付けていません（CONTRIBUTING.md）。"
    echo "   方針コメント付きで close してください（docs/runbooks/workflow.md）。"
    exit 1 ;;
  *)
    echo "⛔ isCrossRepository が想定外の値です: '${CROSS}'。STOP してユーザーに報告"; exit 1 ;;
esac

BASE=$(gh pr view "$PR_NUM" --json baseRefName -q .baseRefName) || { echo "⚠️ baseRefName 取得失敗"; exit 1; }

# 取得失敗・空値は return 1（fail-closed）。エラーメッセージは >&2（$() にキャプチャさせない）
get_status() {
  local v
  v=$(gh pr view "$PR_NUM" --json mergeStateStatus -q .mergeStateStatus) || { echo "⚠️ mergeStateStatus 取得失敗" >&2; return 1; }
  [ -n "$v" ] || { echo "⚠️ mergeStateStatus が空値" >&2; return 1; }
  printf '%s\n' "$v"
}

# UNKNOWN（と final の DRAFT）は反映ラグの可能性があるためリトライして確定値を得る。
# 途中の取得失敗も return 1 で呼び出し元へ伝播する（fail-closed）
resolve_status() {
  local s i=0
  s=$(get_status) || return 1
  while [ "$i" -lt "$RETRY_MAX" ]; do
    case "$s" in
      UNKNOWN) ;;                                # 常にリトライ対象
      DRAFT) [ "$MODE" = "final" ] || break ;;   # sync では DRAFT は確定値（step 0 の正常状態）
      *) break ;;
    esac
    sleep "$RETRY_INTERVAL"; i=$((i+1))
    s=$(get_status) || return 1
  done
  echo "$s"
}

merge_base() {
  git fetch origin "$BASE" || { echo "⚠️ git fetch 失敗"; exit 1; }
  if ! git merge "origin/$BASE" --no-edit; then
    echo "⛔ マージコンフリクト。自動解決しません（fail-closed）。競合ファイル:"
    git diff --name-only --diff-filter=U
    git merge --abort
    echo "（作業ツリーは merge 前の状態に復元済み。解決方針をユーザーに確認してから再実行）"
    exit 1
  fi
}

# I530: CI 待ち。code-review.sh を関数だけ読み込む形（REVIEW_LIB_SOURCE_ONLY=1）で別の bash に読ませ、wait_ci を呼ぶ
# （同じシェルで読むと code-review.sh の set -euo pipefail がこのスクリプトに入るため）。
# 合格（戻り値 0 かつ CI_WAIT: OK）なら return 0。それ以外は理由を出して exit 1（止まる側）
run_wait_ci() {
  local log rc result limit
  log=$(mktemp) || { echo "⛔ 一時ファイルを作れません。STOP してユーザーに報告"; exit 1; }
  # shellcheck disable=SC2016  # 単一引用符の中は子の bash が展開する
  REVIEW_LIB_SOURCE_ONLY=1 bash -c '
    . "$1" || exit 4
    rc=0; wait_ci "$2" || rc=$?
    [ "$rc" -ne 3 ] || echo "CI_WAIT_LIMIT: ${CI_WAIT_TIMEOUT:-$CI_WAIT_TIMEOUT_DEFAULT}"
    exit "$rc"' _ "$CR_SCRIPT" "$PR_NUM" 2>&1 | tee "$log"
  rc=${PIPESTATUS[0]}
  result=$(grep '^CI_WAIT: ' "$log" | tail -1)
  limit=$(sed -n 's/^CI_WAIT_LIMIT: //p' "$log" | tail -1)
  rm -f "$log"
  case "${rc}:${result}" in
    "0:CI_WAIT: OK")         return 0 ;;
    3:*)                     echo "⚠️ CI タイムアウト（${limit}秒）"; exit 1 ;;
    "1:CI_WAIT: FAIL")       echo "⛔ CI 失敗（上のチェックの一覧を見る）"; exit 1 ;;
    "1:CI_WAIT: NOT_PUSHED") echo "⛔ 手元のコミットが PR に送られていません（CI_WAIT: NOT_PUSHED）。push してから final をやり直す"; exit 1 ;;
    "1:CI_WAIT: NO_JOBS")    echo "⛔ PR で動くワークフローのジョブ名を読めません（CI_WAIT: NO_JOBS）。STOP してユーザーに報告"; exit 1 ;;
    4:*)                     echo "⛔ CI 待ちの処理（${CR_SCRIPT}）を読み込めません。STOP してユーザーに報告"; exit 1 ;;
    *)                       echo "⛔ CI 待ちが想定外の終わり方をしました（rc=${rc} ${result:-CI_WAIT 行なし}）。STOP してユーザーに報告"; exit 1 ;;
  esac
}

if [ "$MODE" = "sync" ]; then
  # $() はサブシェルのため、resolve_status 内の失敗は || で親に伝播させる（fail-open 防止）
  S=$(resolve_status) || { echo "⛔ mergeStateStatus が取得できません。STOP してユーザーに報告"; exit 1; }
  case "$S" in
    BEHIND)  merge_base; echo "✅ base（origin/${BASE}）を取り込みました（push は step 3 の close コミットに相乗り）" ;;
    DIRTY)   echo "⛔ DIRTY（マージ不能・コンフリクト予測）。STOP してユーザーに報告"; exit 1 ;;
    UNKNOWN) echo "⚠️ UNKNOWN が ${RETRY_MAX} 回リトライ後も継続。続行可否をユーザーに確認"; exit 2 ;;
    *)       echo "✅ 追従不要（mergeStateStatus=${S}）" ;;   # CLEAN/HAS_HOOKS/BLOCKED/UNSTABLE/DRAFT
  esac
  exit 0
fi

# final モード
n=0
while :; do
  S=$(resolve_status) || { echo "⛔ mergeStateStatus が取得できません。STOP してユーザーに報告"; exit 1; }
  case "$S" in
    BEHIND)
      n=$((n+1))
      if [ "$n" -gt "$LOOP_MAX" ]; then echo "⛔ base が進み続けています（${LOOP_MAX} 回追従済み）。STOP してユーザーに報告"; exit 1; fi
      merge_base
      git push || { echo "⚠️ git push 失敗"; exit 1; }
      run_wait_ci ;;                               # 追従後に再チェック（ループ先頭へ）
    DIRTY)   echo "⛔ DIRTY（コンフリクト）。STOP してユーザーに報告"; exit 1 ;;
    DRAFT)   echo "⛔ Ready 化後も DRAFT のまま（gh pr ready が効いていない可能性）。STOP してユーザーに報告"; exit 1 ;;
    UNKNOWN) echo "⚠️ UNKNOWN が ${RETRY_MAX} 回リトライ後も継続。続行可否をユーザーに確認"; exit 2 ;;
    BLOCKED|UNSTABLE) run_wait_ci; echo "✅ CI 全グリーン（${S}＝Approve 待ち等）。マージ依頼へ進めます"; exit 0 ;;
    CLEAN|HAS_HOOKS)  run_wait_ci; echo "✅ ${S}（マージ可・CI 通過）。マージ依頼へ進めます"; exit 0 ;;
    *)       echo "⚠️ 未知の mergeStateStatus: ${S}。STOP してユーザーに報告"; exit 1 ;;
  esac
done
