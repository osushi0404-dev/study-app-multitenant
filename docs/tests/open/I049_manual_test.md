# I049 手動テスト

## 対象
plan_I049: Playwright E2Eテスト基盤を導入しクリティカルパスを保護する

## テスト実施前提
- Docker Compose が起動している（`docker compose up -d`）
- E2E 実装が完了している

## 手動テスト項目

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `cat e2e/.env.e2e.example` でファイル内容を確認する | `E2E_TEST_PASSWORD=<set-your-e2e-password-here>` が出力される | Claude | - | テンプレートファイル存在確認 |
| 2 | `E2E_TEST_PASSWORD` を未設定の状態で `docker compose --profile e2e run --rm e2e npm test` を実行する | `E2E_TEST_PASSWORD is not set.` というエラーメッセージが出力されて即停止する | Claude | - | 未設定時のフェイルファスト確認 |
| 3 | `e2e/.env.e2e` に `E2E_TEST_PASSWORD` を設定した状態で `docker compose --profile e2e run --rm e2e npm test` を実行する | 全テスト（auth / tenant-isolation / quiz-session）が PASS する | Claude | - | E2E 全テスト通過確認 |
| 4 | `cat e2e/.auth/user_a.json` でファイル内容を確認する | JSON 形式の storageState（cookies / localStorage）が出力される | Claude | - | storageState 生成確認 |
| 5 | CI（GitHub Actions）で `e2e.yml` ジョブが実行されていることを確認する | PR の Checks 一覧に「E2E Tests (Playwright)」ジョブが表示され、`backend/.env` 不在でも `Start services` ステップが成功する | Human | - | CI 統合確認・GitHub Secrets 設定も必要。`docker-compose.yml` の `required: false` が効いていることの確認も兼ねる |
| 6 | `docker compose --profile e2e run --rm e2e npm test` 実行後にトレースファイルを確認する | `playwright-report/` に trace ファイルが生成されている（失敗時のみ） | Claude | - | trace ファイル存在確認 |
| 7 | ログイン画面（`http://localhost:3000/login`）を開き、`data-testid` 属性が付与されていることを確認する | DevTools で `email-input`・`password-input`・`login-button` の `data-testid` が確認できる | Human | - | data-testid 追加確認 |
