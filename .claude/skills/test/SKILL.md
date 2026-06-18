---
name: test
description: Run the plan-specified automated tests (default: pytest + Jest + E2E) and prompt manual test verification.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /test

前提: /code-review OK。

## 自動テストの選択（計画駆動）
実行する自動テストは **計画書のテスト計画（`docs/tests/open/$ARGUMENTS_auto_test.md`）が正**。
- auto_test.md が **専用の自動テスト**（例: `bash scripts/...` の専用スクリプト・特定 TC）を指定している場合: **それを正として実行**し結果を記録する。auto_test.md が「非該当」と明記した既定テスト（pytest/Jest/E2E のいずれか）は実行せず「非該当」と記録する。
- auto_test.md が自動テストを **指定していない場合**、または **auto_test.md が存在しない場合**: 下記の既定（pytest → Jest → E2E）にフォールバックする。

app/非app の区別では分岐しない。Backend/Frontend 変更が無いイシューでは、auto_test.md が専用テストを正と指定し pytest/Jest/E2E を「非該当」と明記する運用になる。

## 停止条件
- 自動テスト（pytest / Jest / Playwright E2E）が1件でも失敗した場合: STOP。`/fix-loop $ARGUMENTS` を案内する。`/retro` および `/close` は案内しない。
- 計画書（auto_test.md）が指定する専用自動テストが1件でも失敗した場合: STOP。`/fix-loop $ARGUMENTS` を案内する。`/retro` および `/close` は案内しない。
- 手動テスト確認でユーザーが NG を返した場合: STOP。`/fix-loop $ARGUMENTS` を案内する。`/retro` および `/close` は案内しない。

### 既定の自動テスト（auto_test.md に指定が無い場合のフォールバック）

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
   docker compose --profile e2e run --rm e2e
   ```
   # コマンド省略時は compose file の default command が適用される:
   # sh -c "npm install && npm test"
   # e2e-init（Init Container）が先行して migrate・seed を実行してから e2e が起動する
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

5) 手動テストを実施する:

   **【重要】実施者の区別**
   - テスト計画書（`I###_manual_test.md`）の「実施者」欄を必ず確認する
   - **実施者: Claude** の項目 → 自分で Bash/Read ツールを使って実行し、結果を記録する（ユーザーに依頼しない）
   - **実施者: Human** の項目のみ → ユーザーに確認を依頼する

   Claude 実施項目をすべて自己実行してから、Human 実施項目のみ以下の形式でユーザーに提示する:
   ```
   ## 手動テスト確認項目（Human 実施分）
   | # | 確認内容 | 操作手順 | 期待結果 | 結果(OK/NG) |
   |---|---------|---------|---------|------------|
   ```

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
