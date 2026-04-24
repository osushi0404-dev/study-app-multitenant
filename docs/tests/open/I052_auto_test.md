# 自動テスト: I052 — webpack proxy を設定してローカル Docker E2E テストを可能にする

## テスト方針

| テストレベル | 内容 | 理由 |
|------------|------|------|
| E2E（Playwright） | ローカル Docker での全件 pass | 本イシューの再発防止テスト。「ローカルで E2E が動かない」問題の直接的な検証 |
| Jest（Frontend） | 既存テスト regression なし | `api.ts`・`url.ts` の `||` → `??` 変更が既存動作を壊さないことを確認 |

## 自動テストケース

### E2E（再発防止）

| No | コマンド | 期待結果 | 実施者 |
|---:|---------|---------|--------|
| 1 | `docker compose rm -f e2e-init && docker compose --profile e2e run --rm e2e` | 全テストケース pass（exit 0） | Claude |

### Frontend Jest（regression）

| No | コマンド | 期待結果 | 実施者 |
|---:|---------|---------|--------|
| 2 | `docker compose exec frontend npm test -- --watchAll=false` | 既存 7 件 pass、新規失敗なし | Claude |

## 新規自動テストの追加

なし。受け入れ条件（ローカル E2E 全件 pass）は既存 E2E テストスイートで直接検証できる。
