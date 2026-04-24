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

### 失敗内容（1回目: CI E2E fix-loop）
CI E2E: `DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'` → ログイン API が 400 で拒否 → タイムアウト

**根本原因**: `setupProxy.js` の `changeOrigin: true` が `Host: backend:8000` を設定するが、Django の `ALLOWED_HOSTS` に `backend` が含まれていなかった。

**修正内容（revert 済み）**: ~~`settings.py` デフォルト値に `backend` を追加~~ → 責務分離の観点から不適切として revert。

---

### 失敗内容（2回目: ローカル E2E fix-loop）
ローカル E2E: 同じ `DisallowedHost` エラー

**根本原因**: `backend/.env` が `ALLOWED_HOSTS=localhost,127.0.0.1` を env var で設定しており、`settings.py` の default（`backend` 含む想定）を上書きしていた。Docker Compose の優先順位: `environment` > `env_file`（`.env`）> `settings.py` default。CI には `.env` がないため CI のみ pass という環境依存の差異が発生。

**修正内容**: `docker-compose.yml` backend environment に `ALLOWED_HOSTS=localhost,127.0.0.1,backend` を明示設定。`environment` が `env_file` を上書きするため `.env` の内容に依存しない。

### セキュリティ考慮点
- `backend` は Docker 内部ネットワーク専用ホスト名。外部インターネットから到達不能。
- `settings.py` のデフォルト値は変更しない（`backend` は Docker 専用設定のため一般デフォルトに含めない）。

### 次回の防止策
- webpack proxy + Django の構成では「proxy target のホスト名が Django の `ALLOWED_HOSTS` に含まれているか」をチェックする
- `.env` ファイルが存在するローカル環境と CI の環境差異を考慮し、Docker 固有の設定は `docker-compose.yml` environment（`env_file` より優先）に集約する
