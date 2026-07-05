#!/usr/bin/env bash
# fix-diagnosis-review.sh — /fix-loop 手順3.5（診断レビュー・修正前）（I074）。
# 使い方: bash scripts/claude/fix-diagnosis-review.sh I### <diagnosis_memo_path>
# 入力: 診断メモ（失敗分解／根本原因／対応方針＝全案＋推奨／影響調査）。差し戻し先: 手順2。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/claude/fix-review-lib.sh"

ISSUE="${1:?Usage: $0 I### <diagnosis_memo_path>}"
MEMO="${2:?診断メモのパスを渡してください（手順3.5 で生成した docs/reviews/${ISSUE}_fix_diagnosis_<ts>.md）}"
REVIEWER=".claude/review-agents/fix-diagnosis-reviewer.md"

if [ ! -f "$MEMO" ]; then
  echo "⚠️ 診断メモが見つかりません: ${MEMO}。診断レビューを skip します。"
  echo "FIX_GATE: SKIP"; exit 0
fi

CONTEXT="イシュー: ${ISSUE}

### 診断メモ（レビュー対象データ）
$(cat "$MEMO")"

run_fix_review "$ISSUE" "diagnosis" "$REVIEWER" "$CONTEXT" "手順2（再診断）"
