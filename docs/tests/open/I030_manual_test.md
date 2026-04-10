# I030 手動テスト

## 前提条件
- GitHub で Fine-grained PAT を発行済み（対象: `study-app-multitenant`、権限: Issues R/W・Pull Requests R/W・Contents Read）
- 環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` に PAT を設定済み
- Claude Code を再起動済み

## テストケース

### T1: JSON フォーマット確認
- **手順**: `python3 -m json.tool .mcp.json` を実行
- **期待値**: エラーなく JSON が出力される（有効な JSON である）
- **合否**: [ ]

### T2: PAT ハードコード確認
- **手順**: `cat .mcp.json` でファイル内容を確認
- **期待値**:
  - `GITHUB_PERSONAL_ACCESS_TOKEN` の値が `${GITHUB_PERSONAL_ACCESS_TOKEN}` 形式（参照）
  - `ghp_` や `github_pat_` で始まるトークン値が含まれていない
- **合否**: [ ]

### T3: MCP ツールの表示確認
- **手順**: Claude Code を起動し、利用可能なツール一覧を確認（または `claude mcp list` を実行）
- **期待値**: `github` MCP サーバーが listed され、ステータスが connected になっている
- **合否**: [ ]

### T4: issue コメントの取得
- **手順**: Claude に「GitHub issue #71 の内容を MCP で確認して」と指示
- **期待値**: GitHub MCP 経由で issue の詳細・コメントを取得できる（gh CLI を使わずに）
- **合否**: [ ]

### T5: PR 差分・コメントの取得
- **手順**: Claude に「PR #70 の差分とコメントを MCP で確認して」と指示
- **期待値**: GitHub MCP 経由で PR の差分・コメントを取得できる
- **合否**: [ ]

### T6: git 追跡状態の確認
- **手順**: `git status` で `.mcp.json` の追跡状態を確認
- **期待値**: `.mcp.json` が git 追跡対象（untracked ではなく staged or committed）
- **合否**: [ ]

### T7: Fine-grained PAT の権限範囲確認（セキュリティ）
- **手順**: GitHub Settings > Developer settings > Fine-grained tokens で発行した PAT の設定を確認
- **期待値**:
  - 対象リポジトリが `study-app-multitenant` のみ
  - 権限が Issues (R/W)・Pull Requests (R/W)・Contents (Read) のみ
  - その他のリポジトリ・権限へのアクセスなし
- **合否**: [ ]
