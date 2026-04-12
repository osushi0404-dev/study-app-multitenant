# I041 自動テスト

## テスト対象
- `docs/runbooks/plan-writing-rules.md`（追記）

## 自動テスト方針

ドキュメントのみの変更のため pytest / Jest による自動テスト対象外。
手動テストのみで検証する（`I041_manual_test.md` 参照）。

## 静的チェック

| No | チェック内容 | 手順 | 期待結果 | 実施者 | 実結果 |
|---:|------------|------|----------|--------|--------|
| 1 | 3原則の追記確認 | `grep -n "垂直スライス\|未知リスク\|依存関係" docs/runbooks/plan-writing-rules.md` | 3行がヒットする | Claude | OK（10・13・16行目） |
| 2 | 具体例の記載確認 | `grep -n "例:" docs/runbooks/plan-writing-rules.md` | 実装手順セクション内に3件の「例:」がある | Claude | OK（12・15・17行目に3件） |
| 3 | Backend テスト | `docker compose exec backend python -m pytest --tb=short -q` | 全テスト pass | Claude | OK（25 passed） |
| 4 | Frontend テスト | `docker compose exec frontend npm test -- --watchAll=false` | 全テスト pass | Claude | OK（7 passed） |
