# I024 レビュー文書

## 対象計画書
`docs/plans/open/plan_I024_Docker_webpack_キャッシュ失効対処.md`

## レビュー観点

### 1. 受け入れ条件との照合

| 受け入れ条件 | 実装による充足 | 確認方法 |
|-------------|--------------|---------|
| コンテナ起動時に自動でキャッシュがクリアされる | `docker-entrypoint.sh` で `rm -rf /app/node_modules/.cache` を実行 | MT-01 |
| 手動操作が不要になること | entrypoint が自動実行 | MT-01, MT-02 |
| `common-commands.md` に暫定回避手順が記載 | 手順を追記 | MT-04 |

### 2. コードレビューチェックリスト

- [ ] `docker-entrypoint.sh` に `set -e` があり、エラー時に即座に停止するか
- [ ] `exec npm start` を使っており、シグナル伝播が正しいか（`npm start` の前に `exec` があるか）
- [ ] `Dockerfile.dev` でスクリプトのコピーと実行権限付与が正しい順序か
- [ ] `docker-compose.yml` の `WATCHPACK_POLLING=true` が frontend サービスの `environment` に追記されているか
- [ ] `common-commands.md` の記載が正確か（コマンドに typo がないか）

### 3. `.gitattributes` 確認

- [ ] `*.sh text eol=lf` が設定されているか（Windows 環境での CRLF 問題を防ぐ）

### 4. セキュリティレビュー

- アプリケーションコードの変更なし
- 新規依存ライブラリなし
- **セキュリティ影響なし**

### 5. レビュー結果

| 観点 | 結果 | コメント |
|------|------|---------|
| 計画書との一致 | — | — |
| セキュリティ | — | — |
| ベストプラクティス | — | — |
| テスト充足度 | — | — |

**総合判定**: （未実施）
