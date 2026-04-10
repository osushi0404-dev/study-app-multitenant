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

GitHub MCP サーバー（`@modelcontextprotocol/server-github`）を導入し、Claude が GitHub API を直接活用できるようにする。これにより `/code-review`・`/plan-issue`・`/close` フェーズの品質と自動化度を向上させる。

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
  - `.mcp.json`（プロジェクトルート）: 新規作成（MCP サーバー設定）
  - `docs/runbooks/mcp-github-setup.md`: 新規作成（設定手順 runbook）

## 調査結果

### GitHub MCP パッケージの選択

npm で利用可能な主なパッケージを確認した：

| パッケージ | バージョン | 管理元 |
|-----------|-----------|--------|
| `@modelcontextprotocol/server-github` | 2025.4.8 | MCP org 公式（modelcontextprotocol.io） |
| `github-mcp-server` | 1.8.7 | 個人（非公式） |
| `@github/mcp-server` | 存在しない | — |

→ **`@modelcontextprotocol/server-github`（v2025.4.8）を採用**

MCP org が公式メンテしており、バージョンが 2025.4.8 と活発に更新されている。`@github/mcp-server` は npm に存在しない。

### MCP 設定ファイルの場所

Claude Code のプロジェクトレベル MCP 設定は `.mcp.json`（プロジェクトルート直下）に配置する。`claude mcp add --scope project` コマンドが生成するファイルも同じパスであり、Claude Code の公式仕様に準拠する。

`.claude/settings.json` は `permissions`・`hooks` 専用とし、MCP 設定と混在させない（分離の原則）。

`.mcp.json` には PAT 値を書かず環境変数参照のみ記載するため、git 追跡に問題なし。

### PAT の種別とスコープ

GitHub は 2022 年に **Fine-grained PAT** を正式リリースした。クラシック PAT と比較した場合：

| | クラシック PAT `repo` | Fine-grained PAT（採用） |
|--|---------------------|----------------------|
| 対象リポジトリ | アカウント全リポジトリ | 指定した 1 リポジトリのみ |
| 権限粒度 | カテゴリ単位（粗い） | 操作単位（細かい） |
| 最小権限の実現 | 困難（`repo` は過剰） | 可能（Issues+PRs のみ） |
| 有効期限 | 無期限設定可 | 最大 1 年（強制） |

→ **Fine-grained PAT（対象: `study-app-multitenant`）を採用**

必要な権限：
- **Issues**: Read and Write（issue 参照・コメント投稿）
- **Pull Requests**: Read and Write（PR 差分・コメント参照、レビュー投稿）
- **Contents**: Read-only（コード参照が必要な場合）

## 変更点一覧

### 1. `.mcp.json`（プロジェクトルート直下・新規）

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

- `command: "npx"` + `args: ["-y", ...]` により初回起動時に自動インストール
- `env.GITHUB_PERSONAL_ACCESS_TOKEN` は OS 環境変数を参照（PAT 値はファイルに書かない）
- このファイルは git で追跡する（トークン値を含まないため安全）

### 2. `docs/runbooks/mcp-github-setup.md`（新規）

以下を記載する：
- Fine-grained PAT 発行手順（スコープ・対象リポジトリの指定方法）
- 環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` の設定方法（`~/.bashrc` 等への追記）
- Claude Code 再起動手順
- 動作確認方法（`claude mcp list` での確認・issue 取得テスト）
- トラブルシューティング

## 実装手順

### Step 1: `.mcp.json` を作成（プロジェクトルート直下）

上記の JSON を `.mcp.json` として作成する。PAT 値は絶対に記載しない。

### Step 2: `docs/runbooks/mcp-github-setup.md` を新規作成

ユーザーが PAT を発行・設定するための手順書を作成する。

### Step 3: `.gitignore` 確認

`.mcp.json` が git 追跡対象であることを確認する（PAT 値を含まないため追跡可）。

## テスト計画

### 自動テスト

設定ファイル追加・ドキュメント作成のみのため、自動テストは既存 CI の通過確認のみ。

### 手動テスト

1. `.mcp.json` の JSON フォーマット検証
2. Fine-grained PAT を発行し環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` に設定
3. Claude Code 再起動後、MCP ツールが表示されることを確認
4. issue コメント・PR 差分を MCP 経由で取得できることを確認
5. `.mcp.json` に PAT 値がハードコードされていないことを確認

## ロールバック

- `.mcp.json` を削除
- `docs/runbooks/mcp-github-setup.md` を削除
- PAT 環境変数はユーザーが手動で shell profile から削除

コード・DB への影響なし。

## Risk & 回避策

| リスク | 対策 |
|--------|------|
| PAT が git にコミットされる | `.mcp.json` の env 値は `${...}` 参照のみ。PAT 値を直接書かないことをレビューで確認 |
| Fine-grained PAT の権限不足 | エラーメッセージで不足権限を確認し PAT を再発行。Issues+PRs+Contents で対応可能なはず |
| npx パッケージ取得失敗 | 初回起動時に自動ダウンロード。ネットワーク接続が必要（WSL2 環境では通常問題なし） |
| MCP サーバーが起動しない | `claude mcp list` でステータス確認。npx キャッシュ削除（`npx clear-npx-cache`）で再試行 |
| 環境変数未設定で Claude 起動 | MCP ツールが表示されないかエラーになる。runbook の手順を確認して環境変数を設定 |
| Fine-grained PAT の有効期限切れ | 期限切れ前に GitHub から通知が来る。runbook に更新手順を記載 |
