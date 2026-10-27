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

## 計画との差分
- `delta_files` を `branch_own_files` の上に作り直した（/simplify の指摘。挙動は同じで、R2・FG-R2 で確かめた）。計画の範囲（code-review.sh の範囲の決め方）の中の整理
- 計画 §5 のステップ 6 の「語の付け替え」で、`test_i193_official_flow.sh`（S19）・`test_fix_review.sh`（TC-22・TC-26）も直した（スキルの語を変えたため）

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

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
