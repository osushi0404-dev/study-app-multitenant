# plan_I030: GitHub MCP の導入・設定

## 基本情報
- **計画書ID**: plan_I030
- **関連イシュー**: #71 (I030)
- **作成根拠資料**: docs/issues/open/I030.md, docs/proposals/I026_ai_dev_improvement_proposal.md（改善案 B）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-10

## 背景・目的

現状の `gh` CLI では以下の操作が煩雑：
- PR の全コメント一括取得（ページネーション手動処理が必要）
- PR 差分の Claude への直接受け渡し（ファイル経由が必要）
- issue のラベル・マイルストーン操作（コマンド組み合わせが複雑）

GitHub が公式提供する MCP サーバー（`@modelcontextprotocol/server-github`）を導入し、Claude が GitHub API を直接活用できるようにする。これにより `/code-review`・`/plan-issue`・`/close` フェーズの品質と自動化度を向上させる。

## 受け入れ条件

- [ ] Claude が GitHub MCP 経由で issue のコメントを取得できる
- [ ] Claude が GitHub MCP 経由で PR の差分・コメントを取得できる
- [ ] PAT がファイルにハードコードされていない（環境変数管理）
- [ ] MCP の設定方法が runbook に記載されている

## 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra:
  - `.claude/settings.json`: `mcpServers` セクション追加
  - `docs/runbooks/mcp-github-setup.md`: 新規作成（設定手順 runbook）

## 調査結果

### GitHub MCP パッケージの選択

| パッケージ | 管理元 | 特徴 |
|-----------|--------|------|
| `@modelcontextprotocol/server-github` | MCP リファレンス実装 | 安定・Claude Code ドキュメントで多く参照 |
| `@github/mcp-server` | GitHub 公式（新） | 最新・公式メンテ、より高機能 |

→ **`@modelcontextprotocol/server-github` を採用**（Claude Code との実績が豊富で、設定手順のドキュメントが充実）

### MCP 設定ファイルの場所

Claude Code のプロジェクト設定は `.claude/settings.json` に集約されており、`mcpServers` キーをここに追加するのが最もシンプル。別途 `.claude/mcp.json` を作成する方法もあるが設定が分散するため、既存の `settings.json` に統合する。

### PAT スコープ

このプロジェクト（プライベートリポジトリ）で issue/PR を読み書きするために必要な最小スコープ：
- `repo`（プライベートリポジトリのフル読み取り・PR/issue の書き込み）

最小権限の原則に基づき `repo` スコープのみで開始。必要に応じて後から追加する。

## 変更点一覧

### 1. `.claude/settings.json`（変更）

`mcpServers` セクションを追加：

```json
"mcpServers": {
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
    }
  }
}
```

- `command: "npx"` + `args: ["-y", ...]` により初回起動時に自動インストール
- `env.GITHUB_PERSONAL_ACCESS_TOKEN` は OS 環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` を参照（PAT 値はファイルに書かない）

### 2. `docs/runbooks/mcp-github-setup.md`（新規）

以下の内容を記載：
- GitHub PAT 発行手順（スコープ: `repo`）
- 環境変数の設定方法（`~/.bashrc` 等）
- Claude Code 再起動手順
- 動作確認方法（MCP ツール一覧の確認・issue 取得テスト）
- トラブルシューティング

## 実装手順

### Step 1: `.claude/settings.json` に `mcpServers` 追加

既存の `settings.json` に `mcpServers` キーを追加する。既存の `permissions`・`hooks` の設定は変更しない。

### Step 2: `docs/runbooks/mcp-github-setup.md` を新規作成

ユーザーが PAT を発行・設定するための手順書を作成する。

### Step 3: 動作確認（手動）

ユーザーが PAT を設定した後、Claude Code を再起動して動作確認を実施する。

## テスト計画

### 自動テスト

設定ファイルの追加・ドキュメント作成のみのため、自動テストなし。

### 手動テスト

1. 環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` を設定した状態で Claude Code を起動
2. GitHub MCP ツールが Claude のツール一覧に表示されることを確認
3. MCP 経由で本リポジトリの issue コメントを取得できることを確認
4. MCP 経由で PR の差分・コメントを取得できることを確認
5. `settings.json` に PAT 値がハードコードされていないことを確認（env 参照のみ）

## ロールバック

- `.claude/settings.json` の `mcpServers` セクションを削除
- `docs/runbooks/mcp-github-setup.md` を削除
- PAT 環境変数はユーザーが手動で shell profile から削除

コード・DB への影響なし。

## Risk & 回避策

| リスク | 対策 |
|--------|------|
| PAT が git にコミットされる | `settings.json` の env 値は環境変数参照のみ。PAT 値を直接書かないことをレビューで確認 |
| npx パッケージ取得失敗 | 初回起動時に自動ダウンロード。ネットワーク接続が必要（WSL2 環境では通常問題なし） |
| PAT スコープ不足でエラー | エラーメッセージで不足スコープを確認し PAT を再発行。`repo` スコープで対応可能なはず |
| MCP サーバーが起動しない | `claude mcp list` でステータス確認。ログで原因調査後、npx キャッシュ削除で再試行 |
| 環境変数未設定で Claude 起動 | MCP ツールが表示されないかエラーになる。runbook の手順を確認して環境変数を設定 |
