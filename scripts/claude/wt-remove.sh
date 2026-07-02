#!/usr/bin/env bash
set -euo pipefail
# wt-remove: worktree を撤去する（I096）。down -v は DANGER_OK=1 必須。
# Usage: [DANGER_OK=1] wt-remove.sh <track>
#   - 撤去前チェック: 未コミット変更・未 push コミット（remote に無い HEAD）を検出したら --force を使わず中止
#   - docker compose down -v は破壊的（Postgres 開発データ削除）＝DANGER_OK=1 必須（pretooluse_guard.py と同一契約）
#   - down -v（§5D volume 回収）→ git worktree remove の順で実行
# 詳細: docs/runbooks/worktree.md §3/§5 ・ docs/plans/closed/plan_I096.md ・ docs/runbooks/danger-ops.md

TRACK="${1:?Usage: [DANGER_OK=1] $0 <track>}"
printf '%s' "$TRACK" | grep -Eq '^[A-Za-z0-9._-]+$' || { echo "[wt-remove] track に不正文字: '$TRACK'" >&2; exit 2; }

PRIMARY="$(git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)"
[ -n "$PRIMARY" ] || { echo "[wt-remove] primary checkout を特定できません" >&2; exit 2; }
BASE="$(dirname "$PRIMARY")"
WT_PATH="$BASE/wt-$TRACK"

[ -d "$WT_PATH" ] || { echo "[wt-remove] worktree path が存在しません: $WT_PATH" >&2; exit 2; }
WT_REAL="$(cd "$WT_PATH" && pwd -P)"
# primary を誤って撤去しない
[ "$WT_REAL" = "$(cd "$PRIMARY" && pwd -P)" ] && { echo "[wt-remove] primary checkout は撤去できません" >&2; exit 2; }
# CWD が撤去対象 WT 内だと後段の git worktree remove が拒否する → 事前に明示エラーで弾く
case "$(pwd -P)/" in
  "$WT_REAL"/*) echo "[wt-remove] 撤去対象 WT の内側からは実行できません。外（例: primary）に cd して再実行してください: $WT_PATH" >&2; exit 2 ;;
esac

# 撤去前チェック（1）未コミット変更（git 失敗は set -e で abort＝fail-safe。$() を [ ] に埋めると失敗が握り潰されるため一旦代入）
DIRTY="$(git -C "$WT_PATH" status --porcelain)"
[ -n "$DIRTY" ] && \
  { echo "[wt-remove] 未コミット変更あり。撤去中止（作業消失防止）: $WT_PATH" >&2; exit 2; }
# 撤去前チェック（2）未 push コミット（HEAD がどの remote-tracking にも含まれない＝未 push）
if [ -z "$(git -C "$WT_PATH" branch -r --contains HEAD 2>/dev/null)" ]; then
  echo "[wt-remove] HEAD が未 push（remote に無い）。撤去中止（作業消失防止）: $WT_PATH" >&2; exit 2
fi

# COMPOSE_PROJECT_NAME 検出（§5C）
[ -n "${COMPOSE_PROJECT_NAME:-}" ] && \
  echo "[wt-remove] ⚠️ COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME が設定されています（§5C・分離が壊れている恐れ）" >&2

# volume 回収は danger-op（DANGER_OK=1 必須＝pretooluse_guard.py と同一契約）
if [ "${DANGER_OK:-}" = "1" ]; then
  # 当該ディレクトリで named volume を回収（§5D）。down 失敗時は remove へ進まず対処を案内
  ( cd "$WT_PATH" && docker compose down -v ) || {
    echo "[wt-remove] docker compose down -v が失敗しました。docker 稼働・compose ファイルを確認し、手動対応後に 'git worktree remove $WT_PATH' を実行してください。" >&2
    exit 2; }
else
  echo "[wt-remove] docker compose down -v は破壊的操作です（Postgres 開発データ削除を含む）。" >&2
  echo "[wt-remove] 必要なら 'scripts/db_backup.sh' で事前バックアップのうえ 'DANGER_OK=1 $0 $TRACK' で再実行してください。" >&2
  exit 2
fi

# remove（--force は使わない＝撤去前チェックで担保）。cwd は変えていないので内部からの remove ではない
git worktree remove "$WT_PATH"
echo "[wt-remove] 撤去完了: $WT_PATH"
