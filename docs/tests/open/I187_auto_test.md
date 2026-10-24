# I187 自動テスト: フロント開発の検証ループを整える

実行コマンド: 下の「決定論ゲート」を `/code-review` が実走する。heavy なもの（下の「/test に委譲」）は `/test` で確かめる。

pytest・Jest・E2E: 手元では流さず、CI で確かめる（TC-H1）。アプリのコード（`backend/`・`frontend/src/`）は変えていないが、E2E の設定（`playwright.config.ts`）と CI の定義は変えているため、PR の HEAD で pytest・Jest・E2E が全部緑であることを TC-H1 で確かめる。実装中に手元の E2E 8 件も合格している（M-13）

## TC 一覧

| TC | 確かめること | 合否（exit code） |
|---|---|---|
| TC-01 | `.mcp.json` が JSON として正しい | 合格=0 |
| TC-02 | `.claude/settings.json` が JSON として正しい | 合格=0 |
| TC-03 | `test_i187_frontend_verify_config.sh`（新規）: ①`.mcp.json` の `playwright` の `command` が `npx`、`args` が計画 5-2-1 の 12 語と完全一致（順番を含む） ②`github` の設定が変わっていない（`@modelcontextprotocol/server-github@2025.4.8`） ③`.claude/settings.json` の allow に計画 5-2-1 の 20 個（`mcp__playwright__<名前>`）がすべてある ④allow に `browser_run_code_unsafe`・`browser_evaluate`・`browser_file_upload`・`browser_drop`・`browser_network_request` が無い（`mcp__playwright` だけ・`mcp__playwright__*` などサーバー全体を許す書き方も無い） ⑤allow に `Bash(docker compose port *)` がある（⑤a）。e2e サービスの実行は既定コマンド `Bash(docker compose --profile e2e run --rm e2e)` と `Bash(docker compose --profile e2e run --rm e2e npx playwright test *)`（`RATELIMIT_ENABLE=false ` の前置きあり版も同じ 2 つ）の 4 つがある（⑤b）。e2e・e2e-init での `npm test -- --output=.`・`npx jest`・`migrate` を、よくある書き方（`--rm` なし・順番違い・`--service-ports`・`exec`・`docker-compose`・前置きあり）で並べた代表コマンドのどれにも、allow のどのルールもワイルドカードとして一致しない（⑤b'・計画変更記録 3）。既定コマンドと `npx playwright test tests/auth.spec.ts --retries=0`、`docker compose exec [-T] frontend npm run typecheck`・`lint` は allow に一致する（⑤b''・計画変更記録 4）。frontend の exec に末尾を何でも受ける許可が無い（⑤d）。効かない `Bash(RATELIMIT_ENABLE=false docker compose up *)` が無い（⑤c・計画変更記録 2） ⑥deny の `Read(**/.env.e2e)` が残っている ⑦（/security-review で追加）`hooks.PreToolUse` に matcher `mcp__playwright__.*` で `pretooluse_guard.py` が登録されている | 合格=0 |
| TC-04 | `.gitignore` に `.evidence/` だけの行がある（行全体で一致） | 合格=0 |
| TC-05 | `test_pretooluse_container_guard.sh`: 既存のケースすべてに加え、I187 のケース（下の表）が期待どおり | 合格=0 |
| TC-06 | `pretooluse_guard.py` が Python として正しい | 合格=0 |
| TC-07 | `test_check_frontend_evidence.sh`（新規）: 下の表の 16 ケース（E1〜E15・E12 は 2 つ）が期待どおり | 合格=0 |
| TC-08 | `check-frontend-evidence.sh` が bash として正しい | 合格=0 |
| TC-09 | runbook に URL の求め方 `docker compose port frontend 3000` がある | 合格=0 |
| TC-10 | runbook に画像の保存先 `.evidence/I###/` がある | 合格=0 |
| TC-11 | runbook に `e2e_user_a@example.com` と `e2e_user_c@example.com` がある（2 件） | 合格=0 |
| TC-12 | runbook に落とし穴 4 件の避け方のキーワード（`install-deps`・`RATELIMIT_ENABLE=false`・`unsafely-treat-insecure-origin-as-secure`・`npm run typecheck`）がある（4 件） | 合格=0 |
| TC-13 | runbook に画像が消えるタイミング（`wt-remove.sh`）・テスト記録の見出し（`## 画面確認`）・公式と自作の分担の見出し（`## 公式と自作の分担`）・境界ではない旨（`セキュリティの境界ではない`）がある（4 件） | 合格=0 |
| TC-14 | `CLAUDE.md` と `docs/runbooks/workflow.md` に `docs/runbooks/frontend-verify.md` への参照がある（2 件） | 合格=0 |
| TC-15 | テンプレート `manual_test_template.md` に `## 画面確認` の表がある | 合格=0 |
| TC-16 | `/test` の SKILL.md が `check-frontend-evidence.sh` を実行する | 合格=0 |
| TC-17 | 実施者の基準の 3 か所（plan-issue の SKILL.md・plan-writing-rules.md・テンプレート）に「ブラウザ操作」を Human とする書き方が残っていない（3 件） | 合格=0 |
| TC-18 | `frontend/package.json` に `"typecheck": "tsc --noEmit"` と `"lint": "eslint src/ --ext .ts,.tsx --max-warnings 0"` がある（2 件） | 合格=0 |
| TC-19 | `ci.yml` が `npm run typecheck`・`npm run lint -- -f github-actions` を呼び、`npx tsc`・`npx eslint` が残っていない（4 件） | 合格=0 |
| TC-20 | `.pre-commit-config.yaml` の ESLint が `npm run lint` を呼び、`npx eslint` が残っていない（2 件） | 合格=0 |
| TC-21 | `playwright.config.ts` に `screenshot: 'only-on-failure'`・`isCI ? 'off' : 'retain-on-failure'`・`unsafely-treat-insecure-origin-as-secure` があり、`on-first-retry` が残っていない（4 件） | 合格=0 |
| TC-22 | `e2e.yml` の失敗時アップロードが `path: e2e/test-results/**/*.png`・`retention-days: 14` で、`playwright-report` が残っていない（3 件） | 合格=0 |
| TC-23 | `code-reviewer.md` に観点「E2E か単体テストを追加・更新」がある | 合格=0 |
| TC-25 | （/security-review で追加）`test_i187_mcp_filename_guard.sh`（新規）: 下の表の 11 ケースが期待どおり。見張りの複製から `mcp__playwright__` の分岐を外すと F3 が不合格（0 が返る）になる | 合格=0 |
| TC-24 | 計画書の「16. フロント開発設定の点検結果」が記入済み（`（ステップ 7 で記入する）` が残っていない）で、見出し `### 別イシューのタイトル案` がある（2 件） | 合格=0 |

