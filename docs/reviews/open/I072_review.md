# レビュー: I072 否定・回帰系の決定論テストの false-green 検出ゲート追加

- **関連イシュー**: #148
- **計画書**: docs/plans/open/plan_I072.md
- **Draft PR**: #149

## レビュー対象
ドキュメント・指示ファイルの追加/変更のみ（コード変更なし）:
- `docs/runbooks/plan-writing-rules.md`（do層・正本: false-green 禁止の一般原則を新規追加）
- `.claude/skills/plan-issue/SKILL.md`（do層・強制チェック: L169 lint 異常系項目を一般形へ更新）
- `.claude/review-agents/plan-reviewer.md`（gate層: P4 に false-green 検出 bullet）
- `.claude/review-agents/code-reviewer.md`（gate層: P4 に false-green 検出 bullet）

## レビュー観点（本イシュー固有）
- [ ] do層（runbook 原則＋SKILL 強制チェック）と gate層（review P4）の2層が揃い、文言が同一概念・粒度パリティで整合しているか
- [ ] L169 一般化で lint 異常系の「非ゼロ終了」要件が後退していないか（特例包含が保たれているか）
- [ ] 追加文言が I071 固有トークン（P9/VERDICT/HIGHRISK）に依存しない一般形か
- [ ] 既存の文書品質ゲート他項目・P1〜P9 観点が無改変か（回帰）
- [ ] 本イシュー自身の否定・回帰系 TC（TC-05/TC-06）が失敗注入で NG を返すことが確認・記録されているか（ドッグフーディング）

## Claude Code ベストプラクティス準拠チェック（指示ファイル変更を含むため必須）
- [ ] `plan-issue/SKILL.md`・`plan-reviewer.md`・`code-reviewer.md` の変更が `review-rules.md` の準拠チェックリストを満たすか
- [ ] SKILL.md / review-agent の追記後も妥当な行数か
- [ ] 指示ファイルの分岐パリティ（do層と gate層の文言が同粒度）が保たれているか

## 指摘記録欄
（plan-issue-review / code-review 実行時に記入）

| 重大度 | 観点 | 指摘内容 | 該当箇所 | 対応 |
|--------|------|---------|---------|------|
| | | | | |
