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
  // 同じ画面にほかの保存のボタン（「学ぶ科目を保存」など・I494）もあるので、「学習設定」の form の中の「保存」を押す。
  // 保存の応答（PATCH の 200）を待ってから読み直す（I636: 並行で流したときに 1 回だけ落ちた。3 回流して再現せず、
  // 原因は未特定。保存の前に読み直しが走る順序を消しておく）
  const saved = page.waitForResponse(
    (response) => new URL(response.url()).pathname === SETTINGS_PATH && response.request().method() === 'PATCH'
  );
  await page.getByRole('form', { name: '学習設定' }).getByRole('button', { name: '保存' }).click();
  const savedResponse = await saved;
  expect(savedResponse.status()).toBe(200);
  expect((await savedResponse.json()).daily_study_goal_minutes).toBe(Number(next));
  await expect(page.getByText('設定を保存しました')).toBeVisible();

  const reloaded = page.waitForResponse(
    (response) => new URL(response.url()).pathname === SETTINGS_PATH && response.request().method() === 'GET'
  );
  await page.reload();
  const body = await (await reloaded).json();
  expect(body.daily_study_goal_minutes).toBe(Number(next));
  await expect(page.getByLabel('1日の学習目標時間（分）')).toHaveValue(next);
});
