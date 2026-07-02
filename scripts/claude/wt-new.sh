#!/usr/bin/env bash
set -euo pipefail
# wt-new: worktree を作成し foot-gun を機械化する（I096・ポート分離 I097）。
# Usage: [COMPOSE_PROJECT_NAME=...] wt-new.sh <track> <番号(数字)> <概要> [--env-source <path>] [--up] [--port-offset N]
#   - 基点を origin/develop に固定（§3 重大＝main 基点の空ツリーを回避）
#   - backend/.env を primary（または --env-source）からコピーし存在検証（§5B＝静かな insecure 起動を回避）
#   - up は既定 OFF・--up で opt-in（同ホストで複数スタックを同時 up する場合はポート分離が要る＝下記 --port-offset）
#   - ポート分離（I097）: 直下 .env に DB/REDIS/BACKEND/FRONTEND_PORT を生成。--port-offset 未指定時は既存 worktree を走査し空きオフセット(+10)を自動割当・衝突時は fail
#   - COMPOSE_PROJECT_NAME が設定されていれば警告（§5C）
# 詳細: docs/runbooks/worktree.md §3/§5/§6 ・ docs/plans/closed/plan_I096.md ・ docs/plans/open/plan_I097.md

usage() { echo "Usage: $0 <track> <番号(数字)> <概要> [--env-source <path>] [--up] [--port-offset N]" >&2; exit 2; }

# ポート base（container 側と一致）とオフセット刻み（I097）
PORT_STEP=10
BASE_DB=5432; BASE_REDIS=6379; BASE_BACKEND=8000; BASE_FRONTEND=3000

TRACK="${1:-}"; NUM="${2:-}"; DESC="${3:-}"
{ [ -n "$TRACK" ] && [ -n "$NUM" ] && [ -n "$DESC" ]; } || usage
shift 3
ENV_SOURCE=""; DO_UP=0; PORT_OFFSET_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --env-source)
      [ -n "${2:-}" ] || { echo "[wt-new] --env-source に値がありません" >&2; exit 2; }
      ENV_SOURCE="$2"; shift 2 ;;
    --port-offset)
      [ -n "${2:-}" ] || { echo "[wt-new] --port-offset に値がありません" >&2; exit 2; }
      printf '%s' "$2" | grep -Eq '^[0-9]+$' || { echo "[wt-new] --port-offset は数字のみ: '$2'" >&2; exit 2; }
      PORT_OFFSET_ARG="$2"; shift 2 ;;
    --up)         DO_UP=1; shift ;;
    *) echo "[wt-new] 不明な引数: $1" >&2; usage ;;
  esac
done

# 引数検証（決定論・無言変換なし）
printf '%s' "$NUM"   | grep -Eq '^[0-9]+$'          || { echo "[wt-new] 番号は数字のみ: '$NUM'" >&2; exit 2; }
printf '%s' "$TRACK" | grep -Eq '^[A-Za-z0-9._-]+$' || { echo "[wt-new] track に不正文字: '$TRACK'" >&2; exit 2; }
printf '%s' "$DESC"  | grep -Eq '^[A-Za-z0-9._-]+$' || { echo "[wt-new] 概要に不正文字（空白不可）: '$DESC'" >&2; exit 2; }

# primary/base 導出（/mnt/c/app を直書きしない・primary は worktree list 先頭）
PRIMARY="$(git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)"
[ -n "$PRIMARY" ] || { echo "[wt-new] primary checkout を特定できません" >&2; exit 2; }
BASE="$(dirname "$PRIMARY")"
WT_PATH="$BASE/wt-$TRACK"
BRANCH="feature/I${NUM}-${DESC}"

# 衝突事前検査（fail-fast・git の生失敗に委ねない）
[ -e "$WT_PATH" ] && { echo "[wt-new] worktree path が既に存在: $WT_PATH" >&2; exit 2; }
git show-ref --verify --quiet "refs/heads/$BRANCH" && { echo "[wt-new] branch が既に存在: $BRANCH" >&2; exit 2; }

# .env source 決定（既定=primary/backend/.env）・存在検証（欠落なら add 前に停止＝orphan worktree を作らない）
ENV_SRC="${ENV_SOURCE:-$PRIMARY/backend/.env}"
[ -f "$ENV_SRC" ] || { echo "[wt-new] .env source が存在しません: $ENV_SRC" >&2; exit 2; }

# COMPOSE_PROJECT_NAME 検出（§5C）
[ -n "${COMPOSE_PROJECT_NAME:-}" ] && \
  echo "[wt-new] ⚠️ COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME が設定されています。worktree 分離が壊れる恐れ（§5C）" >&2

