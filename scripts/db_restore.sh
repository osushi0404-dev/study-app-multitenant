#!/bin/bash
# 開発DB リストアスクリプト
# 使い方: bash scripts/db_restore.sh [SQLファイルパス]
set -e

SQL_FILE="${1}"

if [ -z "$SQL_FILE" ]; then
  echo "使い方: bash scripts/db_restore.sh [SQLファイルパス]"
  echo "例: bash scripts/db_restore.sh backup_20260320_120000.sql"
  exit 1
fi

if [ ! -f "$SQL_FILE" ]; then
  echo "エラー: ファイルが見つかりません: $SQL_FILE"
  exit 1
fi

echo "DBリストアを開始します: $SQL_FILE"
docker compose exec -T db psql -U postgres learning_app < "$SQL_FILE"
echo "✅ リストア完了"
