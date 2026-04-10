# I030 コードレビュー

## レビュー対象

| ファイル | 変更種別 |
|---------|---------|
| `.mcp.json` | 新規作成（MCP サーバー設定） |
| `docs/runbooks/mcp-github-setup.md` | 新規作成（設定手順 runbook） |

## セキュリティチェック

- [x] `.mcp.json` に PAT 値（`ghp_xxx` / `github_pat_xxx`）がハードコードされていないこと
- [x] `.mcp.json` の `env.GITHUB_PERSONAL_ACCESS_TOKEN` が `${GITHUB_PERSONAL_ACCESS_TOKEN}` 形式（環境変数参照）であること
- [x] コミット履歴に PAT 値が含まれていないこと（`git log -p | grep "ghp_\|github_pat_"` で確認）
- [x] runbook に Fine-grained PAT（クラシック PAT ではない）を使うよう明記されていること
- [x] runbook に PAT のスコープが `study-app-multitenant` リポジトリのみ・Issues+PRs+Contents のみと明記されていること

## 設定正確性チェック

- [x] `.mcp.json` が有効な JSON であること（`python3 -m json.tool .mcp.json` で確認）
- [x] `mcpServers.github.command` が `"npx"` であること
- [x] `mcpServers.github.args` に `"-y"` と `"@modelcontextprotocol/server-github@2025.4.8"` が含まれること（バージョン固定済み）
- [x] `.claude/settings.json` が変更されていないこと（`permissions`・`hooks` に影響なし）
- [x] `.mcp.json` が git 追跡対象であること

## runbook チェック

- [x] Fine-grained PAT 発行手順が具体的で正確であること（GitHub UI の操作手順）
- [x] 環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` の設定方法が記載されていること（echo 禁止・エディタ直接編集で履歴漏洩対策済み）
- [x] Claude Code 再起動手順が記載されていること
- [x] 動作確認方法（`claude mcp list` 等）が記載されていること
- [x] トラブルシューティング（権限不足・環境変数未設定・PAT 期限切れ・`${...}` 展開失敗）が記載されていること

## レビュー結果

- [x] OK（承認）
- [ ] NG（要修正）

### コメント

（レビュー実施後に記載）