### /test に委譲（heavy）
| TC | 確かめること | 合否 |
|---|---|---|
| TC-H1 | PR の HEAD で CI（Frontend Type Check・Frontend Lint & Security・Frontend Tests ほか全ジョブ）と E2E が全部 success（`gh pr checks`） | 全 success で合格 |
| TC-H2 | `docker compose exec frontend npm run typecheck` と `docker compose exec frontend npm run lint` が exit 0 | 合格=0 |

### TC-05: 見張りに足すケース（`test_pretooluse_container_guard.sh`）
`E='docker compose --profile e2e run --rm e2e'` とする。

| ケース | コマンド | 期待 |
|---|---|---|
| P100 | `$E npx playwright test tests/auth.spec.ts --retries=0` | 0（素通し） |
| P101 | `$E npx playwright test tests/auth.spec.ts --retries 0 --reporter=line` | 0 |
| P102 | `$E npx playwright test -g ログイン --project chromium-unauthed` | 0 |
| P103 | `$E npx playwright test tests/a.spec.ts tests/b.spec.ts --workers=1 -x --max-failures=1 --timeout=60000` | 0 |
| P104 | `$E npx playwright test --list` | 0 |
| P105 | `$E npx playwright test tests/auth.spec.ts --retries=0 2>&1 \| tail -30` | 0（ホスト側のパイプ・リダイレクトはコンテナ内の判定に入らない。計画 5-2-6・既存の P37・P40 と同じ） |
| P106 | （実装時に追加・計画変更記録 2）`RATELIMIT_ENABLE=false $E npx playwright test tests/auth.spec.ts --retries=0` | 0 |
| C60 | `$E npx playwright test --config other.config.ts` | ASK |
| C61 | `$E npx playwright test --update-snapshots` | ASK |
| C62 | `$E npx playwright test --reporter=./my-reporter.js` | ASK |
| C63 | `$E npx playwright install` | ASK |
| C64 | `$E npm install left-pad` | ASK |
| C65 | `docker compose exec frontend npx playwright test` | ASK（e2e 以外のサービス） |
| C66 | `docker compose run --rm backend npx playwright test` | ASK（e2e 以外のサービス） |
| C67 | `$E sh -c "npx playwright test; npm install left-pad"` | ASK（中のシェルに一覧外の操作。実装時に `rm -r` から変更: `rm -r` は危険操作として先に停止〔exit 2〕になり、確かめたい「一覧外は通さない」の判定に届かないため） |
| C68 | `$E npx playwright test --output /tmp/x` | ASK |

