# I030 コードレビュー

## レビュー対象

| ファイル | 変更種別 |
|---------|---------|
| `.claude/settings.json` | 変更（`mcpServers` セクション追加） |
| `docs/runbooks/mcp-github-setup.md` | 新規作成 |

## セキュリティチェック

- [ ] `settings.json` に PAT 値（`ghp_xxx`等）がハードコードされていないこと
- [ ] `settings.json` の `env.GITHUB_PERSONAL_ACCESS_TOKEN` が環境変数参照（`${...}`形式）であること
- [ ] コミット履歴に PAT 値が含まれていないこと（`git log -p` で確認）

## 設定正確性チェック

- [ ] `mcpServers.github.command` が `"npx"` であること
- [ ] `mcpServers.github.args` に `"-y"` と `"@modelcontextprotocol/server-github"` が含まれること
- [ ] 既存の `permissions`・`hooks` 設定が変更されていないこと
- [ ] `settings.json` が有効な JSON であること

## runbook チェック

- [ ] PAT 発行手順が具体的で正確であること
- [ ] 環境変数設定方法が記載されていること
- [ ] 動作確認方法が記載されていること
- [ ] トラブルシューティングが記載されていること

## レビュー結果

- [ ] OK（承認）
- [ ] NG（要修正）

### コメント

（レビュー実施後に記載）
