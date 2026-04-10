# I030 コードレビュー

## レビュー対象

| ファイル | 変更種別 |
|---------|---------|
| `.mcp.json` | 新規作成（MCP サーバー設定） |
| `docs/runbooks/mcp-github-setup.md` | 新規作成（設定手順 runbook） |

## セキュリティチェック

- [ ] `.mcp.json` に PAT 値（`ghp_xxx` / `github_pat_xxx`）がハードコードされていないこと
- [ ] `.mcp.json` の `env.GITHUB_PERSONAL_ACCESS_TOKEN` が `${GITHUB_PERSONAL_ACCESS_TOKEN}` 形式（環境変数参照）であること
- [ ] コミット履歴に PAT 値が含まれていないこと（`git log -p | grep "ghp_\|github_pat_"` で確認）
- [ ] runbook に Fine-grained PAT（クラシック PAT ではない）を使うよう明記されていること
- [ ] runbook に PAT のスコープが `study-app-multitenant` リポジトリのみ・Issues+PRs+Contents のみと明記されていること

## 設定正確性チェック

- [ ] `.mcp.json` が有効な JSON であること（`python3 -m json.tool .mcp.json` で確認）
- [ ] `mcpServers.github.command` が `"npx"` であること
- [ ] `mcpServers.github.args` に `"-y"` と `"@modelcontextprotocol/server-github"` が含まれること
- [ ] `.claude/settings.json` が変更されていないこと（`permissions`・`hooks` に影響なし）
- [ ] `.mcp.json` が git 追跡対象であること

## runbook チェック

- [ ] Fine-grained PAT 発行手順が具体的で正確であること（GitHub UI の操作手順）
- [ ] 環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` の設定方法が記載されていること
- [ ] Claude Code 再起動手順が記載されていること
- [ ] 動作確認方法（`claude mcp list` 等）が記載されていること
- [ ] トラブルシューティング（権限不足・環境変数未設定・PAT 期限切れ）が記載されていること

## レビュー結果

- [ ] OK（承認）
- [ ] NG（要修正）

### コメント

（レビュー実施後に記載）
