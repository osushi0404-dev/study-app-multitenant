#!/usr/bin/env bash
set -euo pipefail

# issue-review: イシューファイル単体を第三者サブエージェントでレビューし、自己完結度を判定する。
# 呼び出し元: .claude/skills/issue-bootstrap/SKILL.md（step 3.5・GitHub 登録前）
# 方針: ソフト・非ブロック。失敗しても呼び出し元（issue-bootstrap）のフローを止めない。
# PR コメントはしない（この時点で PR は未作成）。

ISSUE="${1:?Usage: $0 I###}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TIMESTAMP=$(date +%Y%m%d_%H%M)
REVIEW_FILE="docs/reviews/${ISSUE}_issue_review_${TIMESTAMP}.md"
REVIEWER=".claude/review-agents/issue-reviewer.md"

# reviewer 指示ファイルの存在確認（非ブロック・防御的）
if [ ! -f "$REVIEWER" ]; then
  echo "⚠️ issue-reviewer.md が見つかりません。issue-review をスキップします。"
  exit 0
fi

# イシューファイル探索（open → closed）。未検出でも非ブロックで終了する
if [ -f "docs/issues/open/${ISSUE}.md" ]; then
  ISSUE_FILE="docs/issues/open/${ISSUE}.md"
elif [ -f "docs/issues/closed/${ISSUE}.md" ]; then
  ISSUE_FILE="docs/issues/closed/${ISSUE}.md"
else
  echo "⚠️ イシューファイルが見つかりません: ${ISSUE}.md。issue-review をスキップします。"
  exit 0
fi

CONTEXT="イシュー番号: ${ISSUE}

### イシューファイル
$(cat "$ISSUE_FILE")"

# claude -p で第三者レビュー（読み取り専用ツールに制限）。失敗しても起票フローを止めない
if ! REVIEW=$(printf '%s' "$CONTEXT" | claude -p \
  --model claude-sonnet-4-6 \
  --system-prompt "$(cat "$REVIEWER")" \
  --tools "Read,Grep,Glob"); then
  echo "⚠️ issue-review をスキップしました（claude -p 失敗）。"
  exit 0
fi

if [ -z "$REVIEW" ]; then
  echo "⚠️ issue-review が空を返しました。スキップします。"
  exit 0
fi

# 出力正規化: 行末スペース除去
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed 's/[[:space:]]*$//')

# ファイル保存
mkdir -p "$(dirname "$REVIEW_FILE")"
printf '%s\n' "$REVIEW_CLEAN" > "$REVIEW_FILE"

echo "📝 issue-review 結果: ${REVIEW_FILE}"
printf '%s\n' "$REVIEW_CLEAN"
# 判定はソフト。呼び出し元（issue-bootstrap）が判定（十分/要補足）を見て報告文を分岐する。
