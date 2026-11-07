# I212 レビュー: 差分のレビューの起点を「見終えた最新の記録」にする（失敗した回の後にセキュリティレビューを飛ばさない）

## 変更概要
- （実装後に記入）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config（ハーネス）: `scripts/claude/code-review.sh`・テスト（`test_i212_review_base.sh` 新規・`test_i197_review_ledger.sh`・`test_i193_official_flow.sh`・`test_i223_gh_app.sh`）・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`

## テスト結果
- 自動:
- 手動:

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する（設定・データの変更なし）

## 自律判断の記録
- [plan] 受け入れ条件 1 の「失敗した回」を「見終えていない回（/security-review が動かなかった・レビュー役の出力が壊れた）」に定めた — ユーザーの判断「ループエンジニアリング、ハーネスエンジニアリングのベストプラクティスと開発をサクサク進めるという観点で問題ないやり方を選択して」を受けた。指摘が残った HIGH まで外すと fix-loop のたびに全体を見直し、I197 の収束の設計が崩れる
- [plan] 同梱 2・4（/security-review の判定の 1 行）・6（G10）を入れ、3・5（敵対的レビュー）は別イシューに切り出す（retro で起票） — 2・4 は直さないとやり直しも同じ FAILED で止まる。3・5 は別の仕組みで設計の検討が要る
- [plan] gate-check.sh は直さない — 直した後の code-review.sh では見終えていない回は必ず HIGH／BLOCKER になり、やり直しは見終えた記録から差分を取るので、gate-check の結果は変わらない（plan §4-4）
