# plan_I187: フロント開発の検証ループを整える（Playwright MCP・画面確認の手順と判定・フロント開発設定の見直し）

## 基本情報
- **計画書ID**: plan_I187
- **関連イシュー**: #318
- **Draft PR**: #323
- **作成根拠資料**: docs/issues/open/I187.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I187_review.md
- **作成日**: 2026-10-24

## 1. 背景/目的
- 背景・目的はイシュー（`docs/issues/open/I187.md`「背景/目的」「現状の問題」）のとおり。要点: Claude がフロントの変更を自分の目で確かめる手段（画面を 1 手ずつ見ながら操作する仕組み）・確かめた証拠の残し方・確認のし忘れを止める仕組みがなく、型チェック・lint も CI にしか書かれていない。
- 目的: Claude が人に頼まずに、起動・ログイン・入力・画面遷移・画面キャプチャ・コンソールエラーの確認まで行えるようにする。証拠は文章の記録だけをコミットし、画像は git に入れない。確認のし忘れは決まった判定（スクリプト）で止める。あわせてフロントの開発設定を点検し、待ち時間と手間を減らす。

## 2. 受け入れ条件
イシューの「受け入れ条件」14 項目をそのまま使う（範囲の追加・変更はしない）。各項目と確かめる TC の対応は「6. テスト計画」の表を参照。

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend | なし（コード変更なし。E2E を続けて流すときだけ、既存の環境変数 `RATELIMIT_ENABLE=false` で backend を起動する手順を文書化する。CI と同じ使い方） |
| Frontend | `frontend/package.json`（scripts に `typecheck`・`lint` を追加。依存の追加・更新はしない） |
| DB | なし |
| Config/Infra | `.mcp.json`・`.claude/settings.json`・`.gitignore`・`e2e/playwright.config.ts`・`.github/workflows/ci.yml`・`.github/workflows/e2e.yml`・`.pre-commit-config.yaml` |
| ハーネス | `scripts/claude/check-frontend-evidence.sh`（新規）・`scripts/claude/tests/test_check_frontend_evidence.sh`（新規）・`scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/tests/test_pretooluse_container_guard.sh`・`.claude/skills/test/SKILL.md`・`.claude/skills/plan-issue/SKILL.md`・`.claude/review-agents/code-reviewer.md` |
| 文書 | `docs/runbooks/frontend-verify.md`（新規）・`docs/runbooks/workflow.md`・`CLAUDE.md`・`docs/tests/templates/manual_test_template.md`・`docs/runbooks/plan-writing-rules.md` |
| ホスト環境（リポジトリ外） | chromium の起動に要る OS ライブラリ（`libnss3`・`libnspr4`・`libasound2t64` など）を `sudo npx -y playwright@1.59.1 install-deps chromium` で入れる（sudo が要るのでユーザーが `!` で実行）。Playwright MCP 用の chromium（revision 1247）を `~/.cache/ms-playwright/` に取得する |
| 変更しない（読むだけ） | `e2e/.env.e2e`（Playwright MCP の `--secrets` で読み込ませる。Claude は中身を読まない） |
| Dockerfile・docker-compose.yml への波及 | なし。`frontend/package.json` は scripts だけの変更で依存は変わらないため、`frontend/Dockerfile.dev` のインストール対象・イメージの作り直しに影響しない（frontend コンテナは `./frontend` をマウントしているので、追加した scripts はそのまま使える） |

## 4. 調査結果

### 4-1. 環境前提（2026-10-24 にこのワークツリーで確認）
| 項目 | 結果 |
|---|---|
| OS | Ubuntu 24.04.4 LTS（WSL2） |
| Node / npm（ホスト） | v24.14.1 / 11.11.0 |
| Docker Compose | v5.6.0 |
| chromium（ホスト） | `~/.cache/ms-playwright/chromium-1217`・`chromium_headless_shell-1217`（`@playwright/test` 1.59.1 用）。`ldd` で `libnspr4.so`・`libnss3.so`・`libnssutil3.so`・`libasound.so.2` が **not found**（I158 の「ホストで起動できない」の原因を特定） |
| このワークツリーのポート | ワークツリー直下の `.env` が無い（`wt-ports.sh` 未実行）。primary のコンテナが既定ポート（3000・8000 など）で動いている。実装のステップ 2 で `bash scripts/claude/wt-ports.sh` を 1 回実行する |
| `frontend/node_modules`（ホスト） | 無い。型チェック・lint・Jest は frontend コンテナ内で動かす（見張りは `npm run typecheck`・`npm run lint` をコンテナ内の安全な操作として既に通す: `pretooluse_guard.py` 2318 行目） |
| develop の CI（50836a9・2026-10-24） | CI・E2E とも success。フロントの所要時間（CI 上）: 型チェック 8 秒・ESLint 2 秒・Jest 7 秒・E2E 本体 17 秒（サービス起動 2 分 16 秒） |
| 既存テストのベースライン | develop 50836a9 の CI で pytest・Jest・E2E・tsc・ESLint（警告 0）すべて合格。lint エラー件数 0（`--max-warnings 0` で合格） |

