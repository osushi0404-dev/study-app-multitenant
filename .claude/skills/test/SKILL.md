---
name: test
description: Run automated tests (pytest + Jest) and prompt manual test verification.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /test

前提: /code-review OK。

1) Backend 自動テスト:
   ```bash
   cd backend && python -m pytest --tb=short -q
   ```
   - 成功: 手順 2) へ
   - 失敗: 即 STOP。以下を報告してユーザー待機:
     - 失敗したテスト名
     - エラー内容（期待値 / 実際値 / ログ抜粋）
     ```
     ⛔ テストが失敗しました。修正作業は開始しません。
     👉 続けるには `/fix-loop $ARGUMENTS` を入力してください。
        fix-loop 完了後は `/test $ARGUMENTS` に戻ってください。
     ```

2) Frontend 自動テスト（Jest）:
   ```bash
   cd frontend && npm test -- --watchAll=false
   ```
   - 成功: 手順 3) へ
   - 失敗: 即 STOP。以下を報告してユーザー待機:
     - 失敗したテスト名
     - エラー内容（期待値 / 実際値 / ログ抜粋）
     ```
     ⛔ テストが失敗しました。修正作業は開始しません。
     👉 続けるには `/fix-loop $ARGUMENTS` を入力してください。
        fix-loop 完了後は `/test $ARGUMENTS` に戻ってください。
     ```

3) docs/reviews と docs/tests に結果を記録

4) 手動テスト確認項目を以下の形式で提示してユーザー検証（OK/NG）待ち:
   ```
   ## 手動テスト確認項目
   | # | 確認内容 | 操作手順 | 期待結果 | 結果(OK/NG) |
   |---|---------|---------|---------|------------|
   ```
   各項目はテスト計画書（docs/tests/open/$ARGUMENTS_manual_test.md）の内容に基づいて記載する

   - ユーザーテスト OK の場合: 以下を提案して停止する
     ```
     ✅ ユーザーテスト完了。
     👉 クローズ前に振り返りを行うことをお勧めします: `/retro $ARGUMENTS`
        または直接クローズ: `/close $ARGUMENTS`
     ```
   - ユーザーテスト NG の場合:
     ```
     ❌ テスト NG。
     👉 `/fix-loop $ARGUMENTS` を入力してください。
        fix-loop 完了後は `/test $ARGUMENTS` に戻ってください。
     ```
