import { chromium, FullConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
// __dirname ベースのパス: CI (working-directory: e2e) とコンテナ (working_dir: /e2e) 両方で正しく解決される
const AUTH_DIR = path.join(__dirname, '.auth');

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

  // DB 初期化（migrate・loaddata・seed_e2e）は docker-compose.yml の e2e-init サービス（Init Container）が担当。
  // globalSetup はブラウザログイン操作と storageState 生成のみを行う。

  // storageState 生成（ユーザー A・ユーザー B）
  fs.mkdirSync(AUTH_DIR, { recursive: true });
  const browser = await chromium.launch();

  const users = [
    { email: 'e2e_user_a@example.com', file: path.join(AUTH_DIR, 'user_a.json') },
    { email: 'e2e_user_b@example.com', file: path.join(AUTH_DIR, 'user_b.json') },
    // I102: 非admin（role='user'）。問題管理 authz E2E で「遮断される側」の storageState。
    { email: 'e2e_user_c@example.com', file: path.join(AUTH_DIR, 'user_c.json') },
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
