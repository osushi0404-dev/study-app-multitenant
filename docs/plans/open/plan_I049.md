# plan_I049: Playwright E2Eテスト基盤を導入しクリティカルパスを保護する

## 基本情報
- **計画書ID**: plan_I049
- **関連イシュー**: #102
- **Draft PR**: #103
- **作成日**: 2026-04-18

---

## 1. 背景/目的

pytest（Backend）・Jest（Frontend）はロジック層をカバーするが、ブラウザ操作を通じたユーザー体験の検証が欠落している。フロントとバックエンドの繋ぎ目・認証フロー・画面表示など「ユニットテストでは検出できないバグ」を保護するため、Playwright による E2E テスト基盤を整備する。

テストピラミッドの最上層として **クリティカルパスのみを薄く保護** する方針とする（細かい分岐は pytest / Jest に委ねる）。

---

## 2. 受け入れ条件

- [ ] `docker compose run e2e` で Playwright が起動しテストが実行される
- [ ] ログイン／ログアウトの E2E テストが通る
- [ ] テナント間データ分離の E2E テストが通る（Organization A のデータが Organization B ユーザーから見えないことを確認）
- [ ] 学習コンテンツ閲覧〜回答の E2E テストが通る
- [ ] `/test` スキルに E2E ステップが追加されている
- [ ] CI（GitHub Actions）で E2E が独立ジョブとして自動実行される

---

## 3. 影響範囲

- **Backend**: `manage.py seed_e2e` カスタム管理コマンド追加、`e2e_master.json` fixture 追加
- **Frontend**: なし（E2E テストはプロジェクトルートの `e2e/` ディレクトリに配置し frontend ディレクトリには触れない）
- **DB**: デフォルト DB（`learning_app`）を使用。E2E データは `e2e_` プレフィックスで識別。CI ではクリーンな DB インスタンスから起動するため本番データとは完全分離。ローカルでは同一 DB に `e2e_` プレフィックス付きデータが混在するが、`seed_e2e` の冪等設計（get_or_create / delete→create）で整合性を維持
- **Config/Infra**: `docker-compose.yml` に `e2e` サービス追加、`.github/workflows/e2e.yml` 追加、`.claude/skills/test/SKILL.md` 更新

---

## 4. 調査結果

### 環境状況
- Playwright: v1.59.1（Node.js ホスト環境にグローバルインストール済み）
- Node.js: v24.14.1
- pytest: Docker 経由で実行（`docker compose exec backend`）
- Backend ベースラインテスト: **25 passed, 3 warnings**（全通過）
- Frontend ベースラインテスト: **7 passed, 2 suites**（全通過）

### 既存コード確認
- ログイン API: `POST /api/auth/login/`（JWT トークン）
- ログアウト API: `POST /api/auth/logout/`
- QuizSession: `/api/quiz/{session_id}/submit_answer/` で回答送信
- マルチテナント: `User.organization` FK（Organization モデル）でデータを分離
- 既存の e2e ディレクトリ・playwright.config.ts は存在しない（新規整備）

---

## 5. 変更点一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `e2e/` | 新規ディレクトリ | Playwright プロジェクトルート |
| `e2e/package.json` | 新規 | Playwright 依存・スクリプト定義（dotenv を含む） |
| `e2e/playwright.config.ts` | 新規 | Playwright 設定（baseURL・globalSetup・storageState・dotenv 読み込み） |
| `e2e/global-setup.ts` | 新規 | DB 初期化・migrate・seed・storageState 生成（E2E_TEST_PASSWORD を環境変数から取得） |
| `e2e/tests/auth.spec.ts` | 新規 | ログイン／ログアウト E2E テスト |
| `e2e/tests/tenant-isolation.spec.ts` | 新規 | テナント間データ分離 E2E テスト |
| `e2e/tests/quiz-session.spec.ts` | 新規 | クイズ閲覧〜回答 E2E テスト |
| `e2e/.auth/` | 新規ディレクトリ | storageState 保存先（.gitignore 対象） |
| `e2e/.gitignore` | 新規 | `.auth/`・`.env.e2e` を除外 |
| `e2e/.env.e2e.example` | 新規 | E2E テスト認証情報のテンプレート（git 管理）。実値は `.env.e2e`（gitignore 済み）に記載 |
| `backend/accounts/management/commands/seed_e2e.py` | 新規 | `manage.py seed_e2e --scenario <name> --password <pw>` 実装 |
| `backend/fixtures/e2e_master.json` | 新規 | 固定マスタデータ（OrganizationCategory 等） |
| `backend/core/urls.py` | 変更 | `/health/` エンドポイント追加（DB 接続確認付き readiness check） |
| `backend/core/settings.py` | 変更 | `MIDDLEWARE` から `HealthCheckMiddleware` を削除（URL ルーティングバイパス・情報漏洩リスク）|
| `backend/Dockerfile` | 変更 | `curl` インストール追加（ヘルスチェック・デバッグ用） |
| `frontend/Dockerfile.dev` | 変更 | `curl` インストール追加（ヘルスチェック用） |
| `docker-compose.yml` | 変更 | `e2e` サービス追加。**`e2e-init` サービス追加（Init Container パターン: backend イメージで `migrate`・`loaddata`・`seed_e2e` を実行し、`e2e` サービスが起動する前に完了させる）。** `env_file` を `required: false` に変更。`backend`・`frontend` に `healthcheck` 追加。`backend` に named volume `backend_logs:/app/logs` 追加（PermissionError 対策）。`e2e` に named volume `e2e_node_modules:/e2e/node_modules` 追加（コンテナ破棄後も `node_modules` を保持）。top-level `volumes` に `backend_logs:`・`e2e_node_modules:` 追加 |
| `.github/workflows/e2e.yml` | 新規 | E2E 独立 CI ジョブ。`docker compose up --wait` でサービス起動待機（手動ポーリング不要）。E2E_TEST_PASSWORD を GitHub Secrets から注入 |
| `.claude/skills/test/SKILL.md` | 変更 | E2E ステップ追加 |

