---
name: test
description: Run automated tests (pytest + Jest) and prompt manual test verification.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /test

前提: /code-review OK。

## 停止条件
- 自動テスト（pytest / Jest / Playwright E2E）が1件でも失敗した場合: STOP。`/fix-loop $ARGUMENTS` を案内する。`/retro` および `/close` は案内しない。
- 手動テスト確認でユーザーが NG を返した場合: STOP。`/fix-loop $ARGUMENTS` を案内する。`/retro` および `/close` は案内しない。

0) 実行環境を確認する:
   ```bash
   # pytest がローカルで利用可能か確認
   python -m pytest --version 2>/dev/null && echo "LOCAL" || echo "DOCKER"
   ```
   - LOCAL: 手順 1a) へ（ローカル直接実行）
   - DOCKER: 手順 1b) へ（Docker コンテナ経由）

1a) Backend 自動テスト（ローカル）:
   ```bash
   cd backend && python -m pytest --tb=short -q
   ```

1b) Backend 自動テスト（Docker）:
   ```bash
   docker compose exec backend python -m pytest --tb=short -q
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
   # ローカル
   cd frontend && npm test -- --watchAll=false
   # Docker
   docker compose exec frontend npm test -- --watchAll=false
   ```
   手順 0) で確認した環境に応じて実行する。
   - 成功: 手順 3) へ
   - 失敗: 即 STOP。以下を報告してユーザー待機:
     - 失敗したテスト名
     - エラー内容（期待値 / 実際値 / ログ抜粋）
     ```
     ⛔ テストが失敗しました。修正作業は開始しません。
     👉 続けるには `/fix-loop $ARGUMENTS` を入力してください。
        fix-loop 完了後は `/test $ARGUMENTS` に戻ってください。
     ```

3) E2E テスト（Playwright）:
   ```bash
   docker compose --profile e2e run --rm e2e npm test
   ```
   - 成功: 手順 4) へ
   - 失敗: 即 STOP。以下を報告してユーザー待機:
     - 失敗したテスト名（spec ファイル名・テスト名）
     - エラー内容（期待値 / 実際値 / スクリーンショットパス）
     ```
     ⛔ E2E テストが失敗しました。修正作業は開始しません。
     👉 続けるには `/fix-loop $ARGUMENTS` を入力してください。
        fix-loop 完了後は `/test $ARGUMENTS` に戻ってください。
     ```

4) docs/reviews と docs/tests に結果を記録

5) 手動テスト確認項目を以下の形式で提示してユーザー検証（OK/NG）待ち:
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
