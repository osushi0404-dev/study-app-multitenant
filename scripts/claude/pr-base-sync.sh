#!/bin/bash
# I113: /close 用 base 追従チェック（mergeStateStatus 単一ソース・fail-closed）
# 使い方: bash scripts/claude/pr-base-sync.sh <sync|final> [PR番号]
#   sync  = /close step 0 用: BEHIND なら origin/<base> を merge するだけ（push/CI なし）
#   final = gh pr ready 直後用: BEHIND なら merge→push→CI 待機。
#           合格条件は「BEHIND/DIRTY でない ＋ CI 全グリーン」（CLEAN は要求しない＝Approve 待ちの BLOCKED は正常）
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
CI_INTERVAL="${PBS_CI_INTERVAL:-15}"        # CI ポーリング間隔（秒）＝code-review.sh と同値
CI_TIMEOUT="${PBS_CI_TIMEOUT:-600}"         # CI 待機上限（秒）＝code-review.sh と同値
LOOP_MAX="${PBS_LOOP_MAX:-3}"               # final の BEHIND 追従再チェック上限

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

ci_wait() {  # code-review.sh L214-237 と同型: pending 待機・fail 時 STOP
  local elapsed=0 out
  while :; do
    out=$(gh pr checks "$PR_NUM" 2>&1 || true)
    if echo "$out" | grep -q "fail"; then echo "⛔ CI 失敗:"; echo "$out"; exit 1; fi
    echo "$out" | grep -q "pending" || return 0
    if [ "$elapsed" -ge "$CI_TIMEOUT" ]; then echo "⚠️ CI タイムアウト（${CI_TIMEOUT}秒）"; exit 1; fi
    echo "  pending... ${elapsed}s / ${CI_TIMEOUT}s"
    sleep "$CI_INTERVAL"; elapsed=$((elapsed + CI_INTERVAL))
  done
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
      ci_wait ;;                                   # 追従後に再チェック（ループ先頭へ）
    DIRTY)   echo "⛔ DIRTY（コンフリクト）。STOP してユーザーに報告"; exit 1 ;;
    DRAFT)   echo "⛔ Ready 化後も DRAFT のまま（gh pr ready が効いていない可能性）。STOP してユーザーに報告"; exit 1 ;;
    UNKNOWN) echo "⚠️ UNKNOWN が ${RETRY_MAX} 回リトライ後も継続。続行可否をユーザーに確認"; exit 2 ;;
    BLOCKED|UNSTABLE) ci_wait; echo "✅ CI 全グリーン（${S}＝Approve 待ち等）。マージ依頼へ進めます"; exit 0 ;;
    CLEAN|HAS_HOOKS)  echo "✅ ${S}（マージ可・CI 通過）。マージ依頼へ進めます"; exit 0 ;;
    *)       echo "⚠️ 未知の mergeStateStatus: ${S}。STOP してユーザーに報告"; exit 1 ;;
  esac
done
