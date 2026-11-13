import { test, expect, Page } from '@playwright/test';
import * as path from 'path';

// I487: ダッシュボードの幅・並び・状態の表示を、実際のブラウザの幅とレイアウトで確かめる。
// 幅の確かめ（TC-21〜23・26）は、グラフが必ず描かれるよう overview の応答を固定する
// （E2E の利用者は種データを流すたびに作り直され、解答が 0 件から始まるため。共有の利用者に解答を足して他の spec に影響させない）。
// 通信の回数（TC-24）・科目の切り替え（TC-25）・科目 0 件（TC-27）は本物の API で確かめる。
const authDir = path.join(__dirname, '..', '.auth');
const OVERVIEW = /\/api\/dashboard\/overview\//;
const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };
const APP_BAR_HEIGHT = 64;

const OVERVIEW_WITH_DATA = {
  has_data: true,
  today: { study_seconds: 1500, answered_count: 12, correct_count: 9, accuracy_rate: 0.75 },
  streak: { current_days: 3 },
  totals: { answered_count: 123456, correct_count: 100000, accuracy_rate: 0.81 },
  last_7_days: [7, 8, 9, 10, 11, 12, 13].map((d, i) => ({
    date: `2026-11-${String(d).padStart(2, '0')}`,
    study_seconds: i * 300,
    answered_count: i,
    correct_count: i,
  })),
  weak_subjects: [
    { subject_id: 9001, subject_name: 'とても長い名前の科目でも横にはみ出さないことを確かめる科目', answered_count: 10, accuracy_rate: 0.5 },
  ],
  recommendations: [],
};

const fixOverview = (page: Page) =>
  page.route(OVERVIEW, (route) => route.fulfill({ json: OVERVIEW_WITH_DATA }));

const hasNoHorizontalOverflow = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);

const expectInsideWidth = async (page: Page, testId: string, width: number) => {
  const box = await page.getByTestId(testId).boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(width);
};

const waitForNumbers = (page: Page) =>
  expect(page.getByText('今日の学習時間')).toBeVisible();

test.describe('ダッシュボードの幅と並び（I487）', () => {
  test('TC-21: 390px で開くと横にはみ出さず、クイズと今日の復習が画面の幅の中にある', async ({ page }) => {
    await fixOverview(page);
    await page.setViewportSize(MOBILE);
    await page.goto('/dashboard');
    await expect(page.getByTestId('stat-answered-count')).toHaveText('123456');

    expect(await hasNoHorizontalOverflow(page)).toBe(true);
    await expectInsideWidth(page, 'start-quiz-button', MOBILE.width);
    await expectInsideWidth(page, 'today-review-card', MOBILE.width);
  });

  test('TC-22: 1440px で開いてから 390px に縮めても横にはみ出さない', async ({ page }) => {
    await fixOverview(page);
    await page.setViewportSize(DESKTOP);
    await page.goto('/dashboard');
    await expect(page.locator('main canvas')).toHaveCount(2);

    await page.setViewportSize(MOBILE);
    await expect.poll(() => hasNoHorizontalOverflow(page), { timeout: 5000 }).toBe(true);
    await expectInsideWidth(page, 'start-quiz-button', MOBILE.width);
    await expectInsideWidth(page, 'today-review-card', MOBILE.width);
  });

  test('TC-23: 1440×900 の最初の画面に、クイズと今日の復習が入る', async ({ page }) => {
    await fixOverview(page);
    await page.setViewportSize(DESKTOP);
    await page.goto('/dashboard');
    await expect(page.getByTestId('stat-answered-count')).toHaveText('123456');

    for (const testId of ['start-quiz-button', 'today-review-card']) {
      const box = await page.getByTestId(testId).boundingBox();
      expect(box).not.toBeNull();
      expect(box!.y).toBeGreaterThanOrEqual(0);
      expect(box!.y + box!.height).toBeLessThanOrEqual(DESKTOP.height);
    }
  });

  test('TC-26: アクセシビリティ設定のボタンは上のバーの中にあり、浮いたボタンが無い', async ({ page }) => {
    await fixOverview(page);
    for (const size of [DESKTOP, MOBILE]) {
      await page.setViewportSize(size);
      await page.goto('/dashboard');
      await waitForNumbers(page);

      const button = page.getByRole('button', { name: 'アクセシビリティ設定' });
      await expect(button).toHaveCount(1);
      const box = await button.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.y + box!.height).toBeLessThanOrEqual(APP_BAR_HEIGHT);
      await expect(page.locator('.MuiFab-root')).toHaveCount(0);
    }
  });

  test('TC-24: 初回の表示で overview の取得は 1 回', async ({ page }) => {
    let calls = 0;
    page.on('request', (request) => {
      if (request.method() === 'GET' && new URL(request.url()).pathname === '/api/dashboard/overview/') {
        calls += 1;
      }
    });

    await page.goto('/dashboard');
    await waitForNumbers(page);
    await page.waitForTimeout(1000);
    expect(calls).toBe(1);
  });

  test('TC-25: 科目を切り替えても画面全体が置き換わらず、MUI の範囲外の値の警告が出ない', async ({ page }) => {
    const messages: string[] = [];
    page.on('console', (message) => messages.push(message.text()));

    await page.goto('/dashboard');
    await waitForNumbers(page);

    await page.getByRole('combobox', { name: '科目を選択' }).click();
    await page.getByRole('option').nth(1).click();

    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await waitForNumbers(page);
    await expect(page.getByText('ダッシュボードを読み込み中...')).toHaveCount(0);
    expect(messages.filter((text) => text.includes('out-of-range'))).toEqual([]);
  });
});

test.describe('科目 0 件の利用者（I487）', () => {
  test.use({ storageState: path.join(authDir, 'user_c.json') });

  test('TC-27: 科目 0 件なら画面の中で管理者への依頼を案内し、クイズを始められない', async ({ page }) => {
    await page.goto('/dashboard');

    await expect(
      page.getByText('科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください')
    ).toBeVisible();
    await expect(page.getByTestId('start-quiz-button')).toBeDisabled();
    await expect(page.getByText(/設定画面から科目を追加/)).toHaveCount(0);
  });
});
