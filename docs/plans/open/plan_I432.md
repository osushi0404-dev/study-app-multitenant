# I432 計画書: Dependabot #377（@playwright/test 1.64.1）で E2E が落ちる原因を直して取り込む

## 基本情報
- **計画書ID**: plan_I432
- **関連イシュー**: #432
- **Draft PR**: #575
- **作成根拠資料**: docs/issues/open/I432.md（起点イシュー・GitHub #432 の本文の写し）
- **実装後評価**: docs/reviews/open/I432_review.md
- **作成日**: 2026-11-18

## 1. 背景/目的
- Dependabot の #377（`@playwright/test` 1.59.1 → 1.65.0）は、10-29 から毎回 CI の E2E だけが落ち、3 週間取り込まれなかった
- 2026-11-17 の午後から GitHub の `ubuntu-latest` が Ubuntu 26.04 になり、今の 1.59.1（26.04 に非対応）ではどの PR でも E2E がブラウザを入れる段で落ちる（I492 の PR #571 で判明・#432 のコメント 2026-11-18）
- 目的: #377 が落ちる原因を直し、Ubuntu 26.04 に対応した Playwright 1.65 系を取り込んで、E2E を含む CI を緑に戻す

### 調査結果
- **原因の概要**: CI の E2E は Node.js 18 で動いているが、Playwright 1.65 は Node.js 20 以上でないと動かない。そのため #377 の E2E は、テストに入る前の「Playwright を入れる段」で毎回止まっていた
- **エラーの詳細**（#377 の最新の実行 run 43364867698・2026-11-13・ランナーは Ubuntu 24.04）:
  - 落ちた手順: `Install Playwright dependencies`（`npm ci && npx playwright install --with-deps chromium`）
  - `npm ci` が `EBADENGINE`（`@playwright/test@1.65.0`・`playwright@1.65.0`・`playwright-core@1.65.0` が `node: '>=20'` を要求、今は `v18.20.8`）を警告した後、`npx playwright install` が `Playwright requires Node.js 20 or higher.` を出して exit 1
  - 10-29・11-04・11-11・11-13 の 4 回とも同じ段で失敗（Ubuntu 26.04 への切り替えの前から）
- **詳細な原因分析**:
  1. `.github/workflows/e2e.yml:43` の `actions/setup-node` が `node-version: '18'`
  2. `@playwright/test` は 1.6x のどこかで `engines.node` を `>=18` から `>=20` に上げた（1.59.1 の lock は `>=18`・1.65.0／1.65.1 は `>=20`。npm の登録簿で 2026-11-18 に確認）
  3. Dependabot は npm の版だけを上げ、CI の Node.js の版は上げない。CI の赤は「E2E は必須チェックでない」ためマージを止めず、直すイシュー（#432）は 11-10 に起票されたが着手されていなかった
  4. Node.js 18 は 2025-03-27 にサポートが終わっている（`rules/react-coding-standards-integrated.md` §0 の前提は Node.js 26 LTS）
- **問題の根本原因（コードの箇所）**: `.github/workflows/e2e.yml:43` `node-version: '18'`
- **#376 の状態**: 手元の E2E のコンテナのイメージを `v1.65.1-jammy@sha256:b0ee5ce5…6dd8` にする版上げ。CI は E2E を含め全部緑（CI の E2E はこのイメージを使わないため）
- **最新の版**: `@playwright/test` の `latest` は 1.65.1（2026-11-18・npm の登録簿）。Ubuntu 26.04 に対応（#432 のコメント・`playwright-core` の中身で確認済み）
- **テストの件数の基準**: develop で最後に E2E が通った実行（run 44046395589・2026-11-17・1.59.1・Ubuntu 24.04）は `Running 19 tests` → `18 passed`・`1 flaky`（`tests/settings.spec.ts:12` の TC-28・再試行で合格）
- **1.59.1 の記載の全件**（`grep -rn "1\.59\.1"`・記録の closed を除く）: `e2e/package.json:10`・`e2e/package-lock.json`・`docker-compose.yml:197`・`docs/runbooks/frontend-verify.md:13`（ほかは I492 の記録 1 行だけ）
- **Node.js 18 の記載**: `.github/workflows/e2e.yml:43`（本イシュー）・`ci.yml:101,118,138,157`・`dependency-audit.yml:67`・`frontend/Dockerfile:2`・`frontend/Dockerfile.dev:2`（画面のビルドの土台。#551 の範囲）
- **環境前提**: `docker compose ps` で db・backend・frontend・redis が稼働中。ホストの `npm` は登録簿に届く（キャッシュは `$TMPDIR` に向ける必要あり・`~/.npm` はサンドボックスで書けない）
- **スパイク（未実証）**: 手元の e2e コンテナで 1.65.1 を一時的に入れて E2E を流そうとしたが、`RATELIMIT_ENABLE=false docker compose …`（手順書の形）は前置きがあるためサンドボックスの外で動く対象（`docker *`）に当たらず、`.env` を読めずに起動前に止まった。前置きなしで流すとログインの制限（5 回／5 分）で落ちるため、手元の全件の実行はしない。1.65 でテストそのものが落ちるかは「未実証」とし、実装ステップ 1 の push の後の CI の E2E（全件・制限なし・Ubuntu 26.04）を確かめのゲートにする（`docs/runbooks/workflow.md`：E2E は CI が正）
- **既存の決定論テストの事前実行**: `test_i213_dependabot.sh` pass=17 fail=0・`test_i182_secret_gates.sh` pass=54 fail=0（どちらも失敗の注入〔FG〕つき）

