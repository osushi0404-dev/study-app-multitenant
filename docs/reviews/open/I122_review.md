# I122 レビュー: 決定論テストの合否判定インターフェース統一（合格=exit 0）

## 変更概要
- 決定論 TC の合否判定インターフェースを「合格=exit 0」に統一するルールを do（作成時）＋gate（レビュー時）の 2 層で導入。4 ファイルへの行追記のみ・既存文言の変更なし（計画書 4 章の固定文言どおり）。

## 変更点
- docs/runbooks/plan-writing-rules.md: false-green 節に「合否判定インターフェースの統一（合格=exit 0）」bullet を追加（出力値の目視比較禁止・`! grep -q` 形・exit code への畳み込み）
- .claude/review-agents/plan-reviewer.md: P4 観点に exit code 向き一致チェックを追加＋差し戻しファースト「自動テストケース」表に Blocker パターン行を追加
- .claude/skills/plan-issue/SKILL.md: 文書品質ゲートに合否判定インターフェース統一のセルフチェック項目を追加
- .claude/review-agents/fix-test-reviewer.md: 観点3（false-green）に決定論 TC の exit code 向き確認を継続行として追加（観点4・5 の番号不変更）

## 影響範囲
- Backend/Frontend/DB: なし・Config はハーネス文書 4 ファイルの行追記のみ

## テスト結果
- 自動: 全 TC 合格（2026-07-18 実装時実走。TC-01〜05・TC-07 = exit 0、TC-06 = 注入 6 件全て exit 1 で NG 化を確認＝false-green でない）
- 手動: （実施後に記入。No.1〜4 = Claude・No.5 = Human）

## 計画との差分
- なし（計画書 4 章の固定文言どおりの行追記のみ・計画外ファイルの変更なし）

## ロールバック
- git revert のみ（DB・設定・サービス影響なし）
