import { test, expect } from '@playwright/test';
import * as path from 'path';

// 未認証状態を自己宣言。chromium-authed で誤実行されても auth state が混入しない（二重防御）。
// ログアウトフロー describe 内の test.use({ storageState: user_a.json }) が Playwright の
// 内側優先ルールにより上書きされるため、ログアウトテストの認証状態には影響しない。
test.use({ storageState: { cookies: [], origins: [] } });

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
    // エラーは react-hot-toast のトースト通知として表示される
    // バックエンドの ValidationError → custom_exception_handler → main_message='入力内容にエラーがあります'
    // ライブラリ内部クラスではなくユーザーが実際に見るテキストでアサートする（ライブラリ非依存）
    await expect(page.getByText('入力内容にエラーがあります')).toBeVisible();
    // ダッシュボードへの遷移が起きないことも確認
    await expect(page).toHaveURL(/login/);
  });
});

// 認証済み状態でのテスト（test.use でプロジェクト設定を上書き）
test.describe('ログアウトフロー（認証済み）', () => {
  test.use({ storageState: path.join(__dirname, '..', '.auth', 'user_a.json') });  // tests/ の親ディレクトリの .auth/

  test('ログアウト後にログイン画面に戻る', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="user-menu-button"]');
    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL(/login/);
  });
});
