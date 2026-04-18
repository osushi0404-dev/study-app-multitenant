import { test, expect } from '@playwright/test';

test.describe('クイズセッション', () => {
  test('ダッシュボードからクイズを開始して回答できる', async ({ page }) => {
    await page.goto('/dashboard');

    // 「クイズを始める」ボタンをクリック
    await page.click('[data-testid="start-quiz-button"]');

    // 科目選択ダイアログが表示される場合は E2E Quiz Subject を選択
    const dialog = page.locator('[role="dialog"]');
    if (await dialog.isVisible()) {
      await page.click('text=E2E Quiz Subject');
    }

    // クイズ画面に遷移することを確認
    await expect(page).toHaveURL(/\/quiz/);

    // 選択肢が表示されるまで待機
    await page.waitForSelector('[data-testid="choice-option"]');

    // 最初の選択肢をクリック
    await page.click('[data-testid="choice-option"]');

    // 回答結果が表示されることを確認
    await expect(page.locator('[data-testid="answer-result"]')).toBeVisible();
  });
});
