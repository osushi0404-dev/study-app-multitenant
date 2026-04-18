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
- **DB**: E2E 専用 DB `learning_app_e2e`（`.env.e2e` で設定）
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
| `docker-compose.yml` | 変更 | `e2e` サービス追加。`backend`・`celery`・`celery-beat` の `env_file` を `required: false` に変更（CI で `.env` が不在でも動作するよう根本対処） |
| `.github/workflows/e2e.yml` | 新規 | E2E 独立 CI ジョブ（E2E_TEST_PASSWORD を GitHub Secrets から注入） |
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
     globalSetup: './global-setup.ts',  // DB 初期化・seed・storageState 生成をここで実行
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
           storageState: 'e2e/.auth/user_a.json',
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

**目的**: E2E 実行前に DB を初期化し、認証状態を生成する。パスワードは `process.env.E2E_TEST_PASSWORD` から取得し、seed コマンドに `--password` 引数として渡す。

`e2e/global-setup.ts` 作成:
```typescript
import { chromium, FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import * as fs from 'fs';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

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

  // 1. DB 初期化・migrate・fixture 投入・seed
  console.log('[globalSetup] Running migrations and seeding...');
  execSync('docker compose exec -T backend python manage.py migrate --noinput', { stdio: 'inherit' });
  execSync('docker compose exec -T backend python manage.py loaddata e2e_master.json', { stdio: 'inherit' });
  execSync(
    `docker compose exec -T backend python manage.py seed_e2e --scenario tenant_isolation --password "${e2ePassword}"`,
    { stdio: 'inherit' },
  );
  execSync(
    `docker compose exec -T backend python manage.py seed_e2e --scenario quiz_session --password "${e2ePassword}"`,
    { stdio: 'inherit' },
  );

  // 2. storageState 生成（ユーザーA・ユーザーB）
  fs.mkdirSync('e2e/.auth', { recursive: true });
  const browser = await chromium.launch();

  const users = [
    { email: 'e2e_user_a@example.com', file: 'e2e/.auth/user_a.json' },
    { email: 'e2e_user_b@example.com', file: 'e2e/.auth/user_b.json' },
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

> **注意**: globalSetup 内の `docker compose exec` は、E2E をホストから実行する場合の記述。Docker 内実行の場合は直接 `python manage.py` を呼び出す形に調整する。`E2E_TEST_PASSWORD` が未設定の場合は明確なエラーメッセージで即停止する（サイレント失敗を防ぐ）。

### Step 5: ログイン／ログアウト E2E テスト実装

`e2e/tests/auth.spec.ts` 作成:
```typescript
import { test, expect } from '@playwright/test';

// 未認証状態でのテスト（chromium-unauthed プロジェクトで実行）
test.describe('ログインフロー（未認証）', () => {
  test('正しい認証情報でログインしてダッシュボードに遷移する', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
    await page.fill('[data-testid="password-input"]', 'E2ePassword1!');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL(/dashboard/);
  });

  test('誤ったパスワードでログインが拒否される', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
    await page.fill('[data-testid="password-input"]', 'WrongPassword!');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
  });
});

// 認証済み状態でのテスト（test.use でプロジェクト設定を上書き）
test.describe('ログアウトフロー（認証済み）', () => {
  test.use({ storageState: 'e2e/.auth/user_a.json' });

  test('ログアウト後にログイン画面に戻る', async ({ page }) => {
    await page.goto('/dashboard');
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

test.describe('テナント間データ分離', () => {
  test('Organization A のデータが Organization B ユーザーから見えない', async ({ browser }) => {
    // User A: Organization A の Subject が見える
    const ctxA = await browser.newContext({ storageState: 'e2e/.auth/user_a.json' });
    const pageA = await ctxA.newPage();
    await pageA.goto('/subjects');
    await expect(pageA.locator('text=E2E Subject A')).toBeVisible();
    await ctxA.close();

    // User B: Organization A の Subject が見えない
    const ctxB = await browser.newContext({ storageState: 'e2e/.auth/user_b.json' });
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

### Step 8: CI GitHub Actions 独立ジョブ追加

`.github/workflows/e2e.yml` 新規作成:
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
      - name: Start services
        run: docker compose up -d db backend frontend
      - name: Wait for frontend to be ready
        run: |
          timeout 60 sh -c 'until curl -s http://localhost:3000 > /dev/null; do sleep 2; done'
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
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
```

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

- 本イシューの変更は全て**追加のみ**（既存ファイルへの変更は `/test` スキルのみ）
- ロールバック手順:
  1. `e2e/` ディレクトリを削除
  2. `docker-compose.yml` の `e2e` サービスを削除
  3. `.github/workflows/e2e.yml` を削除
  4. `backend/accounts/management/commands/seed_e2e.py` を削除
  5. `.claude/skills/test/SKILL.md` のE2Eステップを削除
  6. ブランチを revert

---

## 10. Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| Docker e2e コンテナから frontend にアクセスできない | Step 1 でブロック | Step 1 を先行実施し、疎通確認後に進む |
| Login UI の `data-testid` 属性が存在しない | テスト全般がブロック | Step 4 実施前にログイン画面の HTML 確認、必要に応じて data-testid を追加（計画変更を提案） |
| seed_e2e コマンドで Subject モデルのフィールドが不足 | Step 3 でエラー | Subject モデルの必須フィールドを事前確認（調査済み: organization FK が必須） |
| CI の E2E が既存ジョブをブロック | PR マージに影響 | 独立ジョブ（別 workflow）にし、既存 ci.yml には触れない |
| E2E テストがフレーキー（非決定的失敗） | CI 信頼性低下 | retry: 2、trace: on-first-retry 設定、テスト間の状態分離（beforeEach で必要に応じて状態リセット） |
| CI に `backend/.env` が存在しないため `docker compose up` が失敗する | E2E CI ジョブ全体がブロック | `docker-compose.yml` の `env_file` を `required: false` に変更（根本対処）。CI ワークフロー側の補完ステップは不要になる。`settings.py` の全変数にデフォルト値があるため動作に問題なし |

---

## 11. セキュリティ

- **E2E テスト用パスワードはソースコードに一切ハードコードしない**（12-Factor App・OWASP 準拠）
  - ローカル開発: `e2e/.env.e2e`（gitignore 済み）に `E2E_TEST_PASSWORD=<値>` を記載
  - CI: GitHub Actions Secrets に `E2E_TEST_PASSWORD` を登録し、`e2e.yml` から注入
  - `E2E_TEST_PASSWORD` 未設定時は `globalSetup` が明確なエラーで即停止（サイレント失敗を防ぐ）
- `e2e/.env.e2e` は `.gitignore` 対象にする。テンプレートとして `e2e/.env.e2e.example` を git 管理する
- E2E 専用 DB 名 (`learning_app_e2e`) を `.env.e2e` で管理し、本番 DB (`learning_app`) とは別インスタンス
- seed コマンドで作成するデータは `e2e_` プレフィックスを持つため本番データとの混在を防ぐ
- npm audit: Playwright 公式パッケージのみ使用。高/クリティカル脆弱性があれば修正対象

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
