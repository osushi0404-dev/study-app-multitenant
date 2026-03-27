# 自動テスト: I011 dev 環境で Service Worker を無効化

## 方針

変更対象は `pwa.service.ts` の `registerServiceWorker()` 1 メソッドのみ。
`process.env.NODE_ENV` を mock して SW 登録が呼ばれる/呼ばれないことを検証する。

---

## 既存テストへの影響確認

実装後に以下を実行して既存テストが壊れていないことを確認:

```bash
cd frontend
npm test -- --watchAll=false
```

---

## 新規自動テスト

**ファイル**: `frontend/src/services/__tests__/pwa.service.test.ts`

### AT-01: development モードで SW 登録が呼ばれない

```typescript
// process.env.NODE_ENV = 'development' を設定
// navigator.serviceWorker.register をモック
// pwaService をインスタンス化（または registerServiceWorker を直接呼ぶ）
// 期待値: navigator.serviceWorker.register が呼ばれない
```

検証項目:
- `navigator.serviceWorker.register` が 0 回呼ばれる
- コンソールに `'Service Worker registration skipped in development mode'` が出力される

### AT-02: production モードで SW 登録が試みられる

```typescript
// process.env.NODE_ENV = 'production' を設定
// navigator.serviceWorker.register をモック
// registerServiceWorker を呼ぶ
// 期待値: navigator.serviceWorker.register('/sw.js') が呼ばれる
```

検証項目:
- `navigator.serviceWorker.register` が 1 回呼ばれる

---

## ビルド確認

```bash
cd frontend
npm run build
```

エラーなく完了することを確認。
