# コードレビュー: I052 — webpack proxy を設定してローカル Docker E2E テストを可能にする

## レビュー対象
- `frontend/src/setupProxy.js`（新規）
- `frontend/src/services/api.ts`（修正）
- `frontend/src/utils/url.ts`（修正）
- `docker-compose.yml`（修正）
- `.github/workflows/e2e.yml`（修正）

## チェックリスト

### setupProxy.js
- [ ] proxy パスが `/api` と `/media` の 2 系統に限定されている（全リクエストを proxy していない）
- [ ] `changeOrigin: true` が設定されている
- [ ] `BACKEND_URL` のフォールバックが `http://localhost:8000` になっている
- [ ] `http-proxy-middleware` の `require` が正しい（CRA 同梱版）

### api.ts / url.ts
- [ ] `??` 演算子（nullish coalescing）を使用している（`||` でない）
- [ ] `baseURL`・`refreshAccessToken`・`getMediaUrl` の 3 箇所すべて修正済み

### docker-compose.yml
- [ ] frontend サービスに `REACT_APP_API_BASE_URL=`（空文字）が設定されている
- [ ] frontend サービスに `BACKEND_URL=http://backend:8000` が設定されている
- [ ] `REACT_APP_API_URL=http://localhost:8000/api` が削除されている（デッドコード）
- [ ] e2e サービスから `API_URL=http://backend:8000` が削除されている（デッドコード）

### e2e.yml
- [ ] `API_URL: http://localhost:8000` が削除されている（デッドコード）

### セキュリティ
- [ ] setupProxy.js は `src/` 配置であり webpack dev server 専用（本番ビルドに含まれない）
- [ ] proxy ターゲットがユーザー入力でなく環境変数（SSRF リスクなし）

## 備考
- セキュリティ影響なし（dev server proxy のみ）
- 本番 nginx プロキシ設定への変更なし

## テスト実行結果（/test）

| テスト種別 | 結果 | 備考 |
|-----------|------|------|
| Backend (pytest) | ✅ 25 passed | |
| Frontend (Jest) | ✅ 7 passed | |
| E2E (Playwright) ローカル | ✅ 8 passed | `RATELIMIT_ENABLE=false` で実行 |
| E2E (Playwright) CI | ✅ pass (3m25s) | GitHub Actions |
