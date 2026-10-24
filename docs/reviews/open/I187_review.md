# I187 レビュー: フロント開発の検証ループを整える

## 変更概要
- Playwright MCP（0.0.83 固定・headless・開ける先は手元だけ・状態は使い捨て・パスワードは `--secrets`）を追加し、Claude が自分で画面を確かめられるようにする
- 画面確認の手順とエビデンスの残し方を `docs/runbooks/frontend-verify.md` にまとめ、`frontend/src` を変えたイシューで確認のし忘れを止める判定スクリプトを `/test` に組み込む
- 型チェック・lint を `frontend/package.json` のコマンドにし、CI と pre-commit がそれを呼ぶ
- E2E の失敗時の記録（手元: 画面キャプチャ＋trace・CI: 画面キャプチャだけ 14 日）と、e2e コンテナを安全なコンテキストとして扱う設定
- 見張りの安全一覧に e2e サービスの `npx playwright test` を追加
- レビューの観点・実施者の基準の更新、フロント開発設定の点検と所要時間の計測

## 変更点
- （実装後に記入）

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
