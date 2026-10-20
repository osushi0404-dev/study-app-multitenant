#!/usr/bin/env bash
set -euo pipefail
# wt-remove: Docker を使ったワークツリーを撤去する（I096・データ判定と パス指定は I179）。
# Usage: [DANGER_OK=1] wt-remove.sh <ワークツリーのパス>
#   - 対象は git worktree list に登録されたワークツリーのパス（公式配置 <primary>/.claude/worktrees/<name> も旧配置も同じ形）
#   - 撤去前チェック: 未コミット変更・未 push コミット（remote に無い HEAD）を検出したら --force を使わず中止
#   - ロック: 終了済みの Claude セッションが残したロックだけを外して撤去。使用中のセッション・その他の理由のロックは中止
#   - データ判定: 当該 Compose プロジェクトのコンテナ・named volume が無ければ down -v を実行せず撤去（DANGER_OK 不要）
#     あり／判定失敗なら docker compose down -v（破壊的＝Postgres 開発データ削除）に DANGER_OK=1 必須（pretooluse_guard.py と同一契約）
#   - down -v（§5D volume 回収）→ git worktree remove の順で実行。ブランチは消さない
# 詳細: docs/runbooks/worktree.md §4/§5 ・ docs/plans/open/plan_I179.md 4-6 ・ docs/runbooks/danger-ops.md

usage() { echo "Usage: [DANGER_OK=1] $0 <ワークツリーのパス>" >&2; exit 2; }
if [ $# -ne 1 ] || [ -z "$1" ]; then usage; fi
WT_ARG="$1"

[ -d "$WT_ARG" ] || { echo "[wt-remove] ワークツリーのパスが存在しません: $WT_ARG" >&2; exit 2; }
WT_REAL="$(cd "$WT_ARG" && pwd -P)"

# git worktree list に登録されたワークツリーか（登録外のフォルダは扱わない）
LIST="$(git worktree list --porcelain)" || { echo "[wt-remove] git worktree list に失敗しました。リポジトリ内で実行してください" >&2; exit 2; }
PRIMARY="$(printf '%s\n' "$LIST" | sed -n 's/^worktree //p' | head -1)"
[ -n "$PRIMARY" ] || { echo "[wt-remove] primary checkout を特定できません" >&2; exit 2; }
WT_PATH=""
while IFS= read -r wt; do
  [ -d "$wt" ] || continue
  if [ "$(cd "$wt" && pwd -P)" = "$WT_REAL" ]; then WT_PATH="$wt"; break; fi
done <<EOF
$(printf '%s\n' "$LIST" | sed -n 's/^worktree //p')
EOF
[ -n "$WT_PATH" ] || { echo "[wt-remove] git worktree list に登録されたワークツリーではありません: $WT_ARG" >&2; exit 2; }

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
BRANCH="$(git -C "$WT_PATH" branch --show-current)"

# 撤去前チェック（3）ワークツリーのロック（公式 claude --worktree はセッション中 "claude session <name> (pid N ...)" でロックし、
# `claude -p` 等ではセッション終了後もロックが残る）。破壊的操作の前に判定し、外してよいのは終了済みセッションのロックだけ。
LOCK_LINE="$(printf '%s\n' "$LIST" | P="$WT_PATH" awk '$0 == "worktree " ENVIRON["P"] {f=1; next} /^worktree /{f=0} f && /^locked/ {print; exit}')"
STALE_LOCK=0
if [ -n "$LOCK_LINE" ]; then
  LOCK_REASON="${LOCK_LINE#locked}"; LOCK_REASON="${LOCK_REASON# }"
  LOCK_PID="$(printf '%s' "$LOCK_REASON" | sed -n 's/^claude session .* (pid \([0-9]\{1,\}\)[ )].*/\1/p')"
  if [ -z "$LOCK_PID" ]; then
    echo "[wt-remove] ワークツリーがロックされています（理由: ${LOCK_REASON:-なし}）。使っている人・セッションに確認のうえ 'git worktree unlock $WT_PATH' してから再実行してください" >&2
    exit 2
  fi
  if ps -p "$LOCK_PID" >/dev/null 2>&1; then
    echo "[wt-remove] このワークツリーを使用中の Claude セッション（pid $LOCK_PID）があります。終了してから再実行してください（pid が別のプロセスに再利用されている場合は、終了済みを確認のうえ 'git worktree unlock $WT_PATH'）" >&2
    exit 2
  fi
  STALE_LOCK=1
fi

# COMPOSE_PROJECT_NAME 検出（§5C）
[ -n "${COMPOSE_PROJECT_NAME:-}" ] && \
  echo "[wt-remove] ⚠️ COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME が設定されています（§5C・分離が壊れている恐れ）" >&2

# Compose プロジェクト名＝フォルダ名を Compose の既定と同じ規則で変換（小文字化・[a-z0-9_-] 以外を除去・先頭の _- を除去）
PROJECT="$(basename "$WT_REAL" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]//g; s/^[_-]*//')"

detect_data() {   # 0=データ無し / 1=データあり / 2=判定失敗（名前を確定できない・docker が使えない）
  [ -n "$PROJECT" ] || return 2
  [ -n "${COMPOSE_PROJECT_NAME:-}" ] && return 2
  grep -q '^COMPOSE_PROJECT_NAME=' "$WT_PATH/.env" 2>/dev/null && return 2
  grep -q '^name:' "$WT_PATH/docker-compose.yml" 2>/dev/null && return 2
  command -v docker >/dev/null 2>&1 || return 2
  local c v
  c="$(docker ps -a -q --filter "label=com.docker.compose.project=$PROJECT")" || return 2
  v="$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT")" || return 2
  [ -z "$c$v" ] && return 0
  return 1
}
DATA=0; detect_data || DATA=$?

