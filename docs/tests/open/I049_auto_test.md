# I049 自動テスト記録

## 対象
plan_I049: Playwright E2Eテスト基盤を導入しクリティカルパスを保護する

## Backend（pytest）

実行コマンド:
```bash
docker compose exec backend python -m pytest --tb=short -q
```

| 実行日時 | Pass | Fail | Warn | 備考 |
|---------|------|------|------|------|
| ベースライン (2026-04-18) | 25 | 0 | 3 | 実装前ベースライン |
| 実装後 | - | - | - | 未実施 |

## CI リント・セキュリティスキャン（backend-lint ジョブ）

> **確認観点**: このプロジェクトでは flake8・bandit は GitHub Actions ランナー上で実行される（`ci.yml` の `backend-lint` ジョブ）。Dockerfile は本番・開発コンテナ共通で `requirements-dev.txt` を含まないため、`docker compose exec backend python -m flake8` は動作しない。これは設計による仕様（Docker コンテナはアプリ実行用、lint は CI ランナーで行う）。
>
> **本実装の変更ファイルの lint リスク評価**:
> - `seed_e2e.py`: 変更は `'loaddata', 'e2e_master.json'` → `'migrate', '--noinput'` の文字列置換1行のみ（新規コードなし）
> - `accounts/migrations/0021_*`: `backend/setup.cfg` の `exclude` 設定と CI の `-x ./\*/migrations/` により flake8・bandit の対象外

確認コマンド:
```bash
gh pr checks [PR番号]
```

| 確認日時 | flake8 pass（backend-lint） | bandit pass（backend-lint） | 備考 |
|---------|--------------------------|--------------------------|------|
| 実装後 | - | - | 未実施 |

## Frontend（Jest）

実行コマンド:
```bash
docker compose exec frontend sh -c "CI=true npm test -- --watchAll=false"
```

| 実行日時 | Suites | Tests | 備考 |
|---------|--------|-------|------|
| ベースライン (2026-04-18) | 2 | 7 | 実装前ベースライン |
| 実装後 | - | - | 未実施 |

## インフラ検証（docker compose 設定確認）

実行コマンド:
```bash
# db ヘルスチェック設定確認
docker compose config --format json | python3 -c "import sys,json; cfg=json.load(sys.stdin); hc=cfg['services']['db'].get('healthcheck',{}); print(hc)"

# backend depends_on 条件確認
docker compose config --format json | python3 -c "import sys,json; cfg=json.load(sys.stdin); dep=cfg['services']['backend'].get('depends_on',{}); print(dep)"

# backend_logs named volume 設定確認
docker compose config --format json | python3 -c "import sys,json; cfg=json.load(sys.stdin); vols=cfg['services']['backend'].get('volumes',[]); print([v for v in vols if 'logs' in str(v)])"
docker compose config --format json | python3 -c "import sys,json; cfg=json.load(sys.stdin); print(list(cfg.get('volumes',{}).keys()))"

# e2e-init サービス定義確認（Init Container パターン）
docker compose config --format json | python3 -c "import sys,json; cfg=json.load(sys.stdin); svc=cfg['services'].get('e2e-init',{}); print('image:', svc.get('image','(build)'), 'profiles:', svc.get('profiles',[]))"
docker compose config --format json | python3 -c "import sys,json; cfg=json.load(sys.stdin); dep=cfg['services']['e2e'].get('depends_on',{}); print(dep)"

# db が healthy になっていることを確認（起動後）
docker compose ps db

# HealthCheckMiddleware が MIDDLEWARE から削除されていることを確認
grep "HealthCheckMiddleware" backend/core/settings.py && echo "NG: まだ残っている" || echo "OK: 削除済み"

# /health/ が {"status": "ok"} を返すことを確認（DB 接続確認のみ）
# ※ curl は deny 設定のため docker compose exec 経由で確認
docker compose exec -T backend python manage.py shell -c "
from django.test import RequestFactory
from django.urls import resolve
rf = RequestFactory()
req = rf.get('/health/')
view = resolve('/health/').func
resp = view(req)
print('status:', resp.status_code, 'body:', resp.content.decode())
"
```