## 2. 受け入れ条件
- [ ] AC1: #377 で E2E が落ちた原因（テスト名と理由の要約）が計画書に記録されている（→ 本書 §1 調査結果。テストに入る前の段で落ちたのでテスト名は無い）
- [ ] AC2: `@playwright/test` 1.65.1 で、E2E を含む CI が全部緑になる
- [ ] AC3: 原因が不安定なテストだった場合は、続けて流しても通ることを確かめている（→ 原因は Node.js の版で、不安定なテストではない。ただし基準の時点で不安定だった TC-28 の扱いは §8 R2）
- [ ] AC4: #377 と #376 が、取り込み済みとして閉じられている（PR #575 へのリンクつきのコメントを付けて閉じる）
- [ ] AC5: 既存の E2E のテストの件数を減らしていない（CI の `Running N tests` が 19 以上）

## 3. 影響範囲
- Backend: なし
- Frontend: なし（`frontend/` は触らない。画面のビルド・テストの Node.js 18 は #551）
- DB: なし
- Config/Infra:
  - `.github/workflows/e2e.yml`（E2E のジョブの Node.js）— 安全装置の集合（`.github/*`）に当たる
  - `e2e/package.json`・`e2e/package-lock.json`（CI の `npm ci` と、手元の e2e コンテナの既定コマンド `npm install` が入れるもの）
  - `docker-compose.yml` の `e2e` サービスのイメージ（`--profile e2e` のときだけ使う。Dockerfile・ビルドの対象には波及しない）
  - `docs/runbooks/frontend-verify.md:13`（ホストに入れる OS の部品を調べるコマンドの版）

## 4. 変更点一覧（具体）
### 修正アプローチ
E2E のジョブの Node.js を規約の前提の 26 に上げ、Playwright を 1.65.1 に上げる。手元の E2E のコンテナのイメージも同じ 1.65.1 にそろえ、版を書いた手順書も直す。Dependabot のブランチにはコミットせず、このブランチで同じ版上げを行って、#377・#376 は取り込み済みとして閉じる。

| ファイル | 修正方針 | 変更内容 |
|---|---|---|
| `.github/workflows/e2e.yml:43` | Playwright 1.65 が動く Node.js にする | `node-version: '18'` → `node-version: '26'`。ほかの行（permissions・パスワードの伏せ字・action の SHA 固定・`cache`）は変えない |
| `e2e/package.json:10` | Ubuntu 26.04 に対応した最新の安定版にする（完全一致の固定は今のまま） | `"@playwright/test": "1.59.1"` → `"1.65.1"` |
| `e2e/package-lock.json` | `package.json` と一致させる | ホストで `npm install --save-exact @playwright/test@1.65.1`（`e2e/` で・キャッシュは `$TMPDIR`）で作り直す。変わるのは `@playwright/test`・`playwright`・`playwright-core`（と、それらが引く `fsevents` の任意の依存）の版・integrity・engines だけ |
| `docker-compose.yml:197` | 手元の E2E のイメージを npm の版とそろえる（#376 と同じ値） | `mcr.microsoft.com/playwright:v1.59.1-jammy@sha256:8a0360d3…c8ff` → `mcr.microsoft.com/playwright:v1.65.1-jammy@sha256:b0ee5ce5e14ac42c394c0564a0a30adbda052153c611561bb2d31263593d6dd8` |
| `docs/runbooks/frontend-verify.md:13` | 手順書の版を今の版に合わせる | `npx -y playwright@1.59.1 install-deps --dry-run chromium` → `playwright@1.65.1` |

