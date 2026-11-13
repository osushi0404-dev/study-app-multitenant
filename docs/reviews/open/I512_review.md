# I512 レビュー: 計画で受け入れた残余リスクを、後続イシュー・最優先から外して一覧へ回す

## 変更概要
- 計画書の「## 8. Risk & 回避策」の表に「処遇」の列を足し、`受け入れ` の R 番号を code-reviewer が FINDING 行の目印 `ACCEPTED=R<番号>` で示す。retro の振り分け（`code-review.sh --route`）が計画書と照合し、Medium 以下・再現なし・アプリ本体でない行を一覧へ回す。止める判定は変えない
- I430 の F1〜F3 を受け入れのまま `docs/reviews/backlog/I430.md` へ

## 変更点
- （implement で記入）

## 影響範囲
- Backend/Frontend/DB/Config: ハーネスだけ（`scripts/claude/code-review.sh`・`.claude/agents/code-reviewer.md`・`docs/plans/templates/plan_template.md`・`.claude/skills/retro/SKILL.md`・`docs/runbooks/review-rules.md`・テスト・一覧）

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし

## ロールバック
- PR を revert する（plan §7。目印のある記録が develop にあれば先に目印を消す）

## 自律判断の記録
- [plan] grill-me の 4 問はユーザーの委任（「ベストなやり方で」）を受けてすべて推奨案で確定 — 取り消しやすく手間が増えず安全側に倒れる案
- [plan] アプリ本体の行には目印を効かせない — アプリ本体の Medium・SECURITY=yes が最優先から外れるのを防ぐ（効く範囲を狭める安全側）
- [plan-review] Warning 2 件は計画書・manual_test を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
