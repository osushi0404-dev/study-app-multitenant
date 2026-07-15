# I109 レビュー: 依存脆弱性ドリフトの定期検知（scheduled 監査＋自動起票）

## 基本情報
- **対象計画書**: docs/plans/open/plan_I109.md
- **関連イシュー**: #205（docs/issues/open/I109.md）
- **Draft PR**: #211

## レビュー目的
- scheduled 監査が PR ゲート（ci.yml）と判定一貫（同一ツール・同一条件）であること
- 検知 → 自動起票 → 重複防止 → 運用導線（runbook）が自己完結で機能すること
- default branch 切替（前提ゲート）と Phase B（マージ後 live 検証）の順序特例が記録どおり実施されること

## 期待する成果
- 依存の新規 CVE を最大 24 時間で検知し、PR 契機の一斉 CI ブロック（I108 型）を予防する仕組みが稼働する
- 検知時の対応がイシュー起票（GitHub のみ）→ /issue-bootstrap の 2 段階運用として runbook 化される

## 変更概要
- （実装後に記入）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.github/workflows/dependency-audit.yml`・`scripts/claude/dependency-audit-issue.sh`・`scripts/claude/tests/test_i109_dependency_audit.sh`・`docs/runbooks/dependency-audit.md`・`CLAUDE.md`（1 行）・リポジトリ設定（default branch / ラベル）

## 実装結果評価
- （実装後に記入）

## テスト結果
- 自動: （実装後に記入: test_i109_dependency_audit.sh の exit code・false-green 注入検証の記録）
- 手動: （Phase A / Phase B の結果を記入）

## 計画との差分
- （実装後に記入: なし / あり（理由））

## ロールバック
- 追加ファイル群の削除（revert 1 コミット）＋ラベル削除（任意）＋ default branch 復帰（オーナー操作・任意）
