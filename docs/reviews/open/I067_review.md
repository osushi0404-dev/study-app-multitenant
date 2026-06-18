# I067 レビュー記録

- **関連計画書**: docs/plans/open/plan_I067.md
- **関連イシュー**: #135

## レビュー対象
スキル指示文 4 ファイルへの分岐明文化（手続き→決定論的判定/ゲートへの格上げを含む）:
- `.claude/skills/plan-issue/SKILL.md` — invariant＋**既コミット自動判定分岐**（`git log` で `ISSUE_ALREADY_ON_BASE` 判定→経路決定）
- `.claude/skills/test/SKILL.md` — 計画駆動の自動テスト選択＋description 更新
- `.claude/skills/retro/SKILL.md` — バックログ issue 未コミット invariant
- `.claude/skills/close/SKILL.md` — `git add -u`＋**決定論ゲート**（I### スコープ外 staged の検出・中断／broad add 禁止）

## レビュー観点
- 受け入れ条件（AC 4 項目＋完走シナリオ）を満たしているか
- 追記文言が既存節構造を壊さず、frontmatter が妥当か（TC-07）
- 既コミット自動判定・計画駆動 test・close ゲートが論理的に破綻しないか（手動 No.1〜3）
- 決定論ゲートの許可条件（`I${ISSUE_NUM}` 含有）が close の正当ファイルを誤検知せず、番号アンカーで `I0670` 等の誤マッチも無いか
- 命名規約 runbook・I066 担当のスクリプト/close ロジックに踏み込んでいないか（スコープ逸脱なし）
- セキュリティ影響なし（コード・依存関係・認可に変更なし）の妥当性

## plan-issue-review 記録
（`/plan-issue-review I067` 実行時に追記）

## code-review 記録
（`/code-review` 実行時に追記）
