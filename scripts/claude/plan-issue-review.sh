#!/usr/bin/env bash
set -euo pipefail

ISSUE="${1:?Usage: $0 I###}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TIMESTAMP=$(date +%Y%m%d_%H%M)
REVIEW_FILE="docs/reviews/${ISSUE}_plan_review_${TIMESTAMP}.md"
REVIEWER=".claude/review-agents/plan-reviewer.md"

# open/closed 両方を検索してパスを返す
find_file() {
  local dir="$1" pattern="$2"
  if [ -f "docs/${dir}/open/${pattern}" ]; then echo "docs/${dir}/open/${pattern}"
  elif [ -f "docs/${dir}/closed/${pattern}" ]; then echo "docs/${dir}/closed/${pattern}"
  else echo ""
  fi
}

ISSUE_FILE=$(find_file "issues" "${ISSUE}.md")
PLAN_FILE=$(find_file "plans" "plan_${ISSUE}.md")
AUTO_TEST=$(find_file "tests" "${ISSUE}_auto_test.md")
MANUAL_TEST=$(find_file "tests" "${ISSUE}_manual_test.md")

[ -z "$ISSUE_FILE" ] && { echo "⚠️ イシューファイルが見つかりません: ${ISSUE}.md"; exit 1; }
[ -z "$PLAN_FILE" ]  && { echo "⚠️ 計画書が見つかりません: plan_${ISSUE}.md"; exit 1; }

# コンテキスト組み立て
CONTEXT="イシュー番号: ${ISSUE}

### イシューファイル
$(cat "$ISSUE_FILE")

### 計画書
$(cat "$PLAN_FILE")"

[ -n "$AUTO_TEST" ]   && CONTEXT+="

### 自動テスト
$(cat "$AUTO_TEST")"

[ -n "$MANUAL_TEST" ] && CONTEXT+="

### 手動テスト
$(cat "$MANUAL_TEST")"

# claude -p でレビュー実行（Read/Grep/Glob のみ許可・Bash/Edit/Write 禁止）
# --allowedTools はスペース区切りの個別引数。コンテキストは stdin 経由で渡す
REVIEW=$(printf '%s' "$CONTEXT" | claude -p \
  --model claude-sonnet-4-6 \
  --system-prompt "$(cat "$REVIEWER")" \
  --allowedTools "Read" "Grep" "Glob")

[ -z "$REVIEW" ] && { echo "⚠️ claude -p が空を返しました。終了します。"; exit 1; }

# 出力正規化: 行末スペース除去 + 末尾改行保証
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed 's/[[:space:]]*$//')

# ファイル保存
mkdir -p "$(dirname "$REVIEW_FILE")"
printf '%s\n' "$REVIEW_CLEAN" > "$REVIEW_FILE"

# PR コメント投稿
PR_NUM=$(gh pr view --json number -q .number 2>/dev/null || echo "")
if [ -n "$PR_NUM" ]; then
  gh pr review "$PR_NUM" --comment --body "$(cat "$REVIEW_FILE")" \
    || echo "⚠️ PR コメント投稿失敗。手動で実行: gh pr review $PR_NUM --comment --body \"\$(cat $REVIEW_FILE)\""
fi

# 計画書にレビュー結果リンクを追記
if [ -f "$PLAN_FILE" ]; then
  VERDICT=$(grep -o '判定:.*' "$REVIEW_FILE" | head -1 || echo "完了")
  printf '\n## レビュー結果\n- [%s %s](../../reviews/%s)\n' \
    "$TIMESTAMP" "$VERDICT" "$(basename "$REVIEW_FILE")" >> "$PLAN_FILE"
fi

# 判定とユーザー案内
if grep -qE "判定:.*差し戻し" "$REVIEW_FILE"; then
  printf '\n⛔ Blocker が残っています。修正後に `/plan-issue-review %s` を再実行してください。\n' "$ISSUE"
elif grep -qi "高リスク判定.*Yes" "$REVIEW_FILE"; then
  printf '\n✅ プランレビュー完了。`/security-review %s` を実行してから `/implement %s` へ進んでください。\n' "$ISSUE" "$ISSUE"
else
  printf '\n✅ プランレビュー完了。`/implement %s` を実行してください。\n' "$ISSUE"
fi
