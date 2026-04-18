import { test, expect } from '@playwright/test';

// 未認証状態でのテスト（chromium-unauthed プロジェクトで実行）
test.describe('ログインフロー（未認証）', () => {
  test('正しい認証情報でログインしてダッシュボードに遷移する', async ({ page }) => {
    // E2E_TEST_PASSWORD は playwright.config.ts の dotenv.config() で .env.e2e から読み込まれる
    // CI では GitHub Actions Secrets から直接 process.env に注入される
    const password = process.env.E2E_TEST_PASSWORD || '';
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
    await page.fill('[data-testid="password-input"]', password);
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL(/dashboard/);
  });

  test('誤ったパスワードでログインが拒否される', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
    await page.fill('[data-testid="password-input"]', 'WrongPassword999!');
    await page.click('[data-testid="login-button"]');
    // エラーはreact-toastifyのトースト通知として表示される
    await expect(page.locator('.Toastify__toast--error')).toBeVisible();
    // ダッシュボードへの遷移が起きないことも確認
    await expect(page).toHaveURL(/login/);
  });
});

// 認証済み状態でのテスト（test.use でプロジェクト設定を上書き）
test.describe('ログアウトフロー（認証済み）', () => {
  test.use({ storageState: 'e2e/.auth/user_a.json' });

  test('ログアウト後にログイン画面に戻る', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="user-menu-button"]');
    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL(/login/);
  });
});