### 4-2. Playwright MCP のスパイク（稼働中セッションで実証できた部分）
| 確かめたこと | 方法 | 結果 |
|---|---|---|
| 採用するバージョン | `npm view @playwright/mcp time` | 最新の安定版は **0.0.83**（2026-09-28 公開・4 週間前）。中で使う playwright は `1.64.0-alpha-1790635538000`（chromium revision **1247**。手元の 1217 とは別に取得が要る） |
| 既知の脆弱性 | スクラッチパッドに `@playwright/mcp@0.0.83` だけを依存に持つ package.json を作り、`npm install --package-lock-only --ignore-scripts` → `npm audit` | `found 0 vulnerabilities`（exit 0・2026-10-24）。バージョンを上げるときも同じ確認をする（runbook に書く） |
| オプション名 | `npx -y @playwright/mcp@0.0.83 --help` | `--headless`・`--isolated`（プロファイルをメモリに置き、ディスクに残さない）・`--allowed-origins`（`;` 区切り）・`--output-dir`・`--secrets`（dotenv 形式）・`--browser` が存在 |
| `--allowed-origins` の挙動 | パッケージのソース（`originOrHostGlob`・`_setupRequestInterception`）を読んだ | 指定があると、まず全リクエストを `blockedbyclient` で止め、指定した origin だけ通す。`http://localhost:*` のように **ポートを `*` にできる**ので、ワークツリーごとにポートが違っても 1 つの設定で足りる。ただし公式の説明どおり「セキュリティの境界ではなく、リダイレクトには効かない」 |
| `--secrets` の挙動 | 同上（`redactSecrets`） | 操作の入力に秘密の **名前**（例 `E2E_TEST_PASSWORD`）を書くと本当の値に置き換えて入力し、ツールの出力に値が出たら `<secret>名前</secret>` に置き換える。→ Claude はパスワードを読まず・見ずにログインできる |
| `--browser` の既定 | 同上（`validateBrowserConfig`・`resolveBrowserParam`） | 既定は Google Chrome（`chrome` チャネル）。Playwright 同梱の chromium を使うには `--browser chromium`（`chrome-for-testing` チャネル）を指定する |
| 提供される操作（ツール）の一覧 | MCP を標準入出力で起動し `tools/list` を呼んだ | 25 個。うち任意コードを動かす・ローカルのファイルを渡すもの: `browser_evaluate`（ページ内で JS を実行）・`browser_run_code_unsafe`（Playwright サーバー側＝ホストの Node で任意の JS を実行）・`browser_file_upload`・`browser_drop`。通信の中身（ヘッダー・本文）を返すもの: `browser_network_request` |
| ブラウザの起動・画面操作 | — | **未実証**（ホストに OS ライブラリが無く、入れるには sudo が要る）。→ 実装のステップ 1 に前倒しし、後続を止めるゲートにする |
| Claude Code が `.mcp.json` の新しいサーバーを読み、許可設定どおりに動くか | — | **未実証**（MCP サーバーはセッション開始時に読まれるため、稼働中のセッションでは確かめられない）。→ ステップ 1 で新しいセッションで確かめる |

### 4-3. その他のスパイク・調査
| 確かめたこと | 方法 | 結果 |
|---|---|---|
| ワークツリーの片付けで `.evidence/` が消えるか | 使い捨てのリポジトリで `.evidence/` を gitignore し、ワークツリーに画像を置いて `git worktree remove`（スクリプト: スクラッチパッドの `wtspike.sh`） | `git status --porcelain` は空（gitignore 済みのファイルは「変更あり」に数えられない）で、`git worktree remove` は exit 0、フォルダごと消えた。`wt-remove.sh` も最後に `git worktree remove` を使う（215 行目）ので同じく消える。公式の自動片付け（変更が無いワークツリーをセッション終了時に消す）でも消える |
| 見張りの現状 | `pretooluse_guard.py` にコマンドを流した | `docker compose --profile e2e run --rm e2e npx playwright test tests/auth.spec.ts --retries=0` → ask（「許可リストにない」）。`docker compose --profile e2e run --rm e2e`（既定コマンド）・`docker compose port frontend 3000`・`RATELIMIT_ENABLE=false docker compose up -d backend` → 見張りは通す（ただし `.claude/settings.json` の allow に無いので通常の確認が出る） |
| コンテナ内の判定の場所 | `pretooluse_guard.py` を読んだ | `_container_safe()`（2272 行目〜）がコンテナ内の単純コマンドを許可リストで判定する。`npx` は `tsc`・`eslint`・`jest` だけ（2319 行目）。サービス名は `c.get("service")`（1825 行目で設定）で取れる |
| ログインのレート制限 | `backend/accounts/views.py`・`core/settings.py` | ログインは IP ごとに 5 回／5 分。`RATELIMIT_ENABLE`（既定 True）を `false` にすると無効。docker-compose.yml の backend は `- RATELIMIT_ENABLE` でホストの値を渡す。CI の E2E も同じ方法で無効にしている（e2e.yml）。本番の設定は変えない |
| 安全なコンテキスト | `QuizSession.tsx`・e2e の設定 | e2e コンテナは `http://frontend:3000` を開くので安全なコンテキストにならない（`crypto.randomUUID` などが使えない。`QuizSession.tsx` は代わりの処理を持つ）。Chromium の起動オプション `--unsafely-treat-insecure-origin-as-secure=<origin>` で、その origin を安全なコンテキストとして扱える |
| E2E の失敗時の記録 | `playwright.config.ts`・`e2e.yml` | 今は `trace: 'on-first-retry'` だけで画面キャプチャを撮らない。CI は失敗時に `e2e/playwright-report/` を 7 日上げる設定だが、reporter に html を指定していないため、このフォルダは作られず何も上がっていない。仮に html レポートを作ると trace が中に入る（trace にはログイン時に入力したパスワードが残る） |
| 型チェック・lint のコマンドを使っている場所 | リポジトリ全体を grep（`tsc --noEmit`・`eslint src`） | `.github/workflows/ci.yml`（108・125 行目）・`.pre-commit-config.yaml`（44 行目・`npx eslint src/ --ext .ts,.tsx --max-warnings 0`）。文書では `docs/runbooks/onboarding.md:62`（説明文のみ・変更不要）・`plan-writing-rules.md:143`（lint 件数の計測例・変更不要） |
| 変更するスキルの行数 | `wc -l` | `.claude/skills/test/SKILL.md` 119 行・`.claude/skills/plan-issue/SKILL.md` 185 行・`.claude/review-agents/code-reviewer.md` 227 行。追記はそれぞれ 10 行程度・1 行の書き換え・1 項目で、公式の目安（500 行以内）に収まるため分割しない |
| 「Human = ブラウザ操作」の基準を書いている場所（今回の決定を消費する箇所） | grep（`ブラウザ操作`・`画面目視`） | `.claude/skills/plan-issue/SKILL.md:95`・`docs/runbooks/plan-writing-rules.md:506`・`docs/tests/templates/manual_test_template.md:9` の 3 か所。このままだと、今後の計画で画面確認がすべて「Human」になり、目的（Claude が自分で確かめる）と食い違う |
| レビューの観点の置き場所 | `.claude/skills/code-review/SKILL.md`・`scripts/claude/code-review.sh` | SKILL.md は流れ（スクリプト実行と分岐）だけを書いており、基本レビューの観点はスクリプトが読む `.claude/review-agents/code-reviewer.md` にある。観点はここに足す |
| 関連イシューとの重なり | イシュー・メモリ | I188（公式機能への置き換え）は計画前・未マージ。I185 の P6（`/test` を CI 確認に置き換え）・P15（見張りの絞り込み）は未起票。重なるファイルは今の develop に合わせて変え、後から入る側が合わせる |

