import { test, expect } from '@playwright/test';
import * as path from 'path';

// I487: 設定画面の目標時間を保存して、読み戻せる（画面と裏側の項目名がそろっている）。
// e2e_user_c の目標時間だけを書き換える（ほかの spec は e2e_user_c の目標時間を見ない）。
// 今の値と違う値（45 か 50）を保存するので、何度流しても同じように確かめられる。
const authDir = path.join(__dirname, '..', '.auth');
const SETTINGS_PATH = '/api/settings/';

test.use({ storageState: path.join(authDir, 'user_c.json') });

test('TC-28: 目標時間を保存して、再読み込みの後も同じ値が出る', async ({ page }) => {
  await page.goto('/settings');
  const goal = page.getByLabel('1日の学習目標時間（分）');
  await expect(goal).not.toHaveValue('');

  const next = (await goal.inputValue()) === '45' ? '50' : '45';
  await goal.fill(next);
  await page.getByRole('button', { name: '保存' }).click();
  await expect(page.getByText('設定を保存しました')).toBeVisible();

  const reloaded = page.waitForResponse(
    (response) => new URL(response.url()).pathname === SETTINGS_PATH && response.request().method() === 'GET'
  );
  await page.reload();
  const body = await (await reloaded).json();
  expect(body.daily_study_goal_minutes).toBe(Number(next));
  await expect(page.getByLabel('1日の学習目標時間（分）')).toHaveValue(next);
});