if [ "$DATA" -eq 0 ]; then
  echo "[wt-remove] Compose プロジェクト '$PROJECT' のコンテナ・volume はありません。docker compose down -v は実行しません"
elif [ "${DANGER_OK:-}" = "1" ]; then
  # 当該ディレクトリで named volume を回収（§5D）。down 失敗時は remove へ進まず対処を案内
  ( cd "$WT_PATH" && docker compose down -v ) || {
    echo "[wt-remove] docker compose down -v が失敗しました。docker 稼働・compose ファイルを確認し、手動対応後に 'git worktree remove $WT_PATH' を実行してください。" >&2
    exit 2; }
else
  if [ "$DATA" -eq 1 ]; then
    echo "[wt-remove] Compose プロジェクト '$PROJECT' のコンテナまたは volume が残っています。" >&2
  else
    echo "[wt-remove] Compose のデータの有無を判定できません（COMPOSE_PROJECT_NAME・compose の name: 指定・docker 不在/失敗のいずれか）。" >&2
  fi
  echo "[wt-remove] docker compose down -v は破壊的操作です（Postgres 開発データ削除を含む）。" >&2
  echo "[wt-remove] 必要なら 'scripts/db_backup.sh' で事前バックアップのうえ 'DANGER_OK=1 $0 $WT_ARG' で再実行してください。" >&2
  exit 2
fi

# 終了済みセッションのロックを外す（撤去前チェック（3）で使用中でないことを確認済み）
if [ "$STALE_LOCK" -eq 1 ]; then
  git worktree unlock "$WT_PATH"
  echo "[wt-remove] 終了済みの Claude セッション（pid $LOCK_PID）が残したロックを解除しました"
fi
# remove（--force は使わない＝撤去前チェックで担保。中に別ワークツリーがあれば git が拒否する）
git worktree remove "$WT_PATH"
echo "[wt-remove] 撤去完了: $WT_PATH"
if [ -n "$BRANCH" ]; then
  echo "[wt-remove] ブランチ $BRANCH は残っています（不要なら git branch -d $BRANCH）"
fi
