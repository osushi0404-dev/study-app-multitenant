# GitHub MCP セットアップ手順

GitHub MCP サーバーを導入することで、Claude が GitHub API を直接活用できるようになる。
`gh` CLI では煩雑だった PR コメント一括取得・差分解析・issue 操作等がシンプルになる。

---

## 1. Fine-grained PAT の発行

**Classic PAT（`repo` スコープ）は使用しないこと。** 対象リポジトリ・権限を限定できる Fine-grained PAT を使用する。

### 手順

1. GitHub にログインし、右上アバター → **Settings** を開く
2. 左サイドバー最下部 → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
3. **Generate new token** をクリック
4. 以下を設定する：

   | 項目 | 設定値 |
   |------|--------|
   | Token name | `claude-mcp-study-app`（任意の識別名） |
   | Expiration | 90日 or 1年（無期限は非推奨） |
   | Resource owner | 自分のアカウント |
   | Repository access | **Only select repositories** → `study-app-multitenant` を選択 |

5. **Permissions** セクションで以下のみを有効化（それ以外は No access のまま）：

   | Permission | 設定値 |
   |-----------|--------|
   | Issues | Read and write |
   | Pull requests | Read and write |
   | Contents | Read-only |

6. **Generate token** をクリックし、表示されたトークン（`github_pat_xxx...`）をコピーする  
   ⚠️ このページを閉じると二度と表示されない

---

## 2. 環境変数の設定

発行したトークンを環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN` に設定する。

### WSL2 / Linux / macOS（bash）

```bash
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_ここにトークンを貼る' >> ~/.bashrc
source ~/.bashrc
```

### zsh の場合

```bash
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_ここにトークンを貼る' >> ~/.zshrc
source ~/.zshrc
```

### 設定確認

```bash
echo $GITHUB_PERSONAL_ACCESS_TOKEN
# github_pat_xxx... と表示されれば OK
```

---

## 3. Claude Code の再起動

環境変数を読み込ませるため、Claude Code を完全に再起動する。

```bash
# Claude Code を終了してから再度起動
claude
```

---

## 4. 動作確認

### MCP サーバーの接続確認

```bash
claude mcp list
```

`github` が表示され、ステータスが `connected` になっていれば OK。

### issue 参照テスト

Claude に以下のように指示して動作確認する：

```
GitHub issue #71 の内容を確認して
```

`gh` CLI を使わずに MCP 経由で issue の詳細・コメントが返ってくれば成功。

### PR 差分・コメント取得テスト

```
PR #70 の差分とコメントを確認して
```

---

## 5. トラブルシューティング

### MCP が `connected` にならない

**原因候補 1: 環境変数が未設定**

```bash
echo $GITHUB_PERSONAL_ACCESS_TOKEN
```

空の場合は「2. 環境変数の設定」を再実施し、Claude Code を再起動する。

**原因候補 2: `${...}` 形式が展開されない**

Claude Code が `.mcp.json` の `${GITHUB_PERSONAL_ACCESS_TOKEN}` を展開しない場合、`.mcp.json` の `env` セクションを削除し、OS 環境変数の自動継承に切り替える：

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

MCP サーバープロセスは親プロセス（Claude Code）の環境変数を継承するため、`env` セクションなしでも `GITHUB_PERSONAL_ACCESS_TOKEN` が設定されていれば機能する。

**原因候補 3: npx の初回インストール失敗**

```bash
npx clear-npx-cache
# Claude Code を再起動
```

### 認証エラー（401 Unauthorized）

PAT のスコープまたは対象リポジトリの設定が誤っている。「1. Fine-grained PAT の発行」を参照して PAT を再発行する。

### PAT の有効期限切れ

GitHub から期限切れ前にメール通知が届く。新しい PAT を発行し「2. 環境変数の設定」を再実施する。

---

## 6. セキュリティ注意事項

- PAT をコードや設定ファイルに直接書かない
- `.mcp.json` には PAT 値を記載しない（環境変数参照のみ）
- PAT を誤ってコミットした場合は即座に GitHub で失効させ、新しい PAT を発行する
- リポジトリが不要になった場合や退職時は PAT を削除する
