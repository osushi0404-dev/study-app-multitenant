import { test, expect, Page, Request } from '@playwright/test';

/**
 * ダッシュボードの「クイズを始める」で、問題のある科目のクイズへ進む。
 *
 * e2e-init のシードで、利用者 A の学ぶ科目は E2E Quiz Subject（問題 1 問）と E2E Subject A（問題 0 問）の 2 つ。
 * クイズの対象は問題のある科目だけ（I539 AC13）なので、「すべて」でも対象は E2E Quiz Subject の 1 件で、
 * 科目を選ぶダイアログを出さずにそのクイズへ進む（問題 0 問の科目を選んでエラーの通知で戻されない）。
 */
const startQuizFromDashboard = async (page: Page) => {
  await page.click('[data-testid="start-quiz-button"]');
  await expect(page).toHaveURL(/\/quiz\?subject=\d+/);
  await page.waitForSelector('[data-testid="choice-option"]');
  await expect(page.locator('[role="dialog"]')).toHaveCount(0);
};

test.describe('クイズセッション', () => {
  test('ダッシュボードからクイズを開始して回答できる', async ({ page }) => {
    await page.goto('/dashboard');
    await startQuizFromDashboard(page);

    // 最初の選択肢をクリック
    await page.click('[data-testid="choice-option"]');

    // 回答結果が表示されることを確認
    await expect(page.locator('[data-testid="answer-result"]')).toBeVisible();
  });

  // I473: クイズに答えると、ダッシュボードの「解答問題数」が増える（数字が 0 のままだった不具合の再発防止）。
  // E2E の DB は流すたびに答えが増えるので、前後で比べる。共有の利用者 A で別の spec が同時に答えても
  // 落ちないよう「前の値より大きい」で比べる（I491。数え方の正確さは backend の pytest が確かめる）
  test('クイズに答えると、ダッシュボードの解答問題数が増える', async ({ page }) => {
    await page.goto('/dashboard');
    const answeredCount = page.locator('[data-testid="stat-answered-count"]');
    // 解答が 0 件のときは数字の代わりに「まだ記録がありません」が出る（I487）ので、数字が無ければ 0 とする
    await expect(page.getByText('解答問題数')).toBeVisible();
    const before = (await answeredCount.count()) > 0 ? Number(await answeredCount.textContent()) : 0;

    await startQuizFromDashboard(page);
    await page.click('[data-testid="choice-option"]');
    await expect(page.locator('[data-testid="answer-result"]')).toBeVisible();

    await page.goto('/dashboard');
    await expect.poll(async () => Number(await answeredCount.textContent())).toBeGreaterThan(before);
  });

  // I466: 「苦手を優先して始める」で、苦手を優先のクイズへ進む（並びの正しさは backend の pytest が確かめる）
  test('ダッシュボードから苦手を優先のクイズを始められる', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="start-weak-quiz-button"]');
    await expect(page).toHaveURL(/\/quiz\?subject=\d+&mode=weak/);
    await page.waitForSelector('[data-testid="choice-option"]');
    await expect(page.getByText('苦手を優先', { exact: true })).toBeVisible();
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
    await startQuizFromDashboard(page);

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
