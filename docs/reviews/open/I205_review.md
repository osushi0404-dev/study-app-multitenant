# I205 レビュー: レビューで止める基準を変更の種類で分ける・差分の中かどうかを行で決める

- 計画書: docs/plans/open/plan_I205.md
- イシュー: docs/issues/open/I205.md（#341）
- Draft PR: #342

## 変更概要
基本レビューの止める基準を、変更の種類（アプリ本体／GitHub から復旧できない例外／それ以外のハーネス）で分けた。止めるかどうかは、FINDING 行の欄（FILE・LINE・STOP・再現）からスクリプトが決める。差分の中かどうかを、ファイル単位から行単位（変えた行と前後 3 行）に変えた。code-reviewer の VERDICT 行は、全体のレビューでも合否に使わない。fix-loop は記録の「止める指摘」の節だけを直す。retro は台帳の残りを必ず 1 か所に振り分ける。

## 変更点
- `scripts/claude/code-review.sh`: `branch_own_files`・`delta_hunks`（`_HUNKS_PY`）を追加し、`delta_files` を `branch_own_files` の上に作り直した。`_LEDGER_PY` は FINDING 行・台帳の行の新しい欄、前の形の台帳の行も読む、`kind_of`、`kinds` モード、行で決める `scope_of`（casefold）、種類ごとの `blocking()` に変えた。本体は行の塊・ブランチのファイルを台帳に渡し、入力に「変更の種類」の節を足し、記録に「止める指摘（スクリプトが決めた）」の節を足し、全体のレビューでも LLM の VERDICT を合否に使わないようにした
- `.claude/agents/code-reviewer.md`: 「止める指摘の書き方（I205）」の節を追加（種類ごとの止め方・止める条件の一覧・再現・LINE）。FINDING 行の形を変え、指摘の表を外し（F11）、VERDICT 行の説明と重大度の表を直した
- `.claude/skills/review-gate/SKILL.md`: §1 の止める基準、§2 の上限（最後の安全網）と直す範囲、§3-2 のアプリ本体のイシューに関係する Medium の扱いを直した
- `.claude/skills/fix-loop/SKILL.md`: 直す範囲を「止める指摘（スクリプトが決めた）」の節に変えた
- `.claude/skills/retro/SKILL.md`: 手順 4-0「台帳の残り」を追加した
- `docs/runbooks/review-rules.md`: 「検証の全体設計」に、変更の種類ごとの止める基準の表を足した
- `scripts/claude/tests/test_i205_stop_criteria.sh`（新設・78 項目）。`test_i197_review_ledger.sh`・`test_i193_official_flow.sh`（S19）・`test_fix_review.sh`（TC-22・TC-26）は、新しい形・語に付け替えた

## 影響範囲
ハーネスだけ（`scripts/claude/code-review.sh`・`.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/`・`.claude/skills/fix-loop/`・`.claude/skills/retro/`・`docs/runbooks/review-rules.md`・`scripts/claude/tests/`）。アプリ本体・DB・GitHub の設定は変えない。

## テスト結果
- 自動: 決定論ゲート 12 本すべて exit 0（review-gate・HEAD 7f3167e）。CI 全ジョブ pass（Harness Tests を含む）。gate-check OK
- 手動: No.1〜3 すべて OK（実施者はすべて Claude・Human の項目なし）。実物のレビュー役が新しい FINDING 行の形で 10 行を書き、形の崩れは 0 件

- （計画変更記録 2）`scripts/claude/code-review.sh`: `delta_hunks` の git diff に `--no-ext-diff --no-textconv --no-relative --src-prefix=a/ --dst-prefix=b/` を付けた（F1）。塊を読む処理を `hunks_from_diff` にし、見出しは最初の `@@` までだけ読む（F6）。対象のファイルのうち diff に出てこなかったものはファイル全体にした（F2）。テストに H7〜H9・B7 の追加・FG-H7〜H9 を足した

## 計画との差分
- `delta_files` を `branch_own_files` の上に作り直した（/simplify の指摘。挙動は同じで、R2・FG-R2 で確かめた）。計画の範囲（code-review.sh の範囲の決め方）の中の整理
- 計画 §5 のステップ 6 の「語の付け替え」で、`test_i193_official_flow.sh`（S19）・`test_fix_review.sh`（TC-22・TC-26）も直した（スキルの語を変えたため）

## 振り返り

### I205 振り返り（かんたんなまとめ）

