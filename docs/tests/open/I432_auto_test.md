# I432 自動テスト: Dependabot #377（@playwright/test 1.64.1）で E2E が落ちる原因を直して取り込む

実行コマンド（例）: CI の E2E（`.github/workflows/e2e.yml`・PR #575）／ `npm audit --audit-level=high`（`e2e/` で・キャッシュは `$TMPDIR`）

| TC | 内容 | 期待値 | 種別 | 結果 |
|---|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i213_dependabot.sh`: 土台イメージ（`docker-compose.yml` の e2e を含む）の `@sha256:` 固定・action の SHA 固定・pull_request のワークフローに secrets を置かない・パスワードの伏せ字が `GITHUB_ENV` への書き込みより先 | exit 0（`fail=0`）。失敗の注入（FG-I1a・FG-I1b・FG-W1c・FG-W3a など）は既存のテストに入っていて、それぞれ不合格になる | 決定論ゲート（既存・FG つき） | 計画時（変更前）: pass=17 fail=0 |
| TC-02 | `bash scripts/claude/tests/test_i182_secret_gates.sh`: `e2e.yml` の `permissions` が読み取りだけ（C4）など | exit 0（`fail=0`）。FG-C4（permissions を消すと不合格）は既存 | 決定論ゲート（既存・FG つき） | 計画時（変更前）: pass=54 fail=0 |
| TC-03 | PR #575 の CI の「E2E Tests (Playwright)」 | conclusion が SUCCESS。ログの中身の確かめは手動 No.1 | CI | 実装前のため未実行 |
| TC-04 | `e2e/` で `npm audit --audit-level=high`（1.65.1 の lock に対して） | exit 0（high・critical が 0 件） | heavy（implement で流して結果を記録） | 実装前のため未実行 |

結果:
- backend: 変更なし（CI の Backend Tests が通ること）
- frontend: 変更なし（CI の Frontend Tests が通ること）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i213_dependabot.sh
bash scripts/claude/tests/test_i182_secret_gates.sh
```