### 4-4. 原因の概要
- Claude の手元のブラウザが動かないのは、ホストに chromium の起動に要る OS ライブラリが無いため（ブラウザ本体はある）。
- 画面確認の手順・証拠・し忘れの判定が無いのは、これまでのハーネス改善が工程・レビュー・権限の側に集中し、「フロントの結果を自分の目で確かめる」部分をまとめて決めたことがないため（イシューの根本原因のとおり）。

## 5. 修正アプローチ（全体像）
公式の仕組み（Playwright MCP・`@playwright/test` の設定・GitHub Actions の標準アクション）をそのまま使い、自作は「`frontend/src` を変えたのに画面確認の記録が無いこと」を止める判定スクリプト 1 本だけにする。

### 5-1. 変更点一覧
| # | ファイル | 変更内容 | 修正方針（何を達成するか） |
|---|---|---|---|
| 1 | `.mcp.json` | `playwright` サーバーを追加（下のコード例） | Claude が 1 手ずつ画面を見て操作できるようにする。開ける先を手元だけにし、状態を残さず、パスワードを Claude に見せない |
| 2 | `.claude/settings.json` | allow に Playwright MCP の操作 20 個・`Bash(docker compose port *)`・`Bash(RATELIMIT_ENABLE=false docker compose up *)` を追加 | 画面確認を承認なしで回せるようにする。任意コードを動かす 2 つ・ファイルを渡す 2 つ・通信の中身を返す 1 つは allow に入れず、使うたびに確認が出るままにする（最小権限） |
| 3 | `.gitignore` | `.evidence/` を追加 | 画像をコミットしない |
| 4 | `docs/runbooks/frontend-verify.md`（新規） | 画面確認の手順・エビデンスの残し方・消えるタイミング・落とし穴 4 件の避け方・公式と自作の分担 | 毎回その場で組み立てている手順を 1 か所に決める |
| 5 | `CLAUDE.md`・`docs/runbooks/workflow.md` | 参照先の一覧に `frontend-verify.md` を 1 行足す | 公式 `/run` を含め、どのセッションからも手順にたどり着けるようにする（新しいスキルは作らない） |
| 6 | `docs/tests/templates/manual_test_template.md` | 「## 画面確認」の表を追加。実施者の基準（コメント）を「Playwright MCP で観測できる画面確認は Claude」に改める | 画面確認の 1 行の書き方を決め、判定スクリプトが読める形にする |
| 7 | `.claude/skills/plan-issue/SKILL.md`・`docs/runbooks/plan-writing-rules.md` | 実施者の判定基準を「Playwright MCP で観測できる画面の表示・遷移・コンソールは Claude、Claude では観測できない操作感・外部ツールだけ Human」に改める（各 1 か所） | 今後の計画で画面確認が「Human」に振られないようにする（設計確認メモ「人に頼むのは Claude では観測できない項目だけ」の消費箇所） |
| 8 | `scripts/claude/check-frontend-evidence.sh`（新規）・`scripts/claude/tests/test_check_frontend_evidence.sh`（新規） | 判定スクリプトとそのテスト（5-2-5） | 確認のし忘れを決まった判定で止める |
| 9 | `.claude/skills/test/SKILL.md` | 手動テストの手順に「Claude が Playwright MCP で画面確認をして『画面確認』の行を書く」「判定スクリプトを実行し、不合格なら停止」を追加 | `/test` に組み込む |
| 10 | `.claude/review-agents/code-reviewer.md` | 観点「画面の動きを変えたら E2E か単体テストを追加・更新しているか（テストにしにくい見た目だけ画面キャプチャで確認しているか）」を追加 | 手で確かめただけで終わらせない（判断が要るのでレビューの観点にする） |
| 11 | `scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/tests/test_pretooluse_container_guard.sh` | e2e サービスの中の `npx playwright test`（範囲・表示だけを変える選択肢）を安全一覧に追加し、通る例・通らない例のテストを追加 | 1 ファイルだけ流す E2E を承認なしで回せるようにする |
| 12 | `frontend/package.json` | scripts に `"typecheck": "tsc --noEmit"`・`"lint": "eslint src/ --ext .ts,.tsx --max-warnings 0"` | 手元と CI で同じコマンドを使う |
| 13 | `.github/workflows/ci.yml` | `npx tsc --noEmit` → `npm run typecheck`、`npx eslint ... -f github-actions` → `npm run lint -- -f github-actions` | CI も同じコマンドを呼ぶ |
| 14 | `.pre-commit-config.yaml` | ESLint フックの entry を `bash -c 'cd frontend && npm run lint'` にする | lint の定義を `package.json` の 1 か所にまとめる（今は CI と pre-commit に同じ文字列が 2 つあり、片方だけ変わるとずれる） |
| 15 | `e2e/playwright.config.ts` | `screenshot: 'only-on-failure'`、`trace` は手元 `retain-on-failure`・CI（`process.env.CI`）では `'off'`、Chromium の起動オプションに `--unsafely-treat-insecure-origin-as-secure=<baseURL の origin>` | 失敗時に原因を追える記録を手元に残し、CI では trace を作らない。e2e コンテナでも CI と同じく安全なコンテキストで動かす |
| 16 | `.github/workflows/e2e.yml` | 失敗時のアップロードを `e2e/test-results/**/*.png`（画面キャプチャだけ）・`retention-days: 14`・`if-no-files-found: ignore` に置き換える（今の `playwright-report` のアップロードは削除） | CI では画面キャプチャだけを 14 日残し、trace やレポートを公開しない |

