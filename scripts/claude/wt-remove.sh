#!/usr/bin/env bash
set -euo pipefail
# wt-remove: ワークツリーを撤去する（I096・パス指定・データ判定・ロック・入れ子の検査は I179）。
# Usage: [DANGER_OK=1] wt-remove.sh <ワークツリーのパス>
#   - 対象は git worktree list に登録されたワークツリーのパス（公式配置 <primary>/.claude/worktrees/<name> も旧配置も同じ形）
#   - 撤去前チェック: 未コミット変更・未 push コミット（remote に無い HEAD）・中にある別のワークツリー（入れ子）を検出したら中止
#   - ロック: 終了済みの Claude セッションが残したロックだけを外して撤去。使用中のセッション・判定できない・その他の理由のロックは中止
#   - データ判定: 当該 Compose プロジェクトのコンテナ・named volume が無ければ down -v を実行せず撤去（DANGER_OK 不要）
#     あり／判定失敗なら docker compose down -v（破壊的＝Postgres 開発データ削除）に DANGER_OK=1 必須
#     （DANGER_OK はこのスクリプトが環境変数で検査する。pretooluse_guard.py はスクリプト内部のコマンドを見ない）
#   - down -v（§5D volume 回収）→ git worktree remove の順で実行。ブランチは消さない
# 詳細: docs/runbooks/worktree.md §4/§5 ・ docs/plans/open/plan_I179.md 4-6 ・ docs/runbooks/danger-ops.md

usage() { echo "Usage: [DANGER_OK=1] $0 <ワークツリーのパス>" >&2; exit 2; }
if [ $# -ne 1 ] || [ -z "$1" ]; then usage; fi
WT_ARG="$1"

[ -d "$WT_ARG" ] || { echo "[wt-remove] ワークツリーのパスが存在しません: $WT_ARG" >&2; exit 2; }
WT_REAL="$(cd "$WT_ARG" && pwd -P)"

# Compose の既定のプロジェクト名＝フォルダ名を小文字化し [a-z0-9_-] 以外を除去・先頭の _- を除去
compose_default_name() { basename "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]//g; s/^[_-]*//'; }

# git worktree list に登録されたワークツリーか（登録外のフォルダは扱わない）
LIST="$(git worktree list --porcelain)" || { echo "[wt-remove] git worktree list に失敗しました。リポジトリ内で実行してください" >&2; exit 2; }
WT_PATHS="$(printf '%s\n' "$LIST" | sed -n 's/^worktree //p')"
PRIMARY="$(printf '%s\n' "$WT_PATHS" | head -1)"
[ -n "$PRIMARY" ] || { echo "[wt-remove] primary checkout を特定できません" >&2; exit 2; }
WT_PATH=""
while IFS= read -r wt; do
  [ -d "$wt" ] || continue
  if [ "$(cd "$wt" && pwd -P)" = "$WT_REAL" ]; then WT_PATH="$wt"; break; fi
done <<EOF
$WT_PATHS
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

# 撤去前チェック（3）中にある別のワークツリー（入れ子）。.claude/worktrees/ は gitignore 済みのため（1）の status に出ず、
# git worktree remove も --force なしで中身ごと消してしまう → 登録済みの入れ子と、中にある .git（未登録・prunable を含む）で止める
NESTED=""
while IFS= read -r wt; do
  case "$wt/" in "$WT_PATH"/?*) NESTED="$NESTED $wt"; continue ;; esac
  if [ -d "$wt" ]; then
    case "$(cd "$wt" && pwd -P)/" in "$WT_REAL"/?*) NESTED="$NESTED $wt" ;; esac
  fi
done <<EOF
$WT_PATHS
EOF
if [ -z "$NESTED" ]; then
  NESTED="$(find "$WT_PATH" -mindepth 2 -name .git -print -quit 2>/dev/null || true)"
fi
if [ -n "$NESTED" ]; then
  echo "[wt-remove] 撤去対象の中に別のワークツリー（または git リポジトリ）があります。中のものを先に撤去してください（作業消失防止）: $NESTED" >&2
  exit 2
fi

# 撤去前チェック（4）ワークツリーのロック（公式 claude --worktree はセッション中 "claude session <name> (pid N ...)" でロックし、
# `claude -p` 等ではセッション終了後もロックが残る）。破壊的操作の前に判定し、外してよいのは終了済みと確かめられたロックだけ。
LOCK_LINE="$(printf '%s\n' "$LIST" | P="$WT_PATH" awk '$0 == "worktree " ENVIRON["P"] {f=1; next} /^worktree /{f=0} f && /^locked/ {print; exit}')"
STALE_LOCK=0
if [ -n "$LOCK_LINE" ]; then
  LOCK_REASON="${LOCK_LINE#locked}"; LOCK_REASON="${LOCK_REASON# }"
  LOCK_PID="$(printf '%s' "$LOCK_REASON" | sed -n 's/^claude session .* (pid \([0-9]\{1,\}\)[ )].*/\1/p')"
  if [ -z "$LOCK_PID" ]; then
    echo "[wt-remove] ワークツリーがロックされています（理由: ${LOCK_REASON:-なし}）。使っている人・セッションに確認のうえ 'git worktree unlock $WT_PATH' してから再実行してください" >&2
    exit 2
  fi
  # 生存を確認できない（ps が無い）なら安全側に倒して止める
  command -v ps >/dev/null 2>&1 || {
    echo "[wt-remove] ps が無いため、ロックしたセッション（pid $LOCK_PID）が終了済みか確認できません。終了を確認のうえ 'git worktree unlock $WT_PATH' してから再実行してください" >&2
    exit 2; }
  if [ -e "/proc/$LOCK_PID" ] || ps -p "$LOCK_PID" >/dev/null 2>&1; then
    echo "[wt-remove] このワークツリーを使用中の Claude セッション（pid $LOCK_PID）があります。終了してから再実行してください（pid が別のプロセスに再利用されている場合は、終了済みを確認のうえ 'git worktree unlock $WT_PATH'）" >&2
    exit 2
  fi
  STALE_LOCK=1
