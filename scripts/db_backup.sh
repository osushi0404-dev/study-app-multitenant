#!/bin/bash
# 開発DB バックアップスクリプト
# 使い方: bash scripts/db_backup.sh
set -e

DATE=$(date +%Y%m%d_%H%M%S)
OUTPUT="backup_${DATE}.sql"

echo "DBバックアップを開始します..."
docker compose exec -T db pg_dump -U postgres learning_app > "$OUTPUT"
echo "✅ バックアップ完了: $OUTPUT"
echo "このファイルをGoogle Drive等に保存して他のPCと共有してください。"