#### 良かった点
- 新しい止め方で、レビューが 1 回で終わりました。I197 は同じ種類の仕組みを直すのに 3 回かかっていました。今回、レビュー役は 10 件の指摘を出しましたが、どれも「流れが止まる・情報が漏れる・GitHub を壊す・受け入れ条件を満たさない」に当たりませんでした。そのため止まらず、後続のイシューへ回りました（理由: 止める条件を先に決めてから問う、閉じた問いにしたため）。
- 実物のレビュー役が、新しい指摘の書き方（行番号・止める条件・再現）で 10 行を書き、書き方の崩れは 0 件でした。
- 設計確認で決めたことと、今の最後の関所（gate-check）が食い違う点に、計画を書く段階で気づきました。実装の前にユーザーに 1 問だけ確認して決めたので、手戻りはありませんでした。

#### 今回の問題への直接の対処
- 止めなかった指摘 10 件は、同じ仕組みの残りを片付けるイシュー I202 にまとめて同梱しました。その中には、判定の仕組みの穴が 4 件あります（git の設定で行の位置がずれうる、など）。このため I202 を「次のハーネスの作業で最優先」にしました（理由: 1 件ずつ起票すると管理が増えるので、合う既存のイシューに入れる決まりに従ったため）。
- I202 にあった 2 件（表の中だけの指摘が素通りする・大文字と小文字の表記違い）は、I205 で直したことを I202 に書き添えました。

#### 同じ問題を次回から防ぐ改善
- 新しい改善は足しません。今回の小さなつまずき（設計確認の段階で関所との食い違いに気づけなかった・作業中のコマンドの順番の取り違え）は、どれもその場で見つかり、手戻りが無かったためです。決まりを増やさないほうが、進みが速いままです。

### I205 振り返り（詳細）

#### 良かった点
- 基本レビュー 1 周で OK（台帳 1 周目・F1〜F10 はすべて harness・`STOP=-`）。I197 は 3 周（止める指摘 4→1→0）。周の数が減るかの確認（設計確認メモ 4 問目）の最初のデータ点
- 実物の code-reviewer が新しい FINDING 行の形で 10 行を書き、形の崩れは 0 件（手動 No.1）
- 設計確認メモ 2 問目と `gate-check.sh` の食い違いを /plan-issue で検出し、ユーザー確認 1 問で確定（手戻りなし）

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | セキュリティ（判定の仕組み） | 行で範囲を決める処理に、fail-open の向きの穴が残った（I205-F1・F2・F4・F6） | I202（#338）に同梱し、次のハーネスの作業で最優先と明記（手順 4-0） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| （なし） | | | | |

#### 見送り（理由つき）
- 設計確認の段階で、既存の関所（gate-check）との食い違いを確かめる観点を grill-me に足す案 → 見送り。/plan-issue の段階で捕まり、手戻りが無かった（2.7 の 2 問目）
- 実装中の取り違え（一時ファイルを書く前にそのファイルを読むコマンドを実行した・テストの引数の空白の欠落）→ 見送り。どちらも即座に失敗して実害なし。後者はテストが捕まえた

## ロールバック
PR を revert する。レビューの途中のイシューがあれば、新しい形で書かれたコードレビューの記録の名前を変えて退避する（計画書 7）。

