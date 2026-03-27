# I014 レビュー: /implement 細分化・/code-review・/test スキル新設

## 変更概要
- `.claude/skills/implement/SKILL.md`: 自動テスト・CI確認・手動テスト手順を削除し push 後停止に変更
- `.claude/skills/code-review/SKILL.md`: 新規作成（CI確認 + 受け入れ条件照合）
- `.claude/skills/test/SKILL.md`: 新規作成（自動テスト + 手動テスト確認）
- `docs/runbooks/workflow.md`: フロー定義・移行案内テーブルを新フローに更新

## 変更点
- `.claude/skills/implement/SKILL.md`: 変更
- `.claude/skills/code-review/SKILL.md`: 新規
- `.claude/skills/test/SKILL.md`: 新規
- `docs/runbooks/workflow.md`: 変更

## 影響範囲
- Backend/Frontend/DB: なし（スキル定義とドキュメントのみ）
- Config/Infra: .claude/skills/ 以下のスキル定義

## テスト結果
- 自動: CI 全5ジョブ pass（run ID: 23639244530）、ローカル pytest 25 passed、Jest 7 passed（2026-03-27）
- 手動: 全7項目 OK（2026-03-27）

## 計画との差分
-（実装後に記録）

## ロールバック
- git revert で各スキルファイルを元に戻す

## ユーザー承認
<!-- ⚠️ この欄は Claude が記入禁止。ユーザーが確認後に記入すること。 -->
- **承認日**:
- **手動テスト確認**: 未実施 / 確認済み