# --- ポートオフセット決定と衝突検査（I097・git worktree add の前＝fail-fast）---
# 既存 worktree の使用ポートを収集（.env が在れば各 *_PORT・無ければ既定ポート＝offset 0 相当）
existing_ports() {
  local wt
  git worktree list --porcelain | sed -n 's/^worktree //p' | while IFS= read -r wt; do
    if [ -f "$wt/.env" ]; then
      sed -n 's/^\(DB_PORT\|REDIS_PORT\|BACKEND_PORT\|FRONTEND_PORT\)=\([0-9]\{1,\}\).*/\2/p' "$wt/.env"
    else
      printf '%s\n%s\n%s\n%s\n' "$BASE_DB" "$BASE_REDIS" "$BASE_BACKEND" "$BASE_FRONTEND"
    fi
  done
}
# 既存 worktree の使用オフセット（BACKEND_PORT から算出・.env 無しは 0）
existing_offsets() {
  local wt bp
  git worktree list --porcelain | sed -n 's/^worktree //p' | while IFS= read -r wt; do
    bp=""
    [ -f "$wt/.env" ] && bp="$(sed -n 's/^BACKEND_PORT=\([0-9]\{1,\}\).*/\1/p' "$wt/.env" | head -1)"
    if [ -n "$bp" ]; then echo $((bp - BASE_BACKEND)); else echo 0; fi
  done
}

if [ -n "$PORT_OFFSET_ARG" ]; then
  OFFSET="$PORT_OFFSET_ARG"
else
  MAXOFF=0
  while IFS= read -r o; do
    [ -n "$o" ] || continue
    if [ "$o" -gt "$MAXOFF" ]; then MAXOFF="$o"; fi
  done <<EOF
$(existing_offsets)
EOF
  OFFSET=$((MAXOFF + PORT_STEP))
fi

# 確定ポート集合
NEW_DB=$((BASE_DB + OFFSET)); NEW_REDIS=$((BASE_REDIS + OFFSET))
NEW_BACKEND=$((BASE_BACKEND + OFFSET)); NEW_FRONTEND=$((BASE_FRONTEND + OFFSET))

# 衝突検査（決定論ゲート）: 確定ポートが既存 worktree のいずれのポートとも重複しないこと
EXISTING="$(existing_ports)"
for np in "$NEW_DB" "$NEW_REDIS" "$NEW_BACKEND" "$NEW_FRONTEND"; do
  while IFS= read -r ep; do
    [ -n "$ep" ] || continue
    if [ "$np" = "$ep" ]; then
      echo "[wt-new] ポートが既存 worktree と衝突: $np（offset=$OFFSET）。--port-offset で別の値を指定してください" >&2
      exit 2
    fi
  done <<EOF
$EXISTING
EOF
done

# 作成（基点を origin/develop に固定＝§3 重大の回避）
git fetch origin
git worktree add "$WT_PATH" -b "$BRANCH" origin/develop

# backend .env コピー（中身は読まない・cp と test -f のみ＝§5B の回避）
cp "$ENV_SRC" "$WT_PATH/backend/.env"
[ -f "$WT_PATH/backend/.env" ] || { echo "[wt-new] .env コピー失敗: $WT_PATH/backend/.env" >&2; exit 2; }

# e2e/.env.e2e は source と同じ worktree に在れば同様コピー（非致命）
SRC_ROOT="$(dirname "$(dirname "$ENV_SRC")")"   # .../backend/.env → .../（source worktree root）
if [ -f "$SRC_ROOT/e2e/.env.e2e" ]; then
  cp "$SRC_ROOT/e2e/.env.e2e" "$WT_PATH/e2e/.env.e2e" || echo "[wt-new] e2e/.env.e2e コピーをスキップ（非致命）" >&2
fi

# 直下 .env にポートを生成（I097・docker compose が変数展開で読込。COMPOSE_PROJECT_NAME は書かない＝既定=ディレクトリ名で分離）
cat > "$WT_PATH/.env" <<EOF
DB_PORT=$NEW_DB
REDIS_PORT=$NEW_REDIS
BACKEND_PORT=$NEW_BACKEND
FRONTEND_PORT=$NEW_FRONTEND
EOF
echo "[wt-new] ポート割当: offset=$OFFSET db=$NEW_DB redis=$NEW_REDIS backend=$NEW_BACKEND frontend=$NEW_FRONTEND"

# 任意 up（既定 OFF・§6 ポート衝突のため opt-in）
if [ "$DO_UP" -eq 1 ]; then
  ( cd "$WT_PATH" && docker compose up -d )
fi
echo "[wt-new] 作成完了: $WT_PATH (branch=$BRANCH, base=origin/develop)"