## 自律判断の記録
- [plan] F11・F16（I202）は I205 で直す — 範囲・判定の決め方そのもので、ここで変えないと I205 の判定に既知の抜け道が残るため
- [plan] ハーネスは重大度を見ずに、止める条件の一覧と再現で決める。guard は再現を問わず今の強さのまま — ラベルを下げて関所を通す抜け道を閉じるため／GitHub から戻せない変更を緩める理由が無いため
- [plan] ハーネスの場所の一覧に無いものはアプリ本体（厳しい側）。FILE=- の種類はブランチが変えたファイルから guard＞app＞harness — 知らない場所で甘くならないため
- [plan] 前後の行数は 3 — git の既定の前後の行数と同じで、レビュー役が見る差分の見た目と合うため
- [plan-review] 計画レビュー OK（高リスク判定 No）。Warning 4 件は計画に反映し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記のため（計画変更記録 1）
- [implement] I197 のテストでは、アプリ本体の Medium で「止めない」を確かめていた項目（R5・R7・R13・R14 の F2）を Low に置き換えた — I205 でアプリ本体の Medium は止まるようになり、その確かめは test_i205 の B2 が持つため。FINDING 行は body() で新しい形に直して、I197 の項目の意味を保った
- [implement] /simplify を適用した: delta_files を branch_own_files の上に作り直した・全体のレビューの塊は 1 回だけ読む・変数名 review_kind・再現の読み取りを 1 つの正規表現に・code-reviewer.md の重複の 1 文を削除・K2 のテストを 1 回の読み込みに — 重複と無駄を減らすため
- [implement] /simplify の指摘のうち次は見送った: guard の集合を bash 側で決める（言語をまたぐ受け渡しが増える。R-K2 の一致テストで固定する計画の判断のまま）／台帳の項目の名前付き化（手を入れる量に見合わない）／delta_hunks にファイル一覧を渡す（数十ミリ秒の差で、関数を単体で確かめられる形を保つ）／敵対的レビューの Medium の扱いを blocking() に通す（ユーザー決定で止め方を揃えない）／テストの補助関数の共通化（テストを 1 本で完結させる既存の慣例）
- [review-gate] 基本レビュー（`docs/reviews/I205_code_review_20261027_1123.md`・全体・台帳 1 周目）は OK・高リスク NO で敵対的レビューは不要。指摘 F1〜F10 はすべてハーネスで `STOP=-`（一覧に当たらない）なので止めず、直さない — I205 の新しい決まりのとおり。F1（git の diff の設定で塊がずれうる）・F2（塊が見つからないときに outside になる）・F4・F6 は判定の仕組みの穴（fail-open の向き）なので、retro が後続のイシューで「次のハーネスの作業で最優先」にする。F5 の要約が台帳で途中で切れている（要約の中に `| 再現:` の文字が含まれ、そこで切った）のも同じ後続に入れる
- [review-gate] 新しい FINDING 行の形で実物のレビュー役が 10 行を書き、形の崩れは 0 件（手動 No.1 の材料）
- [retro] 台帳の残り（`docs/reviews/I205_code_review_20261027_1123.md`）の 10 件 F1〜F10 → すべて #338（I202）に同梱（コメント 6432355581）。判定の仕組みの指摘（F1・F2・F4・F6）を含むので「次のハーネスの作業で最優先」と明記 — 同じ仕組みの残りを片付ける既存のイシューがあり、1 件ずつ起票しないため。KIND=app の指摘は 0 件
- [retro] I202 の F11・F16 は I205 で直したと #338 に記載（計画 4.10）
- [retro] 改善案 2 件は見送り（その場で捕まり手戻りなし）。新規起票なし
- [close の後・ユーザー決定] F1・F2・F6（行の塊の読み取りが見逃し側に倒れる穴）を、I202 に回さずこの PR で直す（計画 4.11・計画変更記録 2）。記録を open に戻し、計画レビューから通り直す — 次のアプリのイシュー（I196）がこの判定を使うため、develop に入れる前に直す（ユーザーが評価を経て合意）
- [plan-review] 追記分の計画レビュー（`docs/reviews/I205_plan_review_20261027_1300.md`）OK・高リスク No。Warning 3 件・Info 2 件は計画に反映し、再レビューはしない（計画変更記録 2）
- [implement] 計画 4.11 を実装（F1・F2・F6）。/simplify は今回の追加分では呼ばなかった — 変えたのは 1 回目の /simplify で整理済みの同じ関数の約 40 行で、見出しの読み方・オプション・読めなかったときの扱いだけ（新しい重複・無駄を生む形の変更ではない）。整理の点検は review-gate の組み込み /code-review が受け持つ
- [review-gate] 差分のレビュー（`docs/reviews/I205_code_review_20261027_1307.md`・台帳 2 周目）は HIGH。止める指摘は F11（`STOP=flow`・再現あり: 空白を含むパスで git が `+++ b/<パス>` の後ろにタブを付け、塊の行が 4 列になって台帳の作成が落ちる）の 1 件だけ。F12〜F17 は `STOP=-` で止めない（retro が I202 に回す） — I205 の決まりのとおり
- [fix-loop] F11 は再現を確かめた（scratchpad の f11.sh で 4 列の行が出た）うえで、案 A（行末のタブを取り除く）＋案 B（塊の行を後ろから 2 列で読む）で直した。診断レビュー PASS（`docs/reviews/I205_fix_diagnosis_review_20261027_1318.md`） — 原因を直し、同じ種類の列のずれでも流れを止めないため。どちらも 1 行で新しいコードをほとんど足さない
- [review-gate] 差分のレビュー（`docs/reviews/I205_code_review_20261027_1322.md`・台帳 3 周目）は OK。F11 は resolved。新しい F18・F19（Low・`STOP=-`）は止めない（retro が I202 に回す）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
STAGE_DONE: close NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
