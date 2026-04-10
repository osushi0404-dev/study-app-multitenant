# I030 手動テスト

## 前提条件
- GitHub PAT（スコープ: `repo`）を発行済み
- `GITHUB_PERSONAL_ACCESS_TOKEN` 環境変数を設定済み
- Claude Code を再起動済み

## テストケース

### T1: MCP ツールの表示確認
- **手順**: Claude Code を起動し、ツール一覧を確認
- **期待値**: GitHub MCP 関連ツール（`mcp__github__*`等）がツール一覧に表示される
- **合否**: [ ]

### T2: issue コメントの取得
- **手順**: Claude に「このリポジトリの issue #71 のコメントを確認して」と指示
- **期待値**: GitHub MCP 経由で issue の詳細・コメントを取得できる
- **合否**: [ ]

### T3: PR 差分・コメントの取得
- **手順**: Claude に「PR #70 の差分とコメントを確認して」と指示
- **期待値**: GitHub MCP 経由で PR の差分・コメントを取得できる
- **合否**: [ ]

### T4: PAT ハードコード確認
- **手順**: `cat .claude/settings.json` で設定ファイルを確認
- **期待値**: `GITHUB_PERSONAL_ACCESS_TOKEN` の値が `${GITHUB_PERSONAL_ACCESS_TOKEN}` 形式（参照）であり、実際のトークン値（`ghp_xxx`等）が記載されていない
- **合否**: [ ]

### T5: git-tracked ファイルへの PAT 漏洩チェック
- **手順**: `git diff HEAD` と `git log -p -1` でコミット内容を確認
- **期待値**: `ghp_` で始まる文字列がコミット内容に含まれていない
- **合否**: [ ]
