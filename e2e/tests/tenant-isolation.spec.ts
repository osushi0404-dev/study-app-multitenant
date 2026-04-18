import { test, expect } from '@playwright/test';

test.describe('テナント間データ分離', () => {
  test('Organization A のデータが Organization B ユーザーから見えない', async ({ browser }) => {
    // User A: Organization A の Subject が見える
    const ctxA = await browser.newContext({ storageState: 'e2e/.auth/user_a.json' });
    const pageA = await ctxA.newPage();
    await pageA.goto('/subject-management');
    await expect(pageA.locator('text=E2E Subject A')).toBeVisible();
    await ctxA.close();

    // User B: Organization A の Subject が見えない
    const ctxB = await browser.newContext({ storageState: 'e2e/.auth/user_b.json' });
    const pageB = await ctxB.newPage();
    await pageB.goto('/subject-management');
    await expect(pageB.locator('text=E2E Subject A')).not.toBeVisible();
    await ctxB.close();
  });
});
