# I208 レビュー: 台帳の残りの振り分けと一覧の行をスクリプトが出すようにし、テストを実物の一覧に依存させない

- 計画書: docs/plans/open/plan_I208.md
- イシュー: docs/issues/open/I208.md（#348）
- Draft PR: #350

## 変更概要
（implement で書く）

## 変更点
（implement で書く）

## 影響範囲
- ハーネスだけ（`scripts/claude/code-review.sh`・テスト 2 本・retro・plan-issue・review-rules・`docs/reviews/backlog/I207.md`）。アプリ本体・DB・設定の変更なし

## テスト結果
（test-gate で書く）

## 計画との差分
（実装で計画と違うことをしたら書く）

## ロールバック
- PR を revert する（計画書 7。周の途中のイシューが無いときに行う）

## 自律判断の記録
- [plan-review] 計画レビューの Warning 2 件を直し、再レビューはしない — 引数不足の終了コードと revert 前の確認の追記だけで、方式・範囲・受け入れ条件は変えない（計画変更記録 1）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
