import { test, expect, Page, BrowserContext, Locator } from '@playwright/test';

// I620 TC-30: 組織の管理者（e2e_user_b・org_b）がメンバーを追加して登録用リンクを発行し、
// ログインしていない別のブラウザの文脈でリンクを開いて仮想の認証器でパスキーを登録 → ログイン → ログアウト →
// パスキーでログインする。共有の storageState を使わない（ログアウトで共有の refresh を失効させないため）。
// 追加するメンバーは毎回ちがうユーザー ID にする（何度流しても同じに確かめられる）。
// I636: 表の枠は役割と名前で探す（MUI の内部のクラス名に頼らない）。360px では 3 つのボタンの行を確かめる。
// 通知は上の中央（上のバーのすぐ下）に出て、クリックを受け取らないので、上のバーのボタン・ユーザーメニュー・
// アクセシビリティ設定のパネルの操作を塞がない。通知が消えるのを待たずにログアウトできる。
test.use({ storageState: { cookies: [], origins: [] } });

const TABLE_REGION = 'メンバーの一覧の表（横に動かせます）';

type Box = { x: number; y: number; width: number; height: number };

/** 2 つの枠が重なる部分（重ならなければ null） */
function overlap(a: Box, b: Box): Box | null {
  const x = Math.max(a.x, b.x);
  const y = Math.max(a.y, b.y);
  const right = Math.min(a.x + a.width, b.x + b.width);
  const bottom = Math.min(a.y + a.height, b.y + b.height);
  return right > x && bottom > y ? { x, y, width: right - x, height: bottom - y } : null;
}

/** 点の一番手前の押せる要素（クリックを受け取らない要素は返らない）が target の中にあるか */
async function topmostIsInside(target: Locator, point: { x: number; y: number }): Promise<boolean> {
  return target.evaluate((el, p) => {
    const hit = document.elementFromPoint(p.x, p.y);
    return hit !== null && el.contains(hit);
  }, point);
}

const center = (box: Box) => ({ x: box.x + box.width / 2, y: box.y + box.height / 2 });

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
  const openRow = page.getByRole('row', { name: new RegExp(userId) });
  await expect(openRow).toContainText('有効');

  // 幅 360px では、表は表の中で横に流れ、列が縮んで文字が 1 文字ずつ折り返さない（I620 test-gate No.12 の再発防止。
  // jsdom では測れない）。リンクが有効な行は［リンクを取り消す］を含む 3 つのボタン（I636 F11）
  await page.setViewportSize({ width: 360, height: 740 });
  const container = page.getByRole('region', { name: TABLE_REGION });
  await expect.poll(() => container.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
  for (const name of ['登録用リンク', 'パスキー', 'リンクを取り消す']) {
    const box = await openRow.getByRole('button', { name }).boundingBox();
    expect(box?.height).toBeGreaterThanOrEqual(44);
    expect(box?.height).toBeLessThanOrEqual(56);
  }
  await page.setViewportSize({ width: 1280, height: 720 });

  // ログインしていない別の文脈でリンクを開き、パスキーを登録する
  const visitor = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  try {
    const member = await visitor.newPage();
    await member.setViewportSize({ width: 360, height: 740 });
    await addVirtualAuthenticator(visitor, member);
    await member.goto(url);
    await expect(member.getByText(`ユーザーID『${userId}』のパスキーを登録します`)).toBeVisible();
    expect(new URL(member.url()).hash).toBe('');
    await member.getByRole('button', { name: 'パスキーを登録' }).click();
    await member.waitForURL('**/dashboard');

    // 通知（パスキーを登録しました）は上のバーのすぐ下に出る（I636。個々のボタンでなく上のバー全体と比べる）。
    // 出てくるときは上から滑り込むので、上のバーの下端より下に止まるまで待つ。メニュー・パネルを開くと、それ以外の
    // 要素は読み上げから隠れる（aria-hidden）ので、通知は includeHidden で探す
    const toast = member.getByRole('status', { includeHidden: true }).filter({ hasText: 'パスキーを登録しました' });
    const bannerBox = await member.getByRole('banner').boundingBox();
    expect(bannerBox).not.toBeNull();
    await expect.poll(async () => (await toast.boundingBox())?.y ?? -1)
      .toBeGreaterThanOrEqual(bannerBox!.y + bannerBox!.height);

    // 通知が出ている間に上のバーからアクセシビリティ設定のパネルを開いても、重なる所でパネルが押せる
    await member.getByRole('button', { name: 'アクセシビリティ設定' }).click();
    const panel = member.getByRole('dialog', { name: 'アクセシビリティ設定パネル' });
    await expect(panel).toBeVisible();
    await expect(toast).toBeVisible();  // 通知とパネルが同時に出ている状態で確かめる（通知が消えた後では確かめにならない）
    const panelShared = overlap((await panel.boundingBox())!, (await toast.boundingBox())!);
    expect(panelShared).not.toBeNull();  // 幅 360px では同じ高さで重なる（重なっていなければ確かめにならない）
    expect(await topmostIsInside(panel, center(panelShared!))).toBe(true);
    await member.getByRole('button', { name: 'アクセシビリティ設定' }).click();
    await expect(panel).toBeHidden();

    // 通知が出ている間にユーザーメニューを開いても、通知に重なる項目が押せる
    await member.click('[data-testid="user-menu-button"]');
    await expect(member.locator('[data-testid="logout-button"]')).toBeVisible();
    await expect(toast).toBeVisible();
    const toastBox = (await toast.boundingBox())!;
    const items = member.getByRole('menuitem');
    let overlapped = 0;
    for (let i = 0; i < await items.count(); i += 1) {
      const shared = overlap(toastBox, (await items.nth(i).boundingBox())!);
      if (!shared) continue;
      overlapped += 1;
      expect(await topmostIsInside(items.nth(i), center(shared))).toBe(true);
    }
    expect(overlapped).toBeGreaterThan(0);  // 通知に重なる項目が無ければ確かめにならない
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
});
