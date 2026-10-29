# I213 計画書: Dependabot を点検し、動いて役に立つ形に直す

## 基本情報
- **計画書ID**: plan_I213
- **関連イシュー**: #359
- **Draft PR**: #374
- **作成根拠資料**: docs/issues/open/I213.md（起点イシュー・設計確認メモ Q1〜Q9）
- **実装後評価**: docs/reviews/open/I213_review.md
- **作成日**: 2026-10-29

## 1. 背景/目的
- `.github/dependabot.yml`（I028）があるのに、Dependabot の PR が 1 件も来ていなかった。原因はリポジトリの設定で Dependabot の機能が無効だったこと（設計確認メモ Q1。2026-10-29 にユーザーが有効にし、直後に PR が 14 件〔#360〜#373〕届いた）。
- 目的: Dependabot が、アプリ・e2e・Docker イメージ・GitHub Actions・pre-commit の新しい版を、扱いやすい量の PR で届ける。出たばかりの版は待ち、セキュリティの修正はすぐ届く。届いた PR は CI だけで判定でき（Dependabot の PR でも CI が正しく動く）、取り込んだ版が手元にも反映される。

### 調査結果
- **原因の概要**: (1) 機能が無効だった（解決済み）。(2) 有効にした後に分かった問題が 3 つある: Dependabot の PR では E2E が必ず落ちる／`target-branch` を書いているためセキュリティの修正の PR に設定が効かない／Docker のイメージが「同じ名前のまま中身が入れ替わる」書き方なので、同じ版の中の更新を Dependabot が PR にできない。
- **詳細**:
  - E2E: 14 件すべてで `E2E Tests (Playwright)` だけが fail（ほかの CI は #365・#373 の major の中身の問題を除いて pass）。ログは `E2E_TEST_PASSWORD:`（空）→ `e2e/global-setup.ts:14` の「E2E_TEST_PASSWORD is not set」。GitHub は Dependabot が起こした実行に Actions の secrets を渡さない。secrets を使うワークフローは `.github/workflows/e2e.yml:33`・`:50` だけ（`grep -rn "secrets\." .github/workflows/`）。
  - `target-branch`: 公式の設定の説明（dependabot-options-reference）に「`target-branch` を書くと、その package-ecosystem の設定はセキュリティの修正に効かなくなる（セキュリティの修正は常に既定のブランチ宛て）」。既定のブランチは develop（`gh repo view`）なので、`target-branch: develop` は書かなくても同じ宛先になる。
  - Docker: `backend/Dockerfile:2`（`python:3.11-slim`）・`frontend/Dockerfile:2,20`（`node:18-alpine`・`nginx:alpine`）・`frontend/Dockerfile.dev:2`（`node:18-alpine`）・`docker-compose.yml:4,25,172,195`（`postgres:15-alpine`・`redis:7-alpine`・`mcr.microsoft.com/playwright:v1.59.1-jammy`・`nginx:alpine`）。版の上げ方を Q4 で「環境の版を変えるものは出させない」と決めたので、残る更新は同じタグの中身の更新だけで、タグだけの書き方では Dependabot が PR を出せない。中身の指紋（digest）を併記すると Dependabot が指紋を上げる PR を出せる（action の SHA 固定と同じ考え）。今の指紋は `docker buildx imagetools inspect` で取れる（6 つとも取得できた）。
  - 待つ日数: `cooldown` の `semver-major-days` などの版の大きさ別の日数は pip・npm（ほか一部）だけが対応し、docker・docker-compose・github-actions・pre-commit は `default-days` だけ（公式の表）。
  - ラベル: `labels` を書くと既定のラベルを置き換える。無いラベルは無視される。`dependencies` は Dependabot が最初の PR で作った（`gh label list`）。`track:app`・`track:harness` は既にある。
- **スパイク（2026-10-29）**:
  1. uv（成立＝見張れないことを確認）: Dependabot の uv は 0.13.5（dependabot-core の `uv/Dockerfile` の `FROM ghcr.io/astral-sh/uv:0.13.5`）。ハーネスの `scripts/claude/tests/pyproject.toml` は `required-version = "==0.13.6"`（I211）。写しで `pipx run --spec uv==0.13.5 uv lock --project <写し> --upgrade-package pre-commit` → `error: Required uv version ==0.13.6 does not match the running version 0.13.5`・exit 2。Dependabot に uv を見張らせると、ロックファイルを作り直せず毎回失敗する（9 の D2）。
  2. Playwright（成立）: `mcr.microsoft.com/playwright:v1.59.1-jammy` で `@playwright/test@1.59.1` を入れて `npx playwright install chromium` → 何もダウンロードせず exit 0（約 4 秒）。`v1.50.0-jammy`（版がずれたイメージ）で同じことをする → その版のブラウザ（chromium 1217）を約 30 秒で入れて exit 0。e2e のコンテナの起動時にこの 1 行を足せば、イメージと `@playwright/test` の版がずれても動く（9 の D4）。
  3. 設定の形の検証（成立）: 下書きの設定を `check-jsonschema==0.38.2 --builtin-schema vendor.dependabot` で検証 → `ok`。package-ecosystem の綴り・`applies-to` の値・`default-days` の綴り・日数の型をそれぞれ壊すと exit 1（4 種とも）。
  4. `--renew-anon-volumes`（成立）: `docker compose config --format json` で、名前の無い保存領域は frontend の `/app/node_modules` だけ。db（`postgres_data`）・redis（`redis_data`）は名前付きなので、起動のたびに作り直しても消えない。
  5. action の SHA（取得済み）: actions/checkout v4.4.0 `11d5960a326750d5838078e36cf38b85af677262`／actions/setup-python v5.6.0 `a26af69be951a213d495a4c3e4e4022e16d87065`／actions/setup-node v4.4.0 `49933ea5288caeca8642d1e84afbd3f7d6820020`／actions/upload-artifact v4.6.2 `ea165f8d65b6e75b540449e92b4886f43607fa02`／pre-commit/action v3.0.1 `2c7b3805fd2a0fd8c1884dcaebf91fc102a13ecd`／astral-sh/setup-uv v10.3.3 `68559e99cc807c1eb7e9238fd43a15bba460eec2`（実装時に取り直して計画変更記録に書く）
