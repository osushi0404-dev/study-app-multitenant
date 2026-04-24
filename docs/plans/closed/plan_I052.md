# 計画書: I052 — webpack proxy を設定してローカル Docker E2E テストを可能にする

## 基本情報
- **計画書ID**: plan_I052
- **関連イシュー**: #106
- **作成根拠資料**: I049 振り返り（予防処置 #2）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-24

---

## 1. 背景/目的

I049 で導入した Playwright E2E テストはローカル Docker 環境で実行できない。
原因: React アプリが `REACT_APP_API_BASE_URL || 'http://localhost:8000'` を API の絶対 URL として使用しており、
Playwright コンテナ内の Chromium からは `localhost:8000` に到達できない（`localhost` がコンテナ自身のループバックに解決されるため）。

CRA の `setupProxy.js`（webpack devServer proxy）を追加し、
React アプリが相対パス（`/api/...`、`/media/...`）でリクエストを発行できるようにする。
webpack dev server がサーバーサイドで `http://backend:8000` へプロキシするため、
どのコンテナ・環境からアクセスしても Docker ネットワーク経由でバックエンドに届く。

---

## 2. 受け入れ条件

- [ ] `docker compose --profile e2e run --rm e2e` でローカル Docker E2E テストが全件 pass する
- [ ] CI E2E テストが引き続き pass する
- [ ] React アプリからバックエンドへのリクエストが `/api/` 相対パス経由で動作する（`http://localhost:8000` への絶対 URL 依存を除去）

---

## 3. 影響範囲

- Backend: なし
- Frontend: `src/setupProxy.js`（新規）・`src/services/api.ts`・`src/utils/url.ts`
- DB: なし
- Config/Infra: `docker-compose.yml`（frontend/e2e 環境変数整理）・`.github/workflows/e2e.yml`（デッドコード削除）・`docs/runbooks/common-commands.md`

---

## 4. 調査結果

### 現状の問題
- `api.ts:12` — `baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'`
  → `REACT_APP_API_BASE_URL` 未設定時は絶対 URL `http://localhost:8000` を使用
  → Playwright コンテナ内の Chromium は `localhost:8000` に到達できない（ループバック）
- `api.ts:132` — `refreshAccessToken` でも同じ絶対 URL を直接構築
- `url.ts:26` — `getMediaUrl` でも同じパターン
- `QuizSession.tsx:420,427,561,568` — `${process.env.REACT_APP_API_BASE_URL}${imagePath}` を直接使用（フォールバックなし）

### デッドコードの発見
- `docker-compose.yml` frontend サービス: `REACT_APP_API_URL=http://localhost:8000/api`（コードは `REACT_APP_API_BASE_URL` を読むため未使用）
- `docker-compose.yml` e2e サービス: `API_URL=http://backend:8000`（Playwright テストで未使用）
- `.github/workflows/e2e.yml`: `API_URL: http://localhost:8000`（同上）

### 採用アプローチ
- CRA 標準の `src/setupProxy.js`（`http-proxy-middleware` は `react-scripts` に内包済み、追加インストール不要）
- Proxy 対象: `/api`（API リクエスト）と `/media`（画像ファイル）の 2 系統
- Proxy ターゲット: `BACKEND_URL` 環境変数（Node.js 実行時に読み込み）→ デフォルト `http://localhost:8000`
  - Docker 内: `BACKEND_URL=http://backend:8000`（docker-compose で設定）
  - Docker なしの直接 `npm start`: `BACKEND_URL` 未設定 → フォールバック `http://localhost:8000`

### `||` → `??` への変更理由
`process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'` は空文字 `''` が falsy のため、
`REACT_APP_API_BASE_URL=''` を設定しても `http://localhost:8000` にフォールバックしてしまう。
`??`（nullish coalescing）に変更すると `null`/`undefined` のみフォールバック対象となり、
`''` が正しく空文字として機能する。

### 環境別動作確認
| 環境 | `REACT_APP_API_BASE_URL` | proxy ターゲット | 動作 |
|------|--------------------------|-----------------|------|
| ローカル開発者ブラウザ | `''`（docker-compose） | `backend:8000` | ✅ |
| ローカル E2E（Docker） | `''`（docker-compose） | `backend:8000` | ✅（修正対象） |
| CI（GitHub Actions） | `''`（docker-compose） | `backend:8000` | ✅ |
| 本番（nginx + 静的配信） | `https://api.prod.com`（ビルド時注入） | proxy 不使用 | ✅（影響なし） |

---

## 5. 変更点一覧

