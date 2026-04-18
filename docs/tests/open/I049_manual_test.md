# I049 手動テスト

## 対象
plan_I049: Playwright E2Eテスト基盤を導入しクリティカルパスを保護する

## テスト実施前提
- Docker Compose が起動している（`docker compose up -d`）
- E2E 実装が完了している

## 手動テスト項目

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `curl -sf http://localhost:8000/health/` を実行する | `{"status": "ok"}` が返る（DB 接続確認済み）。`timestamp`・`redis`・`overall_status` 等の詳細フィールドは含まれない | Claude | - | `/health/` エンドポイント動作確認。`HealthCheckMiddleware` 削除後に `health()` 関数が応答することを確認 |
| 2 | `curl -sf http://localhost:8000/health/` の応答時間を確認する | 1秒以内に応答が返る | Claude | - | レスポンスタイム確認 |
| 3 | `cat e2e/.env.e2e.example` でファイル内容を確認する | `E2E_TEST_PASSWORD=<set-your-e2e-password-here>` が出力される | Claude | - | テンプレートファイル存在確認 |
| 4 | `E2E_TEST_PASSWORD` を未設定の状態で `docker compose --profile e2e run --rm e2e npm test` を実行する | `E2E_TEST_PASSWORD is not set.` というエラーメッセージが出力されて即停止する | Claude | - | 未設定時のフェイルファスト確認 |
| 5 | `e2e/.env.e2e` に `E2E_TEST_PASSWORD` を設定した状態で `docker compose --profile e2e run --rm e2e` を実行する（command は docker-compose.yml の `npm install && npm test` が自動適用。`e2e-init` が先行して migrate・seed を実行する） | 全テスト（auth / tenant-isolation / quiz-session）が PASS する | Claude | - | E2E 全テスト通過確認（Init Container パターン：`e2e-init` が DB 初期化、`e2e` がテスト実行） |
| 6 | `cat e2e/.auth/user_a.json` でファイル内容を確認する | JSON 形式の storageState（cookies / localStorage）が出力される | Claude | - | storageState 生成確認 |
| 7 | CI（GitHub Actions）で `e2e.yml` ジョブが実行されていることを確認する | PR の Checks 一覧に「E2E Tests (Playwright)」ジョブが表示され、`Start services and wait for healthy` ステップが成功する（手動ポーリングステップなし） | Human | - | CI 統合確認・GitHub Secrets 設定も必要 |
| 8 | `docker compose --profile e2e run --rm e2e npm test` 実行後にトレースファイルを確認する | `playwright-report/` に trace ファイルが生成されている（失敗時のみ） | Claude | - | trace ファイル存在確認 |
| 9 | ログイン画面（`http://localhost:3000/login`）を開き、`data-testid` 属性が付与されていることを確認する | DevTools で `email-input`・`password-input`・`login-button` の `data-testid` が確認できる | Human | - | data-testid 追加確認 |
| 10 | `docker compose up -d db backend` 後に `docker compose ps db` を実行する | db サービスのステータスが `healthy` と表示される（`pg_isready` ヘルスチェックが機能している） | Claude | - | db ヘルスチェック動作確認・migrate レースコンディション防止の検証 |
| 11 | `docker compose config --format json \| python3 -c "import sys,json; cfg=json.load(sys.stdin); vols=cfg['services']['backend'].get('volumes',[]); print([v for v in vols if 'logs' in str(v)])"` を実行する | `backend_logs:/app/logs` を含む出力が表示される（named volume が設定されている） | Claude | - | named volume 設定確認・PermissionError 対策の検証 |