> **確認観点**: `db.healthcheck.test` に `pg_isready -U postgres` が含まれること、`backend.depends_on.db.condition` が `service_healthy` であること、`backend.volumes` に `backend_logs` が含まれること、top-level `volumes` に `backend_logs` が定義されていること。`e2e-init` サービスが `e2e` プロファイル付きで定義されていること（コマンドに `loaddata` が含まれないこと）、`e2e.depends_on` に `e2e-init: condition: service_completed_successfully` が設定されていること。`HealthCheckMiddleware` が `MIDDLEWARE` から削除されていること。`/health/` が `{"status": "ok"}` (HTTP 200) を返すこと。

| 確認日時 | db healthcheck 設定 | backend condition: service_healthy | backend_logs named volume 設定 | e2e-init サービス定義（loaddata なし） | e2e depends_on e2e-init | HealthCheckMiddleware 削除 | /health/ 応答 | 備考 |
|---------|--------------------|------------------------------------|-------------------------------|--------------------------------------|------------------------|--------------------------|--------------|------|
| 実装後 | - | - | - | - | - | - | - | 未実施 |

## マイグレーション追加（problems.0017）

### 検証内容
`problems.0017_remove_problem_points` の孤立カラム削除確認。

**背景**: `points` は `problems/migrations/0001_initial.py` で `IntegerField(default=10, NOT NULL)` として作成されたが、その後 `models.py` から削除されたにもかかわらず DROP 用マイグレーションが存在しなかった。fresh DB（CI）では Django ORM の INSERT に `points` が含まれず NOT NULL 違反で `seed_e2e` の quiz_session シナリオが失敗していた。

確認コマンド（CI ログで確認）:
```bash
# problems.0017 が正常完了することを確認
gh run view <run_id> --log 2>&1 | grep "0017_remove_problem_points"

# seed_e2e quiz_session シナリオが成功することを確認
gh run view <run_id> --log 2>&1 | grep "quiz_session"
```

| 確認日時 | 0017 マイグレーション正常完了（CI） | seed_e2e quiz_session 成功（CI） | 備考 |
|---------|----------------------------------|-------------------------------|------|
| 実装後 | - | - | 未実施 |

## マイグレーション修正（accounts.0021）

### 検証内容
`accounts.0021_rename_organization_id_to_id` の型不一致バグ修正確認。

**背景**: 新規 DB では `problems.0004` が `accounts.0010` より先に実行されるため `problems_subject.organization_id` が UUID 型で作成される。`accounts.0010` が Organization を INTEGER PK で再作成（DROP TABLE CASCADE）した後、カラム型が UUID のまま残り、`accounts.0021` の FK 再作成で `DatatypeMismatch` が発生していた。

確認コマンド（CI ログまたはローカル fresh DB での確認）:
```bash
# accounts.0021 が正常完了することを確認（CI ログで "OK" が表示されること）
# ローカル確認は既存 DB に適用済みのため CI ログで代替確認
gh run view <run_id> --log 2>&1 | grep "0021_rename_organization_id_to_id"
```

| 確認日時 | 0021 マイグレーション正常完了（CI） | 備考 |
|---------|-----------------------------------|------|
| 実装後 | - | 未実施 |

## E2E（Playwright）

実行コマンド:
```bash
# 前提: e2e/.env.e2e に E2E_TEST_PASSWORD が設定されていること（e2e/.env.e2e.example を参照）
# CI では GitHub Actions Secrets の E2E_TEST_PASSWORD が自動注入される
docker compose --profile e2e run --rm e2e npm test
```

> **注意**: `E2E_TEST_PASSWORD` が未設定の場合、globalSetup が即停止してテストは実行されない（フェイルファスト）。
> **前提**: `docker-compose.yml` の `env_file` が `required: false` になっているため、`backend/.env` が存在しなくても `docker compose up` は動作する（CI・新規開発者環境どちらでも追加手順不要）。
> **前提**: `db` の `pg_isready` ヘルスチェックが通過した後に `backend` が起動するため、migrate のレースコンディションは発生しない。
> **前提**: `backend_logs:/app/logs` named volume により、CI チェックアウト後に `backend/logs/` が存在しなくても `enhanced_logging.py` の `LOG_DIR.mkdir()` が `PermissionError` を起こさない。

