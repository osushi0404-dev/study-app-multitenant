import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';

// .env.e2e をローカル開発用に読み込む。CI では GitHub Secrets から直接 process.env に注入される。
dotenv.config({ path: path.resolve(__dirname, '.env.e2e') });

const baseURL = process.env.BASE_URL || 'http://localhost:3000';
// trace にはログイン時に入力したパスワードが残る。CI の成果物は公開リポジトリで誰でも取れるため、CI では trace を作らない（I187）
const isCI = !!process.env.CI;

export default defineConfig({
  testDir: './tests',
  globalSetup: './global-setup.ts',
  use: {
    baseURL,
    screenshot: 'only-on-failure',
    trace: isCI ? 'off' : 'retain-on-failure',
    // e2e コンテナは http://frontend:3000 を開くため、CI（localhost）と同じく安全なコンテキストとして扱う（I187）。
    // この起動オプションは画面なし専用版（headless shell）では効かないため、通常版の chromium（新しい画面なしモード）を使う
    channel: 'chromium',
    launchOptions: { args: [`--unsafely-treat-insecure-origin-as-secure=${new URL(baseURL).origin}`] },
  },
  retries: 2,
  projects: [
    // 認証済みユーザーAでのテスト（auth.spec.ts を除く全 .spec.ts に適用）
    {
      name: 'chromium-authed',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(__dirname, '.auth', 'user_a.json'),  // __dirname ベース: CI/コンテナ両方で正しく解決
      },
      testIgnore: '**/auth.spec.ts',  // glob で明示除外（旧 testMatch 負の先読み regex はバグあり: I053 fix）
    },
    // 認証不要テスト（auth.spec.ts のみ。storageState を適用しない）
    {
      name: 'chromium-unauthed',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: '**/auth.spec.ts',
    },
  ],
});
