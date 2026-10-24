#!/usr/bin/env bash
# post-review-comment.sh <記録ファイル>: レビュー記録を、今のブランチの開いている PR にコメントとして投稿する（I193）。
# 呼び出し元: .claude/skills/review-gate/SKILL.md 3-4（敵対的レビューの記録）
# GitHub のコメントの上限 65,536 文字を超えるときは、先頭 58,000 文字と記録ファイルへの参照だけを載せる。
# 失敗しても流れを止めない（exit 0 で、失敗を出力に書く）。手順に `gh pr review` を直接書くと settings の allow に
# 一致せず承認画面が出るので、code-review.sh・fix-review-lib.sh と同じくスクリプトから投稿する
set -uo pipefail
FILE="${1:-}"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  echo "⚠️ 記録ファイルがありません: '${FILE}'。PR コメントを投稿しません。"
  exit 0
fi
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
PR_NUM=$(gh pr list --head "$BRANCH_NAME" --state open --json number --jq '.[0].number // empty' 2>/dev/null || true)
if [ -z "$PR_NUM" ]; then
  echo "⚠️ ブランチ ${BRANCH_NAME} の開いている PR を取れません。PR コメントを投稿しません（記録は ${FILE}）。"
  exit 0
fi
BODY_FILE=$(mktemp)
trap 'rm -f "$BODY_FILE"' EXIT
if [ "$(wc -c < "$FILE")" -gt 60000 ]; then
  { head -c 58000 "$FILE"; printf '\n\n（長いため一部だけを載せた。全文は %s）\n' "$FILE"; } > "$BODY_FILE"
else
  cp "$FILE" "$BODY_FILE"
fi
if gh pr review "$PR_NUM" --comment --body-file "$BODY_FILE" >/dev/null 2>&1; then
  echo "✅ PR #${PR_NUM} にコメントしました: ${FILE}"
else
  echo "⚠️ PR #${PR_NUM} へのコメントに失敗しました（流れは止めない）: ${FILE}"
fi
exit 0
