# I004 自動テスト: 移管用フォルダの資材をリポジトリに配置

実行コマンド:
```bash
# DBコンテナ先行起動
docker-compose up -d db

# DBリストア
docker-compose exec -T db psql -U postgres learning_app < 移管用/backup_migration.sql

# リストア確認（テーブル一覧）
docker-compose exec db psql -U postgres learning_app -c "\dt"

# 全コンテナ起動
docker-compose up -d

# コンテナ稼働状態確認
docker-compose ps

# バックエンドエラーログ確認
docker-compose logs backend 2>&1 | grep -i "error\|exception\|traceback" || echo "エラーなし"

# フロントエンドエラーログ確認
docker-compose logs frontend 2>&1 | grep -i "error\|failed" || echo "エラーなし"

# DB 接続確認
docker-compose exec backend python manage.py check --database default
```

結果:
- DB リストア（テーブル一覧）:
- docker-compose ps:
- backend エラーログ:
- frontend エラーログ:
- DB 接続確認:

## 完了情報
- **完了日時**: 2026-03-20
- **結果**: OK
