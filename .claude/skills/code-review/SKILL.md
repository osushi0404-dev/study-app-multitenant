---
name: code-review
description: Verify CI passes and review implementation against acceptance criteria.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Glob, Grep
---

# /code-review

前提: /implement 完了・push 済み。

1) CI 確認:
   ```bash
   gh pr checks [PR番号]
   ```
   - 全ジョブ pass: 手順 2) へ
   - pending: 数分待って再確認してから手順 2) へ
   - 失敗あり: STOP。失敗ジョブのログを確認して報告し、修正後に再 push するよう案内する。

2) 計画書・イシューの受け入れ条件を読む:
   - docs/issues/open/$ARGUMENTS.md
   - docs/plans/open/$ARGUMENTS_plan.md

3) 実装差分を確認:
   ```bash
   git diff origin/develop...HEAD --name-only
   git diff origin/develop...HEAD
   ```

4) 各受け入れ条件について実装との照合を行い、結果を以下の形式で報告:
   ```
   ## コードレビュー結果
   | # | 受け入れ条件 | 実装状況 | 備考 |
   |---|------------|---------|------|
   | 1 | ...        | ✅ 実装済み / ⚠️ 一部不足 / ❌ 未実装 | ... |
   ```

5) コードの品質・ロジック上の問題があれば追記する

6) ユーザーへ OK/NG の判断を求める:
   - OK: 「✅ コードレビュー完了。`/test $ARGUMENTS` を実行してください。」
   - NG: 「❌ レビュー NG。`/fix-loop $ARGUMENTS` を実行してください。fix-loop 完了後は `/code-review $ARGUMENTS` に戻ってください。」
