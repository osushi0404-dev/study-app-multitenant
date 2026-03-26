---
name: implement
description: Implement an approved plan, run automated tests, update PR and docs.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /implement

必読:
- docs/plans/open/$ARGUMENTS_plan.md
- docs/tests/open/$ARGUMENTS_auto_test.md
- docs/tests/open/$ARGUMENTS_manual_test.md
- docs/reviews/open/$ARGUMENTS_review.md

ルール:
- 計画書に書いていない実装は禁止。必要なら停止→提案→承認→計画更新。
- Danger Ops は danger-approved + DANGER_OK=1 が必須。
- テストフレームワーク（pytest 等）が存在しない・追加が必要な場合はユーザーに承認を得てからインストールする。
- 既存テストファイルのフレームワーク・形式（pytest / Django TestCase 等）を変更する場合もユーザーの承認が必須。承認なしの形式変更は禁止。

手順:
1) 計画どおり実装
2) テスト実行前に環境確認:
   ```bash
   cd backend && pip show pytest 2>/dev/null || echo "pytest not found"
   ```
3) 自動テスト実行
   - 成功: 手順 4) へ
   - 失敗: 即 STOP。以下を報告してユーザー待機:
     - 失敗したテスト名
     - エラー内容（期待値 / 実際値 / ログ抜粋）
     ```
     ⛔ テストが失敗しました。修正作業は開始しません。
     👉 続けるには `/fix-loop $ARGUMENTS` を入力してください。
     ```
4) docs/reviews と docs/tests に結果を記録
5) commit/push して PR を更新
6) 手動テスト要点を提示してユーザー検証（OK/NG）待ち
