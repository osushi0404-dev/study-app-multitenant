# I213 自動テスト: Dependabot を点検し、動いて役に立つ形に直す

実行コマンド（例）: `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i213_dependabot.sh` / `pre-commit run check-dependabot --files .github/dependabot.yml`

アプリの pytest・Jest は非該当（アプリのコードを変えない）。E2E は PR の CI（e2e.yml）が流す。

結果:
- backend: 非該当
- frontend: 非該当
- harness（計画時・2026-10-29・変更前の基準）: TC-02・TC-04 の 6 本は `run-all: pass=6 fail=0`。TC-01 は実装前のため未実行（テストのファイルがまだ無い）。TC-03 は実装前のため未実行（フックがまだ無い。スキーマの FG は計画のスパイク 3 で確認済み）

## TC-01 `scripts/claude/tests/test_i213_dependabot.sh`（新規）
実物のファイルで合格（exit 0）し、写しを壊した FG ではそれぞれ不合格になること。合否は終了コード（合格 0・不合格 1）。

| ID | 確かめること | 合格の条件 | FG（写しを壊すと不合格） |
|---|---|---|---|
| D1 | dependabot.yml の対象 | (package-ecosystem, directory) の組がちょうど {pip:/backend, npm:/frontend, npm:/e2e, docker:/backend, docker:/frontend, docker-compose:/, github-actions:/, pre-commit:/} | 1 組を消す／`uv:/scripts/claude/tests` を足す |
| D2 | `target-branch` が無い | どの対象にも `target-branch` キーが無い | 1 つに `target-branch: "develop"` を足す |
| D3 | 待つ日数 | 全部の対象で `cooldown.default-days == 7`。pip・npm は `semver-major-days == 14`。ほかの対象に `semver-*-days` が無い | default-days を 3 にする／npm /e2e の semver-major-days を消す／docker に semver-major-days を足す |
| D4 | まとめ方 | 全部の対象の `groups` に `applies-to: version-updates` と `applies-to: security-updates` の組がそれぞれちょうど 1 つずつあり、どちらも `update-types == ["minor", "patch"]` | security の組を消す／version の update-types に major を足す |
| D5 | ラベル | pip・npm・docker・docker-compose は `["dependencies", "track:app"]`、github-actions・pre-commit は `["dependencies", "track:harness"]` | github-actions のラベルを track:app にする |
| D6 | ignore | docker /backend に `python` の `version-update:semver-major`・`version-update:semver-minor`、docker /frontend に `node` の major、docker-compose に `postgres`・`redis` の major | python の minor を消す／redis の行を消す |
| W1 | action の固定 | `.github/workflows/*.yml` の `uses:` の行がすべて `uses: <owner>/<repo>@<40 桁の 16 進> # v<数字と点>` | 写しの 1 行を `@v4`／`@v10.3.3`／SHA のまま版のコメントを消す |
| W2 | secrets を使わない | `on:` に `pull_request` がある workflow に `secrets.` の文字列が無い（`secrets.GITHUB_TOKEN` も含めて無い） | e2e.yml の写しに `${{ secrets.E2E_TEST_PASSWORD }}` を戻す |
| W3 | パスワードの作り方 | e2e.yml のある step の `run` が `openssl rand -hex` を含み、`::add-mask::` の行が `>> "$GITHUB_ENV"` の行より前。その step が `Initialize E2E database` より前 | add-mask の行を消す／add-mask と GITHUB_ENV の行の順を入れ替える |
| I1 | 土台イメージの指紋 | `backend/Dockerfile`・`frontend/Dockerfile`・`frontend/Dockerfile.dev` の `FROM` のうち、前の段の名前（`base` など）でないものと、`docker-compose.yml` のすべての `image:` が `@sha256:<64 桁の 16 進>` で終わる | 写しの 1 つから `@sha256:…` を消す（Dockerfile・compose それぞれ） |
| V1 | 名前の無い保存領域 | `docker-compose.yml` の全サービスの volumes のうち名前の無いもの（短い書き方で `:` を含まない・長い書き方で `source` が無い）が、frontend の `/app/node_modules` ちょうど 1 つ | db に `- /var/lib/postgresql/data` を足す |
| P1 | e2e のブラウザ | e2e サービスの command に `npx playwright install chromium` があり、`npm test` より前 | 写しから `npx playwright install chromium && ` を消す |
| R1 | 起動コマンド | `docs/runbooks/common-commands.md`・`frontend-verify.md`・`worktree.md` に `docker compose up -d --build --renew-anon-volumes` があり、`docker compose up -d` の直後が行末・空白＋`#`・`` ` ``・`）` の書き方（サービス名を付けない素の起動）が無い | 写しの 1 か所を `docker compose up -d` に戻す |
| K1 | 書き間違いの検証 | `.pre-commit-config.yaml` に repo `https://github.com/python-jsonschema/check-jsonschema` のフック `check-dependabot` がある | 写しからそのフックを消す |
| M1 | runbook | `docs/runbooks/dependency-audit.md` に `## Dependabot` の見出しがあり、その節に `CI が緑` `/issue-bootstrap` `track:app` `track:harness` `cooldown` `--renew-anon-volumes` `uv` `target-branch` `@sha256:` の言葉がすべてある | 写しから `/issue-bootstrap` を消す |

## TC-02 `scripts/claude/tests/test_i204_tool_sync.sh`（書き換え）
- 実物の `ci.yml`（setup-uv を SHA で固定）で合格
- FG: setup-uv を `@v10`（今の uv_major_tag）・`@v10.3.3`（新しい FG）にすると不合格。ほかの既存の FG（python-version・version・version-file を消す・setup-python・別の uses・install）は今のまま不合格

## TC-03 `check-dependabot`（pre-commit）
- `pre-commit run check-dependabot --files .github/dependabot.yml` が Passed（test-gate で実行し記録する）。CI の `Backend Lint & Security` でも走る
- FG（計画のスパイク 3 で確認済み）: package-ecosystem の綴り・`applies-to` の値・`default-days` の綴り・日数の型を壊すと exit 1

## TC-04 影響を受ける既存のテスト
- `test_i182_secret_gates.sh`（e2e.yml の permissions・pre-commit の detect-secrets。SHA でも `pre-commit/action@` の判定は通る）
- `test_i109_dependency_audit.sh`（runbook の実在・CLAUDE.md の参照パス）
- `test_i179_worktree_docs.sh`（worktree.md・common-commands.md・danger-ops.md の言葉）
- `test_review_verdict.sh`（common-commands.md の言葉）
- `test_i211_version_pin.sh`（ci.yml の harness-tests）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i213_dependabot.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i204_tool_sync.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i182_secret_gates.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i109_dependency_audit.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i179_worktree_docs.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_review_verdict.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh
```
