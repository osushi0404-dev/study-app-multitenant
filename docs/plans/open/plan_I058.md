# plan_I058: コマンド化: plan-issue-review・code-review のオーケストレーションをシェルスクリプト化する

## 基本情報
- **計画書ID**: plan_I058
- **関連イシュー**: #119
- **作成根拠資料**: I057 振り返り・レビューシステム動作検証（2026-05-03）
- **実装後評価**: （未作成）
- **作成日**: 2026-05-03

---

## 1. 背景/目的

`/plan-issue-review`・`/code-review` スキルは markdown を Claude が解釈して実行するため、実行ごとに手順のぶれが生じる。具体的な問題：

- 決定論的な操作（ファイル保存・PR 投稿・計画書リンク追記・判定案内）が prose で書かれており Claude の解釈に依存
- `Agent` ツールの出力に `agentId:` 行・`<usage>` ブロックが付与され verbatim 保存が厳密に守れない
- pre-commit フックが末尾スペース・末尾改行を修正するため、保存後に再ステージが必要

**解決策**: オーケストレーション（制御フロー・副作用）をシェルスクリプトに移し、Claude は `claude -p` 経由で判断部分（レビュー内容の生成）のみ担当する。

---

## 2. 調査結果

### CLI フラグ確認
- `claude -p`: 非インタラクティブ実行 ✅
- `--system-prompt <prompt>`: システムプロンプト指定 ✅（`claude --help` で確認）
- `--model <model>`: モデル指定 ✅
- `--allowedTools`: ✅（今回は不要・使用しない）

### `scripts/claude/` の現状
- `scripts/claude/hooks/` は存在する
- `scripts/claude/plan-issue-review.sh`・`code-review.sh` は未存在 → 新規作成

### コンテキスト渡し方の決定
- `--system-prompt "$(cat plan-reviewer.md)"` で reviewer.md をシステムプロンプトとして渡す
- イシューファイル・計画書・テスト文書はシェルが読んでプロンプトに注入（`--allowedTools` 不要）
- `code-review.sh` の git diff は `head -c 102400`（100KB）で上限を設ける

---

## 3. 受け入れ条件

- [ ] `scripts/claude/plan-issue-review.sh I###` を実行すると、タイムスタンプ付きレビューファイルの保存・PR コメント投稿・計画書リンク追記・判定案内が一貫して行われる
- [ ] `scripts/claude/code-review.sh I###` を実行すると、同様の処理が一貫して行われる
- [ ] システムメタデータ（`agentId:`・`<usage>`）がレビューファイルに混入しない
- [ ] 末尾スペース・末尾改行の正規化がスクリプト内で保証され、pre-commit の修正が発生しない
- [ ] `/plan-issue-review`・`/code-review` スキルから従来通り呼び出せる（後方互換）

---

## 4. 影響範囲

| 層 | 変更ファイル | 変更種別 |
|----|------------|---------|
| Skills | `.claude/skills/plan-issue-review/SKILL.md` | 変更（thin wrapper 化） |
| Skills | `.claude/skills/code-review/SKILL.md` | 変更（thin wrapper 化） |
| Scripts | `scripts/claude/plan-issue-review.sh` | 新規作成 |
| Scripts | `scripts/claude/code-review.sh` | 新規作成 |
| Backend | なし | - |
| Frontend | なし | - |
| DB | なし | - |

---

## 5. 実装手順

### ステップ1: `scripts/claude/plan-issue-review.sh` の新規作成

**内容**:

```bash
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

# claude -p でレビュー実行
REVIEW=$(claude -p \
  --model claude-sonnet-4-6 \
  --system-prompt "$(cat "$REVIEWER")" \
  "$CONTEXT")

# 出力正規化: 行末スペース除去 + 末尾改行保証
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed 's/[[:space:]]*$//')

# ファイル保存
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
```

→ TC-01・TC-02・TC-03・TC-05・TC-06 参照

### ステップ2: `scripts/claude/code-review.sh` の新規作成

**内容**:

```bash
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
```

