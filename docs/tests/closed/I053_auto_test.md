# I053 自動テスト

## 概要

ドキュメント変更（ステップ 1）は自動テスト対象なし。
E2E インフラ修正（ステップ 2）は既存 E2E スイートで検証する。

## 既存テストへの影響

- Backend / Frontend: なし（コード変更を伴わない）
- E2E: `e2e/playwright.config.ts` と `e2e/tests/auth.spec.ts` の修正により、既存 E2E スイート全体の正常動作を確認する

---

## fix-loop 再発防止記録

### なぜ失敗したか

`playwright.config.ts` の `chromium-authed` プロジェクトの `testMatch` に負の先読み regex のバグがあった。

```js
// バグあり
testMatch: /(?!.*auth\.spec).*\.spec\.ts/,
```

JavaScript の正規表現は**部分一致**で動作するため、文字列 `auth.spec.ts` に対してマッチ開始位置を 1 ずつずらすと、位置 1（`u` から）では負の先読みが通過し `.*\.spec\.ts` が `uth.spec.ts` にマッチしてしまう。

結果として `chromium-authed`（認証済みプロジェクト）が `auth.spec.ts`（未認証テスト）を実行し、期限切れ JWT の auth state が適用された状態でテストが走った。ページロード時に 403 エラーの toast「アクセスが拒否されました」が表示され、期待の toast「入力内容にエラーがあります」が出なかった。

### 何を変えたか

**設定レベル（プライマリ防御）**:
- `chromium-authed` の `testMatch` 複雑 regex を削除し、`testIgnore: '**/auth.spec.ts'` に置換
- `chromium-unauthed` の `testMatch` regex を glob `'**/auth.spec.ts'` に統一

**テストレベル（セカンダリ防御・二重防御）**:
- `auth.spec.ts` 先頭に `test.use({ storageState: { cookies: [], origins: [] } })` を追加
- どのプロジェクトで実行されても未認証状態が保証される

### セキュリティ上の考慮点

- 変更は E2E テスト設定のみ。本番コードへの影響なし。
- `storageState: { cookies: [], origins: [] }` はテスト実行時のブラウザ状態をクリアするだけであり、セキュリティリスクなし。

### 次回どう防ぐか

1. **glob を優先する**: Playwright の testMatch/testIgnore は regex より glob が読みやすく、部分マッチの罠がない
2. **テストは自身の前提条件を宣言する**: 未認証テストは `test.use({ storageState: ... })` で明示することで、config の設定ミスに依存しない
3. **新規 E2E ファイルを追加する際**: 認証状態が必要かどうかをファイル先頭で `test.use()` にて宣言する慣習を徹底する

---

## E2E 自動テスト実行コマンド

```bash
# 事前準備（毎回）
RATELIMIT_ENABLE=false docker compose up -d backend
docker compose rm -f e2e-init

# 実行
docker compose --profile e2e run --rm e2e
```

**期待結果**: 8 passed、0 failed
