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
- 手動: No.1 OK・No.2 OK・No.3 は 1 回目 NG（`docker compose ps --status …` に承認画面）→ fix-loop の後 OK

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
- [review-gate] 基本レビュー OK（CI OK・RISK: NO・敵対的レビューは不要）。Low 5 件（F1 noexec の言い直しに新しい id を案内していない・F4 `docker compose ps --status …` が allow の完全一致に当たらない疑い ほか）は止める指摘ではないので直さず、retro で振り分ける
- [test-gate] 台帳 F4（コンテナの確認のコマンドが allow に当たらない疑い）を check-permission-prompt.sh で確かめ、承認画面が出ることを確認したので手動テスト No.3 として NG を記録し fix-loop に回した — 足した手順そのものが流れを止めるため（止める条件の「流れが動かなくなる」）
- [fix-loop] 診断レビュー PASS の案 C（確かめを省き常に `docker compose up -d backend`）で直した — 案 A（引数なしの `docker compose ps` の表を読む）より判断が要らず粗く確実、案 B（allow を足す）は `.claude/settings.json` が復旧できない例外で重すぎる
- [review-gate] 差分のレビュー OK（F4 は解消・新しい Low 3 件 F6〜F8〔`up -d` の作り直し・`--build` なし・失敗時の分岐〕は止める指摘ではなく retro へ）

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
