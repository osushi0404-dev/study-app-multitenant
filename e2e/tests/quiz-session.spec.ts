import { test, expect } from '@playwright/test';

test.describe('クイズセッション', () => {
  test('ダッシュボードからクイズを開始して回答できる', async ({ page }) => {
    await page.goto('/dashboard');

    // 「クイズを始める」ボタンをクリック
    await page.click('[data-testid="start-quiz-button"]');

    // e2e-init が tenant_isolation → quiz_session の順でシードするため
    // org_a には E2E Subject A + E2E Quiz Subject の 2件が存在し、
    // Dashboard の handleStartQuiz は必ずダイアログを開く（subjects.length >= 2）。
    // expect(...).toBeVisible() は自動リトライ付きアサートで
    // React 状態更新 + MUI ダイアログアニメーション（~300ms）を安全に待機する。
    const subjectDialog = page.locator('[role="dialog"]');
    await expect(subjectDialog).toBeVisible();

    // aria-label="E2E Quiz Subjectのクイズを開始" に基づくアクセシビリティファーストなセレクタ
    await subjectDialog.getByRole('button', { name: /E2E Quiz Subject/ }).click();

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