| # | ファイル | 種別 | 内容 |
|---|---------|------|------|
| 1 | `frontend/src/setupProxy.js` | 新規 | `/api`・`/media` を `BACKEND_URL`（or `localhost:8000`）へプロキシ |
| 2 | `frontend/src/services/api.ts` | 修正 | `baseURL` と `refreshAccessToken` の `\|\|` を `??` に変更 |
| 3 | `frontend/src/utils/url.ts` | 修正 | `getMediaUrl` の `\|\|` を `??` に変更 |
| 4 | `docker-compose.yml` | 修正 | frontend: `REACT_APP_API_URL`削除・`REACT_APP_API_BASE_URL=''`・`BACKEND_URL=http://backend:8000` 追加; e2e: `API_URL` 削除 |
| 5 | `.github/workflows/e2e.yml` | 修正 | `API_URL: http://localhost:8000` 削除（デッドコード） |
| 6 | `docker-compose.yml` | 追加修正 | backend environment に `ALLOWED_HOSTS=localhost,127.0.0.1,backend` を追加（proxy `changeOrigin: true` が `Host: backend:8000` を設定するため） |
| 7 | `backend/core/settings.py` | 変更なし | `ALLOWED_HOSTS` default は `'localhost,127.0.0.1'` のまま。`backend` は Docker 専用ホスト名のため docker-compose.yml で管理 |
| 8 | `docs/runbooks/common-commands.md` | 修正 | ローカル E2E 実行手順に `RATELIMIT_ENABLE=false docker compose up -d backend` を追加（proxy 経由リクエストが frontend コンテナ IP に集約されるため rate limit が累積しやすい。CI は常に `RATELIMIT_ENABLE=false` を設定） |

---

## 6. 実装手順

### ステップ 1: `frontend/src/setupProxy.js` を新規作成

```javascript
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

  app.use(
    ['/api', '/media'],
    createProxyMiddleware({
      target: backendUrl,
      changeOrigin: true,
    })
  );
};
```

**方針**: CRA の自動検出ルールにより `src/setupProxy.js` は webpack dev server 起動時に自動でロードされる。
`changeOrigin: true` で Host ヘッダーをターゲットに合わせる（Django の ALLOWED_HOSTS チェックを通過させるため）。
`BACKEND_URL` は Node.js 実行時の環境変数（`REACT_APP_*` のようなビルド時バンドル対象ではない）。

### ステップ 2: `api.ts` の baseURL と refreshAccessToken を修正

```typescript
// 修正前
baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',

// 修正後
baseURL: process.env.REACT_APP_API_BASE_URL ?? '',
```

```typescript
// 修正前（refreshAccessToken 内）
`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'}/api/auth/token/refresh/`,

// 修正後
`${process.env.REACT_APP_API_BASE_URL ?? ''}/api/auth/token/refresh/`,
```

### ステップ 3: `url.ts` の getMediaUrl を修正

```typescript
// 修正前
const baseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// 修正後
const baseUrl = process.env.REACT_APP_API_BASE_URL ?? '';
```

### ステップ 4: `docker-compose.yml` を修正

frontend サービス:
```yaml
# 削除: - REACT_APP_API_URL=http://localhost:8000/api
# 追加:
- REACT_APP_API_BASE_URL=
- BACKEND_URL=http://backend:8000
```

e2e サービス:
```yaml
# 削除: - API_URL=http://backend:8000
# 維持: - BASE_URL=http://frontend:3000
```

### ステップ 5: `.github/workflows/e2e.yml` を修正

```yaml
# 削除:
# API_URL: http://localhost:8000
```

### ステップ 6: `docker-compose.yml` の backend environment に `ALLOWED_HOSTS` を追加

`changeOrigin: true` により proxy が `Host: backend:8000` を設定する。
`backend` は Docker 専用ホスト名であり、`settings.py` の一般デフォルト値には含めず、
Docker 環境固有の設定である `docker-compose.yml` で明示的に管理する。

```yaml
# backend サービスの environment に追加
- ALLOWED_HOSTS=localhost,127.0.0.1,backend
```

**方針**:
- `docker-compose.yml` の `environment` は `env_file`（`.env`）より優先されるため、
  ローカル `.env` の `ALLOWED_HOSTS` 設定に依存せず確実に動作する
- CI（`.env` なし）・ローカル（`.env` あり）どちらも同じ docker-compose.yml を使うため一貫して動作する
- `settings.py` の `ALLOWED_HOSTS` default は `'localhost,127.0.0.1'` のまま維持する
  （`backend` は Docker 専用なので一般デフォルトに含めない）

### ステップ 7: `common-commands.md` の E2E 手順を更新

proxy 導入により、E2E テストの全 API リクエストが frontend コンテナの IP から backend に届く（サーバーサイド proxy のため）。
これにより rate limit のカウントが累積しやすくなり、`誤ったパスワードでログインが拒否される` テストが失敗する。
CI は `RATELIMIT_ENABLE=false` を設定してこの問題を回避している。ローカルでも同様の設定を手順に追加する。

```markdown
## E2E テスト実行前の準備（Rate Limiting 無効化）