- **ログイン画面のパスワードの決まり**: `frontend/src/pages/Login.tsx:32` は 8 文字以上。`seed_e2e`（`backend/accounts/management/commands/seed_e2e.py:67,77,93`）は `create_user(password=...)` で強さを確かめない。→ `openssl rand -hex 24`（48 文字・記号なし）で足りる。
- **書き方に頼っている既存のテスト**: `scripts/claude/tests/test_i204_tool_sync.sh:113` が setup-uv を `@vX.Y.Z` の形で求める（SHA にすると落ちる）。`test_i182_secret_gates.sh` は `pre-commit/action@` で始まるかだけを見る（SHA でも通る）。ほかのテストは `uses` の書き方を見ていない。
- **環境の前提**: docker compose・pipx（uv 0.13.6・pre-commit）あり。`gh` は bot（管理者権限なし）。
- **ベースライン**: develop の CI は全緑（PR #357）。Dependabot の 14 件は E2E が全件 fail。

## 2. 受け入れ条件
イシューの AC と、計画での読み替え（読み替えの理由は 9）:
- [x] AC1: PR が来なかった原因が記録されている（イシューの設計確認メモ Q1）
- [x] AC2: Dependabot が実際に動き、版上げの PR が確認できる（#360〜#373）
- [ ] AC3: `.github/dependabot.yml` が、backend の pip・frontend の npm・e2e の npm・Docker（`/backend`・`/frontend` の Dockerfile と `docker-compose.yml`）・GitHub Actions・pre-commit を見張る。**ハーネスの uv は見張らない**（スパイク 1。理由と代わりを runbook に書く。9 の D2）
- [ ] AC4: minor・patch が見張りの対象ごとに 1 つの PR にまとまり（普段の版上げとセキュリティの修正の両方）、major は 1 件ずつ。`cooldown` は全部の対象で `default-days: 7`、pip・npm は `semver-major-days: 14`（ほかの対象は版の大きさ別の日数に対応していない）
- [ ] AC5: `target-branch` を書かない（セキュリティの修正にも設定が効く）
- [ ] AC6: Docker の土台イメージの環境の版を変える版上げ（python の major・minor、node・postgres・redis の major）が `ignore` されている
- [ ] AC7: Docker の土台イメージがすべて「タグ＋指紋（`@sha256:`）」で書かれ、Dependabot が同じ版の中の更新を PR にできる
- [ ] AC8: `.github/workflows/*.yml` のすべての action がコミットの SHA で固定され、横に版が書かれている
- [ ] AC9: `.github/workflows/e2e.yml` が secrets を使わず、ジョブごとにランダムなパスワード（伏せ字）を作る。pull_request で動くワークフローに `secrets.` が無い
- [ ] AC10: 手元の e2e のコンテナが、起動時に `@playwright/test` の版のブラウザを入れてから流す（イメージと版がずれても動く）
- [ ] AC11: 標準の起動コマンドが `docker compose up -d --build --renew-anon-volumes`（`common-commands.md`・`frontend-verify.md`・`worktree.md`）。依存の一覧ファイルや土台イメージの指紋を変えて起動し直すと、新しい版が入る（指紋を併記するので `--pull` は要らない）
- [ ] AC12: `dependency-audit.md` に Dependabot の節がある（見張りの対象と見張らないもの・PR の受け取り方〔minor・patch と security は CI が緑ならユーザーがマージ／CI が赤と major はイシュー〕・ラベル・待つ日数・取り込んだあと手元でやること・依存監査との役割分担・止まったときに見る場所・action と土台イメージの固定の決まり）
- [ ] AC13: `.github/dependabot.yml` の書き間違いを pre-commit（`check-dependabot`）が止める（手元のコミット時と CI の両方）
- [x] AC14: Malware alerts が On（2026-10-29）
- [ ] AC16: 決定論テストの対象の選び方（守るのは壊れても気づきにくく被害が大きい決まりだけ・設定の写しと意図的な変更の検知は作らない）が `docs/runbooks/plan-writing-rules.md` にあり、計画レビュー役・コードレビュー役がそれを参照する観点を 1 行ずつ持つ（計画変更記録 3）
- [ ] AC15（マージ後）: 新しい設定で Dependabot が全部の対象で正常に動き（実行記録）、Dependabot の PR で E2E が pass し、新しい設定に置き換わった古い PR（#360〜#373 の該当分）が理由つきで閉じられている。major の残りは一覧で示す

## 3. 影響範囲
- Backend: なし（コードは変えない）。`backend/Dockerfile` の `FROM` の書き方だけ（同じイメージを指紋で固定）
- Frontend: なし（コードは変えない）。`frontend/Dockerfile`・`frontend/Dockerfile.dev` の `FROM` の書き方だけ
- DB: なし（`docker-compose.yml` の db のイメージは同じものを指紋で固定。データの保存領域は変えない）
- E2E: `docker-compose.yml` の e2e の command に 1 行足す。`e2e/global-setup.ts`・`e2e/playwright.config.ts`・`e2e/.env.e2e.example` は説明の文言だけ。手元のパスワード（`e2e/.env.e2e`）は変えない
- Config/Infra: `.github/dependabot.yml`・`.github/workflows/ci.yml`・`e2e.yml`・`dependency-audit.yml`（SHA 固定。e2e.yml はパスワード）・`.pre-commit-config.yaml`（フック 1 つ追加）・runbook（`dependency-audit.md`・`common-commands.md`・`frontend-verify.md`・`worktree.md`・`danger-ops.md`）・`CLAUDE.md`（参照の見出しの文言だけ）
- 依存関係ファイル: `backend/requirements*.txt`・`frontend/package*.json`・`e2e/package*.json` は変えない。Dockerfile・docker-compose.yml の波及は上のとおり（同じイメージの固定だけで、入る部品は変わらない）
- GitHub 上の操作（マージ後）: Dependabot の古い PR を閉じる（開き直せる）

## 4. 変更点一覧（具体）

### 修正アプローチ
Dependabot の設定を「見張る対象を全部入れ、小さい版上げはまとめ、出たばかりの版は待ち、セキュリティの修正にも同じ設定が効く」形に書き直す。そのうえで、Dependabot の PR を CI だけで判定できるように、CI から secrets を無くし（E2E のパスワードを毎回作る）、action とイメージを中身で固定して Dependabot が上げられる形にする。手元は「毎回作り直す」起動コマンドと「e2e は起動時にブラウザを入れる」で、取り込んだ版に自動で追いつく。設定の書き間違いとこれらの決まりは、pre-commit とハーネスのテストで機械的に止める。

### 4-1. `.github/dependabot.yml`（書き直し）
修正方針: 8 つの対象を同じ形で並べる。`target-branch` は書かない（既定のブランチ develop 宛てになる）。
- 共通: `schedule: {interval: "weekly"}`・`cooldown.default-days: 7`・`groups`（下）。PR の上限は既定の 5 のまま（書かない・計画変更記録 5）
- `groups`（全部の対象）:
  ```yaml
  groups:
    minor-and-patch:
      applies-to: version-updates
      update-types: ["minor", "patch"]
    security-minor-and-patch:
      applies-to: security-updates
      update-types: ["minor", "patch"]
  ```
- 対象・ラベル・追加の設定:
  | package-ecosystem | directory | labels | 追加 |
  |---|---|---|---|
  | `pip` | `/backend` | `dependencies`・`track:app` | `cooldown.semver-major-days: 14` |
  | `npm` | `/frontend` | `dependencies`・`track:app` | `cooldown.semver-major-days: 14` |
  | `npm` | `/e2e` | `dependencies`・`track:app` | `cooldown.semver-major-days: 14` |
  | `docker` | `/backend` | `dependencies`・`track:app` | `ignore`: `python` の `version-update:semver-major`・`version-update:semver-minor` |
  | `docker` | `/frontend` | `dependencies`・`track:app` | `ignore`: `node` の `version-update:semver-major` |
  | `docker-compose` | `/` | `dependencies`・`track:app` | `ignore`: `postgres`・`redis` の `version-update:semver-major` |
  | `github-actions` | `/` | `dependencies`・`track:harness` | なし |
  | `pre-commit` | `/` | `dependencies`・`track:harness` | なし |
- 冒頭のコメント: 受け取り方は `docs/runbooks/dependency-audit.md`、ハーネスの uv を見張らない理由（1 行）

### 4-2. `.github/workflows/ci.yml`・`e2e.yml`・`dependency-audit.yml`（SHA 固定）
修正方針: すべての `uses:` を `<owner>/<repo>@<40 桁の SHA> # <版>` にする（版は今と同じ系列の最新。スパイク 5）。
- `actions/checkout@v4` → `@11d5960a… # v4.4.0`、`actions/setup-python@v5` → `@a26af69b… # v5.6.0`、`actions/setup-node@v4` → `@49933ea5… # v4.4.0`、`actions/upload-artifact@v4` → `@ea165f8d… # v4.6.2`、`pre-commit/action@v3.0.1` → `@2c7b3805… # v3.0.1`、`astral-sh/setup-uv@v10.3.3` → `@68559e99… # v10.3.3`（今の行末のコメントは、意味が残るものだけ版のコメントの後ろに残す。setup-uv の「配布元は細かい版のタグだけを出す」はタグの書き方の説明で SHA にすると意味が無いので消す・計画レビュー 2 の Warning）
- 版を上げる（v4 → v7 など）のは固定の後に Dependabot の PR で受け取る（設計確認メモ Q7）

### 4-3. `.github/workflows/e2e.yml`（パスワードを毎回作る）
修正方針: checkout の直後に 1 step 足し、以降の step の `E2E_TEST_PASSWORD: ${{ secrets.E2E_TEST_PASSWORD }}` を消す（`$GITHUB_ENV` で後の step に渡る）。
```yaml
      - name: Generate one-time E2E password
        # I213: CI の使い捨ての DB の試験アカウントだけに使う。secrets にしない（Dependabot の PR にも secrets は渡らないため）
        run: |
          pw="$(openssl rand -hex 24)"
          echo "::add-mask::$pw"
          echo "E2E_TEST_PASSWORD=$pw" >> "$GITHUB_ENV"
```
- 「Initialize E2E database」の `docker compose exec -T -e E2E_TEST_PASSWORD ...` はそのまま（ホストの環境変数を渡す）

### 4-4. 土台イメージの指紋の併記
修正方針: タグはそのまま残し、`@sha256:<指紋>` を足す（指紋は実装時に `docker buildx imagetools inspect` で取り直す。マルチアーキテクチャの一覧の指紋）。
- `backend/Dockerfile:2` `FROM python:3.11-slim@sha256:… AS base`
- `frontend/Dockerfile:2` `FROM node:18-alpine@sha256:… as build`・`:20` `FROM nginx:alpine@sha256:…`
- `frontend/Dockerfile.dev:2` `FROM node:18-alpine@sha256:…`
- `docker-compose.yml` の `postgres:15-alpine@sha256:…`・`redis:7-alpine@sha256:…`・`mcr.microsoft.com/playwright:v1.59.1-jammy@sha256:…`・`nginx:alpine@sha256:…`

### 4-5. `docker-compose.yml` の e2e の command
```yaml
    command: sh -c "npm install && npx playwright install chromium && npm test"   # （今のコメント）＋ I213: イメージと @playwright/test の版がずれても、その版のブラウザを入れてから流す（版が同じなら何もしない）
```

### 4-6. `.pre-commit-config.yaml`
```yaml
  - repo: https://github.com/python-jsonschema/check-jsonschema
    rev: 0.38.2
    hooks:
      - id: check-dependabot
```
- 0.39.0 は 2026-10-26 に出たばかりなので、待つ日数（7 日）に合わせて 1 つ前を使う。以後は Dependabot（pre-commit）が上げる
- CI の `Backend Lint & Security` の `pre-commit/action`（`SKIP: eslint`）で全ファイルに走る

### 4-7. 新規 `scripts/claude/tests/test_i213_dependabot.sh`
修正方針: 壊れても気づきにくく、壊れると被害が大きい決まりだけを機械的に確かめる（設定の中身の写しはしない・計画変更記録 2）。YAML は PyYAML で読む（`run-all.sh` の uv の環境）。各項目に、写しを壊して不合格になる FG を付ける。中身は `docs/tests/open/I213_auto_test.md` の TC-01 の表。
- D2: dependabot.yml に `target-branch` が無い
- W1・W2・W3: 全 `uses:` が SHA＋版のコメント／pull_request で動くワークフローに `secrets.` が無い／e2e.yml の伏せ字の順
- I1: 土台イメージ（Dockerfile の外部の `FROM` と compose の `image:` が全部 `@sha256:<64 桁>`）
- V1: compose の名前の無い保存領域が frontend の `/app/node_modules` だけ（`--renew-anon-volumes` で消えてよいものだけ）

### 4-8. `scripts/claude/tests/test_i204_tool_sync.sh`
- `:113` の setup-uv の形を `astral-sh/setup-uv@[0-9a-f]{40}` に変え、メッセージを「setup-uv はコミットの SHA で固定する（版は行末のコメント・I213）」にする。FG の `uv_major_tag`（`@v10`）は引き続き不合格。SHA でない細かい版のタグ（`@v10.3.3`）も不合格にする FG を足す

### 4-9. runbook・説明の文言
- `docs/runbooks/dependency-audit.md`: 見出しを「依存監査と Dependabot の運用」にし、「## Dependabot（版上げの PR）」の節を足す（AC12 の中身。届いた PR の流れ: CI 緑の minor・patch・security → ユーザーがマージ／CI 赤・major → `/issue-bootstrap` でイシュー〔タイトルに PR 番号〕・PR は閉じずに通知として残す／取り込んだあと: 標準の起動コマンドだけ／見張らないもの: ハーネスの uv〔理由〕・環境の版を変える版上げ〔別イシュー〕／役割分担: 監査は「今の版の穴を毎日見つける」、Dependabot は「直した版を PR で届ける」。監査が fail してセキュリティの修正の PR が来ていればそれを通す／止まったとき: Settings → Advanced Security・Actions の「Dependabot Updates」の実行記録／新しい action・イメージを足すときは SHA・指紋で書く／土台イメージの OS の修正を急ぐときは手で指紋を上げてよい〔`docker buildx imagetools inspect <タグ>` の `Digest:`〕／既定のブランチを変えると Dependabot の PR の宛先も変わる〔`target-branch` は戻さない〕・セキュリティ設計レビュー）
- `docs/runbooks/common-commands.md:14`・`docs/runbooks/frontend-verify.md:19`・`docs/runbooks/worktree.md:152,188,189`: `docker compose up -d` → `docker compose up -d --build --renew-anon-volumes`（理由を 1 行: 依存・イメージの変更を毎回取り込む。名前の無い保存領域は frontend の node_modules だけで、DB は消えない）
- `docs/runbooks/danger-ops.md:43`: 「`E2E_TEST_PASSWORD` は試験アカウントの値でログは伏せ字」→「CI の E2E のパスワードはジョブごとに作る使い捨ての値（secrets を使わない・ログは伏せ字・I213）」
- `e2e/global-setup.ts:17`・`e2e/playwright.config.ts:5`・`e2e/.env.e2e.example:4`: 「CI は GitHub Secrets」→「CI は e2e.yml がジョブごとに作る」
- `CLAUDE.md`: 「依存監査（定期検知）: docs/runbooks/dependency-audit.md」→「依存監査と Dependabot: docs/runbooks/dependency-audit.md」（パスは変えない。`test_i109_dependency_audit.sh` はパスを見る）
- `docs/reviews/backlog/I211.md`: F6 の行を消す（同梱して直した）

### 4-11. 決定論テストの対象の選び方をルールに書く（計画変更記録 3）
修正方針: 計画変更記録 2 で使った判断の基準を、テストを書く人・レビュー役が同じように使えるようにする。正は 1 か所（plan-writing-rules.md）で、レビュー役は 1 行の観点と参照だけを持つ（写しを増やさない・I195 の決まり）。
- `docs/runbooks/plan-writing-rules.md`: 「否定・回帰系の決定論テストの自己検証（false-green 禁止）」の直後に「### 決定論テストの対象の選び方（写しのテストを作らない）」を足す。中身:
  - 決定論テストで守るのは「壊れても気づきにくく、壊れると被害が大きい決まり」（例: action・イメージを中身で固定する・pull_request で動くワークフローに secrets を置かない・秘密の伏せ字の順・消えてよい保存領域の範囲・知らないと踏む設定の落とし穴）
  - 作らない: 設定ファイルの中身をテストにもう一度書いて照合するもの（設定を変えるたびに両方を直すだけ。形の誤りは公式のスキーマ検証・リンターに任せる）／消すのが意図的な変更でしか起きないものの有無（文言・フックがあるか・並び）
  - 迷ったら「普通の書き方で、気づかずに壊すことがあるか」「壊れたとき、CI や画面で気づけるか」を問う。どちらも「いいえ・気づける」ならテストにしない
- `.claude/agents/plan-reviewer.md:118` と `.claude/agents/code-reviewer.md:115`（false-green の観点の行）の直後に 1 行: 「決定論テストが、設定の中身の写しや、意図的な変更でしか壊れないものを確かめていないか（過剰。`docs/runbooks/plan-writing-rules.md`「決定論テストの対象の選び方」）」

### 4-10. マージ後の GitHub 上の操作（設計確認メモ Q7）
- マージ後、Dependabot の実行記録で 8 つの対象が正常に動いたことを見る。新しい設定のまとめ PR に含まれた・`ignore` に当たる古い PR（#360〜#373）を、理由をコメントして閉じる（`gh pr close <番号> --comment "..."`）。major で残るもの（#365 `@mui/material` 5→9・#373 `@types/node` 16→26 など）は close の報告で一覧にする

