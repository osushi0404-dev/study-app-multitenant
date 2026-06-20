# レビュー: I071 レビュー観点に P9（プライバシー・コンプライアンス）を追加

- **関連イシュー**: #145
- **計画書**: docs/plans/open/plan_I071.md
- **Draft PR**: #147

## レビュー対象
ドキュメント・指示ファイルの追加/変更のみ（コード変更なし）:
- `docs/proposals/review_perspective_framework.md`（§2 表・§3 P9 詳細・§4 含めないもの・§5 マッピング・§8 対応表＋プレースホルダ確定・8観点→9観点）
- `docs/proposals/learning_app_quality_criteria.md`（§6 C2↔P9 確定・C1 注記・P1〜P8→P1〜P9）
- `.claude/review-agents/plan-reviewer.md`（P9 観点・高リスク判定接続）
- `.claude/review-agents/code-reviewer.md`（P9 観点）
- `.claude/skills/plan-issue/SKILL.md`（P9 影響なし運用）
- `.claude/skills/implement/SKILL.md`（条件付き確認 P9）
- `docs/runbooks/review-rules.md`（P1〜P8→P1〜P9）

## レビュー観点（本イシュー固有）
- [ ] P9 が宣言（framework）だけでなく消費箇所（review-agents・plan-issue/implement・ライブ相互参照）に**全件**反映されているか
- [ ] P9 と P2 の境界が誤解なく書き分けられているか（二重チェック・抜けを誘発しない）
- [ ] C1 を観点化しない判断が framework / criteria で一貫し、矛盾がないか
- [ ] 未成年データ・個人情報越境が高リスク判定（I043）に接続され `/security-review` 対象になっているか
- [ ] 既存 P1〜P8 の記述・運用（停止条件・重大度区分・高リスク判定・VERDICT 行）が無改変か（回帰）
- [ ] 概念変更（8観点→9観点 / P1〜P8→P1〜P9）の取りこぼしがないか（歴史的記述の誤改変もないか）

## Claude Code ベストプラクティス準拠チェック（指示ファイル変更を含むため必須）
- [ ] `plan-reviewer.md`・`code-reviewer.md`・`plan-issue/SKILL.md`・`implement/SKILL.md` の変更が `review-rules.md` の「Claude Code ベストプラクティス準拠チェックリスト」を満たすか
- [ ] SKILL.md の追記後も 500 行以内か
- [ ] 指示ファイルの分岐パリティ（P9 ブロックが対の既存ブロックと同粒度）が保たれているか

## 指摘記録欄
（plan-issue-review / code-review 実行時に記入）

| 重大度 | 観点 | 指摘内容 | 該当箇所 | 対応 |
|--------|------|---------|---------|------|
| | | | | |