### TC-07: 判定スクリプトのケース（`test_check_frontend_evidence.sh`）
一時リポジトリ（`origin/develop` 相当の基準コミットを作り、`BASE_REF` で渡す）で実行する。

| ケース | 状況 | 期待 |
|---|---|---|
| E1 | `frontend/src` を変えていない（`backend/` だけ変更）・テスト記録なし | exit 0（対象外） |
| E2 | `frontend/src/App.tsx` を変更・テスト記録に `## 画面確認` が無い | exit 1 |
| E3 | 変更あり・行の画像 `login-a-1.png` が `.evidence/I999/` に実在 | exit 0 |
| E4 | 変更あり・行の画像が実在しない | exit 1 |
| E5 | 変更あり・画像の列が `理由: バックエンドだけの不具合でエラー画面を出せないため` | exit 0 |
| E6 | 変更あり・画像の列が `理由:`（理由が空） | exit 1 |
| E7 | 変更あり・画像の列が `../secret.png`（`..` を含む） | exit 1 |
| E8 | 変更あり・テンプレートの空行だけ（画像の列が空） | exit 1 |
| E9 | 変更あり・合格の行と不合格の行が 1 行ずつ | exit 1 |
| E10 | 変更あり・画像 2 つ（`a.png, b.png`）がどちらも実在 | exit 0 |
| E11 | 変更あり・テスト記録が `docs/tests/closed/` にだけある（画像あり） | exit 0 |
| E12 | 引数なし（E12a）／`I99` のような形（E12b） | exit 2 |
| E13 | （実装時に追加）変更あり・テスト記録が無い | exit 1 |
| E14 | （実装時に追加）基準のブランチが無い（`git diff` が失敗） | exit 2 |
| E15 | （実装時に追加）`## 画面確認` の表は空で、後ろの別の節の表に合格の行がある | exit 1（別の節は数えない） |

### TC-25: MCP の書き先のケース（`test_i187_mcp_filename_guard.sh`）
見張りに `{"tool_name": <操作>, "tool_input": {...}}` を渡し、終了コードを見る（2 = 止める・0 = 通す）。

