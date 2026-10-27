# I208 レビュー: 台帳の残りの振り分けと一覧の行をスクリプトが出すようにし、テストを実物の一覧に依存させない

- 計画書: docs/plans/open/plan_I208.md
- イシュー: docs/issues/open/I208.md（#348）
- Draft PR: #350

## 変更概要
台帳の残りの振り分け（後続イシュー／軽い指摘の一覧）を、retro の手順書の正規表現から `code-review.sh` のスクリプトに移した。判定は台帳の欄の値だけで行い、要約の文字では変わらない。guard の Medium 以上は再現を問わず後続イシューにする。台帳の行に `FILE=` の欄を持たせ、一覧の行のファイルを台帳から出す。テストは実物の記録・一覧の行数に依存しない形にした。

## 変更点
- `scripts/claude/code-review.sh`: 台帳の行の `FILE=`（`LEDG`・`read_ledger`・`ledger_line`・`update`・`merged`）・`route_reasons()` と `route` モード・`ledger_route`・入口 `--route <issue|backlog> <I###>`・`latest_ledger_record()`
- `.claude/skills/retro/SKILL.md` 4-0: `bash scripts/claude/code-review.sh --route issue|backlog $ARGUMENTS` の出力を使う（正規表現・FINDING 行をたどる手作業を消した）
- `.claude/skills/plan-issue/SKILL.md`: 一覧の grep を `FILE=<パス> |`（前方一致をやめる）と `FILE=- |` に
- `docs/runbooks/review-rules.md`: 振り分けはスクリプト・guard の Medium 以上・止める指摘
- `scripts/claude/tests/test_i202_ledger_cleanup.sh`: I207 の D1〜D3 を書き換え（実物は形だけ）・I208 の節 Q1〜Q9 と失敗注入。`test_i205_stop_criteria.sh` の D4
- `docs/reviews/backlog/I207.md`: 同梱して直した F1・F3・F4・F5・F8 の行を消した

## 影響範囲
- ハーネスだけ（`scripts/claude/code-review.sh`・テスト 2 本・retro・plan-issue・review-rules・`docs/reviews/backlog/I207.md`）。アプリ本体・DB・設定の変更なし

## テスト結果
- 自動: TC-01 `test_i202_ledger_cleanup.sh` pass=148 fail=0（実装前 fail=25）・TC-02 関係する 5 本すべて合格・TC-03 CI 全緑（Harness Tests を含む）
- gate-check: GATE_CHECK OK（2026-10-27）
- 手動: No.1〜3 すべて OK（Claude 実施・Human の項目なし）。実物の I207 の記録で F2 が欄どおり一覧側に出ること、retro のコマンドが承認なしで通ること、計画で一覧を見る新しいコマンドが前方一致せずに当たることを確かめた

## 計画との差分
- 計画変更記録 2（`f2_same` に FILE の値を渡す）・3（`/simplify` の整理: `latest_ledger_record()`・理由の無い一覧の行で exit 2）。どちらも方式・範囲・受け入れ条件は変えない

## ロールバック
- PR を revert する（計画書 7。周の途中のイシューが無いときに行う）

## 自律判断の記録
- [plan-review] 計画レビューの Warning 2 件を直し、再レビューはしない — 引数不足の終了コードと revert 前の確認の追記だけで、方式・範囲・受け入れ条件は変えない（計画変更記録 1）
- [implement] `f2_same` に FILE の値を引数で渡す — P6 では止めない中身の書き直しが前の形の `-` を埋める（計画 4.1 の規則どおり）ので `-` 固定では合わない（計画変更記録 2）
- [implement] /simplify の指摘のうち 4 件を採用（使わない欄を展開しない・一覧と後続イシューの行の共通部分を 1 回だけ作る・理由の無い一覧の行で exit 2・`latest_ledger_record()` にまとめる）— 出力・判定は同じで、止める側に倒す守りが増える（計画変更記録 3）
- [implement] /simplify の指摘のうち見送り: 台帳の項目を namedtuple にする（既存の作りへの上乗せで範囲外）・テストの route の二重起動（数秒の差）・一覧のフォルダの写しを作る小関数（D3 だけで使う）・「止める指摘」の理由の重なり（止める指摘を必ず後続イシューに回す安全側の重ね書き）— 範囲外か、効果が小さい
- [review-gate] 基本レビュー（`docs/reviews/I208_code_review_20261027_2304.md`・全体の 1 周目）は CI 全緑・FINAL_VERDICT OK・敵対的レビュー不要（高リスク NO）。台帳の Low 6 件（F1〜F6）は直さず retro に回す — 止める指摘ではなく、レビュー後に差分を足さない

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
