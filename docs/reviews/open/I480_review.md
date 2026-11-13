# I480 レビュー: SECURITY=yes でも Low・再現なしの指摘は軽い指摘の一覧に回す

## 変更概要
- retro の台帳の振り分け（`code-review.sh --route`）で、`SECURITY=yes` でも `SEV=Low` かつ `REPRO=no` の行は軽い指摘の一覧に回す。retro 4-0 の「最優先」の条件と review-rules の要約を合わせる

## 変更点
- `scripts/claude/code-review.sh`: `route_reasons()` の `SECURITY=yes` の条件・guard の行のコメント（一覧 I208 F1 の同梱）
- `.claude/skills/retro/SKILL.md`: 手順 4-0 の振り分けと最優先の条件
- `docs/runbooks/review-rules.md`: 振り分けの要約
- `scripts/claude/tests/test_i202_ledger_cleanup.sh`: Q7・FG-Q7 の直し、Q10・FG-Q10a〜c の追加
- `docs/reviews/backlog/I208.md`: F1 の行を消す

## 影響範囲
- Backend/Frontend/DB/Config: ハーネスの retro の振り分けだけ（`blocking()`・レビューの合否は変えない）

## テスト結果
- 自動: 未実施（計画の段階）
- 手動: 未実施

## 計画との差分
- なし

## ロールバック
- このブランチのコミットを revert する

## 自律判断の記録
- [plan-review] 計画レビュー OK（Warning 1 件: 最優先の条件を `後続イシューにする理由:` より後ろに限る形に直した。文言の明確化なので再レビューはしない） — 方式・範囲・受け入れ条件を変えないため
- [plan-review] 高リスク判定は NO（PLAN_VERDICT: OK）なので design-security-review を飛ばして implement へ — スクリプトの判定どおり

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
