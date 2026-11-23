import { test, expect, Page } from '@playwright/test';

// I619 TC-30: Chromium の仮想の認証器（CDP）で「登録 → ログアウト → パスキーでログイン → 削除」を通す。
// 共有の storageState（user_a など）のリフレッシュトークンをログアウトで無効にしないよう、空の状態から
// e2e_user_b でパスワードのログインをする。最後に足したパスキーを消すので、何度流しても同じに確かめられる。
test.use({ storageState: { cookies: [], origins: [] } });

const PASSKEYS_API = '/api/auth/passkeys/';

async function addVirtualAuthenticator(page: Page) {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('WebAuthn.enable');
  await cdp.send('WebAuthn.addVirtualAuthenticator', {
    options: {
      protocol: 'ctap2',
      transport: 'internal',
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  });
}

async function passkeyCount(page: Page): Promise<number> {
  const loaded = page.waitForResponse(
    (response) => new URL(response.url()).pathname === PASSKEYS_API && response.request().method() === 'GET'
  );
  await page.goto('/settings');
  return (await (await loaded).json()).count;
}

test('TC-30: パスキーを登録し、ログアウトしてパスキーでログインし、最後に削除する', async ({ page }) => {
  const password = process.env.E2E_TEST_PASSWORD;
  if (!password) throw new Error('E2E_TEST_PASSWORD is not set');
  await addVirtualAuthenticator(page);

  // パスワードでログイン
  await page.goto('/login');
  await page.fill('[data-testid="email-input"]', 'e2e_user_b@example.com');
  await page.fill('[data-testid="password-input"]', password);
  await page.click('[data-testid="login-button"]');
  await page.waitForURL('**/dashboard');

  // 登録（本人の確認はパスワード）
  const before = await passkeyCount(page);
  const card = page.getByTestId('passkeys-card');
  await card.getByRole('button', { name: 'パスキーを登録' }).click();
  const reauth = page.getByRole('dialog', { name: '本人の確認' });
  await reauth.getByLabel('パスワード').fill(password);
  await reauth.getByRole('button', { name: '確かめる' }).click();
  await expect(page.getByText('パスキーを登録しました')).toBeVisible();
  await expect(card.getByRole('listitem')).toHaveCount(before + 1);
  const added = card.getByRole('listitem').last();
  await expect(added).toContainText('まだ使っていません');

  // ログアウト → パスキーでログイン
  await page.click('[data-testid="user-menu-button"]');
  await page.click('[data-testid="logout-button"]');
  await expect(page).toHaveURL(/login/);
  const login = page.waitForResponse(
    (response) => new URL(response.url()).pathname === `${PASSKEYS_API}login/` && response.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'パスキーでログイン' }).click();
  expect((await login).status()).toBe(200);
  await page.waitForURL('**/dashboard');

  // 最後に使った日が今日になり、削除できる（新しいセッションなので本人の確認はパスキーで）
  const today = new Intl.DateTimeFormat('ja-JP', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date());
  await passkeyCount(page);
  const last = card.getByRole('listitem').last();
  await expect(last).toContainText(`最後に使った日 ${today}`);
  await last.getByRole('button', { name: /を削除$/ }).click();
  await page.getByRole('dialog', { name: 'パスキーの削除' }).getByRole('button', { name: '削除' }).click();
  await page.getByRole('dialog', { name: '本人の確認' }).getByRole('button', { name: 'パスキーで確かめる' }).click();
  await expect(page.getByText('パスキーを削除しました')).toBeVisible();
  await expect(card.getByRole('listitem')).toHaveCount(before);
});
