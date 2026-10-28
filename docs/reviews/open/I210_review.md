# I210 レビュー: ハーネスのテスト N10（敵対的レビューの締め切り）が実時間に依存して揺れるのを直す

- 計画書: docs/plans/open/plan_I210.md
- イシュー: docs/issues/open/I210.md（#352）
- Draft PR: #353

## 変更概要
敵対的レビューの締め切りの計算が読む時刻を `adv_now` 1 か所に集め、テストは `ADV_CLOCK_FILE`（偽の時計）で待たずに境目の前後を作るようにした。N10・FG-N10・A1b は偽の時計、A1・FG-A1 は相手の開始を待つ形で、実時間の速さに左右されない。あわせて、pipefail の下の `! … | grep -q` が大きな入力で結果を反転させる 4 か所を直し、その形を止める規則のテストを足した。負荷をかけてテストを繰り返す道具 `stress-repeat.sh` も足した。

## 変更点
- `scripts/claude/adversarial-review.sh`: `adv_now`（`ADV_CLOCK_FILE` があれば中身の整数の秒・無ければ `date +%s`）・`remaining`（読めなければ 0）・`elapsed_since`（表示用）。起動時に時刻を読めなければ exit 2（`ADVERSARIAL_ERROR: CLOCK`）。既定値・判定の式は変えていない
- `scripts/claude/tests/test_i202_ledger_cleanup.sh`: 偽物の実験役を「順番の印を待つ・偽の時計を進める」形に。A1・FG-A1・A1b・N10・FG-N10 を書き換え、I210 の節（N15〜N19）を足した。`d3_bl` の反転を直した
- `scripts/claude/check-frontend-evidence.sh`: 27 行の反転をヒアストリングの `grep -q` に。`test_check_frontend_evidence.sh` に E16〜E18
- `scripts/claude/tests/test_posttooluse_check.sh`: 32 行を同じ形に。`test_i193_official_flow.sh`: 前の形の写しと、それを合格の条件にする FG を消した
- 新規 `scripts/claude/tests/test_pipefail_negated_grep.sh`（規則）・`scripts/claude/tests/stress-repeat.sh`（負荷をかけて繰り返す道具）・`scripts/claude/tests/test_stress_repeat.sh`（道具のテスト）
- `docs/reviews/backlog/I206.md` の F5・`docs/reviews/backlog/I195.md` の F11 の行を消した

## 影響範囲
- ハーネスだけ（`scripts/claude/adversarial-review.sh`・`scripts/claude/check-frontend-evidence.sh`・テスト 4 本の書き換えと 3 本の新規・`docs/reviews/backlog/I206.md`・`docs/reviews/backlog/I195.md`）。アプリ本体・DB・設定の変更なし

## テスト結果
- 自動: TC-01 `test_i202_ledger_cleanup.sh` pass=157・TC-01b 規則のテスト pass=10（実装前は 4 か所に当たって不合格）・TC-01c pass=5・TC-02 pass=19・TC-03 関係する 3 本すべて合格・TC-04 CI 全緑（Harness Tests を含む）
- gate-check: GATE_CHECK OK（2026-10-28）
- 手動: No.1 負荷をかけて 20 回 → `STRESS: 20/20`（AC1）・No.2 前の `check-frontend-evidence.sh` では E16 だけが落ちる（AC6 の失敗注入）。どちらも Claude 実施・Human の項目なし

## 計画との差分
- 計画変更記録 1（計画レビューの Warning 対応）・2（`/simplify` の整理: 反転の直し方をリポジトリのヒアストリングの形にそろえた・`d3_bl` は grep のまま全部読む形・E16/E17 は 1000 個など）。どちらも方式・範囲・受け入れ条件は変えない

## ロールバック
- PR を revert する（計画書 7）

## 自律判断の記録
- [plan] 時刻の注入点は `adv_now`（`ADV_CLOCK_FILE` のファイルを読む）1 つにした — 判定の 2 か所と `step_timeout` がすべて `remaining()` を通るため。コマンドを渡す形は任意のコマンドの実行になるので避けた
- [plan] 鍵の待ちの順番は、本体が鍵の前に書く `exec_in1.txt` を偽物の実験役が待つ形で作る — `/proc/locks` は `flock 9` の鍵を表示しない（スパイクで確認）。偽の時計だけでは FG-N10 が揺れる
- [plan] 規則（`! … | grep -q`）を実物で流したら 4 か所（grill-me の時点の見立ては 3 か所）。`test_i202` の `d3_bl` も同じ見逃しの向きなので直す。`test_i193` 527 行は一覧 I195 F11 を同梱して消す — 規則に除外の印を作らないため
- [plan] AC1 の負荷は CPU の数だけのループ（`stress-repeat.sh`）にした — I195 で落ちたのは CPU が埋まっていたとき。新しい道具を入れずに手元と CI で同じ形にできる

- [plan-review] 判定 OK（高リスク No）。Warning 2 件（stress-repeat.sh の失敗注入・表示の経過の秒）は計画に足し、規則の誤検知の Warning は許容した — 方式・範囲・受け入れ条件は変わらないので再レビューはしない
- [implement] 計画のステップ 2 の「N15〜N19 を先に書いて落ちることを確かめる」は、ステップ 1 で 4.1 をまとめて入れたので Red を見ていない。代わりに N15・N16・N18・N19 は壊した写しで不合格になる FG を付けて効き目を確かめた — 計画の目的（偽の合格を防ぐ）は FG で満たせる
- [implement] 手動 No.2（前の `check-frontend-evidence.sh` で E16 が落ちる）は implement で実施して記録した — test-gate を待たずに確かめられ、/simplify で一覧を 1000 個に減らした後にもう一度流して同じ結果
- [implement] /simplify の指摘のうち、本体に実験の場所を渡す環境変数（`ADV_RUN_DIR`）・A1 の待ちのやり方の作り直しは採らなかった — 計画で決めた形で、順番の印の時間切れは N10 が毎回落とす。本番の本体にテストのための値を増やさない
- [implement] /simplify が挙げた「`!` の無い `cmd | grep -q`（pipefail の下で、見つけたのに見つからない側に倒れる）が `code-review.sh:221`・`pr-base-sync.sh`・`wt-ports.sh` に残る」は、このイシューの範囲（`!` の形）の外なので直していない — retro で扱いを決める

- [review-gate] 基本レビュー OK（`docs/reviews/I210_code_review_20261028_1236.md`・CI_WAIT: OK・RISK: NO・敵対的レビューは不要）。台帳の F1〜F7 はすべて Low・再現なしで止めない — retro が一覧か後続イシューへ回す

- [test-gate] 手動はどちらも Claude で実施し OK（No.1 は 20/20）。Human の項目は無いので retro へ進む — 計画の実施者のとおり

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
