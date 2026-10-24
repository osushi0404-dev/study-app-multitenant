#!/usr/bin/env bash
# flow-stage.sh I###: イシューの記録の最後の `STAGE_DONE: <段階> NEXT: <次の段階>` 行から、次の段階を返す（I193）。
# 呼び出し元: .claude/skills/proceed/SKILL.md
# 出力: `NEXT_STAGE: <名前>` と `LAST_LINE: <その行の行番号>`（proceed が「段階が STAGE_DONE を書いたか」を見分けるのに使う）
# 終了コード: 0=次の段階を返した / 2=決められない（記録が無い・STAGE_DONE 行が無い・NEXT が一覧に無い）
# 記録: docs/reviews/open/I###_review.md（無ければ docs/reviews/closed/I###_review.md）。REVIEW_DIR で差し替えられる（テスト用）
set -uo pipefail

ISSUE="${1:-}"
if ! [[ "$ISSUE" =~ ^I[0-9]{3}$ ]]; then
  echo "⛔ 使い方: $0 I###（受け取った値: '${ISSUE}'）"
  exit 2
fi

# どのフォルダから実行しても、リポジトリのルートの記録を読む（REVIEW_DIR を相対で渡したときもルートから解決する）
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "⛔ git リポジトリの中で実行してください"; exit 2; }
cd "$REPO_ROOT" || exit 2
REVIEW_DIR="${REVIEW_DIR:-docs/reviews}"
FILE=""
for d in open closed; do
  if [ -f "${REVIEW_DIR}/${d}/${ISSUE}_review.md" ]; then FILE="${REVIEW_DIR}/${d}/${ISSUE}_review.md"; break; fi
done
if [ -z "$FILE" ]; then
  echo "⛔ 記録が見つかりません: ${REVIEW_DIR}/{open,closed}/${ISSUE}_review.md"
  exit 2
fi

# 行頭の STAGE_DONE 行だけを数える（本文の途中の引用は数えない）。最後の 1 行を使う
LAST=$(grep -nE '^STAGE_DONE:[[:space:]]' "$FILE" | tail -1 || true)
if [ -z "$LAST" ]; then
  echo "⛔ ${FILE} に STAGE_DONE 行がありません（新しい流れで始めていないイシューの可能性があります）"
  exit 2
fi
LINE_NO="${LAST%%:*}"
TEXT="${LAST#*:}"

NEXT=$(printf '%s\n' "$TEXT" | sed -nE 's/^STAGE_DONE:[[:space:]]+[a-z-]+[[:space:]]+NEXT:[[:space:]]+([a-z-]+)[[:space:]]*$/\1/p')
case "$NEXT" in
  plan-review|design-security-review|implement|review-gate|fix-loop|test-gate|human-test|retro|close|merge)
    echo "NEXT_STAGE: ${NEXT}"
    echo "LAST_LINE: ${LINE_NO}"
    exit 0 ;;
esac
echo "⛔ 最後の STAGE_DONE 行の NEXT が読めません（${FILE}:${LINE_NO}）: ${TEXT}"
exit 2
