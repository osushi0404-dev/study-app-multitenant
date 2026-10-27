# I205 手動テスト: レビューで止める基準を変更の種類で分ける・差分の中かどうかを行で決める

実際の code-reviewer（スクリプトが起動する別プロセスの `claude -p`）が新しい FINDING 行の形で書けるかと、retro の手順の実物での動きを確かめる。承認画面の有無は確かめる対象に含まない（スクリプトの起動のしかたは変えない）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 実装の後、このイシュー自身の review-gate の最初の記録（`docs/reviews/I205_code_review_*.md` のうち、実装後の最初のもの）を読む | ①「形の崩れた FINDING 行」による BLOCKER が出ていない（出ていれば、その周の FINDING 行を見て、どの欄で崩れたかを記録する）②`## 台帳（累積・スクリプトが書く）` の `LEDGER:` 行に `KIND=`・`STOP=`・`REPRO=` がある（指摘が 0 件なら「指摘なし」と書いてあり、台帳の行が無い）③`## 止める指摘（スクリプトが決めた` の節がある ④FINAL VERDICT が台帳の止める指摘の有無と一致する | Claude | OK（2026-10-27・`docs/reviews/I205_code_review_20261027_1123.md`・HEAD 7f3167e）: ①形の崩れの BLOCKER は無い（FINDING 行 F1〜F10 の 10 行がすべて読めた）②`LEDGER:` の 10 行すべてに `KIND=harness`・`STOP=-`・`REPRO=yes|no` がある ③`## 止める指摘（スクリプトが決めた・fix-loop が直すのはこれだけ）` の節がある（中身は 0 件）④止める指摘 0 件で FINAL VERDICT OK（一致） | 実物の LLM が新しい形で書けるかの確認。①が NG なら code-reviewer.md の書き方を直す（fix-loop） |
| 2 | ①このブランチが変えたファイルの一覧（`git -c core.quotePath=false diff --name-only origin/develop...HEAD`）を scratchpad のファイルに書き、`code-review.sh` を `REVIEW_LIB_SOURCE_ONLY=1` で読み込むスクリプト（scratchpad）で `kinds` モードに渡して出力を見る ②手順 1 の記録の `FINDING:` 行の `STOP=` の値をすべて見る | ①記録の場所の外のファイル（`scripts/claude/`・`.claude/`・`docs/runbooks/`）の行がすべて `harness`（`guard`・`app` が 0 行）②`STOP=` の値がどれも `flow`・`leak`・`github`・`ac:<番号>`・`-` のどれか（指摘が 0 件なら②は「該当なし」） | Claude | OK（2026-10-27）: ①ブランチが変えた 18 ファイル（記録の場所を含む）がすべて `harness`（`guard`・`app` は 0 行）。scratchpad のスクリプトで `ledger_kinds` を呼んだ ②手順 1 の記録の F1〜F10 の `STOP=` はすべて `-` | 入力の「変更の種類」の節は記録に残らない（入力は一時ファイル）ので、同じ関数を直接呼んで確かめる。入力に節が入ることは TC-01 の W4 で確かめる |
| 3 | `.claude/skills/retro/SKILL.md` の「4-0) 台帳の残り」のコマンドを、I197 の最後のコードレビューの記録（`docs/reviews/closed/I197_code_review_20261027_0140.md`）に当てて実行する | I197 の台帳の `STATUS=open` の行（F5〜F19 の Medium・Low）が出る。出た番号が I202（#338）の本文の F5〜F19 と一致する | Claude | OK（2026-10-27）: `grep -h '^LEDGER: .*STATUS=open' docs/reviews/closed/I197_code_review_20261027_0140.md` で F5〜F19 の 15 行（Medium 7・Low 8）が出た。I202 の本文の F5〜F19 と番号・内容が一致 | 手順のコマンドが実物の記録で動くかの確認 |

結論: OK（No.1〜3 すべて OK・2026-10-27。Human の項目なし）

再確認（計画変更記録 2・F11 の修正の後・2026-10-27）: No.1 は差分のレビューの記録 `docs/reviews/I205_code_review_20261027_1307.md`（F11〜F17 の 7 行）・`_1322.md`（F11・F18・F19）でも、形の崩れは 0 件・止める指摘の節あり・合否は台帳と一致（1307 は止める指摘 F11 で HIGH、1322 は 0 件で OK）。No.2・No.3 が見る関数（`kind_of`）と手順（retro 4-0）は今回の修正で変えていないので、結果は同じ
