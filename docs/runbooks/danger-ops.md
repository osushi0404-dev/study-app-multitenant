# 危険操作（Danger Ops）ルール

以下は原則「計画書に明記」＋「ユーザー明示承認」＋「PRに danger-approved」＋「実行時 DANGER_OK=1」でのみ実行する。

## 例
- DB: DROP / TRUNCATE / WHEREなし UPDATE・DELETE / 大量更新・削除 / 破壊的マイグレーション
- Git: force push / reset --hard / 大規模rebase
- Docker: down -v / --volumes（データ消失）
- Files: rm -rf / secrets 操作

## 実行テンプレ
- 影響範囲:
- 代替案:
- ロールバック:
- 実行コマンド（DANGER_OK=1 付き）:
