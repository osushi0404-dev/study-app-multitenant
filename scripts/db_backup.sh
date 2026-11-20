#!/bin/bash
# 開発DB バックアップスクリプト（人が使う）。控えを取る処理と確かめは scripts/claude/db-backup.sh にある（I597）
# 使い方: bash scripts/db_backup.sh [名前]
# Claude はこれを使わない（サンドボックスの中で止まる）。docs/runbooks/danger-ops.md「破壊的な DB の操作の前の控え」
set -e
cd "$(git rev-parse --show-toplevel)"

echo "DBバックアップを開始します..."
bash scripts/claude/db-backup.sh "$@"
echo "このファイルをGoogle Drive等に保存して他のPCと共有してください。"