### 5-2. 各修正項目の詳細

#### 5-2-1. Playwright MCP（変更点 1・2）
`.mcp.json` に追加する内容:
```json
"playwright": {
  "command": "npx",
  "args": [
    "-y", "@playwright/mcp@0.0.83",
    "--browser", "chromium",
    "--headless",
    "--isolated",
    "--allowed-origins", "http://localhost:*;http://127.0.0.1:*",
    "--output-dir", ".evidence",
    "--secrets", "e2e/.env.e2e"
  ]
}
```
- バージョンは GitHub MCP と同じく `@x.y.z` で固定する。上げるときはこの行を変える PR で行う。
- 画像の保存先: Claude はファイル名を `.evidence/I###/<画面>-<アカウント>-<連番>.png` の形で明示して撮る（名前を付けたファイルはワークスペースのルート基準で保存される）。名前なしで撮った場合の受け皿が `--output-dir .evidence`。
- `--secrets e2e/.env.e2e`: ログインのパスワード欄には値ではなく名前 `E2E_TEST_PASSWORD` を入力させる。`.env.e2e` が無いと E2E も動かないので、作り方は既存どおり `e2e/.env.e2e.example` からコピー（ユーザーが行う）。
- `.claude/settings.json` の allow に追加する操作（20 個）: `browser_navigate`・`browser_navigate_back`・`browser_snapshot`・`browser_find`・`browser_take_screenshot`・`browser_click`・`browser_hover`・`browser_drag`・`browser_type`・`browser_fill_form`・`browser_select_option`・`browser_press_key`・`browser_wait_for`・`browser_handle_dialog`・`browser_tabs`・`browser_resize`・`browser_emulate_media`・`browser_close`・`browser_console_messages`・`browser_network_requests`（一覧だけ）。いずれも `mcp__playwright__<名前>` の形で書く。
  - allow に入れないもの（使うたびに確認が出る）: `browser_run_code_unsafe`（ホストで任意の JS が動く）・`browser_evaluate`（ページ内で任意の JS）・`browser_file_upload`・`browser_drop`（ローカルのファイルをページへ渡す）・`browser_network_request`（通信のヘッダー・本文。ログイン時の送信内容が出うる）。
- `--allowed-origins` はセキュリティの境界ではない（リダイレクトに効かない・公式の説明）。手元のアプリは外部へリダイレクトしないので、画面確認の目的（外部サイトの文章を読まない・外へ送らない）には足りる。境界として扱わないことを runbook に書く。
- chromium の取得: `npx -y -p @playwright/mcp@0.0.83 playwright install chromium`（MCP が使う playwright のバージョンに合った chromium を `~/.cache/ms-playwright/` に入れる）。この書き方で入らない場合は、MCP 起動時のエラーに出る取得コマンドに従う（ステップ 1 で確定し runbook に書く）。

