# I432 手動テスト: Dependabot #377（@playwright/test 1.64.1）で E2E が落ちる原因を直して取り込む

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | PR #575 の最新の「E2E Tests (Playwright)」の実行のログを `gh run view <id> --log` で読み、`Operating System`・`node:`（setup-node の Environment details）・`npx playwright --version` 相当の版（`npm ci` で入った `@playwright/test`）・`Running N tests`・最後の集計の行を抜き出す | ランナーが Ubuntu 26.04、Node.js が `v26.`、Playwright が 1.65.1、`Running N tests` の N が 19 以上、集計に `failed` が無く `passed` がある（導入の段で止まった失敗・テスト 0 件の緑は不合格）。`flaky` があればテスト名を実結果に書く（`settings.spec.ts` の TC-28 だけなら計画書 §8 R2 として扱う。TC-28 以外が flaky なら NG〔CI の再実行で緑になっても合格にしない〕） | Claude |  | AC2・AC5・V3 |
| 2 | `gh pr checks 575` で E2E 以外の CI のジョブの結果を見る | Backend Lint & Security・Backend Tests・Frontend Type Check・Frontend Lint & Security・Frontend Tests・API Types Up To Date・Harness Tests がすべて pass | Claude |  | AC2 |
| 3 | `docker compose run --rm --no-deps e2e sh -c "npm install && npx playwright --version && npx playwright install --dry-run chromium && ls /ms-playwright"` を流す | イメージの取得が `sha256:b0ee5ce5…6dd8` で成功し、`Version 1.65.1` が出る。`--dry-run` が示す chromium の置き場所（`/ms-playwright/chromium-<番号>`）が `ls /ms-playwright` の一覧にある（イメージの中のブラウザを取り直さずに使える） | Claude |  | V2・手元の E2E のイメージ |
| 4 | `docs/runbooks/frontend-verify.md` の「初回だけの準備」の `install-deps` の行と、`rules/react-coding-standards-integrated.md` §16 の #551 の行を読む。続けて `! git grep -q "1\.59\.1" -- ':!docs/plans' ':!docs/reviews' ':!docs/tests' ':!docs/issues'` を流す | 手順書が `npx -y playwright@1.65.1 install-deps --dry-run chromium` になっている。§16 の行に E2E のジョブ（`e2e/`）を対象外とする文言がある。コマンドが exit 0（記録の外に `1.59.1` が無い。直す前の 2026-11-18 は exit 1 で、不合格になることを確認済み） | Claude |  | 消費箇所の全件・V4 |
| 5 | No.1・No.2 が OK の後に、#377・#376 それぞれに「PR #575 で同じ版上げ（`@playwright/test` 1.65.1・イメージ v1.65.1-jammy）と E2E の Node.js 26 を取り込むため閉じる」とコメントして（`gh pr comment <番号> --body-file <ファイル>`）閉じ（`gh pr close <番号>`）、`gh pr view 377 --json state,comments` と `gh pr view 376 --json state,comments` を見る | どちらも `state` が `CLOSED` で、PR #575 で取り込む旨のコメントがある | Claude |  | AC4 |

結論: OK / NG
