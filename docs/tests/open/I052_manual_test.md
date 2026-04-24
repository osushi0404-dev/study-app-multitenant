# 手動テスト: I052 — webpack proxy を設定してローカル Docker E2E テストを可能にする

## テスト目的
webpack proxy 導入後に、開発者ブラウザからのアプリ操作が正常に動作することを確認する。

## 前提条件
- 実装完了後（`RATELIMIT_ENABLE=false docker compose up -d backend` でバックエンドを rate limiting 無効で起動済み）
- ブラウザで `http://localhost:3000` にアクセス可能

## テストケース

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `frontend/src/setupProxy.js` が存在することを確認 | ファイルが存在する | Claude | | |
| 2 | `docker-compose.yml` の frontend サービスに `REACT_APP_API_BASE_URL=` が含まれることを確認 | 空文字設定が存在する | Claude | | |
| 3 | `docker-compose.yml` の frontend サービスに `BACKEND_URL=http://backend:8000` が含まれることを確認 | 設定が存在する | Claude | | |
| 4 | `docker-compose.yml` に `REACT_APP_API_URL=` が残っていないことを確認（デッドコード削除） | 該当行が存在しない | Claude | | |
| 5 | `api.ts` の baseURL が `??` 演算子を使用していることを確認 | `process.env.REACT_APP_API_BASE_URL \?\? ''` の形式 | Claude | | |
| 6 | `docker-compose.yml` の backend サービス environment に `ALLOWED_HOSTS=localhost,127.0.0.1,backend` が含まれることを確認 | 該当行が存在する | Claude | | |
| 7 | ブラウザで `http://localhost:3000` を開き、ログイン画面が表示される | ログイン画面が表示される | Human | | |
| 8 | ログイン（E2E テストユーザー or 自分のアカウント）してダッシュボードが表示される | ダッシュボードが表示され、API エラーが出ない | Human | | |
| 9 | ブラウザの DevTools Network タブで API リクエストの送信先を確認 | リクエスト Host が `localhost:3000`（`http://localhost:3000/api/...`）になっており、以前の `localhost:8000` への直接通信が消えている | Human | | |
