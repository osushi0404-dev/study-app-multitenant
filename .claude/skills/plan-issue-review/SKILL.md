---
name: plan-issue-review
description: Review plan and test docs for best practices, security, and modern web dev.
argument-hint: "I###"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Agent, Edit, Bash
---

# /plan-issue-review

前提: /plan-issue 完了・生成ドキュメント作成済み。

## 実行手順

### 1. タイムスタンプとパスを準備する

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M)
ISSUE=$ARGUMENTS  # 例: I054
REVIEW_FILE="docs/reviews/${ISSUE}_plan_review_${TIMESTAMP}.md"
```

### 2. サブエージェントを起動する

**渡すもの**: イシュー番号と指示ファイルのパスのみ。
**渡さないもの**: ファイル内容・ファイルパス一覧・差分・設計の背景・ユーザーとの議論内容。

Agent を以下の設定で起動する:
- model: `claude-sonnet-4-6`
- allowed_tools: `[Read, Glob, Grep]`（Edit・Bash・Agent は渡さない）
- prompt:
  ```
  イシュー番号: [ISSUE番号]

  まず .claude/review-agents/plan-reviewer.md を Read して指示を取得してください。
  指示に従い、イシュー番号からファイルパスを自力で導出してすべてのファイルを Read し、
  計画書・テスト文書のレビューを実施してください。
  ```

サブエージェントはファイルへの書き込みを一切行わず、構造化テキストを返却するのみ。

### 3. サブエージェントの出力を verbatim でファイルに保存する

- 内容を加工・解釈・要約しない
- Write/Edit ツールで `$REVIEW_FILE` にそのまま保存する

### 4. GitHub PR にコメントを投稿する（**親エージェントのみ実行**）

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
  ファイルは保存済みのため作業は継続可能。

### 5. 計画書への参照リンクを追記する

`docs/plans/open/plan_${ISSUE}.md`（なければ `docs/plans/closed/`）の末尾に追記する:

```markdown
## レビュー結果
- [2026-04-26_1530 ✅ 完了](../../reviews/I054_plan_review_20260426_1530.md)
```
（例: `[YYYYMMDD_HHMM 判定結果](../../reviews/[REVIEW_FILE名])`）

### 6. 判定とユーザー案内

サブエージェントの出力を確認して判定する（内容は加工しない）:

**差し戻し（Blocker あり）の場合**:
⛔ STOP。以下を出力して停止する:
「Blocker が残っています。修正後に `/plan-issue-review $ARGUMENTS` を再実行してください。」
`/implement` は案内しない。

**完了（Blocker なし）の場合**:
✅ プランレビュー完了。
- 高リスク判定 Yes の場合: 「`/security-review $ARGUMENTS` を実行してから `/implement $ARGUMENTS` へ進んでください。」
- 高リスク判定 No の場合: 「`/implement $ARGUMENTS` を実行してください。」
