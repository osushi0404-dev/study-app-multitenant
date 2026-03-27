# 計画書: I011 Service Worker・PWA コンポーネントを完全撤去

## 基本情報
- **計画書ID**: I011_plan
- **関連イシュー**: #26
- **作成根拠資料**: docs/issues/open/011.md
- **実装後評価**: （未作成）
- **作成日**: 2026-03-27

---

## 1. 背景/目的

`pwa.service.ts` が常時 Service Worker を登録しており、dev 環境でキャッシュした古いバンドルが返ってくる問題が発生した。
調査の結果、現行 SW 実装には以下の根本的な問題があることが判明した：

- `CACHE_NAME = 'learning-app-v1'` 固定 → 更新後も古いキャッシュが残る
- 静的 URL（`/static/js/bundle.js`）が CRA 出力のハッシュ付きファイル名と不一致 → pre-cache が機能しない
- Cache First 戦略 → 再ビルド後も古い JS を返す
- `skipWaiting()` + `clients.claim()` → 「最新 SW + 古いコンテンツ」の最悪の組み合わせ

SW はセキュリティ機構でも、モダン Web のデフォルトでもない。
現時点でオフライン利用・プッシュ通知・インストール体験の要件は未確定。
壊れた実装を抱え続けるより、要件確定時に Workbox 等で正しく再実装する方針とし、全撤去を行う。

---

## 2. 受け入れ条件

- [ ] dev 環境（`npm start`）で SW が登録されない
- [ ] ソースファイル変更 → コンテナ再起動 → ブラウザリロードで最新コードが反映される
- [ ] アプリが正常に起動し、既存機能に影響がない
- [ ] `npm run build` がエラーなく完了する
- [ ] TypeScript エラーなし

---

## 3. 影響範囲

| 層 | 影響 |
|----|------|
| Backend | なし |
| Frontend | 削除 5 ファイル + 修正 1 ファイル（下記参照） |
| DB | なし |
| Config/Infra | なし |

---

## 4. 調査結果

### 現行 SW の問題点

#### sw.js（`public/sw.js`）
- `CACHE_NAME = 'learning-app-v1'` 固定。activate 時に「自分以外のキャッシュを削除」するが、自分自身は削除されない → 再デプロイ後も古いキャッシュが残る
- `STATIC_CACHE_URLS = ['/static/js/bundle.js', '/static/css/main.css']` — CRA 本番ビルドは `main.f3b66563.js` のようなハッシュ付きファイルを出力するため、これらのパスは存在しない → pre-cache が無意味
- 静的ファイルに Cache First 戦略 → 一度キャッシュされると永続
- `skipWaiting()` で即座にアクティブ化するが、キャッシュは古いまま

#### pwa.service.ts（`frontend/src/services/pwa.service.ts`）
- `NODE_ENV` チェックなしで `navigator.serviceWorker.register('/sw.js')` を実行
- dev でも prod でも常時登録される

#### PWA コンポーネント（`frontend/src/components/PWA/`）
- `PWAProvider`: `pwaService` をコンテキスト経由で提供
- `InstallPrompt`: `beforeinstallprompt` イベントに依存（SW 必須ではないが SW と一体で設計）
- `OfflineIndicator`: `navigator.onLine` ベース（SW 不要だが、今は要件外として撤去）
- `UpdateNotifier`: SW 更新通知専用

#### App.tsx
- `PWAProvider` でアプリ全体をラップ
- `<OfflineIndicator />` / `<UpdateNotifier />` / `<InstallPrompt />` を直接使用

---

## 5. 修正対象と具体的変更内容

### 修正アプローチ

5 ファイルを削除し、`App.tsx` から参照を除去する。
`App.tsx` の `<PWAProvider>` ラッパーを外す際は、その子要素（`<AuthProvider>` 以下）を保持する。

### 変更一覧

#### 削除ファイル（5）

| ファイル | 理由 |
|----------|------|
| `public/sw.js` | SW 本体。撤去対象 |
| `frontend/src/services/pwa.service.ts` | SW 登録・管理サービス。撤去対象 |
| `frontend/src/components/PWA/PWAProvider.tsx` | `pwaService` 依存。撤去対象 |
| `frontend/src/components/PWA/InstallPrompt.tsx` | `pwaService` 依存。撤去対象 |
| `frontend/src/components/PWA/OfflineIndicator.tsx` | 要件外。撤去対象 |
| `frontend/src/components/PWA/UpdateNotifier.tsx` | SW 更新通知専用。撤去対象 |

#### 修正ファイル（1）: `frontend/src/App.tsx`

**修正方針**: PWA 関連の import 4 行と、コンポーネント使用箇所（`<PWAProvider>` ラッパー・`<OfflineIndicator />` / `<UpdateNotifier />` / `<InstallPrompt />`）を削除する。

**修正前（抜粋）**:
```tsx
// PWA Components
import PWAProvider from './components/PWA/PWAProvider';
import InstallPrompt from './components/PWA/InstallPrompt';
import OfflineIndicator from './components/PWA/OfflineIndicator';
import UpdateNotifier from './components/PWA/UpdateNotifier';

// ...

<PWAProvider>
  <AuthProvider>
    <NotificationProvider>
      {/* ... */}
      <OfflineIndicator />
      <UpdateNotifier />
      <InstallPrompt />
      {/* ... */}
    </NotificationProvider>
  </AuthProvider>
</PWAProvider>
```

**修正後（抜粋）**:
```tsx
// PWA Components の import を削除

// ...

<AuthProvider>
  <NotificationProvider>
    {/* ... */}
    {/* OfflineIndicator / UpdateNotifier / InstallPrompt を削除 */}
    {/* ... */}
  </NotificationProvider>
</AuthProvider>
```

---

## 6. 実装手順

1. `public/sw.js` を削除
2. `frontend/src/services/pwa.service.ts` を削除
3. `frontend/src/components/PWA/PWAProvider.tsx` を削除
4. `frontend/src/components/PWA/InstallPrompt.tsx` を削除
5. `frontend/src/components/PWA/OfflineIndicator.tsx` を削除
6. `frontend/src/components/PWA/UpdateNotifier.tsx` を削除
7. `frontend/src/App.tsx` を修正（import 削除・`<PWAProvider>` ラッパー除去・3 コンポーネント削除）
8. `npm run build` でエラーなし確認
9. `npm test` で既存テスト通過確認

---

## 7. テスト計画

- **自動テスト**: `npm test` で既存テストがパスすることを確認（新規テスト不要）
- **手動テスト**: docs/tests/open/I011_manual_test.md 参照

---

## 8. ロールバック

`git revert` または削除ファイルを `git checkout` で復元する。
変更は独立しており、他機能への影響なし。

---

## 9. Risk & 回避策

| リスク | 可能性 | 回避策 |
|--------|--------|--------|
| `usePWA` フックが他コンポーネントで使われている | 低（調査済み：`App.tsx` のみ参照） | 実装前に `grep -r usePWA` で再確認 |
| `PWAProvider` 削除で子コンポーネントが壊れる | 低（Provider は Context 提供のみ） | `npm run build` で即座に検出可能 |
| 既存 SW がブラウザにキャッシュされておりリロード後も動作する | 低〜中 | DevTools > Application > Service Workers > Unregister で手動削除（初回のみ） |

---

## 10. 承認ポイント

- [ ] スコープ（5 ファイル削除 + `App.tsx` 修正）に合意
- [ ] `manifest.json` と `index.html` は変更しない方針に合意
- [ ] 既存 SW のブラウザキャッシュは手動 Unregister で対応（自動削除しない）方針に合意