---

## 6. テストデータ設計

### 6-1. 固定マスタデータ（`backend/fixtures/e2e_master.json`）
変更頻度が低いデータのみ fixture で管理：
- `OrganizationCategory`（例: `general`）

### 6-2. シナリオデータ（`manage.py seed_e2e --scenario <name>`）

| シナリオ名 | 作成されるデータ |
|-----------|----------------|
| `login` | Organization A、ユーザー A（email: `e2e_user_a@example.com`, pw: `$E2E_TEST_PASSWORD`） |
| `tenant_isolation` | Organization A + B、ユーザー A・B（pw: `$E2E_TEST_PASSWORD`）、Organization A の Subject 1件 |
| `quiz_session` | Organization A、ユーザー A（pw: `$E2E_TEST_PASSWORD`）、Subject + Problem（選択肢付き）数件（QuizSession はフロント操作で作成するため seed しない） |

> **認証情報の扱い**: パスワードはソースコードに一切ハードコードしない。`global-setup.ts` が `process.env.E2E_TEST_PASSWORD` を読み取り、`--password` 引数として seed コマンドに渡す。ローカル開発は `.env.e2e`（gitignore 済み）、CI は GitHub Actions Secrets から注入する。

### 6-3. 認証状態再利用
- Playwright の `storageState` を使用
- `globalSetup` でログイン → `e2e/.auth/user_a.json` / `user_b.json` に保存
- 各テストは `storageState` を読み込んでログイン UI をスキップ

---

## 7. 実装手順

> **依存関係**: Step 1〜3 は並行実施可能。Step 4 は Step 3 完了が前提。Step 5〜7 は Step 4 完了が前提。Step 8・9 は Step 7 完了後。

### Step 1: Docker 環境での Playwright 疎通確認（未知リスク先行）

**目的**: e2e コンテナから `frontend:3000` / `backend:8000` にアクセスできることを確認する（最大の未知リスク）。

1. `docker-compose.yml` に最小限の `e2e` サービスを追加:
   ```yaml
   e2e:
     image: mcr.microsoft.com/playwright:v1.50.0-jammy
     working_dir: /e2e
     volumes:
       - ./e2e:/e2e
     depends_on:
       - frontend
       - backend
     networks:
       - app-network
     environment:
       - BASE_URL=http://frontend:3000
       - API_URL=http://backend:8000
     profiles:
       - e2e
   ```
2. `docker compose --profile e2e run e2e curl http://frontend:3000` で疎通確認
3. 疎通確認 OK → Step 2 へ。NG → ネットワーク設定を調整してから進む

### Step 2: e2e/ ディレクトリ・設定ファイル整備

**目的**: Playwright プロジェクトの骨格を作る。

1. `e2e/package.json` 作成:
   ```json
   {
     "name": "e2e",
     "private": true,
     "scripts": {
       "test": "playwright test",
       "test:headed": "playwright test --headed"
     },
     "devDependencies": {
       "@playwright/test": "^1.50.0",
       "dotenv": "^16.0.0"
     }
   }
   ```
2. `e2e/playwright.config.ts` 作成:
   ```typescript
   import { defineConfig, devices } from '@playwright/test';
   import dotenv from 'dotenv';
   import path from 'path';

   // .env.e2e をローカル開発用に読み込む（CI では GitHub Secrets から直接 process.env に注入される）
   dotenv.config({ path: path.resolve(__dirname, '.env.e2e') });

   export default defineConfig({
     testDir: './tests',
     globalSetup: './global-setup.ts',  // storageState 生成をここで実行（DB 初期化は e2e-init サービスが担当）
     use: {
       baseURL: process.env.BASE_URL || 'http://localhost:3000',
       trace: 'on-first-retry',
     },
     retries: 2,
     projects: [
       // 認証済みユーザーAでのテスト（storageState を適用）
       {
         name: 'chromium-authed',
         use: {
           ...devices['Desktop Chrome'],
           storageState: path.join(__dirname, '.auth', 'user_a.json'),  // __dirname ベース: CI/コンテナ両方で正しく解決される
         },
         testMatch: /(?!.*auth\.spec).*\.spec\.ts/,  // auth.spec 以外に適用
       },
       // 認証不要テスト（auth.spec.ts のみ。storageState を適用しない）
       {
         name: 'chromium-unauthed',
         use: {
           ...devices['Desktop Chrome'],
           // storageState なし（未認証状態でログインテストを実行）
         },
         testMatch: /auth\.spec\.ts/,
       },
     ],
   });
   ```
   > **設計方針**: `globalSetup` のみで storageState を生成する。`setup` プロジェクトは使用しない（`globalSetup` との混在はエラーを招くため）。認証が必要なテスト（`auth.spec.ts` 以外）と不要なテストを別プロジェクトで分離する。
