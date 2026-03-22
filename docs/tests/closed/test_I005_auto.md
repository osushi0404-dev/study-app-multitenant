# I005 自動テスト: 開発DB同期スクリプト整備

実行コマンド:
```bash
# バックアップスクリプト実行
bash scripts/db_backup.sh

# バックアップファイルが生成されたか確認
ls backup_*.sql

# リストアスクリプト実行
bash scripts/db_restore.sh backup_*.sql

# テーブルが存在するか確認
docker compose exec db psql -U postgres learning_app -c "\dt" | grep -c "table"
```

結果:
- backup_*.sql 生成:
- リストア後テーブル数:
