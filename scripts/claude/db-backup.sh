#!/usr/bin/env bash
# db-backup: 開発の DB の控えを取る入口（I597）。破壊的な DB の操作の前に、Claude が単体で流す
#   （手順: docs/runbooks/danger-ops.md「破壊的な DB の操作の前の控え」）。人は scripts/db_backup.sh（この入口を呼ぶ包み）を使ってもよい。
# 使い方: bash scripts/claude/db-backup.sh [名前]   名前は英数字・_・- の 1〜64 文字（例: I590_before）
# 出力: 今いるワークツリーの直下の backup_<名前>_<日時>.sql（名前なしは backup_<日時>.sql。.gitignore の backup_*.sql で git から外れる）
# 終了コード: 0 控えを取った／1 取れない（pg_dump の失敗・確かめの不合格・同じ名前のファイルがある）／2 使い方の誤り
# サンドボックスの外で動く（.claude/settings.json の sandbox.excludedCommands の `bash scripts/claude/*`）。外でする中身は、
#   docker compose exec -T db pg_dump の読み取りと、作業フォルダの直下の backup_*.sql の書き込み・一時のファイルの削除だけ。
#   命令や書き込み先を外から差し替える口（環境変数など）は作らない（plan_I597.md 9）
set -uo pipefail
umask 077   # DB の中身の写しを本人だけが読める権限で作る（/mnt/c の drvfs では効かない・plan_I597.md R6）

DB_USER=postgres       # docker-compose.yml の POSTGRES_USER
DB_NAME=learning_app   # docker-compose.yml の POSTGRES_DB
COMPLETE_LINE='-- PostgreSQL database dump complete'
HINT='Claude からは bash scripts/claude/db-backup.sh <名前> を、前置き・振り向け・つなぎなしで単体で流す（サンドボックスの中では .env が読めず止まる）。DB のコンテナが止まっていれば先に docker compose up -d --wait db。手順: docs/runbooks/danger-ops.md「破壊的な DB の操作の前の控え」'

usage() { echo "使い方: bash scripts/claude/db-backup.sh [名前]（名前は英数字・_・- の 1〜64 文字）" >&2; exit 2; }
fail() { echo "⛔ 控えを取れませんでした: $1" >&2; echo "   $HINT" >&2; exit 1; }

# 引数の確かめ（docker を呼ぶ前）。省略（$# が 0）と空文字（$# が 1 で中身が空）を分ける
case $# in
  0) NAME="" ;;
  1) [[ $1 =~ ^[A-Za-z0-9_-]{1,64}$ ]] || usage; NAME=$1 ;;
  *) usage ;;
esac

ROOT=$(git rev-parse --show-toplevel) || fail "git のリポジトリの中で流してください"
cd "$ROOT" || fail "$ROOT に移れません"

DEST="backup_${NAME:+${NAME}_}$(date +%Y%m%d_%H%M%S).sql"
[ ! -e "$DEST" ] || fail "$DEST が既にあります（上書きしません）"

# 一時のファイルは同じフォルダに置き（backup_*.sql に当たり git から外れる）、どこで止まっても消す
TMP=$(mktemp --suffix=.sql backup_partial_XXXXXX) || fail "一時のファイルを作れません"
trap 'rm -f "$TMP"' EXIT

# 中身はコンテナの中に写しを作らず、標準出力で受ける
docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" > "$TMP" || fail "pg_dump が終了コード $? で終わりました"
[ -s "$TMP" ] || fail "pg_dump の出力が空です"
grep -qxF -- "$COMPLETE_LINE" "$TMP" || fail "完了の行（$COMPLETE_LINE）がありません（途中で切れた）"
# 15.14 以降の pg_dump は先頭近くに \restrict <鍵>、最後に \unrestrict <鍵> を書く。あれば最後の空でない行が対になっているか
# （\restrict は最初の一致で読むのをやめ、最後の行は末尾だけを読む。控えは数十 MB になりうる）
key=$(sed -n '/^\\restrict /{s/^\\restrict //p;q}' "$TMP")
if [ -n "$key" ]; then
  last=$(tail -n 20 "$TMP" | grep -v '^[[:space:]]*$' | tail -n 1)
  [ "$last" = "\\unrestrict $key" ] || fail "最後の行が \\restrict と対の \\unrestrict ではありません（途中で切れた）"
fi

# mv -n は先にファイルがあると黙って移さない。移せなければ一時のファイルが残るので、それで確かめる
mv -n "$TMP" "$DEST"
[ ! -e "$TMP" ] || fail "$DEST に移せません"
echo "✅ 控えを取りました: $DEST（$(wc -c < "$DEST") バイト）"