3. `e2e/.gitignore` 作成（`.auth/`・`.env.e2e` を除外）
4. `e2e/.env.e2e.example` 作成（git 管理。開発者はこれをコピーして `.env.e2e` を作成する）:
   ```
   # E2E テスト専用の認証情報。本番環境とは完全に分離されたテスト DB で使用する。
   # このファイルをコピーして .env.e2e を作成し、パスワードを設定してください。
   E2E_TEST_PASSWORD=<set-your-e2e-password-here>
   ```
5. `e2e/tests/` ディレクトリ作成

### Step 3: seed_e2e Django 管理コマンド実装

**目的**: シナリオ単位でテストデータを投入する管理コマンドを作る。パスワードはコードにハードコードせず `--password` 引数で受け取る。

1. `backend/accounts/management/__init__.py`・`commands/__init__.py`（存在しない場合のみ）確認
2. `backend/accounts/management/commands/seed_e2e.py` 作成:
   ```python
   from django.core.management.base import BaseCommand
   from django.contrib.auth import get_user_model
   from accounts.models import Organization, OrganizationCategory

   User = get_user_model()

   SCENARIOS = {
       'login': '_seed_login',
       'tenant_isolation': '_seed_tenant_isolation',
       'quiz_session': '_seed_quiz_session',
   }

   class Command(BaseCommand):
       help = 'Seed E2E test data by scenario'

       def add_arguments(self, parser):
           parser.add_argument('--scenario', required=True, choices=SCENARIOS.keys())
           parser.add_argument('--password', required=True, help='E2E test user password (do not hardcode; pass via env var)')
           parser.add_argument('--flush', action='store_true', help='Flush DB before seeding')

       def handle(self, *args, **options):
           self.e2e_password = options['password']  # 環境変数由来。コード内でリテラルを持たない

           if options['flush']:
               from django.core.management import call_command
               call_command('flush', '--no-input')
               call_command('loaddata', 'e2e_master.json')

           method = getattr(self, SCENARIOS[options['scenario']])
           method()
           self.stdout.write(self.style.SUCCESS(f"Seeded scenario: {options['scenario']}"))

       def _seed_login(self):
           cat, _ = OrganizationCategory.objects.get_or_create(name='general')
           org_a, _ = Organization.objects.get_or_create(
               slug='e2e-org-a', defaults={'name': 'E2E Org A', 'category': cat}
           )
           User.objects.filter(email='e2e_user_a@example.com').delete()
           User.objects.create_user(
               email='e2e_user_a@example.com',
               user_id='e2e_user_a',
               password=self.e2e_password,
               organization=org_a,
           )

       def _seed_tenant_isolation(self):
           self._seed_login()
           cat = OrganizationCategory.objects.get(name='general')
           org_b, _ = Organization.objects.get_or_create(
               slug='e2e-org-b', defaults={'name': 'E2E Org B', 'category': cat}
           )
           User.objects.filter(email='e2e_user_b@example.com').delete()
           User.objects.create_user(
               email='e2e_user_b@example.com',
               user_id='e2e_user_b',
               password=self.e2e_password,
               organization=org_b,
           )
           from problems.models import Subject
           Subject.objects.get_or_create(
               name='E2E Subject A',
               defaults={'organization': Organization.objects.get(slug='e2e-org-a')}
           )

       def _seed_quiz_session(self):
           self._seed_login()
           from problems.models import Subject, Problem
           org_a = Organization.objects.get(slug='e2e-org-a')
           subj, _ = Subject.objects.get_or_create(
               name='E2E Quiz Subject', defaults={'organization': org_a}
           )
           problem, _ = Problem.objects.get_or_create(
               subject=subj,
               question_text='E2E test question?',
               defaults={
                   'problem_type': 'choice',
                   'explanation': 'E2E explanation',
               }
           )
           # 選択肢がないと quiz-session.spec.ts の [data-testid="choice-option"] クリックが失敗する
           # Choice モデルの正確なフィールドは problems/models.py を確認して補完
   ```
   > **注意**: `--password` 引数に渡す値は `global-setup.ts` が `process.env.E2E_TEST_PASSWORD` から取得して渡す。seed コマンド単体をローカルで呼ぶ場合は `--password $E2E_TEST_PASSWORD` のように明示する。
3. `backend/fixtures/e2e_master.json` 作成（`OrganizationCategory` の `general` レコード）

### Step 4: globalSetup 実装

**目的**: E2E 実行前に認証状態（storageState）を生成する。DB 初期化（migrate・seed）は `e2e-init` サービス（Init Container パターン）が担うため、globalSetup はブラウザログイン操作のみを行う。パスワードは `process.env.E2E_TEST_PASSWORD` から取得する。

> **Init Container パターンの採用理由**: Playwright コンテナ（`mcr.microsoft.com/playwright`）には `docker` CLI が存在しないため、globalSetup 内で `docker compose exec` を呼ぶことができない（`ENOENT: No such file or directory, docker`）。Docker socket をマウント（DooD: Docker-outside-of-Docker）する方法はコンテナにホスト root 相当の権限を与えるセキュリティリスクがあり採用しない。代わりに `e2e-init` 専用サービス（backend イメージ）を docker-compose.yml で定義し、migrate・loaddata・seed を実行させる。`e2e` サービスは `depends_on: e2e-init: condition: service_completed_successfully` で完了を待つ。これにより globalSetup はブラウザ操作のみに集中できる（単一責任の原則）。