fi

# COMPOSE_PROJECT_NAME 検出（§5C）
[ -n "${COMPOSE_PROJECT_NAME:-}" ] && \
  echo "[wt-remove] ⚠️ COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME が設定されています（§5C・分離が壊れている恐れ）" >&2

PROJECT="$(compose_default_name "$WT_REAL")"
# 同じプロジェクト名になる別のワークツリー（例: 親の違う同名の入れ子・primary と同名）があれば、データの持ち主を区別できない
SAME_NAME=""
while IFS= read -r wt; do
  [ "$wt" = "$WT_PATH" ] && continue
  if [ "$(compose_default_name "$wt")" = "$PROJECT" ]; then SAME_NAME="$SAME_NAME $wt"; fi
done <<EOF
$WT_PATHS
EOF

detect_data() {   # 0=データ無し / 1=データあり / 2=名前を確定できない / 3=docker が使えない
  local f c v
  [ -n "$PROJECT" ] || return 2
  [ -n "${COMPOSE_PROJECT_NAME:-}" ] && return 2
  # 直下 .env でプロジェクト名・compose ファイルを変えている（export・空白付きの書き方も含む）
  grep -Eq '^[[:space:]]*(export[[:space:]]+)?COMPOSE_(PROJECT_NAME|FILE)[[:space:]]*=' "$WT_PATH/.env" 2>/dev/null && return 2
  # compose ファイル（Compose が読む既定の名前すべて）で最上位の name: を指定している
  for f in compose.yaml compose.yml docker-compose.yaml docker-compose.yml \
           compose.override.yaml compose.override.yml docker-compose.override.yaml docker-compose.override.yml; do
    grep -Eq '^name[[:space:]]*:' "$WT_PATH/$f" 2>/dev/null && return 2
  done
  command -v docker >/dev/null 2>&1 || return 3
  c="$(docker ps -a -q --filter "label=com.docker.compose.project=$PROJECT")" || return 3
  v="$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT")" || return 3
  [ -z "$c$v" ] && return 0
  return 1
}
DATA=0; detect_data || DATA=$?

if [ "$DATA" -ne 0 ] && [ -n "$SAME_NAME" ]; then
  echo "[wt-remove] Compose プロジェクト名 '$PROJECT' が別のワークツリーと同じです: $SAME_NAME" >&2
  echo "[wt-remove] データがどちらのものか区別できないため、DANGER_OK=1 でも down -v は実行しません。データの持ち主を確認して手動で片付けてください（worktree.md §4）" >&2
  exit 2
fi

if [ "$DATA" -eq 0 ]; then
  echo "[wt-remove] Compose プロジェクト '$PROJECT' のコンテナ・volume はありません。docker compose down -v は実行しません"
elif [ "$DATA" -eq 3 ] && [ "${DANGER_OK:-}" = "1" ]; then
  # docker が使えないので down -v はできない。データが残っていても消さずに撤去する（取り残しは §4 の手順で後から片付ける）
  echo "[wt-remove] ⚠️ docker が使えないため down -v を実行せずに撤去します。Compose プロジェクト '$PROJECT' のデータが残っていた場合は、docker が使えるときに worktree.md §4「取り残しの発見と削除」で片付けてください" >&2
elif [ "${DANGER_OK:-}" = "1" ]; then
  # 当該ディレクトリで named volume を回収（§5D）。down 失敗時は remove へ進まず対処を案内
  ( cd "$WT_PATH" && docker compose down -v ) || {
    echo "[wt-remove] docker compose down -v が失敗しました。docker 稼働・compose ファイルを確認し、対処してから再実行してください: $WT_PATH" >&2
    exit 2; }
else
  case "$DATA" in
    1) echo "[wt-remove] Compose プロジェクト '$PROJECT' のコンテナまたは volume が残っています。" >&2 ;;
    2) echo "[wt-remove] Compose のプロジェクト名を確定できません（COMPOSE_PROJECT_NAME・.env の COMPOSE_PROJECT_NAME/COMPOSE_FILE・compose の name: 指定のいずれか）。データの有無を判定できません。" >&2 ;;
    3) echo "[wt-remove] docker が使えない（コマンドが無い・デーモン停止など）ため、データの有無を判定できません。DANGER_OK=1 で再実行すると down -v を実行せずに撤去します（データは残る）。" >&2 ;;
  esac
  echo "[wt-remove] docker compose down -v は破壊的操作です（Postgres 開発データ削除を含む）。" >&2
  echo "[wt-remove] 必要なら 'scripts/db_backup.sh' で事前バックアップのうえ 'DANGER_OK=1 $0 $WT_ARG' で再実行してください。" >&2
  exit 2
fi

# 終了済みセッションのロックを外す（撤去前チェック（4）で使用中でないことを確認済み）
if [ "$STALE_LOCK" -eq 1 ]; then
  git worktree unlock "$WT_PATH"
  echo "[wt-remove] 終了済みの Claude セッション（pid $LOCK_PID）が残したロックを解除しました"
fi
# remove（--force は使わない。未コミット変更・入れ子は撤去前チェックで止めている）
git worktree remove "$WT_PATH"
echo "[wt-remove] 撤去完了: $WT_PATH"
if [ -n "$BRANCH" ]; then
  echo "[wt-remove] ブランチ $BRANCH は残っています（不要なら git branch -d $BRANCH）"
fi
