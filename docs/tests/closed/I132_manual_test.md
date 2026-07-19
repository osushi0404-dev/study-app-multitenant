# I132 手動テスト（FE テストの axios 内部構造依存解消・差分範囲と CI の確認）

- 関連: docs/issues/open/I132.md / docs/plans/open/plan_I132.md / GitHub #240 / Draft PR #243
- 前提: 実装（変更点1〜3）と自動テスト（TC-01〜07）完了後に実施
- 使用アカウント: **不要**（UI 変更ゼロ・ブラウザ操作なし。全項目コマンド/ファイル確認のため Claude 実施）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 変更範囲の確認: `git diff develop --stat` で変更ファイル一覧を取得 | 変更ファイルが計画の変更点一覧のみ: `frontend/package.json`・`frontend/package-lock.json`・`frontend/src/services/api.ts`・`frontend/src/services/__tests__/api.test.ts`（＋docs/。計画外のソース変更がない） | Claude | ✅ 2026-07-19: ソース変更は計画の 4 ファイルのみ・他は I132 の docs 8 ファイル（計 12 ファイル・計画外変更なし） | |
| 2 | api.ts の差分内容確認: `git diff develop -- frontend/src/services/api.ts` を目視 | 差分が変更点2 の 2 箇所のみ（`export class` 追加・コンストラクタの `instance?: AxiosInstance` 注入化）。インターセプタ・各メソッド・シングルトン export（`export const apiClient = new ApiClient()`）に差分がない | Claude | ✅ 2026-07-19: 差分は先頭 1 ハンク（export 追加＋コンストラクタ注入化）のみ。インターセプタ・メソッド・シングルトン export に差分なし | AC「シングルトンの既定動作が不変」の差分レベル確認（挙動レベルは TC-05/07） |
| 3 | PR CI の確認: push 後 `gh pr checks 243` で全チェック結果を取得 | Frontend Tests / Lint & Security（`npm audit --audit-level=critical` 含む）/ Type Check / E2E を含む全チェックが PASS | Claude | ✅ 2026-07-19: 全 6 チェック PASS（Backend Tests 1m10s / Backend Lint & Security / Frontend Tests / Frontend Lint & Security / Frontend Type Check / **E2E Tests (Playwright) 3m11s**） | CI 完了待ちのため最後に実施 |

**実施順**: No.1 → No.2 → No.3（No.3 は push 後の CI 完了待ちのため最後）。

**Claude/Human の判定根拠**（feedback_manual_test_executor 準拠）: 全項目コマンド実行・差分/出力確認のため Claude。UI 変更ゼロのためブラウザ目視（Human）項目なし。