#### 5-2-2. 画面確認の手順（変更点 4・5）— `docs/runbooks/frontend-verify.md` の章立て
1. 目的と範囲（Claude が自分で確かめる・画像は残さない・長く残す証拠は CI のテストと文章の記録）
2. 初回だけの準備: OS ライブラリ（ユーザーが `! sudo npx -y playwright@1.59.1 install-deps chromium`）・MCP 用 chromium の取得・`e2e/.env.e2e`・ワークツリーなら `bash scripts/claude/wt-ports.sh`
3. 起動: `docker compose up -d`（frontend を含む）→ URL は `docker compose port frontend 3000` の出力のポートで `http://localhost:<ポート>` を開く（`.env` を読まずに済み、`localhost:3000` 固定にもならない）
4. 確認の前に: `docker compose exec frontend npm run typecheck`（型エラーのオーバーレイで画面が覆われるのを防ぐ）
5. ログイン: `e2e_user_a@example.com`（管理者）・`e2e_user_c@example.com`（一般ユーザー）。`e2e_user_b` は別組織。パスワード欄には `E2E_TEST_PASSWORD`（秘密の名前）を入力する。ログインできないときだけ `seed_e2e` を流す（E2E 用ユーザーだけを作り直す。`--flush` は使わない）
6. 確かめること: 画面の表示（`browser_snapshot` で要素を確認）・操作と遷移・画面キャプチャ（`.evidence/I###/` に名前を付けて保存し、Read で中身を見る）・コンソールエラー（`browser_console_messages`）
7. 記録: テスト記録（`docs/tests/open/I###_manual_test.md`）の「## 画面確認」に 1 行書く（列: 日時・コミット・画面と操作・アカウント・期待した結果・実際の結果・画像）。確認できない理由があるときは画像の列に `理由: …` と書く
8. 画像が消えるタイミング: ワークツリーの片付け（`wt-remove.sh`・公式の自動片付け）で一緒に消える。`/close` では消さない（Approve & Merge の前にユーザーが見られる）。primary で作業した場合は、次のイシューの `/plan-issue` で前のイシューの `.evidence/I###/` を消す
9. E2E の落とし穴 4 件と避け方（5-2-4）
10. 公式と自作の分担: 公式（Playwright MCP・`@playwright/test`・`actions/upload-artifact`・公式 `/run`）をそのまま使う。自作は判定スクリプトだけ。根拠: 「変えたファイルの種類に応じて、テスト記録の決まった行と手元の画像の実在を突き合わせる」機能は Claude Code・Playwright のどちらの公式機能にも無い（Claude Code の hooks は「いつ動かすか」を決める仕組みで判定の中身は持たない。Playwright の記録は失敗時の成果物で、記録の有無は判定しない）
11. 安全上の注意: `--allowed-origins` は境界ではない（リダイレクトには効かないので、外部へリダイレクトする URL〔OAuth のコールバックなど〕は開かない）・`browser_network_requests`（複数形・一覧だけ・許可）と `browser_network_request`（単数形・ヘッダーと本文・確認が出る）を取り違えない・画像やパスワードを git や外部に出さない・任意コードを動かす操作は確認が出る
12. MCP のバージョンを上げるとき: `.mcp.json` の 1 語を変える PR で行い、公開から 2 週間以上たった版を選び、`npm audit`（high/critical が 0）を確かめる

#### 5-2-3. 型チェック・lint（変更点 12〜14）
- `frontend/package.json` の scripts:
  ```json
  "typecheck": "tsc --noEmit",
  "lint": "eslint src/ --ext .ts,.tsx --max-warnings 0"
  ```
- `ci.yml`: `run: npm run typecheck`／`run: npm run lint -- -f github-actions`（GitHub の注釈表示を保つ）。
- `.pre-commit-config.yaml`: `entry: bash -c 'cd frontend && npm run lint'`（ほかの設定は変えない）。

#### 5-2-4. E2E の失敗時の記録と落とし穴（変更点 15・16・runbook）
- `playwright.config.ts`:
  ```ts
  const baseURL = process.env.BASE_URL || 'http://localhost:3000';
  // trace にはログイン時に入力したパスワードが残る。CI の成果物は公開リポジトリで誰でも取れるため、CI では trace を作らない
  const isCI = !!process.env.CI;
  ...
  use: {
    baseURL,
    screenshot: 'only-on-failure',
    trace: isCI ? 'off' : 'retain-on-failure',
    // e2e コンテナは http://frontend:3000 を開くため、CI（localhost）と同じく安全なコンテキストとして扱う
    launchOptions: { args: [`--unsafely-treat-insecure-origin-as-secure=${new URL(baseURL).origin}`] },
  },
  ```
- `e2e.yml`（失敗時のアップロード）:
  ```yaml
  - uses: actions/upload-artifact@v4
    if: failure()
    with:
      name: playwright-screenshots
      path: e2e/test-results/**/*.png
      retention-days: 14
      if-no-files-found: ignore
  ```
- 落とし穴 4 件の避け方（runbook に書く）:
  | 落とし穴 | 避け方 |
  |---|---|
  | ホストで `npx playwright test` を動かすと chromium が起動しない | 原因は OS ライブラリ不足。初回準備で `install-deps` を入れれば起動する。ただし E2E はこれまでどおり e2e コンテナで流す（`docker compose --profile e2e run --rm e2e`・1 ファイルなら `... e2e npx playwright test tests/<file>.spec.ts --retries=0`）。ホストの e2e には node_modules が無く、CI と揃える意味もないため |
  | 続けて流すとログインのレート制限（403）に当たる | E2E を続けて流すときは `RATELIMIT_ENABLE=false docker compose up -d backend` で backend を起動し直す（CI と同じ方法・本番の設定は変えない）。元に戻すときは `docker compose up -d backend`。レート制限そのものを確かめる画面確認は、元に戻してから行う |
  | e2e コンテナでは安全なコンテキストにならない | `playwright.config.ts` の起動オプションで baseURL の origin を安全なコンテキストとして扱う（CI と同じ動きになる）。Playwright MCP は `localhost` で開くのでもともと問題ない |
  | 型エラーのオーバーレイが画面を覆う | 画面確認・E2E の前に `docker compose exec frontend npm run typecheck` を通す。オーバーレイが出たら、その画面キャプチャを撮って原因（型エラー・実行時エラー）を直す |

#### 5-2-5. 判定スクリプト（変更点 8・9）
- 使い方: `bash scripts/claude/check-frontend-evidence.sh I###`
- 判定:
  1. `git diff --name-only <基準>...HEAD` に `frontend/src/` で始まるファイルが無ければ「対象外」で exit 0（基準は既定 `origin/develop`。テスト用に環境変数 `BASE_REF` で変えられる）
  2. あれば、`docs/tests/open/I###_manual_test.md`（無ければ `docs/tests/closed/`）の「## 画面確認」の表を読む。見出し・区切り行を除いたデータ行を 1 行ずつ見る
  3. 各データ行の「画像」列（最後の列）が、①`理由:` の後に空でない文があれば合格、②カンマ区切りのファイル名がすべて `.evidence/I###/<名前>` に実在すれば合格、③それ以外（空・ファイルが無い・`/` や `..` を含む名前）は不合格
  4. 合格の行が 1 行以上あり、不合格の行が 0 行なら exit 0。そうでなければ不合格の理由（どの行の・何が足りないか）を出して exit 1
  5. 引数が無い・`I###` の形でない・git の外で実行した・テスト記録が無い（frontend/src を変えた場合）→ exit 2 または 1（理由を出す）。`git diff` が失敗したときは不合格に倒す（exit 2）
- `/test` の手順 5（手動テスト）の最後に実行し、0 以外なら停止して「画面確認をして記録を足してから `/test` をやり直す」よう案内する（コードの不具合ではないので `/fix-loop` には回さない）。

#### 5-2-6. 見張りの安全一覧（変更点 11）
- `_container_safe()` の `npx` の判定に、次を満たすときだけ安全とする分岐を足す: `c["compose"]` が真・`c.get("service")` が `_SAFE_COMPOSE_DEFAULT`（`("e2e",)`）に入る・`npx playwright test` で始まる・後ろの語が「位置引数（ファイル・絞り込み）」か次の選択肢だけ:
  - 値を取るもの: `--retries`・`--reporter`（値は英小文字とカンマだけ＝組み込みの reporter 名）・`--grep`／`-g`・`--grep-invert`・`--project`・`--workers`／`-j`・`--max-failures`・`--timeout`（`--x=値` と `--x 値` の両方）
  - 値を取らないもの: `-x`・`--list`
- それ以外の選択肢（`--config`・`--update-snapshots`・`--output`・`--ui`・`--debug` など）や、e2e 以外のサービス、`npx playwright install` などは、これまでどおり確認が出る（列挙に無いものは安全としない＝fail-closed）。
- 文字列の判定を作り込まない方針（ローカルの安全装置は最小限）に従い、足すのはこの 1 分岐だけにする。
- ホスト側のパイプ・リダイレクト（P105 の `2>&1 | tail -30`）は、上の「後ろの語」の判定に入らない。見張りはコマンドを `|` などの区切りで単純コマンドに分けてから判定し（`_raw_commands`）、`|` の印（`piped`）は区切りの**後ろ**のコマンド（`tail -30`）にだけ付く（1530 行目）。ホスト側のリダイレクトはコンテナ内の書き込みとして引き継がない（1823〜1824 行目）。そのため `_container_safe()` に渡るのは `npx playwright test tests/auth.spec.ts --retries=0` だけで、P105 は通る（0）。既存の P37（`... pytest -q 2>&1 | tail -5`）・P40（`... e2e 2>&1 | tail -30`）と同じ扱い。一方、コンテナの**中**のシェルに書いた連結（C67 の `sh -c "npx playwright test; rm -r ..."`）は、中の各コマンドが判定され、`rm` が一覧外なので確認になる。

#### 5-2-7. レビューの観点（変更点 10）
`.claude/review-agents/code-reviewer.md` の観点に 1 項目を足す: 「`frontend/src` の画面の動き（表示・遷移・入力の結果）を変えた場合、E2E か単体テストを追加・更新しているか。テストにしにくい見た目（配置・色など）だけを画面キャプチャで確かめているか。手で確かめただけで終わっていれば High」。

## 6. テスト計画
- テストレベルの使い分け: 判定スクリプト・見張り・設定ファイルは **決定論テスト（bash のテストスクリプト・grep・json.tool）**。npm コマンドと CI の呼び出しは **CI の実行結果**。Playwright MCP・画面確認・E2E の失敗時の記録・`/run` は **手動テスト（実施者は主に Claude）**。アプリのコード変更は無いので pytest・Jest・E2E の新しいテストは追加しない（既存の E2E は CI で回る）。
- 認証・認可・テナント境界の変更はない（E2E 用アカウントの使い方を文書化するだけ）。
- 自動テスト: `docs/tests/open/I187_auto_test.md`（TC-01〜TC-24・/test に委譲する TC-H1・TC-H2）
- 手動テスト: `docs/tests/open/I187_manual_test.md`（M-01〜M-17）

| 受け入れ条件 | TC |
|---|---|
| 1. 起動・2 アカウントでログイン・入力・遷移・画面キャプチャ | M-02〜M-06 |
| 2. コンソールエラーの確認 | M-07 |
| 3. localhost／127.0.0.1 以外は拒否 | M-08・TC-03 |
| 4. URL が FRONTEND_PORT に従う | M-02・TC-09 |
| 5. runbook の記載 | TC-09〜TC-13 |
| 6. `.evidence/` が gitignore | TC-04・M-09 |
| 7. 判定スクリプトの合否 | TC-07・TC-16・M-10 |
| 8. npm run typecheck／lint・CI | TC-18〜TC-20・TC-H1・TC-H2・M-11 |
| 9. e2e の 1 ファイル実行が承認なし・他は確認 | TC-05・M-12 |
| 10. 落とし穴 4 件の対策 | TC-12・M-13 |
| 11. E2E 失敗時の記録（手元・CI） | TC-21・TC-22・M-14 |
| 12. 公式優先・自作の根拠 | TC-13・M-17 |
| 13. 点検結果・所要時間・タイトル案 | TC-24・M-15 |
| 14. I185・I186・I188 と重ならない | M-16 |