## 5. 実装手順（ステップ）
1. （未知リスク先行）`e2e.yml` の Node.js・`e2e/package.json`・`e2e/package-lock.json` を変えて commit する。push は review-gate の最初（`docs/runbooks/workflow.md`「GitHub への書き込みの時点」）。CI の E2E（Ubuntu 26.04・全件）がこのステップの確かめ → TC-03・手動 No.1・No.2。テストそのものが 1.65 で落ちたら fix-loop で原因を切り分ける（テストの古い書き方なら直す範囲を計画変更記録に書いて plan-review を通り直す）
2. `docker-compose.yml` の e2e のイメージを 1.65.1 にする（ステップ 1 と並行可・依存なし）→ TC-01・手動 No.3
3. `docs/runbooks/frontend-verify.md:13` の版を直す（ステップ 1 と並行可）→ 手動 No.4
4. test-gate 段階の手動テスト No.5 で、#377 と #376 に「PR #575 で同じ版上げを取り込む」とコメントして閉じる（No.1・No.2 で CI が緑と確かめた後。閉じるのは取り消せる操作〔reopen〕）→ 手動 No.5
- サービスの再起動: 不要（手元の e2e コンテナは実行のたびに作り直す `run --rm`。次に流すとき新しいイメージを引く）

## 6. テスト計画
### 自動
- 決定論ゲート（review-gate が実走）: `test_i213_dependabot.sh`（土台イメージの指紋固定・action の SHA 固定・pull_request のワークフローに secrets を置かない・伏せ字の順）・`test_i182_secret_gates.sh`（e2e.yml の権限が読み取りだけ）→ TC-01・TC-02。どちらも失敗の注入つきの既存のテストで、今回の変更で守りが外れていないことを見る
- CI の E2E（全件・PR #575）→ TC-03
- 新しい決定論テストは作らない: 「Node.js の版が Playwright の要求を満たす」は、満たさないと CI の E2E が導入の段で必ず落ち、すぐ気づける（`plan-writing-rules.md`「決定論テストの対象の選び方」）
- テストレベル: 単体・結合の変更なし（アプリのコードを変えない）。E2E（CI）だけ
### 手動（すべて Claude）
- No.1 CI の E2E のログで、Node.js が 26、Playwright が 1.65.1、ランナーが Ubuntu 26.04、`Running N tests` の N が 19 以上、`N failed` が無い
- No.2 E2E 以外の CI のジョブが全部成功
- No.3 手元の e2e コンテナ（新しいイメージ）で Playwright が 1.65.1 で、イメージに入っている chromium をそのまま使える
- No.4 手順書の版の記載が 1.65.1
- No.5 #377・#376 が閉じられ、PR #575 へのコメントが付いている

