# I005 計画書: 開発DB同期スクリプト整備とREADMEセットアップ手順記載

## 基本情報
- **計画書ID**: plan_I005_DB同期スクリプト整備
- **関連イシュー**: #005 (GitHub #15)
- **作成根拠資料**: docs/issues/open/005.md
- **実装後評価**: （未作成）
- **作成日**: 2026-03-20

---

## 1. 背景/目的
- 複数PC間で同じ開発DBデータを扱えるようにする
- `git clone` → 数コマンドで即起動・ログインできる状態を目指す
- pg_dump + クラウドストレージ（Google Drive等）手動共有方式を採用

## 2. 受け入れ条件
- [ ] `scripts/db_backup.sh` を実行すると `backup_YYYYMMDD.sql` が生成される
- [ ] `scripts/db_restore.sh [ファイルパス]` を実行するとDBがリストアされる
- [ ] `README.md` のセットアップ手順通りに実行すると起動・ログインできる
- [ ] スクリプトはDockerが起動していれば追加インストール不要で動作する

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし（スクリプトのみ）
- Config/Infra: `scripts/` にシェルスクリプト追加、`README.md` 全面更新

## 4. 変更点一覧

| 対象 | 種別 | 内容 |
|------|------|------|
| `scripts/db_backup.sh` | 新規追加 | pg_dumpでDBをバックアップ |
| `scripts/db_restore.sh` | 新規追加 | SQLファイルからDBをリストア |
| `README.md` | 更新 | 実態に合ったセットアップ手順に全面書き直し |

## 5. 実装手順

### ステップ1: `scripts/db_backup.sh` 作成

```bash
#!/bin/bash
# 開発DB バックアップスクリプト
# 使い方: ./scripts/db_backup.sh
set -e

DATE=$(date +%Y%m%d_%H%M%S)
OUTPUT="backup_${DATE}.sql"

echo "DBバックアップを開始します: $OUTPUT"
docker compose exec -T db pg_dump -U postgres learning_app > "$OUTPUT"
echo "✅ バックアップ完了: $OUTPUT"
echo "このファイルをGoogle Drive等に保存して共有してください。"
```

### ステップ2: `scripts/db_restore.sh` 作成

```bash
#!/bin/bash
# 開発DB リストアスクリプト
# 使い方: ./scripts/db_restore.sh backup_YYYYMMDD.sql
set -e

SQL_FILE="${1}"

if [ -z "$SQL_FILE" ]; then
  echo "使い方: ./scripts/db_restore.sh [SQLファイルパス]"
  exit 1
fi

if [ ! -f "$SQL_FILE" ]; then
  echo "エラー: ファイルが見つかりません: $SQL_FILE"
  exit 1
fi

echo "DBリストアを開始します: $SQL_FILE"
docker compose exec -T db psql -U postgres learning_app < "$SQL_FILE"
echo "✅ リストア完了"
```

### ステップ3: 実行権限を付与

```bash
chmod +x scripts/db_backup.sh scripts/db_restore.sh
```

### ステップ4: `README.md` を全面書き直し

現状のREADMEは移管前の旧状態のまま（`cp .env.example .env` が間違っている等）。
実態に合わせた内容に書き直す。

**記載する主な内容:**
1. 前提条件（Docker Desktop）
2. 初回セットアップ手順（clone → .env作成 → Docker起動 → DBリストア）
3. DBバックアップ・リストア手順
4. 日常の開発コマンド
5. バイブコーディング運用フロー（Claude Code）

## 6. テスト計画
### 自動
- `scripts/db_backup.sh` 実行 → `backup_*.sql` ファイルが生成されること
- `scripts/db_restore.sh` 実行 → DBのテーブルが存在すること

### 手動
- READMEの手順通りに実行して起動・ログインできること

## 7. ロールバック
- `scripts/` 追加は新規ファイルのため削除するだけ
- `README.md` は git で元に戻せる

## 8. Risk & 回避策
| リスク | 回避策 |
|--------|--------|
| スクリプトがWSL/Mac/Linux環境で動かない | bash標準コマンドのみ使用、docker composeコマンドで統一 |
| バックアップSQLが誤ってcommitされる | `.gitignore` に `backup_*.sql` を追加 |

## 9. 承認ポイント
- [ ] スクリプト内容（コマンド・引数）
- [ ] README構成・記載内容
- [ ] Danger Ops（無）

## ユーザー承認
- **承認日時**: 2026-03-20
- **承認者**: ユーザー
- **承認内容**: OK
