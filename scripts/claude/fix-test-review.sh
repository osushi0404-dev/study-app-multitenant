#!/usr/bin/env bash
# fix-test-review.sh — /fix-loop 手順6.5（テストレビュー・テスト後）（I074）。
# 使い方: bash scripts/claude/fix-test-review.sh I### <test_result_path> [prior_ng_review_path]
#   第3引数（任意）: 直前 REMAND のテストレビュー記録。渡すと reviewer が各前回NG指摘の解消を fail-closed 検証する。
# 入力: 作業ツリー全差分（修正＋テスト）＋未追跡新規ファイル＋テスト実行結果ファイル（＋任意で前回NG）。差し戻し先: 手順5/6。
# ※テスト十分性・false-green 判定には修正の可視化が必須のため、テスト差分単体でなく全差分を渡す。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/claude/fix-review-lib.sh"

ISSUE="${1:?Usage: $0 I### <test_result_path> [prior_ng_review_path]}"
RESULT="${2:?テスト実行結果ファイルのパスを渡してください（手順6.5(a) で保存した docs/reviews/${ISSUE}_fix_test_result_<ts>.md）}"
PRIOR="${3:-}"
REVIEWER=".claude/review-agents/fix-test-reviewer.md"

if [ ! -f "$RESULT" ]; then
  echo "⚠️ テスト実行結果ファイルが見つかりません: ${RESULT}。テストレビューを skip します。"
  echo "FIX_GATE: SKIP"; exit 0
fi

# 修正＋テストを含む全差分（テスト十分性判定のため fix を可視化）
DIFF="$(git diff; git diff --staged)"

UNTRACKED=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  UNTRACKED+=$'\n'"=== 新規ファイル: ${f} ==="$'\n'"$(cat "$f" 2>/dev/null)"
done < <(git ls-files --others --exclude-standard)

# 再レビュー時の前回NG（オプション）: 各指摘の diff 上の解消を fail-closed で検証させる
PRIOR_SECTION=""
if [ -n "$PRIOR" ] && [ -f "$PRIOR" ]; then
  PRIOR_SECTION="

### 前回NG指摘（再レビュー: 各指摘が上記 差分/テストで解消したか検証せよ。確認できなければ未解消として REMAND）
$(cat "$PRIOR")"
fi

CONTEXT="イシュー: ${ISSUE}

### 作業ツリー全差分（修正＋テスト・レビュー対象データ）
${DIFF}

### 未追跡新規ファイル
${UNTRACKED}

### テスト実行結果（レビュー対象データ）
$(cat "$RESULT")${PRIOR_SECTION}"

run_fix_review "$ISSUE" "test" "$REVIEWER" "$CONTEXT" "手順5/6（テスト追記・修正→再テスト）"
