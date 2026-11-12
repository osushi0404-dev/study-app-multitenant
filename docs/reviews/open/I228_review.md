# I228 レビュー: 敵対的レビューで、実験必須の項目が中身と関係なく未検証になって周を失うのを無くす

## 変更概要
- 敵対的レビュー（`scripts/claude/adversarial-review.sh`）で、前の周に実験で確かめた項目を、決まった条件（祖先・記録の場所の外の無変更・項目の行の一致）がそろうときだけ次の周に引き継ぐ
- コマンドが見つからないだけの実験を「実行した」に数えない。レビュー役への案内に、アプリのテストを `docker compose exec -T backend` で流すことを足す
- 計画の書き方と計画レビュー役に、決定論の TC で覆える性質を実験必須にしない決まりを足す

## 変更点
- `scripts/claude/adversarial-review.sh`: `record_item_verdicts`・`carry_items`（前の周の確認の引き継ぎ）・`exp_not_executable`（コマンドが見つからない・コンテナが止まっている出力を `noexec` に）・`APP_TEST_HINT`（実験の約束と noexec の返しに案内）・記録に「引き継ぎ」の行
- `scripts/claude/tests/test_i197_adversarial_process.sh`: スタブに `out_<id>`・A29〜A38（A36b 含む）と FG-A30/A31/A32/A35/A36
- `.claude/agents/adversarial-reviewer.md`・`.claude/skills/review-gate/SKILL.md`（§3-0・§3-1 のコンテナ・§3-3）・`docs/runbooks/review-rules.md`・`docs/runbooks/plan-writing-rules.md`（新しい節）・`.claude/agents/plan-reviewer.md`（P4 の行）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `scripts/claude/adversarial-review.sh`・`.claude/agents/adversarial-reviewer.md`・`.claude/agents/plan-reviewer.md`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`・`docs/runbooks/plan-writing-rules.md`・`scripts/claude/tests/test_i197_adversarial_process.sh`

## テスト結果
- 自動（手元）: TC-01 pass=134 fail=0・TC-02 test_i193_official_flow.sh pass=174・test_i202_ledger_cleanup.sh pass=157（全体は CI）
- 手動: （test-gate で記入）

## 計画との差分
- なし

## ロールバック
- PR を revert する（スクリプト・文書・テストだけ）

## 自律判断の記録
- [plan] I423 は手元のファイルで管理する I228（#423）。app-1 に未コミットで残っていたファイルを grill-me で harness-1 に写して正にし、`/plan-issue I228` でコミットした — ワークツリーの境目を守るため app-1 のファイルは直していない
- [plan] 引き継ぎの条件に「項目の行が前の周の時点の計画書と同じ」を足した — 計画書は記録の場所なので、grill-me の条件だけだと項目の文言を変えた周でも引き継ぐ。止める側への追加
- [plan] 空振りした実験の言い直しに往復を足さず、既存の往復の中で理由つきの結果を返す — 上限を増やさない（I197・I205）
- [plan-review] 計画レビュー OK（高リスク判定 No）。Warning 2 件（コンテナを起こすコマンドの承認の根拠・A36 の出力の実物）を計画とテスト文書に書き足した。方式・範囲・受け入れ条件は変えないので再レビューしない
- [implement] テストを先に足し、今の本体で新しい 17 件だけが落ちることを確かめてから実装した（Red→Green）
- [implement] /simplify の指摘のうち、引き継ぎの起点を `REVIEW_BASE` にそろえる・コンテナ停止の出力を noexec に足す・テストの重複整理を採った。記録末尾の機械の行で判定を持つ案と `prev_tbl` の統合は見送り（計画変更記録に理由）
- [implement] shellcheck はホストに無いので、commit 時の pre-commit の shellcheck に任せた

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement
