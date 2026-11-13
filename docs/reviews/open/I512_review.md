# I512 レビュー: 計画で受け入れた残余リスクを、後続イシュー・最優先から外して一覧へ回す

## 変更概要
- 計画書の「## 8. Risk & 回避策」の表に「処遇」の列を足し、`受け入れ` の R 番号を code-reviewer が FINDING 行の目印 `ACCEPTED=R<番号>` で示す。retro の振り分け（`code-review.sh --route`）が計画書と照合し、Medium 以下・再現なし・アプリ本体でない行を一覧へ回す。止める判定は変えない
- I430 の F1〜F3 を受け入れのまま `docs/reviews/backlog/I430.md` へ

## 変更点
- `scripts/claude/code-review.sh`: FINDING・LEDGER 行の任意の目印 `ACCEPTED=R<番号>`（無い行は前と 1 文字も変えない）・`accepted_risks()`（計画書の 8 の表を読む）・`accepted_why_not()`・`route` モードで目印が効く行だけ `SECURITY=yes`・`guard の Medium 以上` の理由を外す・一覧の行に `SECURITY=` と「計画で受け入れ（R<番号>）」・`--route` の入口で種類と番号の形を先に確かめ、`find_plan_file()` で計画書を選ぶ
- `.claude/agents/code-reviewer.md`: 目印を付ける決まりと FINDING 行の欄
- `docs/plans/templates/plan_template.md`: 8 の表に「処遇」の列
- `.claude/skills/retro/SKILL.md` 4-0・`docs/runbooks/review-rules.md`: 目印の扱い・一覧の行の形
- `scripts/claude/tests/test_i512_accepted_risk.sh`（新規・34 項目）・`test_i202_ledger_cleanup.sh`（一覧の行の形と FG の元の文字列の追従）
- 一覧: `I430.md` に F1〜F3 を足した・同梱して直した `I480.md` F1・`I208.md` F3 を消した

## 影響範囲
- Backend/Frontend/DB/Config: ハーネスだけ（`scripts/claude/code-review.sh`・`.claude/agents/code-reviewer.md`・`docs/plans/templates/plan_template.md`・`.claude/skills/retro/SKILL.md`・`docs/runbooks/review-rules.md`・テスト・一覧）

## テスト結果
- 自動:
- 手動:

## 計画との差分
- あり（計画変更記録の 2026-11-14 implement の行）: /simplify の結果で関数の形と計画書の探し方を変えた・I208 F3 の後半も直した・FG の元の文字列の追従。方式・範囲・受け入れ条件は変えない

## ロールバック
- PR を revert する（plan §7。目印のある記録が develop にあれば先に目印を消す）

## 自律判断の記録
- [plan] grill-me の 4 問はユーザーの委任（「ベストなやり方で」）を受けてすべて推奨案で確定 — 取り消しやすく手間が増えず安全側に倒れる案
- [plan] アプリ本体の行には目印を効かせない — アプリ本体の Medium・SECURITY=yes が最優先から外れるのを防ぐ（効く範囲を狭める安全側）
- [plan-review] Warning 2 件は計画書・manual_test を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない
- [implement] /simplify の 4 体の指摘のうち、計画書の探し方（find_plan_file）・判定の入口の一本化・route_reasons() に旗を足さない形・テストの起動回数の削減を採用。台帳の行を名前で引く形（namedtuple）・BL_FORM の重複・入口と Python の種類の確かめの重複は見送り — 範囲の外か、既存の書き方の慣例
- [implement] 関係するテストだけを 1 本ずつ流し、全体は CI に任せた — run-all.sh はサンドボックスで uv の一時ファイルを書けない
- [review-gate] 1 回目は CI_WAIT: FAIL（Harness Tests の test_pipefail_negated_grep.sh G1: test_i512_accepted_risk.sh:171 の `! grep … | grep -qvE` が pipefail の下の否定とパイプの形）で fix-loop へ — コードレビューは CI が通ってから
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