`e2e/global-setup.ts` 作成:
```typescript
import { chromium, FullConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const AUTH_DIR = path.join(__dirname, '.auth');  // __dirname ベース: CI/コンテナ両方で正しく解決

async function globalSetup(_config: FullConfig) {
  // E2E_TEST_PASSWORD は playwright.config.ts で dotenv.config() により .env.e2e から読み込まれる
  // CI では GitHub Actions Secrets から直接 process.env に注入される
  const e2ePassword = process.env.E2E_TEST_PASSWORD;
  if (!e2ePassword) {
    throw new Error(
      'E2E_TEST_PASSWORD is not set. ' +
      'For local dev: copy e2e/.env.e2e.example to e2e/.env.e2e and set the password. ' +
      'For CI: add E2E_TEST_PASSWORD to GitHub Actions Secrets.'
    );
  }

  // DB 初期化（migrate・loaddata・seed_e2e）は e2e-init サービス（docker-compose.yml）が実行済み
  // globalSetup はブラウザログイン操作と storageState 生成のみを担う

  // storageState 生成（ユーザーA・ユーザーB）
  fs.mkdirSync(AUTH_DIR, { recursive: true });
  const browser = await chromium.launch();

  const users = [
    { email: 'e2e_user_a@example.com', file: path.join(AUTH_DIR, 'user_a.json') },
    { email: 'e2e_user_b@example.com', file: path.join(AUTH_DIR, 'user_b.json') },
  ];

  for (const user of users) {
    const page = await browser.newPage();
    await page.goto(`${BASE_URL}/login`);
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', e2ePassword);  // env var から取得
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
    await page.context().storageState({ path: user.file });
    await page.close();
  }

  await browser.close();
  console.log('[globalSetup] Done.');
}

export default globalSetup;
```

> **`E2E_TEST_PASSWORD` が未設定の場合**: `globalSetup` が明確なエラーメッセージで即停止する（サイレント失敗を防ぐ）。

### Step 5: ログイン／ログアウト E2E テスト実装

`e2e/tests/auth.spec.ts` 作成:
```typescript
import { test, expect } from '@playwright/test';
import * as path from 'path';

// 未認証状態でのテスト（chromium-unauthed プロジェクトで実行）
test.describe('ログインフロー（未認証）', () => {
  test('正しい認証情報でログインしてダッシュボードに遷移する', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
    await page.fill('[data-testid="password-input"]', process.env.E2E_TEST_PASSWORD || '');  // 環境変数から取得。ハードコード禁止
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL(/dashboard/);
  });

  test('誤ったパスワードでログインが拒否される', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
    await page.fill('[data-testid="password-input"]', 'WrongPassword999!');
    await page.click('[data-testid="login-button"]');
    // エラーは react-toastify のトースト通知として表示される
    await expect(page.locator('.Toastify__toast--error')).toBeVisible();
    await expect(page).toHaveURL(/login/);
  });
});

// 認証済み状態でのテスト（test.use でプロジェクト設定を上書き）
test.describe('ログアウトフロー（認証済み）', () => {
  test.use({ storageState: path.join(__dirname, '..', '.auth', 'user_a.json') });  // tests/ からの相対パス

  test('ログアウト後にログイン画面に戻る', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="user-menu-button"]');  // メニューを開いてからログアウトボタンを押す
    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL(/login/);
  });
});
```
> **設計方針**: `auth.spec.ts` は `chromium-unauthed` プロジェクト（storageState なし）で実行されるが、ログアウトテストのみ `test.use({ storageState: '...' })` でファイル内から上書きする。Playwright では `test.use` をネストした `describe` 内に記述することでプロジェクト設定を部分的に上書きできる。

### Step 6: テナント間データ分離 E2E テスト実装

`e2e/tests/tenant-isolation.spec.ts` 作成:
```typescript
import { test, expect, Browser } from '@playwright/test';
import * as path from 'path';

const authDir = path.join(__dirname, '..', '.auth');  // tests/ からの相対パス

test.describe('テナント間データ分離', () => {
  test('Organization A のデータが Organization B ユーザーから見えない', async ({ browser }) => {
    // User A: Organization A の Subject が見える
    const ctxA = await browser.newContext({ storageState: path.join(authDir, 'user_a.json') });
    const pageA = await ctxA.newPage();
    await pageA.goto('/subjects');
    await expect(pageA.locator('text=E2E Subject A')).toBeVisible();
    await ctxA.close();

    // User B: Organization A の Subject が見えない
    const ctxB = await browser.newContext({ storageState: path.join(authDir, 'user_b.json') });
    const pageB = await ctxB.newPage();
    await pageB.goto('/subjects');
    await expect(pageB.locator('text=E2E Subject A')).not.toBeVisible();
    await ctxB.close();
  });
});
```

### Step 7: クイズ閲覧〜回答 E2E テスト実装

`e2e/tests/quiz-session.spec.ts` 作成:
```typescript
import { test, expect } from '@playwright/test';

test.describe('クイズセッション', () => {
  test('科目を選択してクイズに回答できる', async ({ page }) => {
    await page.goto('/subjects');
    await page.click('text=E2E Quiz Subject');
    // クイズ開始ボタンを押す
    await page.click('[data-testid="start-quiz-button"]');
    await expect(page).toHaveURL(/quiz/);
    // 選択肢をクリックして回答送信
    await page.click('[data-testid="choice-option"]');
    // 結果表示確認
    await expect(page.locator('[data-testid="answer-result"]')).toBeVisible();
  });
});
```

