#!/usr/bin/env bash
set -euo pipefail

# ---- helper functions (テストは REVIEW_LIB_SOURCE_ONLY=1 で source して利用) ----

# open/closed 両方を検索してパスを返す（issues/tests/reviews 等の単一パターン用）
find_file() {
  local dir="$1" pattern="$2"
  if [ -f "docs/${dir}/open/${pattern}" ]; then echo "docs/${dir}/open/${pattern}"
  elif [ -f "docs/${dir}/closed/${pattern}" ]; then echo "docs/${dir}/closed/${pattern}"
  else echo ""
  fi
}

# 計画書専用: plan_I###*.md の連番を数値ソートし最大（最新）を返す。
# 無印=最古=0、_N=N。open/closed 横断で最大サフィックスを選ぶ（同値は open 優先）。該当なしは空文字。
find_plan_file() {
  local issue="$1" f n best="" best_n=-1
  for f in "docs/plans/open/plan_${issue}.md" docs/plans/open/plan_"${issue}"_*.md \
           "docs/plans/closed/plan_${issue}.md" docs/plans/closed/plan_"${issue}"_*.md; do
    [ -f "$f" ] || continue
    if [[ "$f" =~ plan_${issue}_([0-9]+)\.md$ ]]; then n="${BASH_REMATCH[1]}"; else n=0; fi
    if [ "$n" -gt "$best_n" ]; then best_n="$n"; best="$f"; fi
  done
  echo "$best"
}

# レビュー結果の重大度判定: 一次=機械可読 VERDICT 行 / 保険=装飾許容 grep（旧出力の後方互換）
detect_code_verdict() {
  local file="$1" v
  v=$(grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)[[:space:]]*$' "$file" 2>/dev/null | tail -1 | grep -oE '(BLOCKER|HIGH|OK)' || true)
  if [ -n "$v" ]; then echo "$v"; return; fi
  if grep -qE '^\|\s*\*{0,2}Blocker\b' "$file"; then echo "BLOCKER"; return; fi
  if grep -qE '^\|\s*\*{0,2}High\b'    "$file"; then echo "HIGH"; return; fi
  echo "OK"
}

# テストから関数のみを source するためのガード（本体は実行しない）
if [ "${REVIEW_LIB_SOURCE_ONLY:-}" = "1" ]; then return 0; fi

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

ISSUE_FILE=$(find_file "issues" "${ISSUE}.md")
PLAN_FILE=$(find_plan_file "$ISSUE")

[ -z "$ISSUE_FILE" ] && { echo "⚠️ イシューファイルが見つかりません"; exit 1; }

# git 情報取得（最大 100KB、|| true で SIGPIPE による pipefail を抑制）
GIT_DIFF=$(git diff origin/develop...HEAD | head -c 102400 || true)
GIT_LOG=$(git log origin/develop...HEAD --oneline)
GIT_FILES=$(git diff origin/develop...HEAD --name-only)

# コンテキスト組み立て
CONTEXT="イシュー番号: ${ISSUE}

### イシューファイル
$(cat "$ISSUE_FILE")

### 計画書
$([ -n "$PLAN_FILE" ] && cat "$PLAN_FILE" || echo "(計画書なし)")

### git log (origin/develop...HEAD)
${GIT_LOG}

### 変更ファイル一覧
${GIT_FILES}

### git diff (origin/develop...HEAD, max 100KB)
\`\`\`diff
${GIT_DIFF}
\`\`\`"

# claude -p でレビュー実行（--tools でホワイトリスト制限: Read/Grep/Glob のみ）
REVIEW=$(printf '%s' "$CONTEXT" | claude -p \
  --model claude-sonnet-4-6 \
  --system-prompt "$(cat "$REVIEWER")" \
  --tools "Read,Grep,Glob")

[ -z "$REVIEW" ] && { echo "⚠️ claude -p が空を返しました。終了します。"; exit 1; }

# 出力正規化
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed 's/[[:space:]]*$//')

# ファイル保存
mkdir -p "$(dirname "$REVIEW_FILE")"
printf '%s\n' "$REVIEW_CLEAN" > "$REVIEW_FILE"

# PR コメント投稿
if [ -n "$PR_NUM" ]; then
  gh pr review "$PR_NUM" --comment --body "$(cat "$REVIEW_FILE")" \
    || echo "⚠️ PR コメント投稿失敗。手動で実行: gh pr review $PR_NUM --comment --body \"\$(cat $REVIEW_FILE)\""
fi

# 判定とユーザー案内（一次=VERDICT 行 / 保険=装飾許容 grep）
case "$(detect_code_verdict "$REVIEW_FILE")" in
  BLOCKER)
    # shellcheck disable=SC2016
    printf '\n⛔ Blocker が残っています。`/fix-loop %s` で修正後、`/code-review %s` を再実行してください。\n' "$ISSUE" "$ISSUE" ;;
  HIGH)
    # shellcheck disable=SC2016
    printf '\n❌ レビュー NG。`/fix-loop %s` を実行してください。fix-loop 完了後は `/code-review %s` に戻ってください。\n' "$ISSUE" "$ISSUE" ;;
  *)
    # shellcheck disable=SC2016
    printf '\n✅ コードレビュー完了。`/test %s` を実行してください。\n' "$ISSUE" ;;
esac
