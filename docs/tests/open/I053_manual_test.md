# I053 手動テスト

## 概要
- ステップ 1: `rules/ultimate_django_coding_standards.md` に migration 依存ルールが正しく追記されていることを確認する
- ステップ 2（fix-loop 追加）: E2E テスト設定の修正が正しく適用され、ローカル E2E が全 pass することを確認する

---

## テスト項目

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `rules/ultimate_django_coding_standards.md` を開き、Section 4「モデル設計」内に `### マイグレーション` サブセクションが存在することを確認する | サブセクションが `### カスタムマネージャー` の直後・`---` 区切りの前に存在する | Claude | | |
| 2 | `### マイグレーション` セクション内に「FK 追加 migration の dependencies ルール」の見出しが含まれることを確認する | 見出しが存在する | Claude | | |
| 3 | ❌ 悪い例（再作成 migration が dependencies にない）のコードブロックが含まれることを確認する | コードブロックが存在する | Claude | | |
| 4 | ✅ 良い例（再作成 migration を明示的に含める）のコードブロックが含まれることを確認する | `('accounts', '0010_update_organization_structure')` と `# explicit:` コメントが含まれる | Claude | | |
| 5 | 「チェック手順」の 3 ステップ（`makemigrations` 後の確認・git log での履歴確認・依存追加）が記載されていることを確認する | 3 ステップが列挙されている | Claude | | |
| 6 | ファイル全体の Markdown が崩れていないことを確認する（Section 5 以降が正常に表示される） | Section 5「API設計（DRF）」が `---` の後に続いている | Claude | | |
| 7 | `e2e/playwright.config.ts` の `chromium-authed` に `testIgnore: '**/auth.spec.ts'` が設定され、負の先読み `testMatch` regex が削除されていることを確認する | `testIgnore` が存在し、`(?!.*auth\.spec)` を含む regex が存在しない | Claude | | fix-loop 追加 |
| 8 | `e2e/playwright.config.ts` の `chromium-unauthed` の `testMatch` が glob `'**/auth.spec.ts'` になっていることを確認する | glob 文字列になっている | Claude | | fix-loop 追加 |
| 9 | `e2e/tests/auth.spec.ts` の先頭（`test.describe` の前）に `test.use({ storageState: { cookies: [], origins: [] } })` が追加されていることを確認する | 記述が存在する | Claude | | fix-loop 追加 |
| 10 | ローカルで E2E テストを実行し全 pass することを確認する（`RATELIMIT_ENABLE=false docker compose up -d backend && docker compose rm -f e2e-init && docker compose --profile e2e run --rm e2e`） | 8 passed, 0 failed | Claude | | fix-loop 追加 |