### Step 8: Docker ヘルスチェック・CI GitHub Actions 独立ジョブ追加

#### 8-1: `/health/` エンドポイント追加 + `HealthCheckMiddleware` 削除

**`backend/core/urls.py`** に DB のみ確認するシンプルな readiness check を追加する:

```python
from django.db import connection
from django.http import JsonResponse

def health(request):
    """Readiness check: DB 接続を検証してサービス準備完了を示す"""
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'error'}, status=503)

# urlpatterns の先頭に追加:
path('health/', health, name='health'),
```

**`backend/core/settings.py`** の `MIDDLEWARE` から `HealthCheckMiddleware` を削除する:

```python
# 削除する行:
# 'core.middleware.HealthCheckMiddleware',
```

> **設計方針**: `HealthCheckMiddleware` は `process_request` で `/health/` を横取りし `PerformanceMonitor.get_comprehensive_health_check()` を呼ぶ。これは (1) URL ルーティングをバイパスするアンチパターン（ミドルウェアの責務は横断的関心事であり特定 URL のビジネスロジックではない）、(2) 認証なしで DB 接続数・Redis エラーメッセージ・システムリソース情報を公開するセキュリティリスク（OWASP: Sensitive Data Exposure）、(3) Redis エラー時に 503 を返し Docker compose healthcheck が常に失敗する、の 3 点から削除する。詳細な監視情報は認証保護された `/monitoring/status/` 等で提供するのが正しい設計。

#### 8-2: curl インストール（`backend/Dockerfile` と `frontend/Dockerfile.dev`）

```dockerfile
# backend/Dockerfile（既存 RUN apt-get ... の後に追記、または既存行に追加）
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# frontend/Dockerfile.dev（同様）
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
```

#### 8-3: `docker-compose.yml` にヘルスチェック・depends_on 条件追加

```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s

backend:
  volumes:
    - ./backend:/app
    - ./docs:/app/docs
    - backend_static:/app/staticfiles
    - backend_logs:/app/logs   # named volume: bind mount では django ユーザーが /app/logs を作成できないため
  depends_on:
    db:
      condition: service_healthy   # Postgres 接続受付後にのみ起動（migrate の前提）
    redis:
      condition: service_started
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
    interval: 10s
    timeout: 10s
    retries: 18       # 最大 3 分
    start_period: 60s # migrate + 起動猶予

frontend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/"]
    interval: 10s
    timeout: 5s
    retries: 18
    start_period: 60s

e2e-init:
  build:
    context: ./backend
    dockerfile: Dockerfile
  env_file:
    - path: ./backend/.env
      required: false
  environment:
    - DB_HOST=db
    - REDIS_URL=redis://redis:6379/0
    - E2E_TEST_PASSWORD=${E2E_TEST_PASSWORD}
  volumes:
    - ./backend:/app
  depends_on:
    backend:
      condition: service_healthy   # backend（migrate 完了）が healthy になってから実行
  networks:
    - app-network
  profiles:
    - e2e
  command: >
    sh -c "[ -z \"$$E2E_TEST_PASSWORD\" ] && echo 'E2E_TEST_PASSWORD is not set.' >&2 && exit 1;
           python manage.py migrate --noinput &&
           python manage.py loaddata e2e_master.json &&
           python manage.py seed_e2e --scenario tenant_isolation --password $$E2E_TEST_PASSWORD &&
           python manage.py seed_e2e --scenario quiz_session --password $$E2E_TEST_PASSWORD"
  # $$E2E_TEST_PASSWORD: docker-compose.yml 内でシェル変数展開を防ぐため $$ でエスケープ
  # [ -z ... ] チェック: global-setup.ts より先に実行されるため、ここでもフェイルファストを行う

e2e:
  volumes:
    - ./e2e:/e2e
    - e2e_node_modules:/e2e/node_modules   # named volume: --rm でコンテナが消えても node_modules を保持
  depends_on:
    e2e-init:
      condition: service_completed_successfully   # Init Container 完了後に実行
  command: sh -c "npm install && npm test"  # npm install: named volume キャッシュを活かし差分のみ更新（2回目以降は数秒）。CI では e2e.yml が npm ci を使い決定論的インストールを保証

volumes:
  backend_logs:   # named volume: image の /app/logs ディレクトリの所有権（django ユーザー）を引き継ぐ
  e2e_node_modules:   # named volume: Playwright Docker イメージ（Linux）向けに npm install でインストールした node_modules を保持
```