## 7. ロールバック
- PR #575 の revert（設定とロックファイルだけ。DB・データには触らない）。revert すると E2E は Ubuntu 26.04 で再び導入の段で落ちる状態に戻る

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 1.59.1 → 1.65.1 の間の振る舞いの変化で、既存の E2E が落ちる（手元で事前に確かめられなかった） | ステップ 1 を最初に置き、CI の E2E で確かめる。落ちたら fix-loop で原因を特定し、テスト・アプリの直しが要るなら範囲を計画変更記録に書いて plan-review を通り直す | 回避 |
| R2: develop で既に不安定な `settings.spec.ts` の TC-28（1.59.1 でも再試行で合格）が、この PR でも flaky になる | 1.65 で新しく出た不安定さと区別するため、No.1 で flaky のテスト名を記録する。TC-28 だけが flaky なら版上げの回帰とはせず、retro で別に扱う（起票を判断） | 受け入れ |
| R3: `actions/setup-node` v4.4.0 が `node-version: '26'` を解決できない | CI のログ（No.1）で Node.js の版を確かめる。解決できなければ fix-loop で直す | 回避 |
| R4: E2E のジョブ（Node.js 26）と画面のビルド・テスト（Node.js 18）で版が一時的に分かれる | E2E のジョブは `e2e/` の依存（Playwright・dotenv）だけを入れ、画面は docker の frontend コンテナ（Node.js 18）で動かすので、互いに影響しない。画面側は #551 で 26 に上げる | 受け入れ |
| R5: #377・#376 を閉じた後、Dependabot が同じ版上げを作り直す | このブランチのマージ後は develop が同じ版（1.65.1）を持つので、Dependabot は作り直さない。マージ前に閉じても、閉じた版上げは Dependabot が無視する | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている:
- Dependabot のブランチには直接コミットしない（解決方針）
- ほかの開いている Dependabot の PR・E2E を必須チェックに足す設定は範囲外（スコープ）
- 受け入れ条件の「1.64.1（またはそれ以降）」は Ubuntu 26.04 に対応する 1.65 系以降として読む（#432 のコメント 2026-11-18・ユーザーの方針「ハーネス・ループの BP の観点でベストなやり方で」）
- 実行環境を `ubuntu-24.04` に固定する案は採らない（同コメント・ユーザーの指摘）
Claude が決めた（技術的な選択と理由）:
- 取り込み方: 自分のブランチで同じ版上げを行い、#377・#376 は閉じる（Dependabot の PR に直しを足して作り直させる案より、1 本の PR で Node.js とイメージと npm をそろえて確かめられ、版のずれ〔#377 は 1.65.0・#376 は 1.65.1〕も無くせるため）
- Playwright の版: 1.65.1（`latest`・#376 のイメージと同じ。1.65.0 にしない）
- Node.js の版: 26（規約 §0 の前提の版。Playwright の最低限の 20 や 22 にしない — 規約の方針〔最新の Active LTS〕に合わせ、#551 で画面側を上げたときにそろう）
- 規約 §16 の「#551 の行の道具・版を他のイシューで先に入れない」との関係: §16 は画面（`frontend/`）のコードとの差の表で、E2E のジョブ（`e2e/` の別の package・画面と別に動く）は対象外と読む。Playwright 1.65 が Node.js 20 以上を要るので、#551（Vite・Vitest への移行・大きい）を待つと E2E が止まったままになる。画面側の Node.js 18 は触らない
- 取り込む順: #376 と #377 を同じ PR で取り込む（手元と CI の版をそろえる）
- 新しい決定論テストは作らない（§6 の理由）
- 1.65 でのテストの事前の確かめは CI に任せる（§1 スパイク。サンドボックスの中から制限なしで手元の E2E を流せないため）
- 一覧 docs/reviews/backlog/I213.md F3（`e2e.yml` のパスワードを `GITHUB_ENV` に置く）: 残す — 秘密の扱いの話で、本イシューの目的（Node.js・Playwright の版）と別。今回 e2e.yml のその部分は変えない
- 一覧 FILE=- の行（I224 F9・I223 B1〜B4）: 残す — ハーネス・bot の話で本イシューと無関係
- `.github/` を変えること（`docs/runbooks/workflow.md`「止めて聞く条件」2）: 変えるのは Node.js の版の 1 行だけで、権限・秘密・固定などの守りは緩めない（TC-01・TC-02 が確かめる）。直し方は grill-me の報告（2026-11-18）でユーザーに示した後に `/plan-issue` が打たれた。マージは GitHub でユーザーが承認する。過去の `.github` を変えたイシュー（I493）と同じく、計画レビューの高リスク判定と敵対的レビューで確かめて進める
セキュリティ・BP の確認:
- 入力・認証・認可・個人情報・OWASP: 該当なし（アプリのコードを変えない）。セキュリティ影響は CI の設定と依存だけ
- 依存の既知の脆弱性: `@playwright/test` 1.65.1 は実装のステップで `npm audit`（`e2e/`）を流して確かめる（→ TC-04。npm audit の基準は high/critical を直す対象）
- 秘密: e2e.yml のパスワードの作り方・伏せ字・権限は変えない（TC-01・TC-02）
- P3/P5/P8 影響なし（DB・非同期・新しいインフラなし）／P6 影響なし（画面なし）／P9 影響なし（個人情報なし）
- 要件の範囲: 受け入れ条件を超える変更はない（画面の Node.js 18 は #551 に残す）
Danger Ops（有無/手順/ロールバック）:
- 無（設定と依存の変更・revert で戻せる。DB・データに触らない）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | `.github/workflows/e2e.yml` の差分が `node-version` の 1 行だけで、`permissions: contents: read`・パスワードの `::add-mask::` が `GITHUB_ENV` の書き込みより先・action の SHA 固定・secrets を使わないことが保たれている（TC-01・TC-02 がそれぞれ失敗の注入つきで確かめる） |
| V2 | 1 | 読んで可 | `docker-compose.yml` の e2e のイメージが `@sha256:` の指紋で固定され、その値が #376 の値と一字一句同じ（TC-01 の I1 が固定を、手動 No.3 が実際に引けることを確かめる） |
| V3 | 2 | 読んで可 | AC2・AC5 の確かめが CI の実際の E2E の結果（テストに入った後の `Running N tests` と `passed`）に基づき、導入の段で止まった赤や「スキップで緑」を合格にしていない（手動 No.1 の期待結果の書き方） |
| V4 | 3 | 読んで可 | Node.js 26 に上げても、E2E のジョブ以外（画面のビルド・テスト・依存の監査）が Node.js 18 のまま影響を受けない（変更点が e2e.yml だけ）。§16 の #551 との分担の読み方が規約の文言と食い違っていない |
