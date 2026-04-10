# I031 レビュー: issue-flow.md の採番ロジックを issue-bootstrap スキルの実装に統一

## 変更概要
- `docs/runbooks/issue-flow.md` の採番ロジック説明を、`issue-bootstrap` スキルの実装に合わせて修正

## 変更点
- `docs/runbooks/issue-flow.md` 内の旧採番ロジック（ローカル最大 + GitHub件数 + 1）を 3 箇所すべて新ロジック（FS最大値と git履歴最大値の大きい方 + 1）に置換

## 影響範囲
- Backend/Frontend/DB/Config: なし（docs のみ）

## テスト結果
- 自動: OK（Backend: 25 passed / Frontend: 7 passed / 自動チェック: 旧キーワード 0件・I039 残留なし）
- 手動: OK（全8項目確認済み・2026-04-10）

## 計画との差分
- なし

## ロールバック
- `git revert` で即時復元可能