proxy 導入後はすべての E2E リクエストが frontend コンテナ IP からバックエンドに集約されるため、
rate limiting を無効にしてバックエンドを再起動してから E2E を実行する:

```bash
RATELIMIT_ENABLE=false docker compose up -d backend
```

その後、通常通り E2E を実行する:

```bash
docker compose rm -f e2e-init
docker compose --profile e2e run --rm e2e
```

---

## 7. テスト計画

| 種別 | 内容 |
|------|------|
| 自動テスト（E2E） | `docker compose --profile e2e run --rm e2e` でローカル全件 pass（再発防止テスト） |
| 自動テスト（Jest） | 既存 Frontend Jest テストが regression なし |
| 手動テスト | 開発者ブラウザでのログイン・API 疎通・画像表示確認 |

詳細は `docs/tests/open/I052_manual_test.md` および `docs/tests/open/I052_auto_test.md` を参照。

---

## 8. ロールバック

```bash
git revert <コミット SHA>
# または手動で以下を元に戻す:
# - frontend/src/setupProxy.js を削除
# - api.ts・url.ts の ?? を || に戻す
# - docker-compose.yml を元の状態に戻す
# - backend/core/settings.py の ALLOWED_HOSTS から 'backend' を削除
```

---

## 9. Risk & 回避策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| `changeOrigin: true` が `Host: backend:8000` を設定し、Django `ALLOWED_HOSTS` が拒否する | 高（fix-loop で顕在化） | `docker-compose.yml` backend environment に `ALLOWED_HOSTS=localhost,127.0.0.1,backend` を明示設定（ステップ 6）。`environment` が `env_file`（`.env`）を上書きするため `.env` の内容に依存しない |
| 本番ビルドで `REACT_APP_API_BASE_URL` が未設定のまま → 空文字でデプロイ | 高 | `??` 演算子により空文字が正しく通る。本番は `REACT_APP_API_BASE_URL=<prod URL>` を明示設定（既存運用） |
| 既存 Jest テストが proxy 設定で壊れる | 低 | `setupProxy.js` は webpack dev server 専用。Jest テストは Node.js で実行されるため無影響 |
| `BACKEND_URL` 未設定時にプロキシが `localhost:8000` に向く | 低 | Docker なし直接 `npm start` での既存動作と同一。意図通り |

セキュリティ:
- `setupProxy.js` は webpack dev server（開発/CI 環境）専用。本番の nginx には一切影響しない
- proxy ターゲット `BACKEND_URL` はユーザー入力でなく環境変数（サーバーサイド）のため SSRF リスクなし
- `backend` は Docker 内部ネットワーク専用ホスト名。`ALLOWED_HOSTS` への追加はセキュリティリスクなし

---

## 10. 承認ポイント

### 設計判断の明示

| 判断項目 | 根拠 |
|---------|------|
| proxy パスを `/api` と `/media` の 2 系統にする | コード調査で `api.ts`（`/api/*`）と `getMediaUrl`/`QuizSession.tsx`（`/media/*`）の 2 系統が存在することを確認 |
| `BACKEND_URL` 変数名を採用 | `REACT_APP_*` は CRA がクライアントバンドルに焼き込む。proxy ターゲットはサーバーサイドで使うため通常の env var を使用 |
| `||` → `??` への変更 | 空文字 `''` が falsy のため `||` では `REACT_APP_API_BASE_URL=''` が正しく機能しないことをコードから確認 |
| `REACT_APP_API_URL` の削除 | コード全文検索で `REACT_APP_API_URL` を読む箇所なし → デッドコードと判断 |
| `API_URL` を e2e・CI から削除 | E2E テストコード全文検索で `API_URL` を読む箇所なし → デッドコードと判断 |
| `setupProxy.js` に `http-proxy-middleware` を `require` で使用 | CRA の `react-scripts` に同梱済みのため新規インストール不要 |
| `docker-compose.yml` backend environment に `ALLOWED_HOSTS` を明示設定（fix-loop で追加） | `backend` は Docker 専用ホスト名のため `settings.py` 一般デフォルトには含めない。`docker-compose.yml` の `environment` が `env_file`（`.env`）より優先されるため、ローカルの `.env` 内容に依存せず確実に動作する |

すべて「コードから判断」であり、ユーザーの仮定に依存する判断はありません。

### チェックリスト
- [ ] proxy パス（`/api`、`/media`）の範囲は適切か
- [ ] `BACKEND_URL` の変数名は既存の命名規則と合致しているか
- [ ] `QuizSession.tsx` の直接 env var 参照（`${process.env.REACT_APP_API_BASE_URL}${imagePath}`）は空文字になることで正しく相対パスになるか確認したか

**セキュリティ影響**: webpack dev server 専用の proxy。本番環境・DB・認証への影響なし。

**P3/P5/P8 影響なし**（DB なし・外部 API なし・新規インフラなし）

**P6 影響なし**（UI 変更なし・フロントエンドの見た目変更なし）
