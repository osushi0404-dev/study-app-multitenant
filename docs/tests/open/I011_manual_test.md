# 手動テスト: I011 Service Worker・PWA コンポーネントを完全撤去

## 前提条件

- Docker コンテナが起動済み（`docker compose up`）
- ブラウザは Chrome（DevTools の Application パネルを使用）

---

## テスト結果（2026-03-27）: MT-01〜MT-05 すべて OK

---

## MT-01: SW が登録されていないことを確認

1. `npm start`（または Docker dev 環境）でフロントエンドを起動
2. ブラウザで `http://localhost:3000` を開く
3. DevTools > Application > Service Workers を開く
4. **期待値**: 「No service workers detected.」が表示される

> ※ 既存 SW がキャッシュされている場合は「Unregister」ボタンで手動削除してからリロードする

---

## MT-02: ソース変更が即時反映される

1. `frontend/src/pages/` 配下のいずれかのファイルに軽微な変更を加える（例: テキスト修正）
2. コンテナ再起動（`docker compose restart frontend`）
3. ブラウザをリロード
4. **期待値**: 変更が反映される（古いキャッシュが返らない）

---

## MT-03: アプリが正常に起動する

1. ブラウザで `http://localhost:3000` を開く
2. ログイン → 各ページ（ダッシュボード・問題管理・科目管理）を順に開く
3. **期待値**: いずれのページも正常に表示される（コンソールエラーなし）

---

## MT-04: PWA コンポーネントが表示されないことを確認

1. アプリを操作する
2. **期待値**: オフラインバナー・インストールプロンプト・更新通知が表示されない

---

## MT-05: ビルドが正常に完了する

```bash
cd frontend
npm run build
```

**期待値**: エラーなく完了し、`build/` ディレクトリが生成される
