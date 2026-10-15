# I159 手動テスト: frontend 依存の critical 脆弱性（proxy-addr / shell-quote）を npm audit fix で解消

対象: PR #277（feature/I159-fix-frontend-critical-vulns → develop）／取り込み先 PR #269（feature/I151-django-52-lts-upgrade → develop）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | （計画 ステップ4）lockfile を push 後、`gh pr checks 277 --watch` で PR #277 の CI 完了を待ち、`gh pr view 277 --json statusCheckRollup --jq '.statusCheckRollup[]\|"\(.name) \(.conclusion)"'` で結果を確認する。Backend Lint & Security の失敗ステップを `gh run view <run-id> --log-failed` で確認する | **Frontend Lint & Security / Frontend Tests / Frontend Type Check / Backend Tests / E2E Tests (Playwright) の 5 つが SUCCESS**。Backend Lint & Security のみ FAILURE で、失敗ステップが `pip-audit`（Django 4.2 / anyio の CVE・I151 で解消）であること。Frontend Lint & Security の npm audit ステップに `critical` の件数表示がないこと | Claude | OK | 2026-10-15 実施（run 38677187381 / e2e 38677187454）。Backend Tests / E2E / Frontend Lint & Security / Frontend Tests / Frontend Type Check = SUCCESS。Backend Lint & Security = FAILURE で失敗ステップは `pip-audit` のみ（pre-commit は success・migration drift は skipped）。npm audit ステップ出力 `94 vulnerabilities (3 low, 34 moderate, 57 high)`＝critical 0・ローカル TC-10 と一致 |
| M2 | （計画 ステップ5・AC-4）I159 ブランチを I151 ブランチへ `git merge --no-ff` して push 後、`gh pr checks 269 --watch` で PR #269 の CI 完了を待ち、上と同じ `gh pr view 269 ...` で結果を確認する | **6 チェックすべて SUCCESS**（Backend Lint & Security / Backend Tests / E2E Tests (Playwright) / Frontend Lint & Security / Frontend Tests / Frontend Type Check） | Claude | OK | 2026-10-15 実施。取り込み merge commit 729dfbd（I151 ブランチ）で 6 チェックすべて SUCCESS。AC-4・E2E（AC-5）確認済み |
| M3 | （AC-6）frontend ディレクトリで `BROWSER=none PORT=3159 npm start` をバックグラウンド起動し、ログに `Compiled successfully` または `webpack compiled` が出るまで待つ。`curl -s -o /dev/null -w "%{http_code}" http://localhost:3159/login` と `curl -s http://localhost:3159/login` を実行後、開発サーバーを停止する | ステータス **200**、HTML に `<div id="root">` を含む。起動ログに `Failed to compile` / `Module not found` がない | Claude | 一部実施 | 2026-10-15 実施。起動ログ `Compiled successfully!` / `webpack compiled successfully`・`Failed to compile` / `Module not found` なし。**curl による HTTP 確認は実行許可が得られず未実施**（回避手段は取らず、画面表示は同じ react-scripts の開発サーバーを使う M4b・M4c で確認）。確認後に開発サーバーを停止（ポート 3159 の待ち受けなしを確認） |
| M4a | （AC-6・見た目の非回帰）修正前の lockfile でのビルド（`$S/build-base`・ベースライン取得時）と修正後のビルド（`$S/build-after`・TC-09）の CSS を `cmp $S/build-base/static/css/main.*.css $S/build-after/static/css/main.*.css` で比較する | **exit 0**（バイト単位で同一）。postcss / tailwindcss / cssnano 系の更新で生成 CSS が変わっていないこと | Claude | OK | 2026-10-15 実施。両方とも `main.ac72a3e1.css`（同一ハッシュ）・cmp exit 0 |
| M4b | （AC-6・開発サーバー経由の表示とログイン）M1・M2 の CI「E2E Tests (Playwright)」の結果を確認する（docker compose の開発サーバー〔Dockerfile.dev〕＋ seed_e2e ＋ Chromium で `/login` → ログイン → `/dashboard` 遷移を検証している） | PR #277・PR #269 の両方で E2E が **SUCCESS** | Claude | OK | 2026-10-15 確認。M1（e2e run 38677187454）・M2 とも SUCCESS。axios 1.20.0 での実 API 通信を含む |
| M4c | （AC-6・CI で見ていない点: Console エラー／手元 Docker）Docker Desktop を起動し `docker compose up -d --build -V db backend frontend`（`-V` で frontend の node_modules ボリュームを作り直す）→ `docker compose exec backend python manage.py migrate --noinput` → `seed_e2e --scenario tenant_isolation --password <$S 内で生成した値>` → `npm ci --prefix e2e` → `npx --prefix e2e playwright install chromium` → `$S/m4c.spec.ts`（下記）を Playwright で実行する | **exit 0**。判定内容: (1) `/login` に見出し「ログイン」・メール/パスワード入力欄が表示される (2) ログイン後 URL が `/dashboard` (3) Console の error と未捕捉例外が**修正前の lockfile（origin/develop）で同じ手順を実行した結果と同一**（今回の更新で新たなエラーが出ていない）。画面写真（`$S/m4c-login.png` / `$S/m4c-dashboard.png`）は補助として保存し Claude が目視する（合否には使わない） | Claude | OK | 2026-10-15 実施。Playwright 公式イメージ（1.59.1・WSL に Chromium の OS 依存ライブラリが無く sudo 不可のため）を compose ネットワーク内で実行。frontend コンテナ内は axios 1.20.0 / proxy-addr 2.0.8 / shell-quote 1.12.0 / react-router-dom 6.30.6 を確認。(1) login_page=OK (2) dashboard_url=/dashboard (3) Console error 6 件・**すべてログイン前の `/login`**（`GET /api/settings/` 401 →「Error loading user settings for notifications: No refresh token available」×2 系統）、ダッシュボードでは 0 件。**修正前（develop の lockfile・axios 1.17.0 / proxy-addr 2.0.7 / shell-quote 1.8.4 を別コンテナ i159-frontend-base で起動）でも件数・内容・発生画面まで完全に同一** → 既存のアプリ挙動（未ログインで設定 API を呼ぶ）であり I159 起因ではない。当初の期待値「0 件」は既存エラーを考慮しておらず、更新の非回帰を見る判定として「修正前と同一」に改めた。画面写真でもログイン画面・ダッシュボードの表示崩れなし | frontend コンテナ内の node_modules が更新後の版であること（`docker compose exec frontend npm ls axios proxy-addr shell-quote`）も記録する |
| M5 | （計画 ステップ7・PR #269 マージ後）`gh pr view 277 --json state --jq .state` を実行する | **MERGED**。OPEN の場合は `gh pr close 277 --comment "PR #269 経由で develop に取り込み済み"` を実行し、CLOSED になったことを同コマンドで確認する | Claude | | マージ後実施 |
| M6 | （計画 ステップ7・PR #269 マージ後）`gh issue close 220 --comment "I159（PR #277・#269 経由で develop 取り込み）で対応済み"` を実行し、`gh issue view 220 --json state --jq .state` で確認する | **CLOSED** | Claude | | マージ後実施。runbook docs/runbooks/dependency-audit.md 手順 3 |

## M4c 用 Playwright スクリプト（`$S/m4c.spec.ts`・リポジトリには置かない）
```ts
import { test, expect } from '@playwright/test';
test('I159 M4c: login → dashboard without console errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto('http://localhost:3000/login');
  await expect(page.getByRole('heading', { name: 'ログイン' })).toBeVisible();
  await expect(page.locator('[data-testid="email-input"]')).toBeVisible();
  await expect(page.locator('[data-testid="password-input"]')).toBeVisible();
  await page.screenshot({ path: process.env.M4C_OUT + '/m4c-login.png', fullPage: true });
  await page.fill('[data-testid="email-input"]', 'e2e_user_a@example.com');
  await page.fill('[data-testid="password-input"]', process.env.M4C_PASSWORD || '');
  await page.click('[data-testid="login-button"]');
  await expect(page).toHaveURL(/dashboard/);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: process.env.M4C_OUT + '/m4c-dashboard.png', fullPage: true });
  console.log('console_errors=' + errors.length + ' ' + JSON.stringify(errors));
  // 合否: 修正前（develop の lockfile）で同じスクリプトを実行した errors と同一であること
});
```