## 5. 実装手順（ステップ）
1. **テストを先に**（未知の少ない順だが、決まりの形を先に固める）: 4-7 の新しいテストと 4-8 の書き換えを書き、今の実装で不合格になることを見る（Red）→ TC-01・TC-02 参照
2. **Dependabot の設定と形の検証**: 4-1・4-6 → TC-01（D2）・TC-03 参照（ステップ 1 が前提）
3. **CI の secrets をなくす・SHA 固定**: 4-3・4-2 → push して PR #374 の CI（E2E を含む）が緑になることを見る → TC-01（W）・手動 No.3 参照。`.github/workflows/**` の編集は承認画面が出る（予告済み）
4. **土台イメージの指紋・e2e のブラウザ**: 4-4・4-5 → TC-01（I1・V1）・手動 No.1・No.2・No.4 参照。Dockerfile の編集は承認画面が出る（予告済み）。ステップ 3 と並行してよい
5. **runbook・文言**: 4-9 → TC-04・手動 No.5 参照
5b. **テストの選び方のルール**: 4-11（計画変更記録 3。計画レビューのやり直しの後）→ 手動 No.9 参照
6. 影響を受ける既存のテストを流す → TC-04 参照
7. （マージ後）4-10 → 手動 No.6〜No.8

## 6. テスト計画
### 自動
- テストレベル: シェルの決定論テスト（写しを壊して不合格を確かめる FG 付き）と、pre-commit のスキーマ検証。アプリの pytest・Jest は非該当（アプリのコードを変えない）。E2E は PR の CI（e2e.yml）が流す（パスワードの作り方の変更を実地で確かめる）
- 新規 `test_i213_dependabot.sh`（TC-01）、書き換え `test_i204_tool_sync.sh`（TC-02）、`check-dependabot`（TC-03）、影響の確認（TC-04: `test_i182_secret_gates.sh`・`test_i109_dependency_audit.sh`・`test_i179_worktree_docs.sh`・`test_review_verdict.sh`・`test_i211_version_pin.sh`）
### 手動（実施者はすべて Claude）
- 手元: 標準の起動コマンドで全部が起動し DB の中身が残る・e2e が流れる（No.1・No.2）、PR の CI の E2E が secrets なしで緑・パスワードが伏せ字（No.3）、指紋が引ける（No.4）、runbook の手順の通し（No.5）
- マージ後: Dependabot の実行記録・古い PR の整理・Dependabot の PR の E2E（No.6〜No.8。ユーザーのマージの後に Claude が行う）

## 7. ロールバック
- PR を revert する（設定・ワークフロー・Dockerfile の書き方・文書の変更だけ。データの変更なし）。E2E のパスワードを secrets に戻すと Dependabot の PR の E2E がまた落ちる（secrets `E2E_TEST_PASSWORD` は消さずに残すので戻せる）
- 閉じた Dependabot の PR は開き直せる（Dependabot も出し直す）

## 8. Risk & 回避策
- R1: Dependabot の実際の動き（まとめ・待つ日数・ignore・指紋の更新・pre-commit・docker-compose）は既定のブランチに入ってからしか確かめられない → 形はスキーマ（TC-03）とテスト（TC-01）で止め、マージ後に実行記録で確かめる（No.6）。失敗したら直すイシューを立てる
- R2: 指紋で固定したイメージが手元・CI で取れない（アーキテクチャ違い）→ マルチアーキテクチャの一覧の指紋を使う（No.4 で amd64 で取れることを確かめる）
- R3: ランダムなパスワードがログに出る → `::add-mask::` を `$GITHUB_ENV` への書き込みより前に置く（TC-01 W3）。PR の CI のログで伏せ字を確かめる（No.3）
- R4: e2e のコンテナが毎回ブラウザを取りに行って遅くなる → 版が同じなら何もしない（スパイク 2・約 4 秒）。ずれたときだけ約 30 秒
- R5: `--renew-anon-volumes` が将来の名前の無い保存領域（例: DB に付けたもの）を消す → TC-01 V が名前の無い保存領域を frontend の node_modules だけに固定する
- R6: 待つ日数のうち major 14 日は pip・npm にしか効かない（docker・actions・pre-commit は 7 日）→ 受け入れる。actions の major は SHA 固定で中身が変わらず、Docker の環境の版は ignore 済み
- R7: Dependabot の uv は今後も版が遅れるので、ハーネスの uv の見張りは入れられない → 版を上げる手順は I211 の runbook のまま（手で上げる）。runbook に理由を書く
- R8: Dependabot が指紋の更新を minor・patch のまとめに入れるかは公式に書かれていない → まとめに入らなければ 1 件ずつの PR になるだけ（受け取り方は同じ）。No.6 で見る

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 原因は設定で機能が無効だった（Q1）・待つ日数 7／major 14・minor・patch をまとめる（Q2）・受け取り方とラベル・自動マージなし（Q3）・環境の版を変える版上げは ignore（Q4）・action は全部 SHA（Q5）・手元は毎回作り直す（Q6）・古い 14 件は I213 のマージまでマージせず、後で整理（Q7）・Malware alerts On・画面の Grouped security updates は Off で設定ファイルでまとめる（Q8）・E2E のパスワードは毎回作る（Q9）

