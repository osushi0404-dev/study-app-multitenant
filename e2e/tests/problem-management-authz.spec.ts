import { test, expect } from '@playwright/test';
import * as path from 'path';

// I102: 問題管理（/quiz-management）の組織管理者限定を E2E で検証する。
// 非admin（e2e_user_c / role='user'）は遮断され、admin（e2e_user_a / role='admin'）は到達できる。
// tenant-isolation.spec.ts と同様に browser.newContext({ storageState }) でユーザーを切り替える。
const authDir = path.join(__dirname, '..', '.auth');
const DENIED_TEXT = 'このページにアクセスする権限がありません。管理者権限が必要です。';

test.describe('問題管理の認可（I102）', () => {
  test('非admin（role=user）は「問題管理」メニューが出ず、/quiz-management も遮断される', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: path.join(authDir, 'user_c.json') });
    const page = await ctx.newPage();

    // ナビに「問題管理」項目が表示されない
    await page.goto('/dashboard');
    await expect(page.getByText('問題管理', { exact: true })).toHaveCount(0);

    // /quiz-management へ直接遷移すると権限エラーが表示され、管理 UI に到達しない
    await page.goto('/quiz-management');
    await expect(page.getByText(DENIED_TEXT)).toBeVisible();

    await ctx.close();
  });

  test('admin（role=admin）は「問題管理」メニューが表示され、/quiz-management に到達できる', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: path.join(authDir, 'user_a.json') });
    const page = await ctx.newPage();

    // ナビに「問題管理」項目が表示される
    await page.goto('/dashboard');
    await expect(page.getByText('問題管理', { exact: true })).toBeVisible();

    // /quiz-management に到達し、権限エラーが表示されない
    await page.goto('/quiz-management');
    await expect(page.getByText(DENIED_TEXT)).toHaveCount(0);

    await ctx.close();
  });
});
