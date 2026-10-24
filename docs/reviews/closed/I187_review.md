# I187 レビュー: フロント開発の検証ループを整える

## 変更概要
- Playwright MCP（0.0.83 固定・headless・開ける先は手元だけ・状態は使い捨て・パスワードは `--secrets`）を追加し、Claude が自分で画面を確かめられるようにする
- 画面確認の手順とエビデンスの残し方を `docs/runbooks/frontend-verify.md` にまとめ、`frontend/src` を変えたイシューで確認のし忘れを止める判定スクリプトを `/test` に組み込む
- 型チェック・lint を `frontend/package.json` のコマンドにし、CI と pre-commit がそれを呼ぶ
- E2E の失敗時の記録（手元: 画面キャプチャ＋trace・CI: 画面キャプチャだけ 14 日）と、e2e コンテナを安全なコンテキストとして扱う設定
- 見張りの安全一覧に e2e サービスの `npx playwright test` を追加
- レビューの観点・実施者の基準の更新、フロント開発設定の点検と所要時間の計測

## 変更点
- ステップ 1: `.mcp.json`（playwright・0.0.83）・`.claude/settings.json`（MCP 操作 20 個・`docker compose port`・`RATELIMIT_ENABLE=false docker compose up` の許可、`mcp__playwright__.*` の見張り登録）・`.gitignore`（`.evidence/`）・`pretooluse_guard.py`（MCP の保存の書き先を `.evidence/I###/` に限る）・テスト 2 本（`test_i187_frontend_verify_config.sh`・`test_i187_mcp_filename_guard.sh`）
- ステップ 2: `docs/runbooks/frontend-verify.md`（新規）・`CLAUDE.md`・`workflow.md` の参照・テンプレートの「## 画面確認」・実施者の基準 3 か所・`check-frontend-evidence.sh`（新規）とテスト・`/test` の SKILL.md
- ステップ 3: `frontend/package.json`（`typecheck`・`lint`）・`ci.yml`・`.pre-commit-config.yaml`
- ステップ 4: `e2e/playwright.config.ts`（失敗時の画面キャプチャ・手元だけ trace・安全なコンテキスト）・`e2e.yml`（画面キャプチャだけ 14 日）
- ステップ 5: `pretooluse_guard.py`（e2e サービスの `npx playwright test`）・`test_pretooluse_container_guard.sh`（P100〜P105・C60〜C68・G27〜G29）
- ステップ 6: `.claude/review-agents/code-reviewer.md`（画面の動きの回帰テストの観点）

## 影響範囲
- Backend/DB: なし
- Frontend: `frontend/package.json`（scripts のみ）
- Config: `.mcp.json`・`.claude/settings.json`・`.gitignore`・`e2e/playwright.config.ts`・`.github/workflows/ci.yml`・`.github/workflows/e2e.yml`・`.pre-commit-config.yaml`
- ハーネス: `scripts/claude/check-frontend-evidence.sh`（新規）・`scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/tests/`（新規 2 本・既存 1 本にケース追加）・`.claude/skills/test/SKILL.md`・`.claude/skills/plan-issue/SKILL.md`・`.claude/review-agents/code-reviewer.md`
- 文書: `docs/runbooks/frontend-verify.md`（新規）・`docs/runbooks/workflow.md`・`CLAUDE.md`・`docs/runbooks/plan-writing-rules.md`・`docs/tests/templates/manual_test_template.md`

## テスト結果
- 自動: （/test で記入）
- 手動: （/test で記入）
- レビュー: （/code-review で記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- PR の revert。`.mcp.json` の `playwright` を消せば次のセッションから MCP は読み込まれない。ホストの OS ライブラリ・`~/.cache/ms-playwright/` の chromium はリポジトリ外（残しても害はない）
