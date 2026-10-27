# I202 レビュー: I197・I205 の台帳に残った指摘と、見送った共通化を片付ける

- 計画書: docs/plans/open/plan_I202.md
- イシュー: docs/issues/open/I202.md（#338）
- Draft PR: #343

## 変更概要
（実装後に記入）

## 変更点
（実装後に記入）

## 影響範囲
ハーネスだけ（`scripts/claude/code-review.sh`・`scripts/claude/adversarial-review.sh`・`scripts/claude/gate-check.sh`〔関数の置き場所だけ〕・`.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`・`scripts/claude/tests/`）。アプリ本体・DB・GitHub の設定は変えない。

## テスト結果
（test-gate で記入）

## 計画との差分
（実装後に記入）

## ロールバック
計画書 §7 のとおり（PR の revert。レビューの途中のイシューがあれば、新しい形の記録を退避して全体のレビューからやり直す）。

## 自律判断の記録
- [plan-review] 計画レビューの Warning 3 件（V3 の文言・F14 の条件・F6 の締め切りと F8 の語彙）を計画書・auto_test に反映し、再レビューはしない — findings への対応の追記で、方式・範囲・受け入れ条件を変えないため（計画変更記録 1）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
