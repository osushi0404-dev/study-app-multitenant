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

## 振り返り

### I210 振り返り（かんたんなまとめ）

#### 良かった点
- 計画の前に小さな実験をして、作り方の前提を確かめた（理由: 鍵の順番が本当に守られていること、「鍵を待っている」ことは OS の一覧〔`/proc/locks`〕では見えないこと、大きな一覧で判定が 20 回中 20 回入れ替わることを、実装の前に確かめられた。見えないものに頼る作り方を最初から避けられた）
- 規則を実際のファイル全部に流して数を決めた（理由: 設計確認のときの手作業の検索は 3 か所と見ていたが、実際に流すと 4 か所あった。4 つ目〔テストの一覧の形の確認〕も同じ見逃しの向きで、このイシューの中で直せた）
- 直した後、CPU を使い切った状態で 20 回流して 20 回とも合格した。わざと壊した写しで落ちることも 1 つずつ確かめた（理由: 「たまたま合格した」でも「壊れても合格する」でもないことを示せた）

#### 今回の問題への直接の対処
- なし（直すべき問題はこのイシューの中で直した。レビューの軽い指摘 7 件は、軽い指摘の一覧〔`docs/reviews/backlog/I210.md`〕に入れた）

#### 同じ問題を次回から防ぐ改善
- なし。候補は 5 つあったが、どれも「その場で捕まって手戻りが無かった」か「実害が出ていない」ので、手順を増やさない（下の見送りの表）

### I210 振り返り

#### 良かった点
- 計画前のスパイク（鍵の直列化・`/proc/locks` の不可視・SIGPIPE の反転 20/20・fd 9 の引き継ぎ）で前提を確定した
- grill-me の「ツール実行による完了基準の確定」を計画で実ツールに置き換え、手作業の grep（3 か所）が漏らした `d3_bl` を拾った
- AC1 を負荷 20 回（`STRESS: 20/20`）、否定の項目を FG で確かめた

#### 是正処置（Corrective）
今回の事象への対処。同じ問題が再発しないための直接的な修正。
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| — | — | — | なし |

#### 予防処置（Preventive）
仕組み・ルール・スキルの変更により、類似の問題が他イシューでも起きないようにする。
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| — | — | — | — | なし |

#### 見送り（手順 2.7 の 4 問）
| 候補 | 判定 | 理由 |
|---|---|---|
| grill-me の手作業の grep が規則の当たりを 1 つ少なく数えた（引用符の中の `\|`） | 見送り | 計画で実際の規則を流して捕まり、手戻りなし（問 2）。grill-me の「ツールを実際に流す」決まりが既にある |
| N10 が負荷のときに落ちた正確な流れ（時計の巻き戻しか）が特定できなかった | 見送り | テストが実際の時計を読まない形にしたので、原因によらず起きない（20/20 で確認）。調べる費用に見合う損失が無い |
| `!` の無い `cmd \| grep -q`（pipefail の下で逆向きに反転）が 3 か所に残る | 見送り（一覧 F4） | 入力が小さく実害の場面が無い（問 1）。計画でそのファイルを触るときに一覧で見える |
| 計画のステップ 2 の順番（N15〜N19 の Red を先に見る）を守らなかった | 見送り | FG で効き目を確かめ、偽の合格は防げた（問 2）。手戻りなし |
| Bash の中の python のヒアドキュメントがワークツリーの守りに断られた | 見送り | Edit に切り替えて 1 回で済んだ（問 2）。守りの判定は「ローカルの守りは最小限」の方針どおり変えない |
| 性能の上限を測るテスト（`test_pretooluse_gh_pr_guard.sh` G182 など）も実時間に頼る | 見送り | 締め切りの判定とは別の種類で、揺れは観測されていない（問 1）。計画の調査結果 B に記録済み |

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

- [retro] 台帳の残り 7 件（F1〜F7）はすべて `docs/reviews/backlog/I210.md` へ（`--route issue` は 0 件。すべて Low・再現なし）
- [retro] `!` の無い `cmd | grep -q`（F4）は一覧のまま。後続イシューにしない — 当たる 3 か所（`code-review.sh:221` の CI の結果・`pr-base-sync.sh:80-81` の CI の結果・`wt-ports.sh:24` のポート番号）は入力が小さく（反転には 64KB を超える入力が要る）、実害の出る場面が無い
- [retro] 改善案 5 件はすべて見送り（下の「振り返り」の見送りの表）。是正処置・予防処置の表は 0 件

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