> **設計方針**: `db` に `pg_isready` ヘルスチェックを追加し、`backend.depends_on` に `condition: service_healthy` を設定することで、Postgres 初期化完了前に `migrate` が実行されるレースコンディションを根本解消する。`condition: service_started`（旧来の depends_on）ではコンテナ起動のみを待つため不十分。
>
> **Init Container パターン（`e2e-init` サービス）**: Playwright コンテナには Docker CLI が存在しないため、`global-setup.ts` 内で `docker compose exec` による DB 初期化は不可能。`e2e-init` サービスは backend イメージを再利用して `migrate`・`loaddata`・`seed_e2e` を実行し、完了後に終了（exit 0）する。`e2e` サービスは `condition: service_completed_successfully` で `e2e-init` の正常完了を待ってからテストを実行する。これにより `global-setup.ts` はブラウザ操作のみに集中でき、Docker socket マウント（セキュリティリスク）や追加のシェルスクリプトが不要になる。
>
> **`backend_logs` named volume の必要性**: `./backend:/app` の bind mount は CI チェックアウトのルート所有権（UID 1001）で `/app` をオーバーライドする。`backend/logs/` は `.gitignore` 対象のため CI に存在せず、`enhanced_logging.py` が settings インポート時に `LOG_DIR.mkdir(exist_ok=True)` を呼ぶと `PermissionError: [Errno 13] Permission denied: '/app/logs'` が発生する。`.gitkeep` での回避は「ディレクトリは存在するが CI ランナー所有のため django が書き込めない」状態を生み出すため不十分。Named volume は初回マウント時に image の `/app/logs` ディレクトリ（django 所有）をコピーするため、書き込み権限が正しく維持される。
>
> **`e2e_node_modules` named volume の必要性**: `./e2e:/e2e` bind mount で `node_modules` を host と共有すると、host の OS（例: Windows/Mac）向けにコンパイルされた native addon やバイナリが Linux コンテナでは動作しない。Named volume に分離することで Linux 向けの正しい `node_modules` が保持される。`npm install` は既存 `node_modules` を保持したまま差分のみ更新するため、named volume との組み合わせで 2 回目以降は数秒で完了する（`npm ci` は毎回 `node_modules` を削除して全インストールするため named volume のキャッシュ効果がない）。CI（`e2e.yml`）では `npm ci` を使い決定論的・クリーンなインストールを保証する。`e2e` サービスの `command` に `npm install && npm test` を設定し、`docker compose --profile e2e run --rm e2e` だけで依存インストール＋テスト実行が完結する。

#### 8-4: `.github/workflows/e2e.yml` 新規作成

`docker compose up --wait` でサービスが healthy になるまでブロックするため、手動ポーリングステップは不要：

```yaml
name: E2E Tests

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  e2e:
    name: E2E Tests (Playwright)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start services and wait for healthy
        run: docker compose up -d --wait db backend frontend
        timeout-minutes: 5

      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: e2e/package-lock.json

      - name: Install Playwright dependencies
        run: npm ci && npx playwright install --with-deps chromium
        working-directory: e2e

      - name: Run E2E tests
        run: npm test
        working-directory: e2e
        env:
          BASE_URL: http://localhost:3000
          API_URL: http://localhost:8000
          E2E_TEST_PASSWORD: ${{ secrets.E2E_TEST_PASSWORD }}

      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: e2e/playwright-report/
          retention-days: 7
```

> **設計方針**: `--wait` は docker-compose.yml の `healthcheck` が通過するまでブロックする。マジックナンバーのタイムアウトによる手動ポーリングより信頼性が高く、ヘルスチェックの定義がサービス側（compose ファイル）に集約される。`/health/` エンドポイントは DB 接続を検証するため、「サーバーは起動しているが migrate が完了していない」状態も検出できる。

### Step 9: `/test` スキル更新

`.claude/skills/test/SKILL.md` に E2E ステップを追記:

現在の手順 2) の後（手順 3) の前）に以下を追加。既存の手順 3)・4) は番号をシフト（3→4、4→5）:
```
3) E2E テスト（Playwright）:
   ```bash
   docker compose --profile e2e run --rm e2e npm test
   ```
   - 成功: 手順 4) へ
   - 失敗: 即 STOP。以下を報告してユーザー待機:
     - 失敗したテスト名（spec ファイル名・テスト名）
     - エラー内容（期待値 / 実際値 / スクリーンショットパス）
     ```
     ⛔ E2E テストが失敗しました。修正作業は開始しません。
     👉 続けるには `/fix-loop $ARGUMENTS` を入力してください。
        fix-loop 完了後は `/test $ARGUMENTS` に戻ってください。
     ```
```

---

## 8. テスト計画

### テストレベルの選択
- **E2E（本イシュー対象）**: クリティカルパス3本のみ（ログイン・データ分離・クイズ）
- **ユニット/結合（既存）**: seed コマンドの動作は pytest で検証しない（E2E 実行で間接的に確認）

### 自動テスト（E2E 本体）
- `auth.spec.ts`: ログイン成功・ログアウト・ログイン失敗
- `tenant-isolation.spec.ts`: データ分離確認
- `quiz-session.spec.ts`: クイズ閲覧〜回答

### 手動テスト
- `docker compose --profile e2e run e2e npm test` の実行と全テスト PASS 確認
- CI（GitHub Actions）E2E ジョブが独立して動作することの確認

---

## 9. ロールバック

