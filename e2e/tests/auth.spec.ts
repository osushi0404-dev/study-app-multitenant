import { test, expect } from '@playwright/test';
import { randomBytes } from 'crypto';
import * as path from 'path';

// 未認証状態を自己宣言。chromium-authed で誤実行されても auth state が混入しない（二重防御）。
// ログアウトフロー describe 内の test.use({ storageState: user_a.json }) が Playwright の
// 内側優先ルールにより上書きされるため、ログアウトテストの認証状態には影響しない。
test.use({ storageState: { cookies: [], origins: [] } });

// 未認証状態でのテスト（chromium-unauthed プロジェクトで実行）
test.describe('ログインフロー（未認証）', () => {
  test('正しい認証情報でログインしてダッシュボードに遷移する', async ({ page }) => {
    // E2E_TEST_PASSWORD は playwright.config.ts の dotenv.config() で .env.e2e から読み込まれる
    // CI では GitHub Actions Secrets から直接 process.env に注入される
    const password = process.env.E2E_TEST_PASSWORD || '';
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
    await page.fill('[data-testid="password-input"]', password);
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL(/dashboard/);
  });

  test('誤ったパスワードでログインが拒否される', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
    await page.fill('[data-testid="password-input"]', 'WrongPassword999!');
    await page.click('[data-testid="login-button"]');
    // エラーは react-hot-toast のトースト通知として表示される
    // バックエンドの ValidationError → custom_exception_handler → main_message='入力内容にエラーがあります'
    // ライブラリ内部クラスではなくユーザーが実際に見るテキストでアサートする（ライブラリ非依存）
    await expect(page.getByText('入力内容にエラーがあります')).toBeVisible();
    // ダッシュボードへの遷移が起きないことも確認
    await expect(page).toHaveURL(/login/);
  });
});

// I539: 招待リンクなしの会員登録 → ログイン → 科目と問題を作る → クイズを始める（未認証のプロジェクトで動く）。
// 登録のたびに本人ひとりの組織ができるので、ユーザー ID・科目名は時刻で毎回変える
test.describe('招待なしの会員登録（I539）', () => {
  test('登録して、自分の科目と問題を作り、クイズを始められる', async ({ page }) => {
    // 登録画面のパスワードの決まり（大文字・小文字・数字）を満たす値をその場で作る。
    // CI の E2E_TEST_PASSWORD は 16 進（小文字と数字だけ）で決まりを満たさないので使わない（I539 の fix-loop）
    const password = `Aa1-${randomBytes(16).toString('hex')}`;
    const stamp = Date.now();
    const userId = `i539_${stamp}`;
    const subjectName = `E2E I539 ${stamp}`;

    // 1) ログイン画面の新規登録の入口
    await page.goto('/login');
    await page.getByText('アカウントをお持ちでない方はこちら').click();
    await expect(page).toHaveURL(/\/register$/);

    // 2) 科目選びの段は無く、「登録する」で登録を終える
    await expect(page.getByText('科目選択')).toHaveCount(0);
    await page.getByLabel('メールアドレス').fill(`${userId}@example.com`);
    await page.getByLabel('ユーザーID').fill(userId);
    await page.getByLabel('パスワード', { exact: true }).fill(password);
    await page.getByLabel('パスワード確認').fill(password);
    await page.getByRole('button', { name: '登録する' }).click();
    await expect(page.getByText('登録が完了しました。メール認証を行ってからログインしてください。')).toBeVisible();

    // 3) ログイン画面へ移り、登録した人でログインする
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
    await page.fill('[data-testid="email-input"]', `${userId}@example.com`);
    await page.fill('[data-testid="password-input"]', password);
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL(/dashboard/);

    // 4) 科目 0 件の管理者には、科目と問題を作る案内が出て、クイズはまだ始められない
    await expect(page.getByText(/まず科目と問題を作りましょう/)).toBeVisible();
    await expect(page.locator('[data-testid="start-quiz-button"]')).toBeDisabled();

    // 5) 科目を作る
    await page.getByRole('link', { name: '科目を作る' }).click();
    await expect(page).toHaveURL(/\/subject-management/);
    await page.getByRole('button', { name: '最初の科目を追加' }).click();
    const subjectDialog = page.getByRole('dialog');
    await subjectDialog.getByLabel('科目名').fill(subjectName);
    await subjectDialog.getByRole('button', { name: '保存' }).click();
    await expect(page.getByText(subjectName)).toBeVisible();

    // 6) 問題がまだ無いうちは、ダッシュボードで問題を作る案内が出て、クイズは始められない（AC13）
    await page.goto('/dashboard');
    await expect(page.getByText(/問題を作りましょう。問題管理で学ぶ科目の問題を作ると/)).toBeVisible();
    await expect(page.locator('[data-testid="start-quiz-button"]')).toBeDisabled();
    await page.getByRole('link', { name: '問題を作る' }).click();
    await expect(page).toHaveURL(/\/quiz-management/);

    // 7) その科目の問題を作る
    await page.getByRole('button', { name: 'add' }).click();
    const problemDialog = page.getByRole('dialog');
    await problemDialog.getByLabel('問題文').fill('I539 の E2E の問題');
    await problemDialog.getByRole('combobox').first().click();
    await page.getByRole('option', { name: subjectName }).click();
    for (const letter of ['A', 'B', 'C', 'D']) {
      await problemDialog.getByLabel(`選択肢 ${letter}`).fill(`選択肢${letter}`);
    }
    // 正解に A を選ぶ（ラジオは「単一選択」「複数選択」の 2 つの後に選択肢の順で並ぶ）
    await problemDialog.getByRole('radio').nth(2).check();
    await problemDialog.getByLabel('解説').fill('I539 の E2E の解説');
    await problemDialog.getByRole('button', { name: '作成' }).click();
    await expect(problemDialog).toBeHidden();

    // 8) ダッシュボードからクイズを始められる（科目は 1 件なので、選ぶダイアログを出さずに進む）
    await page.goto('/dashboard');
    await expect(page.getByText(/まず科目と問題を作りましょう/)).toHaveCount(0);
    await expect(page.getByText(/問題を作りましょう/)).toHaveCount(0);
    const startButton = page.locator('[data-testid="start-quiz-button"]');
    await expect(startButton).toBeEnabled();
    await startButton.click();
    await expect(page).toHaveURL(/\/quiz\?subject=/);
    await expect(page.locator('[data-testid="choice-option"]').first()).toBeVisible();
  });
});

// 認証済み状態でのテスト（test.use でプロジェクト設定を上書き）
test.describe('ログアウトフロー（認証済み）', () => {
  test.use({ storageState: path.join(__dirname, '..', '.auth', 'user_a.json') });  // tests/ の親ディレクトリの .auth/

  test('ログアウト後にログイン画面に戻る', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="user-menu-button"]');
    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL(/login/);
  });
});