Claude が決めた（技術的な選択と理由）:
- D1: `target-branch` を消す。理由: 書くとセキュリティの修正の PR にまとめ・ラベルが効かない（公式）。既定のブランチが develop なので宛先は変わらない。既定のブランチを main に戻すときは runbook の注意に従う（Dependabot の宛先も main になる）
- D2: ハーネスの uv は Dependabot で見張らない（イシューの AC の「ハーネスの道具（uv）を見張る」を読み替え）。理由: Dependabot の uv（0.13.5）と I211 の「uv はぴったり 0.13.6」がぶつかり、ロックファイルの作り直しが毎回失敗する（スパイク 1）。`required-version` を範囲にすると、I211 の「手元と CI の uv が同じ版」が崩れる（setup-uv が範囲の最新を入れる）。ハーネスの道具は手元と CI のテストだけに使い本番に入らない 2 つ（PyYAML・pre-commit）なので、I211 の手で上げる手順で足りる。失敗し続ける見張りを入れるより、入れない理由を書くほうが運用の音（失敗の通知）が無い
- D3: 土台イメージを「タグ＋指紋」で固定する（AC7 の追加）。理由: Q4 で「Dependabot には同じ版の中の更新だけを任せる」と決めたが、タグだけでは Dependabot がそれを PR にできない（同じタグの中身の更新を知るには指紋が要る）。Q5 の action の SHA 固定と同じ考えで、中身の再現性も上がる。これで Q6 の `--pull` も要らなくなる（指紋が変われば `--build`・起動時に新しいものを取る）。イシューの AC の「Docker の PR のときは `--pull`」は「要らない」に読み替える
- D4: Playwright のイメージと `@playwright/test` を同じ PR で上げる設定（multi-ecosystem-groups）は使わず、e2e のコンテナの起動時にブラウザを入れる（Q4 の「同じ PR で上がるようにする」を読み替え）。理由: multi-ecosystem-groups は、パターンに当たらない部品・ignore・待つ日数・major の扱いが公式に書かれておらず、既定のブランチに入れるまで試せない。起動時に入れる形は CI（`npx playwright install --with-deps chromium`）と同じ方法で、版がずれても動くことを確かめた（スパイク 2）。2 つの版をそろえる必要そのものが無くなる
- D5: 書き間違いを止める仕組みに公式の `check-jsonschema` の `check-dependabot` フックを使う。理由: 自作の検証より公式のスキーマのほうが網羅的で、Dependabot（pre-commit）が版を上げられる。誤りを 4 種とも止めた（スパイク 3）。ワークフロー用の `check-github-workflows` は今回の範囲外（I213 の決まりの外）
- D6: 決まりのうち「壊れても気づきにくく、壊れると被害が大きいもの」（target-branch なし・SHA・指紋・secrets なし・伏せ字の順・名前の無い保存領域）だけを新しいハーネスのテストで確かめる（計画変更記録 2）。理由: 普通の書き方の事故（新しい action を `@v4` で足す等）を決定論ゲートで止める。設定の中身の写しのテストは作らない
- D7: E2E のパスワードは `openssl rand -hex 24`（48 文字・記号なし）。理由: ログイン画面の 8 文字以上を満たし、シェルの引用の心配が無い。runner に標準で入っている
- D8: secrets `E2E_TEST_PASSWORD` は消さない（close でユーザーに示す）。理由: 消しても害は無いが、ロールバックのときに要る。消すのはユーザーの UI 操作
- D9: 版の数字（action の SHA・イメージの指紋）は実装時に取り直す。理由: 計画の時点の値は古くなる
- D10: Dependabot の受け取り方の runbook は新しいファイルにせず `dependency-audit.md` に足す。理由: 監査と Dependabot は役割分担が要る一組で、CLAUDE.md の参照は 1 行のまま（参照を増やさない）
- 一覧 docs/reviews/backlog/I211.md F6: 同梱 — setup-uv を SHA で固定するので直る
- 一覧 docs/reviews/backlog/I211.md F5: 残す — `names()` の読み方の重複の話で I213 と関係しない
- 一覧 docs/reviews/backlog/I204.md F4: 残す — S3 のテスト名の話で I213 と関係しない
- 要件適合性: AC の範囲を超える追加は D3（指紋）・D5（形の検証）・D6（決まりのテスト）で、どれもイシューの決定（Q4・Q5・決定論ゲート）を実現するための最小の追加。マルチテナント・ステータス遷移は非該当
- セキュリティ: アプリのコードの変更なし（認証・認可・入力の扱いは非該当）。供給網の守りが上がる: action と土台イメージを中身で固定（タグの付け替えで別の中身が動かない）・出たばかりの版を待つ・CI から secrets を無くす（Dependabot の PR で新しい版の部品が動いても渡る秘密が無い・`permissions: contents: read` は今のまま）・Malware alerts。足す第三者の部品は `check-jsonschema`（pre-commit のフック・python-jsonschema の公式・版を固定）だけ。パスワードはジョブごとに作り `::add-mask::` で伏せ字にし、使い捨ての DB の試験アカウントだけに使う。bandit・npm audit の対象の変更なし（重大度基準は今のまま: bandit MEDIUM 以上・npm audit high/critical）
- P3/P5/P8 影響なし（DB 変更・外部 API・非同期処理なし。新しいインフラ・費用なし〔Dependabot・Actions は公開リポジトリで無料〕）
- P6 影響なし（UI なし）
- P9 影響なし（個人情報・テナントデータを扱わない）
- 設計品質: 版の数字は設定ファイル（dependabot.yml・ワークフロー・Dockerfile・compose）にだけ書き、テストは形（40 桁・64 桁）だけを見る（版を上げてもテストを書き換えない）
- 要件・基本設計・UI/UX の価値判断に当たる仮定: AC の読み替え（D2・D3・D4）は、ユーザーの委任（「BP の観点で検討して決めて」）の範囲の技術的な実現方法の変更として Claude が決めた。close でユーザーに報告する

Danger Ops（有無/手順/ロールバック）:
- 無（設定・ワークフロー・Dockerfile の書き方・文書の変更。データの変更なし。マージ後に閉じる Dependabot の PR は開き直せる）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | pull_request で動くワークフロー（ci.yml・e2e.yml）に `secrets.` が無く、E2E のパスワードは `::add-mask::` の後で `$GITHUB_ENV` に書かれる（決定論の TC-01 W2・W3 と、それぞれを壊して不合格になる FG-W2・FG-W3a・FG-W3b で覆った・計画変更記録 6。手動 No.3 でログが伏せ字） |
| V2 | 1 | 読んで可 | すべての `uses:` が 40 桁の SHA＋版のコメントで、SHA でない書き方（`@v4`・`@v10.3.3`）を入れると不合格（決定論の TC-01 W1 と FG-W1a・FG-W1b・FG-W1c で覆った。敵対的レビュー 1 周目で実験済み・計画変更記録 7） |
| V3 | 1 | 読んで可 | 土台イメージ（Dockerfile と docker-compose.yml）がすべて指紋付きで、指紋を外すと不合格（決定論の TC-01 I1 と FG-I1a・FG-I1b で覆った。1 周目で実験済み。CI の services は例外・計画変更記録 6・7） |
| V4 | 2 | 読んで可 | `--renew-anon-volumes` で消えるのが frontend の node_modules だけで、DB・redis の中身が残る（決定論の TC-01 V1 と FG-V1 で覆った。1 周目で実験済み。実地は手動 No.1・計画変更記録 7） |
| V5 | 2 | 読んで可 | dependabot.yml に `target-branch` が無く、groups がセキュリティの修正にも効く形（TC-01 D2・TC-03・実物の設定を読む） |
| V6 | 3 | 読んで可 | uv を見張らない理由・Dependabot の PR の受け取り方が runbook にあり、イシューの決定と食い違わない（runbook を読む・手動 No.5） |