| ケース | 操作 | `filename` | 期待 |
|---|---|---|---|
| F1 | `mcp__playwright__browser_take_screenshot` | `.evidence/I187/login-a-1.png` | 0 |
| F2 | `mcp__playwright__browser_take_screenshot` | （なし） | 0 |
| F3 | `mcp__playwright__browser_take_screenshot` | `backend/.env` | 2 |
| F4 | `mcp__playwright__browser_take_screenshot` | `.evidence/I187/../../backend/.env` | 2 |
| F5 | `mcp__playwright__browser_take_screenshot` | `/tmp/x.png` | 2 |
| F6 | `mcp__playwright__browser_take_screenshot` | `.evidence/x.png`（イシューのフォルダなし） | 2 |
| F7 | `mcp__playwright__browser_snapshot` | `.claude/settings.json` | 2 |
| F8 | `mcp__playwright__browser_console_messages` | `.evidence/I187/console.txt` | 0 |
| F9 | `mcp__playwright__browser_network_requests` | `e2e/.env.e2e` | 2 |
| F10 | `mcp__playwright__browser_find` | `.evidence/I187/sub/x.txt`（フォルダの入れ子） | 2 |
| F11 | `mcp__playwright__browser_navigate` | （なし・`url` だけ） | 0 |

## false-green の確認
- 計画時（2026-10-24・実装前）: 下の決定論ゲートのうち grep・json.tool の行を非対話の bash で実走し、**実装前の今の状態ではすべて不合格（exit≠0）**になることを確認した（どれも「まだ変更していない状態」＝失敗条件を注入した状態に当たる）。結果は「計画時の実行結果」を参照。`TC-01`（`.mcp.json` は今も正しい JSON）・`TC-02`・`TC-06` は、今も合格するのが正しい（構文の確認）。
- 実装時に行うこと:
  - TC-03・TC-07: テストスクリプトを先に書き、変更前の設定ファイル（TC-03）・スクリプトが無い状態と常に exit 0 で終わる偽物のスクリプト（TC-07）に当てて不合格になることを確かめてから本体を書く。
  - TC-05: I187 のケースを先に足し、変更前の見張りで P100〜P105 が不合格（ASK が返る）になることを確かめる。さらに、e2e のサービス名の確認を外した見張りの複製で C65・C66 が不合格（0 が返る）になることを確かめる（テストスクリプトの中で複製を作って当てる。既存の G23〜G25 と同じやり方）。
  - TC-17・TC-19〜TC-22 の「残っていない」判定: 変更前のファイルで不合格になることは計画時に確認済み。

### 計画時の実行結果（2026-10-24・実装前・非対話 bash）
- 実装前の今のワークツリー（`47269b2` の状態）で、決定論ゲート 46 行を `code-review.sh` と同じ抽出規則で実走した:
  - 合格（exit 0）: `TC-01`・`TC-02`（構文。今も正しいのが正）・既存の見張りテスト（`test_pretooluse_container_guard.sh`・I187 のケースは未追加）・`TC-06`
  - 不合格: 残り 42 行すべて（新規スクリプト 3 本は exit 127＝ファイルなし、runbook の 12 行は exit 2＝ファイルなし、ほかの grep は exit 1、`! grep` の 9 行は対象の文言が今あるため不合格）
- 逆向きの確認: 期待する行だけを入れたおとりのファイル群（スクラッチパッドの `decoy_pass.sh`）に同じ grep 系 38 行を当て、38 行すべて合格（exit 0）になることを確認した（書き方のせいで常に不合格になる行が無い）
- 46 行とも `classify_gate` の ALLOW 形（チェーン・パイプ・`$(`・`>` を含まない）で書いた

