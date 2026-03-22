# I005 手動テスト: 開発DB同期スクリプト整備

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | `bash scripts/db_backup.sh` を実行する | `backup_YYYYMMDD_HHMMSS.sql` が生成される | | |
| 2 | `bash scripts/db_restore.sh backup_*.sql` を実行する | リストア完了メッセージが表示される | | |
| 3 | READMEのセットアップ手順を最初から読む | 手順が分かりやすく、抜けがない | | |
| 4 | READMEの手順通りに `.env` を作成し `docker compose up -d` を実行する | 全コンテナが起動する | | |
| 5 | ブラウザで `http://localhost:3000` にアクセスしてログインする | ログインできる | | |

結論: OK / NG