## 計画変更記録
- 1（plan-review・2026-10-29）: 計画レビューの Warning 3 件への対応。(a) 手動 No.4 の「7 か所」を「6 種類」に直して列挙した。(b) TC-01 W2 の `secrets.GITHUB_TOKEN` も禁止する件: 計画時に `grep -rn "secrets\." .github/workflows/` で使用箇所は e2e.yml の `E2E_TEST_PASSWORD` の 2 行だけと確認済み（GITHUB_TOKEN を明示的に使う箇所は無い。dependency-audit.yml は `GH_TOKEN: ${{ github.token }}` の形で `secrets.` を使わず、そもそも pull_request で動かない）。実装ステップ 1 の Red/Green で実物を見る。(c) 手動 No.1 の DB 名・ユーザー名・テーブル名を `docker compose config`・`backend/accounts/models.py:142` と照合し、テーブル名を `users` に直した。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）
- 2（implement・2026-10-29・ユーザーの「BP 的に適切？過剰？」を受けて）: 計画書の記載「4-7 新規 test_i213_dependabot.sh（D・W・I・V・P・R・K・M）」→ 採った方法: 「壊れても気づきにくく、壊れると被害が大きい決まり」の 6 項目（D2 target-branch なし・W1 SHA 固定・W2 secrets なし・W3 伏せ字の順・I1 指紋・V1 名前の無い保存領域）に絞る。D1・D3〜D6（dependabot.yml の中身の照合）・R1・M1（runbook の文言）・K1（フックの有無）・P1（e2e の command の並び）は消す。理由: 設定の中身をテストにもう一度書く「写し」のテストは、設定を変えるたびに両方を直す手間だけが増え、守りの力が無い（書き間違いは公式の check-dependabot が止める）。文言・フックの有無・並びは消すのが意図的な変更で、普通の書き方の事故ではない。AC4〜AC6・AC10〜AC13 は、実物の設定（dependabot.yml・compose・runbook・pre-commit）と check-dependabot・コードレビューで確かめる。計画レビューのやり直し: 不要（受け入れ条件・方式は変えず、テストの数を減らすだけ）
- 3（implement・2026-10-29・ユーザーの指示「ルールなどにも反映して」）: 範囲に 4-11 を足す（`docs/runbooks/plan-writing-rules.md` に決定論テストの対象の選び方の節・計画レビュー役とコードレビュー役に 1 行ずつ）。AC16 を足す。理由: 計画変更記録 2 の判断（写しのテストを作らない）は I213 だけの話ではなく、テストを書く・レビューするたびに要る基準。正を 1 か所に置き、レビュー役は参照だけを持つ。計画レビューのやり直し: 要（範囲と受け入れ条件を変える）→ 実施（20261029_1000・Blocker 0・Warning 4・判定 HIGHRISK〔`.github/*` を含むので前回と同じ〕）
- 4（implement・計画レビュー 2 の Warning 4 件への対応）: 手動 No.9 を表の中に入れた／TC-01 W1 の合格条件に「版のコメントの後ろの説明を許す」を明記し、合格側の W1ok を足した／手動 No.1 のコマンドを `docker compose exec -T frontend ...` に具体化した／イシューの受け入れ条件を読み替え後の内容（uv は見張らない・指紋・e2e のブラウザ・テストの選び方・`--pull` 不要）に直し、#359 を同期した。追加のセキュリティ設計レビュー: 不要（計画変更 3 は文書・レビュー役の観点の 1 行だけで、権限・秘密・供給網の扱いを変えない）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）
- 5（implement・/simplify・4 観点）: 採った: dependabot.yml の `open-pull-requests-limit: 5`（既定の値）を消した／`test_i204_tool_sync.sh` の setup-uv の `uses` の書き方の確かめと FG（`uv_major_tag`・`uv_minor_tag`）を消し、TC-01 W1 に一本化した（2 か所で同じ決まりを持たない）／TC-01 W3 を「`E2E_TEST_PASSWORD` を `GITHUB_ENV` に書く step で、その前に `::add-mask::`」だけにし、`openssl rand -hex` と step の名前への依存を外した（4-11 の「写しのテストを作らない」に当たる）・FG の写しを sed 1 行にした／e2e の command のコメントに「版がずれている間は毎回取り直す」を足した。見送った: (a) dependabot.yml の共通部分の YAML アンカー化（Dependabot が読めると確かめられない）・`directories:` での対象の統合（PR が対象ごとに分かれなくなる）、(b) 起動コマンドの `--renew-anon-volumes` をやめて frontend の起動時に `npm install` する案（backend のために `--build` 付きの起動コマンドはどのみち要り、`--renew-anon-volumes` はこの状況のための Docker の公式の仕組み。V1 で安全を固定済み）、(c) Playwright を種類をまたいでまとめる案（9 の D4 で検討済み）、(d) テストの写しの作り方の効率（合計 2〜4 秒）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）
- 6（review-gate・敵対的レビュー 1 周目〔20261029_1032〕）: (a) V1 が「実験必須」を読んで確認しただけで未検証 → 決定論の TC-01 W2・W3 と FG-W2・FG-W3a・FG-W3b で覆っているので、確かめ方を「読んで可」に下げた（review-gate 3-3 の決まり）。(b) Medium「ci.yml の services の postgres・redis が指紋なし」→ 固定しない例外として runbook（dependency-audit.md の固定の決まり）に書いた。理由: Dependabot はワークフローの services のイメージを更新しないので、指紋で固定すると更新が二度と届かず古いまま止まる。CI の services は毎回使い捨てで secrets を持たず、タグのまま毎回新しいものを取るほうが安全。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）
- 7（review-gate・敵対的レビュー 2 周目〔20261029_1044〕・上限到達でユーザーが「もう 1 周だけ延長」を選択）: 2 周目は 1 周目の後の差分（計画書の一覧と runbook の文言だけ）を見たため、V2・V3・V4 を実験せず未検証になった（新しい High・Critical は 0）。V2〜V4 は 1 周目に実験で確認済みで、その後に中身のファイルは変わっていない（`git diff --stat d4dc801d HEAD` は計画書・runbook・記録だけ）。どれも決定論の TC と FG で覆っているので、V1 と同じく確かめ方を「読んで可」に下げた（review-gate 3-3 の決まり）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261029_1000 判定: ✅ 完了](../../reviews/I213_plan_review_20261029_1000.md)
- [20261029_0939 判定: ✅ 完了](../../reviews/I213_plan_review_20261029_0939.md)

