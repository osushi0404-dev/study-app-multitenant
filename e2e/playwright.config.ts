import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';

// .env.e2e をローカル開発用に読み込む。CI では GitHub Secrets から直接 process.env に注入される。
dotenv.config({ path: path.resolve(__dirname, '.env.e2e') });

export default defineConfig({
  testDir: './tests',
  globalSetup: './global-setup.ts',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  retries: 2,
  projects: [
    // 認証済みユーザーAでのテスト（auth.spec.ts 以外に適用）
    {
      name: 'chromium-authed',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(__dirname, '.auth', 'user_a.json'),  // __dirname ベース: CI/コンテナ両方で正しく解決
      },
      testMatch: /(?!.*auth\.spec).*\.spec\.ts/,
    },
    // 認証不要テスト（auth.spec.ts のみ。storageState を適用しない）
    {
      name: 'chromium-unauthed',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /auth\.spec\.ts/,
    },
  ],
});