| 実行日時 | auth.spec | tenant-isolation.spec | quiz-session.spec | 備考 |
|---------|-----------|----------------------|------------------|------|
| 実装後 | - | - | - | 未実施 |

## fix-loop 発見事項（E2E テストコード修正）

CI で E2E_TEST_PASSWORD 設定後に判明した 3 件の失敗と根本原因・修正内容。

### Failure 1: auth.spec.ts — トーストセレクター誤り

**根本原因**: テストコードが `.Toastify__toast--error`（`react-toastify` のクラス）を使っていたが、アプリは `react-hot-toast` を使用しており当該クラスは存在しない。

**修正**: ライブラリ内部実装ではなくユーザーが実際に見るテキストでアサートする。

ログイン失敗時の全経路:
`UserLoginSerializer.validate()` → `serializers.ValidationError("ユーザーIDまたはパスワードが正しくありません。")` → `custom_exception_handler` → `main_message = '入力内容にエラーがあります'` → `showErrorToast` → toast 表示。

```typescript
// ❌ 修正前: react-toastify クラス（アプリに存在しない）
await expect(page.locator('.Toastify__toast--error')).toBeVisible();

// ✅ 修正後: ユーザーが見るテキストでアサート（ライブラリ非依存）
await expect(page.getByText('入力内容にエラーがあります')).toBeVisible();
```

### Failure 2: quiz-session.spec.ts — ダイアログの非同期レース

**根本原因**: `e2e-init` が `tenant_isolation → quiz_session` の順でシードするため（flush なし）、org_a に Subject が 2件（`E2E Subject A` + `E2E Quiz Subject`）累積する。Dashboard の `handleStartQuiz` は `subjects.length >= 2` のときダイアログを開くが、テストの `if (await dialog.isVisible())` は瞬時チェック（待機なし）で React 状態更新 + MUI アニメーション（~300ms）に競合してダイアログを見逃し、科目が選択されないまま `/quiz` 遷移が発生しなかった。

**修正**: 「2件存在するためダイアログが必ず出る」という前提を明示した確定的実装に変更。

```typescript
// ❌ 修正前: 瞬時チェックで非同期レースが発生
if (await dialog.isVisible()) {
  await page.click('text=E2E Quiz Subject');
}

// ✅ 修正後: expect でリトライ付き待機、getByRole でアクセシビリティファースト
const subjectDialog = page.locator('[role="dialog"]');
await expect(subjectDialog).toBeVisible();  // 自動リトライ付きアサート
await subjectDialog.getByRole('button', { name: /E2E Quiz Subject/ }).click();
```

### Failure 3: tenant-isolation.spec.ts — seed ユーザーが non-admin でページにアクセス不可

**根本原因**: `SubjectManagement.tsx` は `user.role === 'admin'` のユーザーにのみ科目一覧を表示する。seed が `role` を指定しておらず、user_a・user_b はデフォルト `role='user'` で作成されていたため `/subject-management` でアクセス拒否画面が表示され `text=E2E Subject A` が見つからなかった。

**修正**: 両ユーザーを `role='admin'` で作成する。これにより「org_a の admin は org_a の科目のみ見える」「org_b の admin に org_a の科目は見えない」というテナント境界を正確に検証できる（ロール制御とテナント分離を混在させない）。

```python
# _seed_login: user_a に role='admin' を追加
User.objects.create_user(
    email='e2e_user_a@example.com',
    user_id='e2e_user_a',
    password=self.e2e_password,
    organization=org_a,
    role='admin',  # 追加
)

# _seed_tenant_isolation: user_b にも role='admin' を追加
User.objects.create_user(
    email='e2e_user_b@example.com',
    user_id='e2e_user_b',
    password=self.e2e_password,
    organization=org_b,
    role='admin',  # 追加
)
```
