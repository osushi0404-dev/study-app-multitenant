#!/usr/bin/env bash
set -euo pipefail

ISSUE="${1:?Usage: $0 I###}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TIMESTAMP=$(date +%Y%m%d_%H%M)
REVIEW_FILE="docs/reviews/${ISSUE}_code_review_${TIMESTAMP}.md"
REVIEWER=".claude/review-agents/code-reviewer.md"

# CI 待機（最大 10 分）
PR_NUM=$(gh pr view --json number -q .number 2>/dev/null || echo "")
CI_OUTPUT=""
if [ -n "$PR_NUM" ]; then
  echo "CI を確認しています (PR #${PR_NUM})..."
  TIMEOUT=600
  ELAPSED=0
  while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    CI_OUTPUT=$(gh pr checks "$PR_NUM" 2>&1 || true)
    if ! echo "$CI_OUTPUT" | grep -q "pending"; then
      break
    fi
    echo "  pending... ${ELAPSED}s / ${TIMEOUT}s"
    sleep 15
    ELAPSED=$((ELAPSED + 15))
  done
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "⚠️ CI タイムアウト（${TIMEOUT}秒）。"
  fi
  if echo "$CI_OUTPUT" | grep -q "fail"; then
    echo "⛔ CI が失敗しています。修正後に再 push してください。"
    echo "$CI_OUTPUT"
    exit 1
  fi
fi

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

[ -z "$ISSUE_FILE" ] && { echo "⚠️ イシューファイルが見つかりません"; exit 1; }

# git diff（最大 100KB）
GIT_DIFF=$(git diff origin/develop...HEAD | head -c 102400)

# コンテキスト組み立て
CONTEXT="イシュー番号: ${ISSUE}

### イシューファイル
$(cat "$ISSUE_FILE")

### 計画書
$([ -n "$PLAN_FILE" ] && cat "$PLAN_FILE" || echo "(計画書なし)")

### git diff (origin/develop...HEAD, max 100KB)
\`\`\`diff
${GIT_DIFF}
\`\`\`"

# claude -p でレビュー実行
REVIEW=$(claude -p \
  --model claude-sonnet-4-6 \
  --system-prompt "$(cat "$REVIEWER")" \
  "$CONTEXT")

# 出力正規化
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed 's/[[:space:]]*$//')

# ファイル保存
printf '%s\n' "$REVIEW_CLEAN" > "$REVIEW_FILE"

# PR コメント投稿
if [ -n "$PR_NUM" ]; then
  gh pr review "$PR_NUM" --comment --body "$(cat "$REVIEW_FILE")" \
    || echo "⚠️ PR コメント投稿失敗。手動で実行: gh pr review $PR_NUM --comment --body \"\$(cat $REVIEW_FILE)\""
fi

# 判定とユーザー案内
if grep -qE "^\| Blocker \|" "$REVIEW_FILE"; then
  printf '\n⛔ Blocker が残っています。`/fix-loop %s` で修正後、`/code-review %s` を再実行してください。\n' "$ISSUE" "$ISSUE"
elif grep -qE "^\| High \|" "$REVIEW_FILE"; then
  printf '\n❌ レビュー NG。`/fix-loop %s` を実行してください。fix-loop 完了後は `/code-review %s` に戻ってください。\n' "$ISSUE" "$ISSUE"
else
  printf '\n✅ コードレビュー完了。`/test %s` を実行してください。\n' "$ISSUE"
fi
