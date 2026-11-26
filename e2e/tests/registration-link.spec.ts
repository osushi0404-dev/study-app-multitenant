import { test, expect, Page, BrowserContext } from '@playwright/test';

// I620 TC-30: 組織の管理者（e2e_user_b・org_b）がメンバーを追加して登録用リンクを発行し、
// ログインしていない別のブラウザの文脈でリンクを開いて仮想の認証器でパスキーを登録 → ログイン → ログアウト →
// パスキーでログインする。共有の storageState を使わない（ログアウトで共有の refresh を失効させないため）。
// 追加するメンバーは毎回ちがうユーザー ID にする（何度流しても同じに確かめられる）。
test.use({ storageState: { cookies: [], origins: [] } });

async function addVirtualAuthenticator(context: BrowserContext, page: Page) {
  const cdp = await context.newCDPSession(page);
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

test('TC-30: メンバーを追加してリンクを発行し、リンクからパスキーを登録してログインする', async ({ page, browser }) => {
  test.setTimeout(60_000);  // 2 つのブラウザの文脈で登録・ログアウト・ログインまで通すので、既定の 30 秒では足りない
  const password = process.env.E2E_TEST_PASSWORD;
  if (!password) throw new Error('E2E_TEST_PASSWORD is not set');
  const userId = `e2e_link_${Date.now()}`;

  // 管理者がパスワードでログイン → メンバー管理
  await page.goto('/login');
  await page.fill('[data-testid="email-input"]', 'e2e_user_b@example.com');
  await page.fill('[data-testid="password-input"]', password);
  await page.click('[data-testid="login-button"]');
  await page.waitForURL('**/dashboard');
  await page.getByRole('button', { name: 'メンバー管理' }).click();
  await page.waitForURL('**/members');

  // 追加 → 本人の確認（パスワード）→ リンクのダイアログ
  await page.getByRole('button', { name: 'メンバーを追加' }).click();
  const add = page.getByRole('dialog', { name: 'メンバーを追加' });
  await add.getByLabel('ユーザーID').fill(userId);
  await add.getByRole('button', { name: '追加してリンクを発行' }).click();
  const reauth = page.getByRole('dialog', { name: '本人の確認' });
  await reauth.getByLabel('パスワード').fill(password);
  await reauth.getByRole('button', { name: '確かめる' }).click();
  const linkDialog = page.getByRole('dialog', { name: `『${userId}』の登録用リンク` });
  await expect(linkDialog.getByRole('img', { name: '登録用リンクの QR コード' })).toBeVisible();
  const url = await linkDialog.getByRole('textbox', { name: 'リンク' }).inputValue();
  expect(url).toMatch(/\/passkey-setup#token=[A-Za-z0-9_-]{43}$/);
  await linkDialog.getByRole('button', { name: '閉じる' }).click();
  await expect(page.getByRole('row', { name: new RegExp(userId) })).toContainText('有効');

  // ログインしていない別の文脈でリンクを開き、パスキーを登録する
  const visitor = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  try {
    const member = await visitor.newPage();
    await addVirtualAuthenticator(visitor, member);
    await member.goto(url);
    await expect(member.getByText(`ユーザーID『${userId}』のパスキーを登録します`)).toBeVisible();
    expect(new URL(member.url()).hash).toBe('');
    await member.getByRole('button', { name: 'パスキーを登録' }).click();
    await member.waitForURL('**/dashboard');

    // ログアウト → パスキーでログイン。通知（ログインしました・パスキーを登録しました）がメニューに重なるので、
    // 消えてからメニューを開く（重なったまま押すと通知の上で止まり、時間切れになる）
    await expect(member.getByText('ログインしました')).toBeHidden({ timeout: 15000 });
    await expect(member.getByText('パスキーを登録しました')).toBeHidden({ timeout: 15000 });
    await member.click('[data-testid="user-menu-button"]');
    await member.click('[data-testid="logout-button"]');
    await expect(member).toHaveURL(/login/);
    await member.getByRole('button', { name: 'パスキーでログイン' }).click();
    await member.waitForURL('**/dashboard');

    // 同じリンクはもう使えない
    await member.goto(url);
    await expect(member.getByText('このリンクは使えません。管理者に新しいリンクを発行してもらってください')).toBeVisible();
  } finally {
    await visitor.close();
  }

  // 管理者の画面を読み直すと、その人のパスキーが 1 個・リンクは「なし」
  await page.reload();
  const row = page.getByRole('row', { name: new RegExp(userId) });
  await expect(row).toContainText('1 個');
  await expect(row).toContainText('なし');

  // 幅 360px では、表は表の中で横に流れ、列が縮んで文字が 1 文字ずつ折り返さない（test-gate No.12 の再発防止。jsdom では測れない）
  await page.setViewportSize({ width: 360, height: 740 });
  const container = page.locator('.MuiTableContainer-root');
  await expect.poll(() => container.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
  for (const name of ['登録用リンク', 'パスキー']) {
    const box = await row.getByRole('button', { name }).boundingBox();
    expect(box?.height).toBeGreaterThanOrEqual(44);
    expect(box?.height).toBeLessThanOrEqual(56);
  }
});
