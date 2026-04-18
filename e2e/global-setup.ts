import { chromium, FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import * as fs from 'fs';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

async function globalSetup(_config: FullConfig) {
  // E2E_TEST_PASSWORD は playwright.config.ts で dotenv.config() により .env.e2e から読み込まれる。
  // CI では GitHub Actions Secrets から直接 process.env に注入される。
  const e2ePassword = process.env.E2E_TEST_PASSWORD;
  if (!e2ePassword) {
    throw new Error(
      'E2E_TEST_PASSWORD is not set. ' +
      'For local dev: copy e2e/.env.e2e.example to e2e/.env.e2e and set the password. ' +
      'For CI: add E2E_TEST_PASSWORD to GitHub Actions Secrets.',
    );
  }

  // 1. DB 初期化・migrate・fixture 投入・seed
  console.log('[globalSetup] Running migrations and seeding...');
  execSync(
    'docker compose exec -T backend python manage.py migrate --noinput',
    { stdio: 'inherit' },
  );
  execSync(
    'docker compose exec -T backend python manage.py loaddata e2e_master.json',
    { stdio: 'inherit' },
  );
  execSync(
    `docker compose exec -T backend python manage.py seed_e2e --scenario tenant_isolation --password "${e2ePassword}"`,
    { stdio: 'inherit' },
  );
  execSync(
    `docker compose exec -T backend python manage.py seed_e2e --scenario quiz_session --password "${e2ePassword}"`,
    { stdio: 'inherit' },
  );

  // 2. storageState 生成（ユーザー A・ユーザー B）
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
    await page.fill('[data-testid="password-input"]', e2ePassword);
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('**/dashboard');
    await page.context().storageState({ path: user.file });
    await page.close();
  }

  await browser.close();
  console.log('[globalSetup] Done.');
}

export default globalSetup;
