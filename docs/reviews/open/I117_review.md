# I117 レビュー: auto_test テンプレートの実行コマンド例示を決定論ゲートセクションへ一本化

## 変更概要
- auto_test テンプレート冒頭の fenced ```bash 例示をインラインコード列挙＋誘導注記へ変更し、ゲート系コマンドの fenced 記載を「## 決定論ゲート（自動実走）」セクションに構造的に一本化。恒久テストスクリプト test_auto_test_template_lint.sh（TC-01〜07・decoy 反証込み）を新規作成。

## 変更点
- docs/tests/templates/auto_test_template.md: 冒頭 fenced ブロック（docker/npm 例）をインラインコード表記に変更＋誘導注記（HTML コメント・行頭 ``` なし）を追加。ゲートセクションコメントの allowlist 表記に `grep -L 文言 dir/*`（不在ファイル一覧）を追記し omission-lint の検知対象 `grep -[qL]` と一致させた（プランレビュー Warning 対応）
- scripts/claude/tests/test_auto_test_template_lint.sh: 新規（実行権限付与済み）。omission_lint() 複製ロジック＋TC-01〜07。合格=exit 0・実行不可=exit 2

## 影響範囲
- Backend/Frontend/DB/Config: Backend/Frontend/DB なし・Config は docs テンプレ1＋テストスクリプト1（新規）

## テスト結果
- 自動: 全 TC 合格・exit 0（TC-01〜07・2026-07-18 実走）。不合格経路も実証済み（複製パターンを故意に破壊したコピーで TC-07 NG・exit 1）
- 手動: 全 OK（No.1〜2 = Claude 実施・テンプレ実体確認、No.3 = Human 実施・注記文言の平易さ確認。2026-07-18・結論 OK）

## 計画との差分
- （実装後に記入）なし / あり（理由）

## ロールバック
- git revert のみ（DB・設定・サービス影響なし）
