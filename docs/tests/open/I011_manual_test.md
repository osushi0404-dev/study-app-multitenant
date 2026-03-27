# 手動テスト: I011 dev 環境で Service Worker を無効化

## 前提条件

- Docker コンテナが起動済み（`docker compose up`）
- ブラウザは Chrome（DevTools の Service Workers パネルを使用）

---

## MT-01: dev 環境で SW が登録されないことを確認

1. `npm start`（または Docker dev 環境）でフロントエンドを起動
2. ブラウザで `http://localhost:3000` を開く
3. DevTools > Application > Service Workers を開く
4. **期待値**: 「No service workers detected.」または登録済み SW が表示されない

---

## MT-02: コンソールに skip メッセージが出力される

1. DevTools > Console を開く
2. ページをリロード
3. **期待値**: `Service Worker registration skipped in development mode` が出力される

---

## MT-03: ソース変更が即時反映される

1. `frontend/src/pages/` 配下のいずれかのファイルに軽微な変更を加える（例: テキスト修正）
2. コンテナ再起動（`docker compose restart frontend`）
3. ブラウザをリロード
4. **期待値**: 変更が反映される（古いキャッシュが返らない）

---

## MT-04: 本番ビルドで SW が登録されることを確認（任意）

1. `npm run build` を実行
2. ビルド成功を確認
3. **期待値**: エラーなくビルドが完了する
4. （本番 SW 動作確認は本番デプロイ時に行う）

---

## MT-05: 既存ページの動作に影響がないことを確認

1. ログイン後、各メインページ（ダッシュボード・問題管理・科目管理）を順に開く
2. **期待値**: いずれのページも正常に表示される（503 等なし）
