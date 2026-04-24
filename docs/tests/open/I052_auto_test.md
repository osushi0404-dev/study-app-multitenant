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

---

## 再発防止記録（fix-loop）

### 失敗内容
CI E2E: `DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'` → ログイン API が 400 で拒否 → `waitForURL('**/dashboard')` タイムアウト

### 根本原因
`setupProxy.js` の `changeOrigin: true` が `Host` ヘッダーを proxy ターゲット名 `backend:8000` に書き換える。Django の `ALLOWED_HOSTS` デフォルト値に `backend` が含まれていなかった。

### 修正内容
`backend/core/settings.py:22` — default 値に `backend` を追加:
```python
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,backend').split(',')
```

### セキュリティ考慮点
- `backend` は Docker 内部ネットワーク専用ホスト名。外部インターネットから到達不能。
- 本番環境では `ALLOWED_HOSTS` を env var で設定するため、このデフォルト値は使われない。

### 次回の防止策
webpack proxy + Django の構成を計画書に含める際は「proxy target のホスト名が Django の `ALLOWED_HOSTS` に含まれているか」を必ずチェックする（plan-issue-review の P1 チェック項目として追加を検討）。