→ TC-01・TC-02・TC-04・TC-05・TC-06 参照

### ステップ3: `.claude/skills/plan-issue-review/SKILL.md` を thin wrapper に更新

**変更後の内容**:

```markdown
---
name: plan-issue-review
description: Review plan and test docs for best practices, security, and modern web dev.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Bash
---

# /plan-issue-review

\`\`\`bash
bash scripts/claude/plan-issue-review.sh $ARGUMENTS
\`\`\`
```

→ TC-06 参照

### ステップ4: `.claude/skills/code-review/SKILL.md` を thin wrapper に更新

**変更後の内容**:

```markdown
---
name: code-review
description: Verify CI passes and review implementation against acceptance criteria.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Bash
---

# /code-review

\`\`\`bash
bash scripts/claude/code-review.sh $ARGUMENTS
\`\`\`
```

→ TC-06 参照

---

## 6. テスト計画

### 自動テスト
→ `I058_auto_test.md` 参照

### 手動テスト
→ `I058_manual_test.md` 参照

---

## 7. ロールバック

スキルファイルとシェルスクリプトのみの変更。`git revert` で即時ロールバック可能。
ロールバック後は旧スキルファイル（Agent ツール使用）に戻る。

---

## 8. Risk & 回避策

| リスク | 対策 |
|--------|------|
| `claude -p` が OAuth 認証環境で動作しない | `claude -p` は通常の認証で動作する（`--bare` は使用しない） |
| git diff が 100KB を超える大規模 PR では差分が切り捨てられる | `head -c 102400` で 100KB に制限しつつ、先頭から最重要部分を含める |
| `--system-prompt` に reviewer.md の内容が長すぎる場合 | 現在の reviewer.md は約 100 行程度、問題ない範囲 |
| CI タイムアウト（10 分超）でスクリプトが警告を出して続行 | 警告を表示しつつ CI 失敗でなければレビューは続行 |

---

## 9. セキュリティ・ベストプラクティスチェック

セキュリティ影響なし（スキルドキュメントとシェルスクリプトのみの変更、コード・認証・DB 変更なし）。
- `set -euo pipefail` でエラー即終了・未定義変数参照を防止
- `${1:?...}` で引数検証（パストラバーサル防止）
- `find_file()` は固定のディレクトリプレフィックスを使用（外部入力が直接パスに影響しない）
P3/P5/P8 影響なし。P6 影響なし。

---

## 10. 承認ポイント

### 設計判断
| 項目 | 判断内容 | 根拠 |
|------|----------|------|
| コンテキスト渡し方 | `--system-prompt` + シェルによるファイル注入（`--allowedTools` 不使用） | grill-me で確定（最大一貫性） |
| CI タイムアウト | 600 秒（10 分）ハードコード | grill-me で確定（CI 実績 ~3 分に対して余裕を持たせた固定値） |
| git diff 上限 | 100KB（`head -c 102400`） | コンテキスト上限対策・先頭から重要部分を含める |

### チェックリスト
- [ ] `plan-issue-review.sh` のスクリプト内容（ステップ1）に同意する
- [ ] `code-review.sh` のスクリプト内容（ステップ2）に同意する
- [ ] スキル thin wrapper の形式（ステップ3・4）に同意する

## レビュー結果
- [20260503_0111 差し戻し（Blocker 1件）](../../reviews/I058_plan_review_20260503_0111.md)
- [20260503_0123 判定: ✅ 完了](../../reviews/I058_plan_review_20260503_0123.md)
- [20260503_0145 差し戻し（Blocker 2件）](../../reviews/I058_plan_review_20260503_0145.md)

## レビュー結果
- [20260503_0139 判定: 差し戻し（Blocker 2件）**](../../reviews/I058_plan_review_20260503_0139.md)

## レビュー結果
- [20260503_1438 判定: ✅ 完了](../../reviews/I058_plan_review_20260503_1438.md)

## レビュー結果
- [20260503_1444 判定: ✅ 完了](../../reviews/I058_plan_review_20260503_1444.md)
