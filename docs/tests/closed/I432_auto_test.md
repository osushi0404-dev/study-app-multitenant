# I432 自動テスト: Dependabot #377（@playwright/test 1.64.1）で E2E が落ちる原因を直して取り込む

実行コマンド（例）: CI の E2E（`.github/workflows/e2e.yml`・PR #575）／ `npm audit --audit-level=high`（`e2e/` で・キャッシュは `$TMPDIR`）

| TC | 内容 | 期待値 | 種別 | 結果 |
|---|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i213_dependabot.sh`: 土台イメージ（`docker-compose.yml` の e2e を含む）の `@sha256:` 固定・action の SHA 固定・pull_request のワークフローに secrets を置かない・パスワードの伏せ字が `GITHUB_ENV` への書き込みより先 | exit 0（`fail=0`）。失敗の注入（FG-I1a・FG-I1b・FG-W1c・FG-W3a など）は既存のテストに入っていて、それぞれ不合格になる | 決定論ゲート（既存・FG つき） | 計画時（変更前）: pass=17 fail=0／implement（変更後）: pass=17 fail=0 |
| TC-02 | `bash scripts/claude/tests/test_i182_secret_gates.sh`: `e2e.yml` の `permissions` が読み取りだけ（C4）など | exit 0（`fail=0`）。FG-C4（permissions を消すと不合格）は既存 | 決定論ゲート（既存・FG つき） | 計画時（変更前）: pass=54 fail=0／implement（変更後）: pass=54 fail=0 |
| TC-03 | PR #575 の CI の「E2E Tests (Playwright)」 | conclusion が SUCCESS。ログの中身の確かめは手動 No.1 | CI | OK: run 44239178761（HEAD b01e9b10）conclusion success |
| TC-04 | `e2e/` で `npm audit --audit-level=high`（1.65.1 の lock に対して） | exit 0（high・critical が 0 件） | heavy（implement で流して結果を記録） | implement（2026-11-18）: `found 0 vulnerabilities`・exit 0 |

結果:
- backend: 変更なし（CI の Backend Tests が通ること）
- frontend: 変更なし（CI の Frontend Tests が通ること）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i213_dependabot.sh
bash scripts/claude/tests/test_i182_secret_gates.sh
```

## 実行記録
- 2026-11-18 implement: `bash scripts/claude/tests/test_i213_dependabot.sh` exit 0（pass=17）・`bash scripts/claude/tests/test_i182_secret_gates.sh` exit 0（pass=54）・`npm --prefix e2e audit --audit-level=high` exit 0（0 件）
- 2026-11-18 review-gate: 決定論ゲート 2 本を code-review.sh が実走（OK）・CI 全ジョブ成功（TC-03）
- 2026-11-18 test-gate: test-gate に回された heavy の TC なし（手元で E2E は流し直さない）

## 再発防止記録（fix-loop・2026-11-18）
- なぜ失敗したか: retro で作った `docs/reviews/backlog/I432.md` の見出しに、`- F4（…）` で始まる説明の行を足した。一覧の `- F` で始まる行は決まった形しか許されず、`test_i202_ledger_cleanup.sh` の D3 が close の後の CI で止めた（review-gate の時点では一覧のファイルがまだ無く、retro・close は手元でハーネスのテストを流さない）
- 何を変えたか: 説明の行を `- 載せないもの: F4（…）` に書き換えた（記録の 1 行だけ）
- セキュリティ上の考慮点: なし
- 次回どう防ぐか: 一覧は retro の手順 4-0 どおり、見出しを I206 と同じ形にし、スクリプトの出力の行だけを `- F…` で書く。テストは正しく止めたので変えない
- 確かめた結果: `bash scripts/claude/tests/test_i202_ledger_cleanup.sh` pass=163 fail=0（D3・FG-D3 合格）
