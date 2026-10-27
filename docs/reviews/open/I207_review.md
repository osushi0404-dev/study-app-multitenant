# I207 レビュー: 台帳の残りを捨てるときに目印・重大度が消える穴を直し、軽い指摘は後続イシューにせず一覧へ回す

- 計画書: docs/plans/open/plan_I207.md
- イシュー: docs/issues/open/I207.md（#346）
- Draft PR: #347

## 変更概要
（implement の後に書く）

## 変更点
（implement の後に書く）

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: ハーネスだけ（`scripts/claude/code-review.sh`・`scripts/claude/tests/test_i202_ledger_cleanup.sh`・`.claude/skills/retro/SKILL.md`・`.claude/skills/plan-issue/SKILL.md`・`.claude/skills/review-gate/SKILL.md`・`.claude/agents/code-reviewer.md`・`docs/runbooks/review-rules.md`・`docs/reviews/backlog/I206.md`〔新規〕）

## テスト結果
（test-gate の後に書く）

## 計画との差分
（implement の後に書く）

## ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・文書・一覧ファイルだけ）

## 自律判断の記録
- [plan] ブランチ名を `feature/I207-ledger-backlog-routing` にした — イシューの 2 つの目的（台帳の直し・一覧への振り分け）を短く表す
- [plan] 台帳の残りの番号の行は、同じ回の前の行に関係なく行の中身だけで決める（`seen` の近道を外す）— F2 と同じ箇所の止まらない向きの穴 2 つ（resolved → 止める中身・止める中身 → resolved）も同じ根本で消える（計画書 4.1・9）
- [plan] 一覧は `docs/reviews/backlog/<起点のイシュー>.md`、見る場所は plan-issue のスキル — 並行のワークツリーで衝突せず、close の glob にも当たらない。計画を作るスキルなので必ず通る（計画書 9）
- [plan] 手動テストは一覧と計画のコマンドの 1 件だけ。このイシューの retro で新しい振り分けを使ったことは retro・close で記録する — test-gate は retro の前なので確かめられない

STAGE_DONE: plan NEXT: plan-review