- ロールバック手順:
  1. `e2e/` ディレクトリを削除
  2. `docker-compose.yml` の `e2e` サービスを削除、**`e2e-init` サービスを削除**、`db` の `healthcheck` を削除、`backend`/`celery`/`celery-beat` の `depends_on` を `service_started`（旧来の記法）に戻す、`env_file` の `required: false` を削除、`backend` の `volumes` から `backend_logs:/app/logs` を削除、top-level `volumes` から `backend_logs:`・`e2e_node_modules:` を削除。named volume 本体を削除する場合は `docker volume rm <project>_backend_logs <project>_e2e_node_modules` を実行する
  3. `.github/workflows/e2e.yml` を削除
  4. `backend/accounts/management/commands/seed_e2e.py` を削除
  5. `backend/core/urls.py` の `/health/` エンドポイントを削除
  5a. `backend/core/settings.py` の `MIDDLEWARE` に `'core.middleware.HealthCheckMiddleware',` を復元
  6. `backend/Dockerfile` と `frontend/Dockerfile.dev` から `curl` のインストール行を削除
  7. `.claude/skills/test/SKILL.md` のE2Eステップを削除
  8. ブランチを revert

---

## 10. Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| Docker e2e コンテナから frontend にアクセスできない | Step 1 でブロック | Step 1 を先行実施し、疎通確認後に進む |
| Login UI の `data-testid` 属性が存在しない | テスト全般がブロック | Step 4 実施前にログイン画面の HTML 確認、必要に応じて data-testid を追加（計画変更を提案） |
| seed_e2e コマンドで Subject モデルのフィールドが不足 | Step 3 でエラー | Subject モデルの必須フィールドを事前確認（調査済み: organization FK が必須） |
| CI の E2E が既存ジョブをブロック | PR マージに影響 | 独立ジョブ（別 workflow）にし、既存 ci.yml には触れない |
| E2E テストがフレーキー（非決定的失敗） | CI 信頼性低下 | retry: 2、trace: on-first-retry 設定、テスト間の状態分離（beforeEach で必要に応じて状態リセット） |
| CI に `backend/.env` が存在しないため `docker compose up` が失敗する | E2E CI ジョブ全体がブロック | `docker-compose.yml` の `env_file` を `required: false` に変更（根本対処）。CI ワークフロー側の補完ステップは不要。`settings.py` の全変数にデフォルト値があるため動作に問題なし |
| バックエンド起動タイムアウト（migrate 完了前にヘルスチェックが失敗） | E2E CI ジョブ全体がブロック | `healthcheck` に `start_period: 60s` を設定し起動猶予を確保。`/health/` エンドポイントが DB 接続を検証するため migrate 完了後にのみ healthy となる |
| コンテナに `curl` が存在せずヘルスチェックが常に unhealthy | E2E CI がハング | Dockerfile に `curl` をインストール（`apt-get install -y --no-install-recommends curl`）。Python/Node の回避策は使わない |
| Postgres 初期化完了前に `migrate` が実行されるレースコンディション（`depends_on: db` は `service_started` であり、DB がまだ接続を受け付けていない段階で backend が起動し migrate に失敗する） | backend コンテナが exit code 1 で終了し `--wait` も失敗 | `db` に `pg_isready` ヘルスチェックを追加し、`backend.depends_on` に `condition: service_healthy` を設定。Postgres が接続受付可能になるまで backend の起動を保留する（根本対処） |
| bind mount で `/app/logs` が `django` ユーザーのパーミッションで作成できない（`enhanced_logging.py` が settings インポート時に `LOG_DIR.mkdir()` を呼ぶが、CI では `/app/logs` が存在せず、ランナー所有の `/app` 配下に `django` ユーザーが mkdir できない） | `PermissionError: [Errno 13] Permission denied: '/app/logs'` で backend が起動失敗し `--wait` がタイムアウト | `backend_logs:/app/logs` named volume を使用。Named volume は初回マウント時に image の `/app/logs`（django 所有）をコピーするため書き込み権限が正しく維持される。`.gitkeep` は回避策にならない（CI ランナー所有のディレクトリになり django が書き込めない） |
| `HealthCheckMiddleware` が `/health/` を横取りし `PerformanceMonitor` の複雑な応答を返す | URL ルーティングで追加した `health()` 関数が呼ばれず、Redis エラー時に 503 が返るため Docker compose healthcheck が常に失敗する | `MIDDLEWARE` から `HealthCheckMiddleware` を削除し、`urls.py` の `health()` 関数が直接処理するよう修正。詳細監視は認証保護された `/monitoring/status/` で提供 |
| `e2e/node_modules` が存在しないため `playwright: not found` が発生し E2E テストが実行できない | `docker compose --profile e2e run --rm e2e npm test` が即座に失敗する | `e2e_node_modules` named volume を追加し `e2e` サービスの command を `npm install && npm test` に変更。`npm install` は named volume のキャッシュを活かして差分のみ更新（2回目以降は数秒）。CI では `e2e.yml` で `npm ci` を使い決定論的インストールを保証 |
| Playwright コンテナに `docker` CLI が存在しないため `global-setup.ts` 内で `docker compose exec` による DB 初期化が不可能（`ENOENT: docker`）。Docker socket マウント（DooD）はホスト root 相当の権限を与えるセキュリティリスク | DB が初期化されないまま全テストが失敗する | **Init Container パターン** を採用。`e2e-init` サービス（backend イメージ）で migrate・loaddata・seed_e2e を実行し、`e2e` サービスは `condition: service_completed_successfully` で完了を待つ。`global-setup.ts` はブラウザ操作のみに限定し Docker CLI への依存を排除する |

---

## 11. セキュリティ

