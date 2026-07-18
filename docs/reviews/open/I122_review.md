# I122 レビュー: 決定論テストの合否判定インターフェース統一（合格=exit 0）

## 変更概要
- （実装後に記入）plan-writing-rules への合否判定インターフェース統一規定の追記・plan-reviewer への P4 観点＋差し戻しファースト表行の追記・plan-issue SKILL セルフチェック項目の追記・fix-test-reviewer 観点3への exit code 向き確認の追記

## 変更点
- docs/runbooks/plan-writing-rules.md: （実装後に記入）
- .claude/review-agents/plan-reviewer.md: （実装後に記入）
- .claude/skills/plan-issue/SKILL.md: （実装後に記入）
- .claude/review-agents/fix-test-reviewer.md: （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし・Config はハーネス文書 4 ファイルの行追記のみ

## テスト結果
- 自動: （実装後に記入。決定論ゲート TC-01〜05 合格=exit 0・TC-06 失敗注入）
- 手動: （実施後に記入。No.1〜3 = Claude・No.4 = Human）

## 計画との差分
- （実装後に記入）

## ロールバック
- git revert のみ（DB・設定・サービス影響なし）
