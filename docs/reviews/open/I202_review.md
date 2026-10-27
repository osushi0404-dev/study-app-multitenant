# I202 レビュー: I197・I205 の台帳に残った指摘と、見送った共通化を片付ける

- 計画書: docs/plans/open/plan_I202.md
- イシュー: docs/issues/open/I202.md（#338）
- Draft PR: #343

## 変更概要
F5（計画の見立てを超えた高リスクの変更が敵対的レビューに入らない穴）を、FINDING 行の任意の目印 `RISK=up` で閉じた。目印が台帳（今回と前の周の記録）に 1 件でもあれば、スクリプトが高リスクを YES にし、一度 YES になったら戻らない。判定の穴（I205-F3〜F5・I197-F12・F18）と台帳の限界（止めない指摘は直しても open のまま）を直し、敵対的レビューの細部（F6〜F8・空の括弧）と、3 本のスクリプトに分かれていた記録の探し方などを共通化した。残りは計画書 4.0 の表のとおり見送った（理由つき）。

## 変更点
- `scripts/claude/code-review.sh`: `review_records`・`record_reviewed_commit` を追加し、`branch_own_files` を `-z` で読む形（rev 指定可）に変えた。`_LEDGER_PY` に `RISK=` の欄・`risk`・`open` モード・`split_repro`（最後の `| 再現:`・「なし」は再現なし）・`is_rest`、guard のファイル単位の判定・`kind_of` の casefold・同じ番号の 2 回目の扱い・台帳の残りの resolved の受け付けを足した。本体は、範囲が空の差分のレビューでレビュー役・組み込みのレビューを呼ばず、入力に「台帳の残り」の節・空の台帳の番号の書き方を足し、台帳の目印で高リスクを YES にし、レビュー役の失敗時に食い違いの検査をしないようにした。`git diff` 3 か所に `--literal-pathspecs`
- `scripts/claude/adversarial-review.sh`: 実験役を `flock` で 1 本ずつにし、待った後に締め切りが迫れば呼ばない。`review_base` は祖先でない起点を使わない。拒否の一覧を読めない記録があれば合格にしない。note が空のとき空の括弧を出さない。記録の探し方は共通の関数
- `scripts/claude/gate-check.sh`: 記録の探し方・REVIEWED_COMMIT の読み方・ブランチが変えたファイルを共通の関数に付け替えた（挙動は同じ。G4 で付け替え前の版と比べて確かめた）
- `.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`: 台帳の目印・台帳の残り・消した行の行番号・「再現: なし」の書き方
- テスト: `test_i202_ledger_cleanup.sh`（新設・67 項目）。`test_i197_review_ledger.sh`（R17 を消し FG-R14c・FG-R16a/b）・`test_i205_stop_criteria.sh`（H7 の設定の後片付け・H10b）・`test_i197_adversarial_process.sh`（S5 の grep を字下げに合わせた）

## 影響範囲
ハーネスだけ（`scripts/claude/code-review.sh`・`scripts/claude/adversarial-review.sh`・`scripts/claude/gate-check.sh`〔関数の置き場所だけ〕・`.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`・`scripts/claude/tests/`）。アプリ本体・DB・GitHub の設定は変えない。

## テスト結果
（test-gate で記入）

## 計画との差分
- 計画変更記録 2: 台帳の残りの番号は resolved のときだけ受け付ける（open の受け付けは I197-F1 の穴を戻すため）
- 計画変更記録 3: G5 を静的な確認に変えた（glob で拾っても塊の出力は変わらないことをスパイクで確かめた）
- /simplify の指摘で整理した（下の自律判断の記録）

## ロールバック
計画書 §7 のとおり（PR の revert。レビューの途中のイシューがあれば、新しい形の記録を退避して全体のレビューからやり直す）。

## 自律判断の記録
- [plan-review] 計画レビューの Warning 3 件（V3 の文言・F14 の条件・F6 の締め切りと F8 の語彙）を計画書・auto_test に反映し、再レビューはしない — findings への対応の追記で、方式・範囲・受け入れ条件を変えないため（計画変更記録 1）
- [implement] 台帳の残りの番号を open で書いた行は振り直す形にした（計画 4.4 の「open すべてを受け付ける」から変更・計画変更記録 2） — I197-F1 の守りを弱めないため。止める側に倒す細部の変更なので計画レビューはやり直さない
- [implement] G5 を静的な確認にした（計画変更記録 3） — スパイクで、glob で余分に拾っても塊の出力が変わらないことを確かめたため
- [implement] /simplify で採った整理: 台帳の目印は記録の一覧だけを `ledger_risk` に渡す（今回の記録にも台帳がある）・`is_rest` と振り直しの条件 `keep` に名前を付けた・拒否が読めないことは印のファイルで持つ（件数は常に数）・組み込みのレビューの起動を 1 つの if にまとめた・casefold の集合を 1 回だけ作る・テストの補助関数（記録の改名・最新の記録・`av`）
- [implement] /simplify で見送った指摘: 台帳の要素を名前つきにする（`_LEDGER_PY` 全体の書き換えになり範囲を超える）・目印を記録の RISK 行で持つ案（計画の A 案は台帳の目印で、rebase の後も前の記録の台帳で残る）・台帳の残りの open も同じ番号で受け付ける案（I197-F1 の穴が戻る）・実験役を別の作業ツリーで動かす案（計画 9 で flock を選んだ。作業ツリーの作成・片付けでコードが大きくなる）・gate-check の 1 行の別名を消す（呼ぶ側の差分を増やすだけ）・テストの補助関数を 3 本のテストで共有（今の慣習は各ファイルで定義）・範囲が空のときの入力の組み立てを省く・`MAX_ID` を Python で出す・`review_base` の理由を 2 か所で判定（どれも効果が小さい）
- [implement] retro で必ず確かめる 2 点を決めた（2026-10-27 のユーザーの確認への回答） — (1) `RISK=up` の付けすぎ（一度付くと戻らないので、誤って付くとそのイシューは毎回敵対的レビューになる）: このイシューの手動 No.1 と、次のアプリのイシュー（I196）の記録で付いた件数と理由を見る (2) 実験役の `flock` での直列化で、敵対的レビューの締め切り（`deadline`）による未検証が増えていないか: 次に敵対的レビューが走ったイシューの記録の「実行していない（締め切り）」の件数を見る。どちらも、困る結果が出たら目印を外す手段・締め切りの見直しを後続で直す
- [fix-loop] review-gate 1 周目の止める指摘 F2（範囲が空ならレビュー役を呼ばない判定が、変更の取り消し・削除の直しでも当たり、流れが進まない）を案 A で直した: 「起点の後に記録の場所の外が変わっていない」で決め、範囲が空でも外が変わったときは取り消しの差分を見せる — 既にある関数の再利用で範囲の判定に触れず、診断レビュー PASS（`docs/reviews/I202_fix_diagnosis_review_20261027_1624.md`）。止めない指摘 F1・F3〜F10 は直さない（台帳に残り retro が後続へ回す。I202 の決まりどおり）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
