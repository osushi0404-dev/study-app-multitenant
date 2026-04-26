---
name: code-review
description: Verify CI passes and review implementation against acceptance criteria.
argument-hint: "I###"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Agent, Edit, Bash
---

# /code-review

前提: /implement 完了・push 済み。

## 1. CI 確認

```bash
gh pr checks [PR番号]
```
- 全ジョブ pass: 手順 2 へ
- pending: 数分待って再確認してから手順 2 へ
- 失敗あり: STOP。失敗ジョブのログを確認して報告し、修正後に再 push するよう案内する。

## 2. タイムスタンプとパスを準備する

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M)
ISSUE=$ARGUMENTS  # 例: I054
REVIEW_FILE="docs/reviews/${ISSUE}_code_review_${TIMESTAMP}.md"
```

## 3. サブエージェントを起動する

**渡すもの**: イシュー番号と指示ファイルのパスのみ。
**渡さないもの**: git diff・ファイル内容・差分・設計の背景。

Agent を以下の設定で起動する:
- model: `claude-sonnet-4-6`
- allowed_tools: `[Read, Glob, Grep, Bash]`（Edit・Agent は渡さない）
- prompt:
  ```
  イシュー番号: [ISSUE番号]

  まず .claude/review-agents/code-reviewer.md を Read して指示を取得してください。
  指示に従い、イシュー番号からファイルパスを自力で導出してすべてのファイルを Read し、
  git diff origin/develop...HEAD を Bash で取得して、コードレビューを実施してください。
  ```

サブエージェントはファイルへの書き込みを一切行わず、構造化テキストを返却するのみ。

## 4. サブエージェントの出力を verbatim でファイルに保存する

- 内容を加工・解釈・要約しない
- Write/Edit ツールで `$REVIEW_FILE` にそのまま保存する

## 5. GitHub PR にコメントを投稿する（**親エージェントのみ実行**）

```bash
PR_NUM=$(gh pr view --json number -q .number)
gh pr review $PR_NUM --comment --body "$(cat $REVIEW_FILE)"
```

**重要**:
- `--body` への内容直書き禁止。必ず `$(cat $REVIEW_FILE)` 経由で参照すること
- 失敗した場合: エラーを報告し、以下のコマンドを表示してノンブロッキングで継続:
  ```
  gh pr review [PR番号] --comment --body "$(cat [REVIEW_FILEのパス])"
  ```

## 6. 判定とユーザー案内

サブエージェントの出力を確認して判定する（内容は加工しない）:

**Blocker あり**:
⛔ STOP。「Blocker が残っています。`/fix-loop $ARGUMENTS` で修正後、`/code-review $ARGUMENTS` を再実行してください。」

**Blocker なし・High あり**:
❌ レビュー NG。「`/fix-loop $ARGUMENTS` を実行してください。fix-loop 完了後は `/code-review $ARGUMENTS` に戻ってください。」

**Blocker・High なし**:
✅ コードレビュー完了。「`/test $ARGUMENTS` を実行してください。」
