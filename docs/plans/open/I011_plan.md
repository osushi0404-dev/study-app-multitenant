# 計画書: I011 dev 環境で Service Worker を無効化

## 基本情報
- **計画書ID**: I011_plan
- **関連イシュー**: #26
- **作成根拠資料**: docs/issues/open/011.md
- **実装後評価**: （未作成）
- **作成日**: 2026-03-27

---

## 1. 背景/目的

`pwa.service.ts` の `registerServiceWorker()` が `NODE_ENV` に関わらず常に Service Worker を登録する。
dev 環境では SW がキャッシュした古いバンドルを配信し、HMR が機能しない・リクエストを SW が横取りして 503 を返すなどの問題が発生している。
`NODE_ENV === 'development'` 時に SW を登録しないのが業界標準（CRA / Workbox 等）であり、本イシューでその対応を行う。

---

## 2. 受け入れ条件

- [ ] dev 環境（`npm start`）で SW が登録されない
- [ ] ソースファイルを変更してコンテナ再起動後、ブラウザリロードで最新コードが即時反映される
- [ ] 本番ビルド（`npm run build`）では SW が引き続き登録される

---

## 3. 影響範囲

| 層 | 影響 |
|----|------|
| Backend | なし |
| Frontend | `frontend/src/services/pwa.service.ts`（1 箇所のみ） |
| DB | なし |
| Config/Infra | なし |

---

## 4. 調査結果

### 原因の概要

`PWAService.registerServiceWorker()` メソッドが `NODE_ENV` チェックなしで Service Worker を登録している。

### 詳細

`pwa.service.ts:39-64` の `registerServiceWorker()` は `'serviceWorker' in navigator` のみをガードとして使い、環境を問わず `/sw.js` を登録する。

```typescript
// 現状（pwa.service.ts:39-44）
private async registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      // ...
```

dev 環境で SW が動くと以下が発生する：
1. SW が古いバンドルをキャッシュし、ソース変更がブラウザに反映されない
2. WSL2 + Docker の inotify 非対応環境では HMR が効かず、さらに問題が悪化
3. SW が API リクエストを横取りして 503 を返すケースがある（`sw.js:152`）

---

## 5. 修正対象と具体的変更内容

### 修正アプローチ

`registerServiceWorker()` の先頭に `process.env.NODE_ENV === 'development'` チェックを追加し、dev 環境では即座に return する。変更は 3 行以内で完結する最小限の修正。

### 修正項目

**ファイル**: `frontend/src/services/pwa.service.ts`

**修正前**:
```typescript
private async registerServiceWorker() {
  if ('serviceWorker' in navigator) {
```

**修正後**:
```typescript
private async registerServiceWorker() {
  if (process.env.NODE_ENV === 'development') {
    console.log('Service Worker registration skipped in development mode');
    return;
  }
  if ('serviceWorker' in navigator) {
```

---

## 6. 実装手順

1. `frontend/src/services/pwa.service.ts` の `registerServiceWorker()` 先頭（行 40 の直前）に 4 行追加
2. `npm start` で動作確認（DevTools の Application > Service Workers で「No service workers detected.」を確認）
3. `npm run build` で本番ビルドを確認（SW が登録されることを確認）

---

## 7. テスト計画

- **自動テスト**: `frontend/src/services/__tests__/pwa.service.test.ts` 新規作成
  - dev モードで SW が登録されないことを確認
  - prod モードで SW 登録が試みられることを確認
- **手動テスト**: docs/tests/open/I011_manual_test.md 参照

---

## 8. ロールバック

修正は 4 行追加のみ。問題発生時は追加した 4 行を削除するだけで元に戻る。

---

## 9. Risk & 回避策

| リスク | 可能性 | 回避策 |
|--------|--------|--------|
| 既存 SW がブラウザにキャッシュされており dev で引き続き動作する | 低（修正後は新規登録されないだけで既存 SW は残る） | DevTools > Application > Service Workers > Unregister で手動削除する（初回のみ） |
| `process.env.NODE_ENV` が未定義の環境での挙動 | 極低（CRA は必ず `NODE_ENV` を設定） | `process.env.NODE_ENV === 'development'` は falsy となり、登録は実行される（安全側） |

---

## 10. 承認ポイント

- [ ] `registerServiceWorker()` 先頭に `NODE_ENV === 'development'` チェックを追加する方針に合意
- [ ] dev 環境での既存 SW は自動削除しない（手動 Unregister で対応）方針に合意
- [ ] 変更ファイルは `pwa.service.ts` 1 ファイルのみで良い
