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

# 計画書レビュー結果の判定: 一次=VERDICT 行 / 保険=既存プレーン判定（後方互換のため残置）
detect_plan_verdict() {
  local file="$1" v
  v=$(grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGHRISK|OK)[[:space:]]*$' "$file" 2>/dev/null | tail -1 | grep -oE '(BLOCKER|HIGHRISK|OK)' || true)
  if [ -n "$v" ]; then echo "$v"; return; fi
  if grep -qE "判定:.*差し戻し" "$file"; then echo "BLOCKER"; return; fi
  # 保険（多行対応）: 「## 高リスク判定」見出しから次の「## 」見出しまでのブロック内に
  # 末尾アンカーで「判定: Yes」があれば HIGHRISK。見出しと判定行が別行の実出力に対応。
  if awk '
    /^## 高リスク判定/ { inblock=1; next }
    /^## /            { inblock=0 }
    inblock && /^判定:[[:space:]]*Yes[[:space:]]*$/ { found=1 }
    END { exit(found?0:1) }
  ' "$file"; then echo "HIGHRISK"; return; fi
  echo "OK"
}

# 計画書の「## レビュー結果」へリンク行を冪等追記（重複見出しを作らない・履歴保持）。
# 既存セクションがあればリンク行のみを見出し直後に挿入、無ければ見出し＋リンクを新規追記。
append_review_link() {
  local plan="$1" ts="$2" verdict="$3" base="$4"
  local line="- [${ts} ${verdict}](../../reviews/${base})"
  if grep -q '^## レビュー結果$' "$plan"; then
    local tmp="${plan}.tmp"
    # LINE を環境変数で渡し ENVIRON で読む（awk -v のバックスラッシュ エスケープ解釈を回避）
    if LINE="$line" awk 'BEGIN{l=ENVIRON["LINE"]} {print} /^## レビュー結果$/ && !d {print l; d=1}' \
         "$plan" > "$tmp"; then
      mv "$tmp" "$plan"
    else
      rm -f "$tmp"; return 1   # awk 失敗時は一時ファイルを残さない
    fi
  else
    printf '\n## レビュー結果\n%s\n' "$line" >> "$plan"
  fi
}

# テストから関数のみを source するためのガード（本体は実行しない）
if [ "${REVIEW_LIB_SOURCE_ONLY:-}" = "1" ]; then return 0; fi

ISSUE="${1:?Usage: $0 I###}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TIMESTAMP=$(date +%Y%m%d_%H%M)
REVIEW_FILE="docs/reviews/${ISSUE}_plan_review_${TIMESTAMP}.md"
REVIEWER=".claude/review-agents/plan-reviewer.md"

ISSUE_FILE=$(find_file "issues" "${ISSUE}.md")
PLAN_FILE=$(find_plan_file "$ISSUE")
AUTO_TEST=$(find_file "tests" "${ISSUE}_auto_test.md")
MANUAL_TEST=$(find_file "tests" "${ISSUE}_manual_test.md")

[ -z "$ISSUE_FILE" ] && { echo "⚠️ イシューファイルが見つかりません: ${ISSUE}.md"; exit 1; }
[ -z "$PLAN_FILE" ]  && { echo "⚠️ 計画書が見つかりません: plan_${ISSUE}*.md"; exit 1; }

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

# claude -p でレビュー実行（--tools でホワイトリスト制限: Read/Grep/Glob のみ）
REVIEW=$(printf '%s' "$CONTEXT" | claude -p \
  --model claude-sonnet-4-6 \
  --system-prompt "$(cat "$REVIEWER")" \
  --tools "Read,Grep,Glob")

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

# 計画書にレビュー結果リンクを冪等追記
if [ -f "$PLAN_FILE" ]; then
  VERDICT=$(grep -o '判定:.*' "$REVIEW_FILE" | head -1 || echo "完了")
  append_review_link "$PLAN_FILE" "$TIMESTAMP" "$VERDICT" "$(basename "$REVIEW_FILE")"
fi

# 判定とユーザー案内（一次=VERDICT 行 / 保険=既存プレーン判定）
case "$(detect_plan_verdict "$REVIEW_FILE")" in
  BLOCKER)
    # shellcheck disable=SC2016
    printf '\n⛔ Blocker が残っています。修正後に `/plan-issue-review %s` を再実行してください。\n' "$ISSUE" ;;
  HIGHRISK)
    # shellcheck disable=SC2016
    printf '\n✅ プランレビュー完了。`/security-review %s` を実行してから `/implement %s` へ進んでください。\n' "$ISSUE" "$ISSUE" ;;
  *)
    # shellcheck disable=SC2016
    printf '\n✅ プランレビュー完了。`/implement %s` を実行してください。\n' "$ISSUE" ;;
esac
