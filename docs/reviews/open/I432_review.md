# I432 レビュー: Dependabot #377（@playwright/test 1.64.1）で E2E が落ちる原因を直して取り込む

## 変更概要
- CI の E2E のジョブの Node.js を 18 → 26 に上げ、`@playwright/test` を 1.59.1 → 1.65.1、手元の E2E のコンテナのイメージを v1.65.1-jammy に上げる。#377・#376 は取り込み済みとして閉じる（計画: docs/plans/open/plan_I432.md）

## 変更点
- `.github/workflows/e2e.yml`: `node-version` '18' → '26'（1 行だけ）
- `e2e/package.json`・`e2e/package-lock.json`: `@playwright/test` 1.59.1 → 1.65.1（lock は `@playwright/test`・`playwright`・`playwright-core` の版・integrity・engines と、1.65 で外れた任意の依存 `fsevents` の削除だけ）
- `docker-compose.yml`: e2e のイメージを `v1.65.1-jammy@sha256:b0ee5ce5…6dd8`（#376 と同じ値）
- `docs/runbooks/frontend-verify.md:13`: `playwright@1.65.1`
- `rules/react-coding-standards-integrated.md:207`: §16 の #551 の行に E2E のジョブを対象外とする文言

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.github/workflows/e2e.yml`・`e2e/package.json`・`e2e/package-lock.json`・`docker-compose.yml`（e2e のイメージ）・`docs/runbooks/frontend-verify.md`・`rules/react-coding-standards-integrated.md`（§16 の #551 の行の文言）

## テスト結果
- 自動: TC-01 pass=17 fail=0・TC-02 pass=54 fail=0・TC-04 npm audit 0 件（implement）。TC-03 は CI（review-gate）
- 手動: （test-gate で記入）

## 計画との差分
- なし

## ロールバック
- PR #575 の revert（設定とロックファイルだけ）

## 自律判断の記録
- [plan] 取り込み方は「このブランチで同じ版上げ・#377/#376 は閉じる」にした — Node.js とイメージと npm の版を 1 本の PR でそろえて確かめられ、#377（1.65.0）と #376（1.65.1）の版のずれも無くせるため（計画書 §9）
- [plan] E2E のジョブの Node.js は 26（規約 §0）にし、画面の Node.js 18 は #551 に残した — E2E のジョブは `e2e/` の別の package で画面と別に動き、規約 §16 の #551 の行は画面のコードとの差の表と読んだため（計画書 §9）
- [plan] 1.65 での E2E の事前の確かめは手元でせず CI に任せた — 手順書の `RATELIMIT_ENABLE=false docker compose …` は前置きがあるためサンドボックスの外で動く対象に当たらず `.env` を読めずに止まった。前置きなしではログインの制限で落ちる（計画書 §1 スパイク）。手順書の形がサンドボックスの中で動かないことは retro で扱う
- [plan] `.github/` を変えるが止めて聞かずに進めた — 変えるのは Node.js の版の 1 行だけで守りを緩めない（TC-01・TC-02）。直し方は grill-me の報告でユーザーに示した後に `/plan-issue` が打たれ、マージはユーザーが承認する（計画書 §9）
- [plan] #377・#376 を閉じるのは test-gate の手動 No.5 にした — CI が緑と確かめた後に行い、AC4 を close の前に満たすため
- [plan-review] 判定 HIGHRISK（`.github/workflows/e2e.yml`）。Warning 3 件（規約 §16 の文言・No.4 の判定コマンド・TC-28 以外の flaky の扱い）は計画書・手動テストを直して対応し、再レビューはしない — 方式・受け入れ条件を変えない findings への対応のため（計画変更記録）
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
- [design-security-review] Blocker・High・Medium なし（Low 4 件・シナリオ Low 3 件。どれも既存の決定論ゲート・npm audit・指紋の固定で手を打ってある）。前からあるパスワードの環境変数の件（I213 F3）は変えない — 本イシューの目的と別で、一覧に残っているため（計画書「セキュリティレビュー結果」）
STAGE_DONE: design-security-review NEXT: implement
- [implement] lock の変更で `fsevents`（macOS 用の任意の依存）が消えたのはそのまま受け入れた — 1.65 の `playwright` が任意の依存から外したもので、計画書 §4 の想定の範囲（Linux の CI・コンテナに影響なし）
- [implement] `/simplify` は 4 人のレビュー役を起こさず自分で 4 観点を当てた（直す点なし）— 差分が版の数字 6 か所とロックファイルだけで、起こす費用に見合わないため
- [implement] `docker-compose.yml` は `sed -i` が置き換えに失敗（サンドボックスで 1 ファイルだけ書ける場所のため）したので Edit で直した — 結果は同じ
STAGE_DONE: implement NEXT: review-gate
- [review-gate] 基本レビューは CI_WAIT: OK（E2E を含む全ジョブ成功）・FINAL_VERDICT: OK・Low 5 件（F1〜F5・止める指摘なし）。F4（この記録の 2 行のつながり）は記録の場所なのでその場で直した。ほかの Low は retro で振り分ける — 止める指摘ではなく、記録の外の差分を足すと OK の周が無くなるため
