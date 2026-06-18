# I067 レビュー記録

- **関連計画書**: docs/plans/open/plan_I067.md
- **関連イシュー**: #135

## レビュー対象
スキル指示文 4 ファイルへの分岐明文化:
- `.claude/skills/plan-issue/SKILL.md` — invariant＋既コミット時分岐
- `.claude/skills/test/SKILL.md` — 計画駆動の自動テスト選択＋description 更新
- `.claude/skills/retro/SKILL.md` — バックログ issue 未コミット invariant
- `.claude/skills/close/SKILL.md` — scoped staging（`git add -u`／broad add 禁止）

## レビュー観点
- 受け入れ条件（AC 4 項目＋完走シナリオ）を満たしているか
- 追記文言が既存節構造を壊さず、frontmatter が妥当か（TC-07）
- 既コミット分岐・計画駆動 test・close 巻き込み防止が論理的に破綻しないか（手動 No.1〜3）
- 命名規約 runbook・I066 担当のスクリプト/close ロジックに踏み込んでいないか（スコープ逸脱なし）
- セキュリティ影響なし（コード・依存関係・認可に変更なし）の妥当性

## plan-issue-review 記録
（`/plan-issue-review I067` 実行時に追記）

## code-review 記録
（`/code-review` 実行時に追記）