## セキュリティレビュー結果

**実施日**: 2026-10-29

バックエンド・フロントエンドのコード変更なし（認証・認可・シリアライザ・モデル・URL は読む対象なし）。対象は Dependabot の設定・CI のワークフロー（action の固定・E2E のパスワード）・土台イメージの固定・手元の起動の仕方・pre-commit のフック。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 依存ライブラリ（供給網） | 受け取り方を「minor・patch・security は CI が緑ならユーザーがマージ」にするので、CI を通る形で悪い中身を持つ版が入ると、develop と手元のコンテナに入る | 必須: 待つ日数（7 日・pip/npm の major 14 日）・Malware alerts On・action は SHA、土台イメージは指紋で固定（タグの付け替えで中身が変わらない）・major は流れを通す。CI は読み取りだけの権限で secrets を持たない（下の 2 行）。残余は受け入れる（BP と同じ水準） |
| Medium | 依存ライブラリ（土台イメージ） | 土台イメージを指紋で固定すると、OS の修正が入った新しいイメージの取り込みが「Dependabot の週 1 の確認＋待つ日数 7 日」だけ遅れる（今はタグのまま CI が毎回最新を取る）。Dependabot のセキュリティの修正は土台イメージには来ない | 受け入れる: 中身の再現性とタグの付け替えへの耐性を優先する（OpenSSF Scorecard の Pinned-Dependencies と同じ考え）。指紋の更新は minor・patch のまとめ PR か 1 件ずつの PR で届く（R8）。急ぐ修正は手で指紋を上げてよい（runbook に書く） |
| Low | 機密情報 | E2E のパスワードがログに出る（`echo` の写し・失敗時の `docker compose logs backend`・`seed_e2e --password` の引数） | 必須: `::add-mask::` を `$GITHUB_ENV` への書き込みより前に置く（TC-01 W3・FG）。伏せ字はジョブの全ログ（後の step・失敗時のログ）に効く。値は使い捨ての DB の試験アカウントにだけ効き、ジョブが終われば DB ごと消える。成果物は画面キャプチャだけ（I187・今のまま） |
| Low | セキュリティ設定ミス（CI） | pull_request で動くワークフローに将来 secrets が足されると、Dependabot の PR で CI が赤くなる／PR の新しい版のコードに secrets を渡す道ができる | 必須: ci.yml・e2e.yml に `secrets.` を置かない（TC-01 W2・FG）。`permissions: contents: read` は今のまま（test_i182_secret_gates.sh） |
| Low | セキュリティ設定ミス（Dependabot） | `target-branch` を消したので、既定のブランチを main に戻すと Dependabot の PR が main 宛てになる | runbook（dependency-audit.md）に「既定のブランチを変えるときは Dependabot の宛先も変わる」と書く。`target-branch` を戻すとセキュリティの修正に設定が効かなくなるので戻さない（TC-01 D2） |
| Low | セキュリティ設定ミス（手元） | `--renew-anon-volumes` が、将来どこかに足された名前の無い保存領域（例: DB）を起動のたびに消す | 必須: 名前の無い保存領域は frontend の `/app/node_modules` だけ（TC-01 V1・FG） |
| Low | 依存ライブラリ（新規） | pre-commit に第三者のフック `check-jsonschema`（0.38.2）を足す | 版を固定・出て 7 日以上の版（0.39.0 は使わない）。スキーマは同梱のもので、検証のときに外へ取りに行かない（`--builtin-schema`）。CI の lint ジョブは secrets を持たない |
| — | 認証・認可／マルチテナント／入力検証／ファイル操作／外部通信 | なし（エンドポイント・データ・アップロード・Webhook の変更なし） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | Dependabot の PR（乗っ取られた版の部品） | 第三者（部品の配布元） | CI の中で動いて secrets・トークンを盗む | pull_request で動くワークフローに secrets が無い・トークンは読み取りだけ | Yes: TC-01 W2・test_i182_secret_gates.sh C4 | Yes: No.3（PR の CI が secrets なしで緑） | CI で盗めるのは使い捨ての試験パスワード（伏せ字・すぐ消える）だけ | Low |
| 2 | 第三者の action のタグ | 第三者（action の配布元） | タグを付け替えて CI で別の中身を動かす | すべての `uses:` が 40 桁の SHA | Yes: TC-01 W1・TC-02 | No | SHA の中身そのものが悪い場合（固定の前から悪い）は防げない | Low |
| 3 | 土台イメージのタグ | 第三者（イメージの配布元・レジストリ） | 同じタグに悪いイメージを押し込む | すべての土台イメージが指紋付き | Yes: TC-01 I1 | Yes: No.4（指紋が引ける） | 指紋の更新 PR の中身を CI だけで判定する（シナリオ 4 と同じ） | Low |
| 4 | Dependabot の minor・patch のまとめ PR | 第三者（部品の配布元） | CI を通る悪い版を出し、マージされるのを待つ | 待つ日数・Malware alerts・major は流れを通す | No（待つ日数は実物の設定と check-dependabot で見る・計画変更記録 2） | No | 待つ日数の間に見つからなかった悪い版は入る（受け入れる・BP と同じ水準） | Medium |
| 5 | PR の `.github/dependabot.yml` | PR を出せる人 | 待つ日数・まとめ・ignore を外す／書き間違いでセキュリティの修正のまとめを無効にする | 形の検証と決まりのテストが CI で止める | Yes: TC-03（check-dependabot）・TC-01 D2 | No | `.github/` の変更は高リスク判定で敵対的レビューに回る | Low |
| 6 | E2E のジョブのログ | PR を見られる人（公開リポジトリなので誰でも） | ログからパスワードを読む | `::add-mask::` が先・成果物に trace を上げない | Yes: TC-01 W3 | Yes: No.3（ログが `***`） | 読めても使い捨ての DB の試験アカウントだけ | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 2件 | 1件 |
| Low     | 5件 | 5件 |

### 残余リスク処遇
（retro 段階で決定する）
