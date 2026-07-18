# I086 レビュー: 高リスク変更の敵対的レビューステージ自動化

- 関連イシュー: #169
- 対象計画書: docs/plans/open/plan_I086.md

## 変更概要
- /code-review の高リスク判定を機械可読化（RISK 行 fail-closed＋パス決定論トリガ）し、高リスク時のみ敵対的レビューステージ（反証マンデート×固定 3 観点＋動的最大 2・loop-until-dry・依頼側修正→対応後再レビュー・上限打ち切り）をスキル主導で自動起動する。実装者の自己認証を非権威化。

## 変更点
- （実装後に記録）

## 影響範囲
- Backend/Frontend/DB: なし・Config はハーネススクリプト/文書 5 変更＋新規 2（adversarial-reviewer.md・test_adversarial_trigger.sh）

## テスト結果
- 自動: （/code-review・/test 時に記録）
- 手動: （/test 時に記録）

## 計画との差分
- （実装後に記録）

## ロールバック
- git revert のみ（DB・設定・サービス影響なし。revert で現行フローに完全復帰）
