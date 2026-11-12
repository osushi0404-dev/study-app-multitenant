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
- [test-gate] 2 回目: gate-check OK。手動テストはすべて Claude の分で、No.3 は fix-loop の後に OK・No.1/No.2 は直した差分（review-gate §3-1 の 1 行）の影響を受けないので結果を流用。Human の項目は無い
- [retro] 台帳の残り 7 件（F1・F2・F3・F5・F6・F7・F8。すべて Low・再現なし）→ `docs/reviews/backlog/I228.md`。後続イシューに回る行は 0 件
- [retro] 改善案「古いイシューを GitHub の番号で呼ぶと本文の読み取りが正しい名前を案内せずに止まる」→ #428 に同梱（同じ `issue-source.sh` と grill-me の入口を直すイシュー。会話の数手の手戻りが 2 回）
- [retro] 改善案「手順書に足したコマンドが allow に当たるかを計画の段階で確かめていない」→ 見送り。既存の決まり（承認画面の有無は `check-permission-prompt.sh` で自分で確かめる）に沿っていなかっただけで、手動テストの行で捕まり fix-loop 1 回（約 10 分）で直った。新しい手順は足さない
- [close] base 追従は不要（mergeStateStatus=BLOCKED）・gate-check OK。記録を closed へ移した（`I228_fix_diagnosis_20261113_0128.md` は close の回収の型 `*_review_*` に当たらないので docs/reviews/ 直下に残る）


## 振り返り

### かんたんなまとめ
**良かった点**
- 先にテストを書いて、今の仕組みでは新しいケースだけが落ちることを確かめてから作った（理由: 引き継ぎの条件が 1 つ欠けたら本当に止まるかを、壊した写しでも確かめられた）
- 整理の点検で「コンテナが止まっているときの出力も空振りとして数える」を足せた（理由: 案内どおりに流しても、コンテナが止まっていれば同じ損失が残るところだった）
- 基本レビューが疑った「コンテナを確かめるコマンドに承認画面が出る」を、テストの段階で実際に確かめて見つけ、その場で直した

**今回の問題への直接の対処**
- review-gate の手順に足した「コンテナが動いているかを見るコマンド」に承認画面が出ることが分かった。許可の決まりが引数なしの形だけだったため。→ 確かめを省き、動いていれば何もしない「コンテナを起こすコマンド」だけにした（許可済みで承認画面が出ないことを確かめた）

**同じ問題を次回から防ぐ改善**
- ユーザーが古いイシューを GitHub の番号（I423）で呼ぶと、本文を読む仕組みが「ファイルが無い」で止まるだけで、「#423 は I228 です」と教えなかった。新しい流れでは GitHub の番号で呼ぶのが普通になったため。→ 同じ仕組みを直すイシュー #428 に同梱して、正しい名前と、ファイルのある場所を案内するようにする
- 見送り: 手順書に足すコマンドの承認を計画の段階で確かめる手順は足さない（今ある決まりで足り、今回もその場で捕まえて直せたため）

### 詳細版
#### 良かった点
- TDD（Red: pass=116 fail=17 → Green: 134/0）・FG で引き継ぎの 4 条件と noexec の判定を固定した
- /simplify の高さの観点で `service "backend" is not running` を noexec に足し、再利用の観点で引き継ぎの起点を `REVIEW_BASE` にそろえた
- 台帳 F4 を test-gate で `check-permission-prompt.sh` により実証して NG にし、fix-loop 1 回で直した

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | review-gate §3-1 に足した `docker compose ps --status running --services` が allow（`Bash(docker compose ps)` の完全一致）に当たらない | §3-1 を `docker compose up -d backend` だけにした（fix-loop・手動 No.3 で承認なしを確認） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 本文の読み取りの入口が、I427 未満でファイルが無いとき GitHub の題名（`I###: `）を見ずに止めるので、GitHub の番号で呼ばれたときに正しい名前を案内できない | 止める理由に「#N は I###」と、他のワークツリーにあるファイルのパスを出す（#428 に同梱） | `scripts/claude/issue-source.sh`・そのテスト |

#### 5 Whys: GitHub の番号で呼ばれて止まった
- Why 1: `/grill-me I423` が「ファイルが無い」で止まった → I423 は手元のファイルで管理する番号の範囲で、そのファイルは無い
- Why 2: 本当は I228 のことだった → 今までの流れで起票したイシューは GitHub の番号と I### が違う
- Why 3: 仕組みが正しい名前を案内しなかった → 本文を読む入口は、I427 未満の経路で GitHub を読まずに止める決まりで、番号の対応を調べる手順が無い
- 根本原因（一般化）: 番号の体系を切り替えたとき、古い体系の名前を新しい体系の呼び方で呼ばれる場面への案内が入口に無かった

#### 見送り
- 計画の段階で手順書に足すコマンドの承認を確かめる手順: 既存の決まり（`check-permission-prompt.sh` で自分で確かめる）で足り、手動テストの行で捕まえて 1 周で直った

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