- **E2E テスト用パスワードはソースコードに一切ハードコードしない**（12-Factor App・OWASP 準拠）
  - ローカル開発: `e2e/.env.e2e`（gitignore 済み）に `E2E_TEST_PASSWORD=<値>` を記載
  - CI: GitHub Actions Secrets に `E2E_TEST_PASSWORD` を登録し、`e2e.yml` から注入
  - `E2E_TEST_PASSWORD` 未設定時は `globalSetup` が明確なエラーで即停止（サイレント失敗を防ぐ）
- `e2e/.env.e2e` は `.gitignore` 対象にする。テンプレートとして `e2e/.env.e2e.example` を git 管理する
- デフォルト DB (`learning_app`) を使用し、別 DB の作成は行わない。CI ではクリーンな Docker volume から起動するため本番データとは完全分離。ローカルでは同一 DB に `e2e_` プレフィックス付きデータが混在するが、`seed_e2e` の冪等設計（get_or_create / delete→create）で整合性を維持する（別 DB 管理は docker-compose の init-db.sql 変更・手動 DB 作成等のコストが高く、プレフィックス識別で十分なため採用しない）
- seed コマンドで作成するデータは `e2e_` プレフィックスを持つため本番データと識別可能
- npm audit: Playwright 公式パッケージのみ使用。高/クリティカル脆弱性があれば修正対象
- **Docker socket マウント（DooD）不採用**: `global-setup.ts` が直接 `docker compose exec` を呼ぶ設計は Playwright コンテナに `/var/run/docker.sock` をマウントする必要があり、コンテナにホスト root 相当の権限を与えるセキュリティリスクがある。代わりに Init Container パターン（`e2e-init` サービス）を採用し、`global-setup.ts` からの Docker CLI 依存を完全に排除する
- **`HealthCheckMiddleware` の削除**: 既存の `HealthCheckMiddleware` は認証なしで DB 接続数・Redis エラー詳細・システムリソース（CPU/メモリ）を公開しており、OWASP Security Misconfiguration / Sensitive Data Exposure に該当する。`/health/` は DB 接続確認のみ返す最小応答に限定する。詳細監視情報は `/monitoring/status/` 等（別途認証保護が必要）で提供するのが正しい設計

---

## 12. コスト・保守見積もり

| 項目 | 見積もり |
|------|---------|
| E2E テスト実行時間（ローカル） | 約 60〜120 秒（chromium のみ） |
| CI 追加時間 | 約 3〜5 分（既存 CI と並列実行のため影響は最小） |
| 保守コスト | UI 変更時に `data-testid` の維持が必要。テスト本数が少ないため低コスト |
| 属人化リスク | Playwright は公式ドキュメントが充実しており低い |

---

## 13. 設計判断の明示

以下の設計判断は **仮定で決めた** 項目です（承認ポイントで確認）:

| 判断項目 | 内容 | 根拠 |
|---------|------|------|
| e2e/ 配置場所 | プロジェクトルート（`frontend/` 外） | Playwright ベストプラクティス。frontend の依存と分離できる |
| テスト用 DB 名 | `learning_app_e2e` | 本番 DB `learning_app` との混同を防ぐ命名 |
| Playwright ブラウザ | chromium のみ | CI 実行時間を最小化するため。クロスブラウザは本イシュースコープ外 |
| storageState 保存先 | `e2e/.auth/user_a.json` / `user_b.json` | Playwright 公式推奨パターン |
| data-testid 追加 | 必要に応じて Login 画面に追加 | E2E テストの安定性のため。ただし Frontend コード変更が発生するため別途確認が必要 |
| E2E CI workflow | 既存 `ci.yml` と分離した `e2e.yml` を新規作成 | 既存の高速 CI をブロックしない |

---

## 承認ポイント

以下をご確認の上、「OK」とお答えください。

### 確認項目

- [ ] **e2e/ 配置**: プロジェクトルートに `e2e/` ディレクトリを作る（`frontend/` の外）
- [ ] **テスト用 DB**: `learning_app_e2e` を別 DB として作成（`.env.e2e` で管理）
- [ ] **ブラウザ**: chromium のみ（Firefox/WebKit は対象外）
- [ ] **data-testid の追加**: ログイン画面に `data-testid="email-input"` 等を追加する可能性がある（Login.tsx への変更が発生）
- [ ] **CI**: `.github/workflows/e2e.yml` を新規作成（既存 `ci.yml` は変更しない）
- [ ] **seed コマンドのテストデータ**: `e2e_user_a@example.com` / `e2e_user_b@example.com` を使用。パスワードは `E2E_TEST_PASSWORD` 環境変数から注入（ソースコードにハードコードしない）
- [ ] **ステップ順序**: Step 1（疎通確認）→ Step 2〜3（並行可）→ Step 4（globalSetup）→ Step 5〜7（テスト）→ Step 8〜9（CI・スキル）

### セキュリティ確認
- [ ] テスト用パスワードはソースコードにハードコードせず、`E2E_TEST_PASSWORD` 環境変数から注入する
- [ ] ローカル開発は `e2e/.env.e2e`（gitignore 済み）、CI は GitHub Actions Secrets から注入する
- [ ] `E2E_TEST_PASSWORD` 未設定時に globalSetup が明確なエラーで停止することを確認する

### 要件適合性確認
- P3/P5/P8（データ整合性・運用性）: **E2E テスト基盤の追加のみ。既存 DB スキーマ変更なし。影響なし**
- P6（性能・UX）: **フロントエンドの UI ロジック変更なし。data-testid 追加のみの場合あり**
