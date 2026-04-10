# I032 レビュー: GitHub Branch protection rules 設定手順書の作成と適用

## 変更概要
- `docs/runbooks/branch-protection-setup.md` を新規作成し、GitHub Branch protection rules の設定手順を文書化する

## 変更点
- `docs/runbooks/branch-protection-setup.md` 新規作成（develop / main の設定値・操作手順・動作確認手順・ロールバック手順）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: GitHub リポジトリ Settings（ユーザーが手順書に従って操作）

## テスト結果
- 自動: （実装後に記入）
- 手動: （ユーザーテスト実施後に記入）

## 計画との差分
- なし

## ロールバック
- GitHub Settings で Branch protection rules を削除するだけで即時復元可能
