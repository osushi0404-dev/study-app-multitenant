#!/usr/bin/env bash
# fix-implementation-review.sh — /fix-loop 手順5.5（実装レビュー・修正後/テスト前）（I074）。
# 使い方: bash scripts/claude/fix-implementation-review.sh I### [prior_ng_review_path]
#   第2引数（任意）: 直前 REMAND の実装レビュー記録。渡すと reviewer が各前回NG指摘の解消を fail-closed 検証する。
# 入力: 作業ツリー差分（git diff + git diff --staged）＋未追跡新規ファイル（＋任意で前回NG）。差し戻し先: 手順5。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/claude/fix-review-lib.sh"

ISSUE="${1:?Usage: $0 I### [prior_ng_review_path]}"
PRIOR="${2:-}"
REVIEWER=".claude/review-agents/fix-implementation-reviewer.md"

# 追跡ファイルの差分（unstaged + staged）
DIFF="$(git diff; git diff --staged)"

# 未追跡（新規作成）ファイルは git diff に出ないため内容を付加する（非破壊で収集）
UNTRACKED=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  UNTRACKED+=$'\n'"=== 新規ファイル: ${f} ==="$'\n'"$(cat "$f" 2>/dev/null)"
done < <(git ls-files --others --exclude-standard)

# 再レビュー時の前回NG（オプション）: 各指摘の diff 上の解消を fail-closed で検証させる
PRIOR_SECTION=""
if [ -n "$PRIOR" ] && [ -f "$PRIOR" ]; then
  PRIOR_SECTION="

### 前回NG指摘（再レビュー: 各指摘が上記 diff で解消したか検証せよ。確認できなければ未解消として REMAND）
$(cat "$PRIOR")"
fi

CONTEXT="イシュー: ${ISSUE}

### 作業ツリー差分（git diff + git diff --staged・レビュー対象データ）
${DIFF}

### 未追跡新規ファイル
${UNTRACKED}${PRIOR_SECTION}"

run_fix_review "$ISSUE" "implementation" "$REVIEWER" "$CONTEXT" "手順5（再修正）"