## 決定論ゲート（自動実走）
```bash
python3 -m json.tool .mcp.json
python3 -m json.tool .claude/settings.json
bash scripts/claude/tests/test_i187_frontend_verify_config.sh
grep -qx "\.evidence/" .gitignore
bash scripts/claude/tests/test_pretooluse_container_guard.sh
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
bash scripts/claude/tests/test_check_frontend_evidence.sh
bash -n scripts/claude/check-frontend-evidence.sh
grep -qF "docker compose port frontend 3000" docs/runbooks/frontend-verify.md
grep -qF ".evidence/I###/" docs/runbooks/frontend-verify.md
grep -qF "e2e_user_a@example.com" docs/runbooks/frontend-verify.md
grep -qF "e2e_user_c@example.com" docs/runbooks/frontend-verify.md
grep -qF "install-deps" docs/runbooks/frontend-verify.md
grep -qF "RATELIMIT_ENABLE=false" docs/runbooks/frontend-verify.md
grep -qF "unsafely-treat-insecure-origin-as-secure" docs/runbooks/frontend-verify.md
grep -qF "npm run typecheck" docs/runbooks/frontend-verify.md
grep -qF "wt-remove.sh" docs/runbooks/frontend-verify.md
grep -qF "## 画面確認" docs/runbooks/frontend-verify.md
grep -qx "## 公式と自作の分担" docs/runbooks/frontend-verify.md
grep -qF "セキュリティの境界ではない" docs/runbooks/frontend-verify.md
grep -qF "docs/runbooks/frontend-verify.md" CLAUDE.md
grep -qF "docs/runbooks/frontend-verify.md" docs/runbooks/workflow.md
grep -qx "## 画面確認" docs/tests/templates/manual_test_template.md
grep -qF "check-frontend-evidence.sh" .claude/skills/test/SKILL.md
! grep -qF "ブラウザ操作" .claude/skills/plan-issue/SKILL.md
! grep -qF "ブラウザ操作" docs/runbooks/plan-writing-rules.md
! grep -qF "ブラウザ操作" docs/tests/templates/manual_test_template.md
grep -qF "\"typecheck\": \"tsc --noEmit\"" frontend/package.json
grep -qF "\"lint\": \"eslint src/ --ext .ts,.tsx --max-warnings 0\"" frontend/package.json
grep -qF "run: npm run typecheck" .github/workflows/ci.yml
grep -qF "run: npm run lint -- -f github-actions" .github/workflows/ci.yml
! grep -qF "npx tsc" .github/workflows/ci.yml
! grep -qF "npx eslint" .github/workflows/ci.yml
grep -qF "npm run lint" .pre-commit-config.yaml
! grep -qF "npx eslint" .pre-commit-config.yaml
grep -qF "screenshot: 'only-on-failure'" e2e/playwright.config.ts
grep -qF "isCI ? 'off' : 'retain-on-failure'" e2e/playwright.config.ts
grep -qF "unsafely-treat-insecure-origin-as-secure" e2e/playwright.config.ts
! grep -qF "on-first-retry" e2e/playwright.config.ts
grep -qF "path: e2e/test-results/**/*.png" .github/workflows/e2e.yml
grep -qF "retention-days: 14" .github/workflows/e2e.yml
! grep -qF "playwright-report" .github/workflows/e2e.yml
grep -qF "E2E か単体テストを追加・更新" .claude/review-agents/code-reviewer.md
! grep -qF "（ステップ 7 で記入する）" docs/plans/open/plan_I187.md
grep -qx "### 別イシューのタイトル案" docs/plans/open/plan_I187.md
bash scripts/claude/tests/test_i187_mcp_filename_guard.sh
```

## 実行結果（/test・2026-10-24）
- 決定論ゲート: 46/46 合格（`1a04245`・auto_test.md の「決定論ゲート」を 1 行ずつ実行）。計画変更記録 4 の後も TC-03 は 14/14 合格
- TC-H1: PR #323 の HEAD `1a04245` で CI 6 ジョブ（Backend Lint & Security・Backend Tests・E2E Tests (Playwright)・Frontend Lint & Security・Frontend Tests・Frontend Type Check）すべて pass（`gh pr checks 323`）。計画変更記録 4 のコミットで再実行される CI も確認する
- TC-H2: `docker compose exec -T frontend npm run typecheck`・`npm run lint` ともに exit 0
- 画面確認の判定: `check-frontend-evidence.sh I187` は「対象外（frontend/src を変えていません）」で exit 0