## 7. 実装手順
各ステップの確認は自動テスト文書・手動テスト文書の TC で行う（ステップ本文には検証コマンドを書かない）。

### ステップ 1（未知リスク先行・後続を止めるゲート）: Playwright MCP を動かす
1. ユーザーに `! sudo npx -y playwright@1.59.1 install-deps chromium` の実行を依頼する（sudo が要るため。Claude の `sudo` は deny）。
2. MCP 用の chromium を取得する（5-2-1）。
3. 設定のテスト `scripts/claude/tests/test_i187_frontend_verify_config.sh`（TC-03）を先に書き、変更前の設定で不合格になることを確かめてから、`.mcp.json`（変更点 1）・`.claude/settings.json`（変更点 2）・`.gitignore`（変更点 3）を変える。
4. ユーザーに Claude Code の再起動（このワークツリーで新しいセッションを開き、この会話を再開）を依頼する。
5. 新しいセッションで、MCP の操作が出ること・許可した操作は承認なしで動くこと・手元のアプリを開けること・外部を開けないこと・秘密の名前で入力できること・画像が `.evidence/` に保存されることを確かめる → M-01・M-08・TC-01〜TC-04 参照。
- **ゲート**: ブラウザが起動しない・Claude Code が MCP を読まない、のどちらかなら、ここで止めて計画を見直す（代わりの案: 公式の Docker イメージ `mcr.microsoft.com/playwright/mcp` でコンテナ内に MCP を動かす。その場合は `localhost` の扱いが変わるため、計画の方式変更として再レビューする）。

### ステップ 2（ステップ 1 が前提）: 画面確認の手順・記録・判定を縦に通す
1. このワークツリーで `bash scripts/claude/wt-ports.sh` を実行し、`docker compose up -d` でアプリを起動する。
2. `docs/runbooks/frontend-verify.md` を書く（5-2-2）。`CLAUDE.md`・`workflow.md` に参照を足す（変更点 5）。
3. テンプレート・実施者の基準（変更点 6・7）を変える。
4. 判定スクリプトとテストを書く（変更点 8）。テストを先に書き、スクリプトが無い・常に exit 0 の偽物で不合格になることを確かめてから本体を書く → TC-07・TC-08 参照。
5. `/test` の SKILL.md に手順を足す（変更点 9）→ TC-14〜TC-17 参照。
6. runbook どおりに、`e2e_user_a`・`e2e_user_c` でログインして 1 画面以上を確かめ、本イシューのテスト記録の「## 画面確認」に行を書く → TC-09〜TC-13・M-02〜M-07・M-09・M-10・M-17 参照。

### ステップ 3（独立・ステップ 2 と並行可）: 型チェック・lint のコマンド化
- 変更点 12〜14 を行う → TC-18〜TC-20・TC-H1・TC-H2・M-11 参照。

### ステップ 4（独立）: E2E の失敗時の記録と落とし穴
- 変更点 15・16 を行い、runbook の落とし穴の節を確定する → TC-12・TC-21・TC-22・M-13・M-14 参照。

### ステップ 5（独立）: 見張りの安全一覧
- テストのケース（通る例・通らない例）を先に足し、今の見張りで通る例が不合格になることを確かめてから `pretooluse_guard.py` を変える（変更点 11） → TC-05・TC-06・M-12 参照。

### ステップ 6（独立）: レビューの観点
- 変更点 10 を行う → TC-23 参照。

### ステップ 7（ステップ 2・3 が前提）: フロントの開発設定の点検（30 分上限）
- 次を測り、結果とタイトル案を本計画書の「16. フロント開発設定の点検結果」に書く → TC-24・M-15 参照。
  - frontend コンテナの起動から「Compiled」が出るまでの時間（初回・2 回目）
  - ファイルを 1 つ変えてから再コンパイルが終わるまでの時間
  - `npm test -- --watchAll=false`・`npm run typecheck`・`npm run lint` の時間（コンテナ内）
  - 設定の点検: CRA（`react-scripts` 5.0.1）・TypeScript 4.9・CI の Node 18・`/mnt/c` 上のマウントとファイル監視のポーリング（`CHOKIDAR_USEPOLLING`・`WATCHPACK_POLLING`）
- 大きな改善（Vite への移行など）は実装せず、数字つきのタイトル案にする。

- サービスの再起動: ステップ 1 で Claude Code の再起動が要る。ステップ 4 で backend を `RATELIMIT_ENABLE=false` で起動し直した場合は、終わったら `docker compose up -d backend` で元に戻す。

## 8. ロールバック
- すべて設定・文書・スクリプトの変更なので、PR の revert で戻る。DB・データへの影響はない。
- `.mcp.json` から `playwright` を消せば MCP は読み込まれなくなる（次のセッションから）。
- ホストに入れた OS ライブラリ・`~/.cache/ms-playwright/` の chromium はリポジトリ外。残しても害はない（消す場合は `apt remove`・フォルダ削除をユーザーが行う）。

