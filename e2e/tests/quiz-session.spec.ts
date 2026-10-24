import { test, expect, Request } from '@playwright/test';

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

  // I158: 開発サーバー（StrictMode 有効）でも開始リクエストは 1 回だけ・Idempotency-Key 付き
  test('クイズ開始時の POST /api/quiz/ は 1 回だけ送られる', async ({ page }) => {
    const startRequests: Request[] = [];
    page.on('request', (request) => {
      if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/quiz/') {
        startRequests.push(request);
      }
    });

    await page.goto('/dashboard');
    await page.click('[data-testid="start-quiz-button"]');
    const subjectDialog = page.locator('[role="dialog"]');
    await expect(subjectDialog).toBeVisible();
    await subjectDialog.getByRole('button', { name: /E2E Quiz Subject/ }).click();
    await page.waitForSelector('[data-testid="choice-option"]');

    expect(startRequests).toHaveLength(1);
    // crypto.randomUUID は安全なコンテキストでのみ使える。CI（localhost）ではキー付き、
    // compose 内の e2e コンテナ（http://frontend:3000）ではキー無しで送る代替動作を確認する
    const idempotencyKey = startRequests[0].headers()['idempotency-key'];
    if (await page.evaluate(() => window.isSecureContext)) {
      expect(idempotencyKey).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
      );
    } else {
      expect(idempotencyKey).toBeUndefined();
    }
  });
});
