#!/usr/bin/env bash
set -euo pipefail
# wt-ports: 今いるワークツリーの直下 .env に Docker 用のポートを割り当てる（I179・規則は I097 のまま）。
# Usage: [COMPOSE_PROJECT_NAME=...] wt-ports.sh [--port-offset N]
#   - Docker を起動する前に、対象のワークツリーで 1 回だけ実行する（2 回目以降は何も変えない）
#   - --port-offset 未指定時は他のワークツリー（入れ子配置を含む）を走査し、空きオフセット(+10)を自動割当・衝突時は fail
#   - primary（git worktree list の先頭）は既定ポート（offset 0）で使うため拒否する
#   - backend/.env が無ければ止める（.worktreeinclude は元ファイルが無いと黙って飛ばす＝§5B の静かな insecure 起動を回避）
#   - COMPOSE_PROJECT_NAME は書かない。設定されていれば警告（§5C）
# 終了コード: 0=割当成功/割当済み・2=明示エラー停止
# 詳細: docs/runbooks/worktree.md §5/§6 ・ docs/plans/open/plan_I179.md 4-4

usage() { echo "Usage: $0 [--port-offset N]" >&2; exit 2; }

# ポート base（container 側と一致）とオフセット刻み（I097）
PORT_STEP=10
BASE_DB=5432; BASE_REDIS=6379; BASE_BACKEND=8000; BASE_FRONTEND=3000

PORT_OFFSET_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --port-offset)
      [ -n "${2:-}" ] || { echo "[wt-ports] --port-offset に値がありません" >&2; exit 2; }
      printf '%s' "$2" | grep -Eq '^[0-9]+$' || { echo "[wt-ports] --port-offset は数字のみ: '$2'" >&2; exit 2; }
      PORT_OFFSET_ARG="$2"; shift 2 ;;
    *) echo "[wt-ports] 不明な引数: $1" >&2; usage ;;
  esac
done

WT="$(git rev-parse --show-toplevel)" || { echo "[wt-ports] git のワークツリー内で実行してください" >&2; exit 2; }
WT_REAL="$(cd "$WT" && pwd -P)"
PRIMARY="$(git worktree list --porcelain | awk 'sub(/^worktree /, "") {print; exit}')"
[ -n "$PRIMARY" ] || { echo "[wt-ports] primary checkout を特定できません" >&2; exit 2; }
if [ "$WT_REAL" = "$(cd "$PRIMARY" && pwd -P)" ]; then
  echo "[wt-ports] primary は既定ポート（offset 0）で使います。割当は不要です" >&2
  exit 2
fi
[ -f "$WT/backend/.env" ] || {
  echo "[wt-ports] backend/.env がありません。primary からコピーしてから再実行してください: $WT/backend/.env" >&2
  exit 2
}

# 割当済みなら何も変えない（冪等）
# 他のワークツリーの値を読む port_val と同じく、export・= の前の空白付きの書き方も割当済みとみなす
PORT_LINE_RE='^[[:space:]]*(export[[:space:]]+)?(DB|REDIS|BACKEND|FRONTEND)_PORT[[:space:]]*='
if [ -f "$WT/.env" ] && grep -Eq "$PORT_LINE_RE" "$WT/.env"; then
  echo "[wt-ports] 割当済みのため変更しません:"
  grep -E "$PORT_LINE_RE" "$WT/.env"
  exit 0
fi

# COMPOSE_PROJECT_NAME 検出（§5C）
[ -n "${COMPOSE_PROJECT_NAME:-}" ] && \
  echo "[wt-ports] ⚠️ COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME が設定されています。worktree 分離が壊れる恐れ（§5C）" >&2

# .env の <変数> のポート値（export・= の前後の空白・クォート付きも読む）。無ければ空
port_val() {
  awk -v k="$2" '{
    line = $0; sub(/^[ \t]*(export[ \t]+)?/, "", line)
    if (index(line, k) != 1) next
    rest = substr(line, length(k) + 1); if (sub(/^[ \t]*=[ \t]*/, "", rest) == 0) next   # 変数名の続き（DB_PORT2 等）は別の変数
    gsub(/["\047]/, "", rest)
    if (match(rest, /^[0-9]+/)) { print substr(rest, 1, RLENGTH); exit }
  }' "$1"
}

# 自分以外のワークツリー（git worktree list・入れ子配置を含む）
other_worktrees() {
  local wt
  git worktree list --porcelain | sed -n 's/^worktree //p' | while IFS= read -r wt; do
    if [ -d "$wt" ] && [ "$(cd "$wt" && pwd -P)" = "$WT_REAL" ]; then continue; fi
    printf '%s\n' "$wt"
  done
}
# 他のワークツリーの使用ポート（各 *_PORT が .env に在ればその値・無ければ既定ポート。.env にポート以外の行しか無い場合も既定ポート扱い）
existing_ports() {
  local wt var base v
  other_worktrees | while IFS= read -r wt; do
    for var in DB_PORT:"$BASE_DB" REDIS_PORT:"$BASE_REDIS" BACKEND_PORT:"$BASE_BACKEND" FRONTEND_PORT:"$BASE_FRONTEND"; do
      base="${var#*:}"; var="${var%%:*}"
      v=""
      [ -f "$wt/.env" ] && v="$(port_val "$wt/.env" "$var")"
      printf '%s\n' "${v:-$base}"
    done
  done
}
# 他のワークツリーの使用オフセット（BACKEND_PORT から算出・.env 無しは 0）
existing_offsets() {
  local wt bp
  other_worktrees | while IFS= read -r wt; do
    bp=""
    [ -f "$wt/.env" ] && bp="$(port_val "$wt/.env" BACKEND_PORT)"
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

# 衝突検査（決定論ゲート）: 確定ポートが他のワークツリーのいずれのポートとも重複しないこと
EXISTING="$(existing_ports)"
for np in "$NEW_DB" "$NEW_REDIS" "$NEW_BACKEND" "$NEW_FRONTEND"; do
  while IFS= read -r ep; do
    [ -n "$ep" ] || continue
    if [ "$np" = "$ep" ]; then
      echo "[wt-ports] ポートが既存 worktree と衝突: $np（offset=$OFFSET）。--port-offset で別の値を指定してください" >&2
      exit 2
    fi
  done <<EOF
$EXISTING
EOF
done

# 直下 .env へ追記（ポート以外の既存行は残す。docker compose が変数展開で読込）
if [ -s "$WT/.env" ] && [ -n "$(tail -c1 "$WT/.env")" ]; then printf '\n' >> "$WT/.env"; fi   # 末尾改行なしの既存行と連結させない
printf 'DB_PORT=%s\nREDIS_PORT=%s\nBACKEND_PORT=%s\nFRONTEND_PORT=%s\n' \
  "$NEW_DB" "$NEW_REDIS" "$NEW_BACKEND" "$NEW_FRONTEND" >> "$WT/.env"
echo "[wt-ports] ポート割当: offset=$OFFSET db=$NEW_DB redis=$NEW_REDIS backend=$NEW_BACKEND frontend=$NEW_FRONTEND（$WT/.env）"