## 9. Risk & 回避策
| リスク | 回避策 |
|---|---|
| ホストで chromium が起動しない（ライブラリ以外の原因） | ステップ 1 のゲートで止める。代わりの案は公式 Docker イメージの MCP |
| `--allowed-origins` は境界ではない（リダイレクト・WebSocket には効かない） | 手元のアプリだけを開く用途に限り、runbook に「境界ではない」と書く。任意コードを動かす操作は allow に入れない |
| MCP のパッケージに問題のある版が出る | バージョン固定（0.0.83 は `npm audit` で 0 件を確認済み）。上げるときは PR で行い、`npm view` で公開日（2 週間以上前）と、上と同じ `npm audit`（high/critical が 0）を確かめる |
| パスワードが会話の記録に残る | `--secrets` で名前だけを入力し、出力も伏せ字にする。`.env.e2e` は settings で Read が deny 済み |
| trace・レポートが CI の成果物で公開される | CI では trace を作らず、上げるのは `*.png` だけ（TC-21・TC-22・M-14） |
| 見張りの許可を広げすぎる | e2e サービス・`npx playwright test`・列挙した選択肢に限る。列挙外は確認（TC-05 の通らない例） |
| 判定スクリプトの見落とし（false-green） | テストを先に書き、偽物のスクリプトで不合格になることを確かめる（TC-07） |
| I188・I185 P6・P15 と同じファイルを触る | 今の develop に合わせて変え、後から入る側が合わせる（イシューの方針）。M-16 で範囲の重なりを確かめる |
| `RATELIMIT_ENABLE=false` のまま忘れる | runbook に元に戻す手順を書く。backend を作り直すと既定（有効）に戻る |

## 11. 運用設計（外部パッケージを使うため）
- 外部パッケージ: `@playwright/mcp@0.0.83` は Claude Code の起動時に `npx -y` で取得される（初回のみダウンロード）。ネットワークが無いと MCP は起動せず、画面確認だけが使えない（他の作業は止まらない）。
- タイムアウト: 既定（操作 5 秒・画面遷移 60 秒・操作後の待ち 500 ミリ秒）を使う。
- ログ: 画面確認の結果はテスト記録の 1 行に残す。MCP のログは残さない。
- 段階リリース・切り戻し: 不要（`.mcp.json` の 1 項目を消せば戻る）。

## 12. コスト・保守見積もり（外部パッケージの追加があるため）
- 費用: 0 円（OSS・GitHub Actions のアーティファクトは失敗時の画像だけ・14 日）。
- 手作業: 初回だけ OS ライブラリと chromium の取得（ユーザーの sudo 1 回）。以後はなし。
- 保守: MCP のバージョンを上げる作業（任意のタイミング）・判定スクリプト 1 本（約 60 行）とそのテスト。

## 13. 性能・UX設計
- アプリの画面は変えない（P6 影響なし: ローディング・空状態・エラー表示・破壊的操作の導線の変更はない）。
- 開発の待ち時間はステップ 7 で測り、改善案は数字つきで別イシューにする。

## 14. 該当しない条件付きセクション
- 10. データ整合性設計: DB 変更なし（P3 影響なし）。
- 14. 学習効果設計: 学習機能の変更なし。
- 15. プライバシー・コンプライアンス設計: 個人情報・未成年データ・テナントデータを新しく扱わない。使うのは E2E 用のテストアカウントだけで、画像は git にも外部にも出さない（P9 影響なし）。

## 15. 承認ポイント
- [ ] 画面を動かす仕組みは Playwright MCP 0.0.83（固定）で、ホストに OS ライブラリを入れて動かす（ユーザーの sudo 1 回）。開ける先は `http://localhost:*`・`http://127.0.0.1:*`、状態は使い捨て、パスワードは `--secrets` で Claude に見せない
- [ ] 許可する MCP の操作は 20 個。任意コードを動かす・ファイルを渡す・通信の中身を返す 5 個は使うたびに確認
- [ ] 判定スクリプトは `frontend/src` を変えたイシューで「## 画面確認」の行と `.evidence/I###/` の画像の実在を確かめ、`/test` の手動テストの最後で止める
- [ ] 実施者の基準を「画面の表示・遷移・コンソールは Claude、観測できないものだけ Human」に改める（plan-issue・plan-writing-rules・テンプレートの 3 か所）
- [ ] lint の定義を `package.json` に 1 本化し、CI と pre-commit がそれを呼ぶ
- [ ] CI では trace を作らず、失敗時の画面キャプチャだけを 14 日残す（今の playwright-report のアップロードは削除）
- [ ] e2e コンテナを安全なコンテキストとして扱う起動オプションを入れる・E2E を続けて流すときは `RATELIMIT_ENABLE=false` で backend を起動
- [ ] 見張りは e2e サービスの `npx playwright test`（列挙した選択肢だけ）を通す
- [ ] レビューの観点は `code-reviewer.md` に足す（イシューの表では code-review の SKILL.md だが、観点の置き場所が code-reviewer.md のため）
- [ ] `.github/workflows/`・`.claude/settings.json`・見張りを変えるので高リスク判定の対象（`/security-review` → `/implement`）

## 16. フロント開発設定の点検結果
（ステップ 7 で記入する）

## レビュー結果
- [20261024_2023 判定: ✅ 完了](../../reviews/I187_plan_review_20261024_2023.md)
- [20261024_2014 判定: 差し戻し（Blocker 1件）](../../reviews/I187_plan_review_20261024_2014.md)
