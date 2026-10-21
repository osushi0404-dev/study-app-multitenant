#!/usr/bin/env bash
set -euo pipefail
# wt-remove: ワークツリーを撤去する（I096・パス指定・データ判定・ロック・入れ子の検査は I179）。
# Usage: [DANGER_OK=1] wt-remove.sh <ワークツリーのパス>
#   - 対象は git worktree list に登録されたワークツリーのパス（公式配置 <primary>/.claude/worktrees/<name> も旧配置も同じ形）
#   - 撤去前チェック: 未コミット変更・未 push コミット（remote に無い HEAD）・中にある別のワークツリー（入れ子）を検出したら中止
#   - ロック: 終了済みの Claude セッションが残したロックだけを外して撤去。使用中のセッション・判定できない・その他の理由のロックは中止
#   - データ判定: 当該 Compose プロジェクト（フォルダ名の既定名）のコンテナ・named volume が無ければ down -v を実行せず撤去（DANGER_OK 不要）
#     あり → docker compose -p <既定名> down -v（破壊的＝Postgres 開発データ削除）に DANGER_OK=1 必須
#     （DANGER_OK はこのスクリプトが環境変数で検査する。pretooluse_guard.py はスクリプト内部のコマンドを見ない）
#     名前を確定できない・コンテナの作業フォルダが別の場所・同名の別ワークツリー → DANGER_OK=1 でも中止（消す相手を確定できない）
#     docker が使えない → 中止。KEEP_DATA=1 なら down -v をせずに撤去（データは消さずに残す。DANGER_OK とは別の合図）
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
PRIMARY="${WT_PATHS%%$'\n'*}"   # 先頭行（パイプの SIGPIPE で pipefail が誤爆しないよう展開で取る）
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
# フォルダが既に無い登録（prunable）は失うものが無いので数えない（git worktree prune で消せる）
NESTED=""
while IFS= read -r wt; do
  [ -d "$wt" ] || continue
  case "$(cd "$wt" && pwd -P)/" in "$WT_REAL"/?*) NESTED="$NESTED $wt" ;; esac
done <<EOF
$WT_PATHS
EOF
if [ -z "$NESTED" ]; then
  NESTED="$(find "$WT_PATH" -mindepth 2 -name .git -print -quit 2>/dev/null || true)"
fi
if [ -n "$NESTED" ]; then
  echo "[wt-remove] 撤去対象の中に別のワークツリー（または git リポジトリ）があります。中のものを先に撤去してください（作業消失防止）: $NESTED" >&2
  echo "[wt-remove] フォルダが既に無い登録が残っているだけなら 'git worktree prune' で消せます" >&2
  echo "[wt-remove] 登録の無い .git（登録が消えた入れ子・clone）なら、撤去対象のワークツリーのセッションで中身を確かめてから消し、再実行してください（worktree.md §4）" >&2
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
  [ -d "$wt" ] || continue   # prunable な登録は数えない
  if [ "$(compose_default_name "$wt")" = "$PROJECT" ]; then SAME_NAME="$SAME_NAME $wt"; fi
done <<EOF
$WT_PATHS
EOF

detect_data() {   # 0=データ無し / 1=データあり / 2=名前を確定できない / 3=docker が使えない / 4=コンテナの作業フォルダが別の場所
  local f w d
  c=""; v=""   # 停止メッセージで使うため関数の外にも残す
  [ -n "$PROJECT" ] || return 2
  [ -n "${COMPOSE_PROJECT_NAME:-}" ] && return 2
  # 直下 .env でプロジェクト名・compose ファイルを変えている（export・空白付きの書き方も含む）
  grep -Eq '^[[:space:]]*(export[[:space:]]+)?COMPOSE_(PROJECT_NAME|FILE)[[:space:]]*[=:]' "$WT_PATH/.env" 2>/dev/null && return 2
  # compose ファイル（Compose が読む既定の名前すべて）で最上位の name: を指定している
  for f in compose.yaml compose.yml docker-compose.yaml docker-compose.yml \
           compose.override.yaml compose.override.yml docker-compose.override.yaml docker-compose.override.yml; do
    grep -Eq '^name[[:space:]]*:' "$WT_PATH/$f" 2>/dev/null && return 2
  done
  command -v docker >/dev/null 2>&1 || return 3
  c="$(docker ps -a -q --filter "label=com.docker.compose.project=$PROJECT")" || return 3
  v="$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT")" || return 3
  [ -z "$c$v" ] && return 0
  # コンテナの作業フォルダ（Compose が付けるラベル）が撤去対象でなければ、同名の別プロジェクト（別のクローン・親フォルダの compose）
  if [ -n "$c" ]; then
    w="$(docker ps -a --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Label "com.docker.compose.project.working_dir"}}')" || return 3
    while IFS= read -r d; do
      [ -n "$d" ] || return 4
      if [ -d "$d" ]; then d="$(cd "$d" && pwd -P)"; fi
      [ "$d" = "$WT_REAL" ] || return 4
    done <<EOF2
$w
EOF2
  fi
  return 1
}
c=""; v=""
DATA=0; detect_data || DATA=$?

# バックアップの案内（撤去対象のプロジェクトを -p で指定。scripts/db_backup.sh は今いるフォルダのプロジェクトが対象のため使えない）
backup_hint() {
  local f="backup_${PROJECT}_<日時>.sql"
  echo "[wt-remove] バックアップは primary で次を順に実行する（scripts/db_backup.sh は今いるフォルダのプロジェクトが対象なので撤去対象には使えない）:" >&2
  echo "[wt-remove]   1) ( cd '$WT_PATH' && docker compose -p '$PROJECT' up -d db )   # コンテナが無い・止まっていても volume のデータで起動する" >&2
  echo "[wt-remove]   2) ( cd '$WT_PATH' && docker compose -p '$PROJECT' exec -T db pg_dump -U postgres learning_app ) > $f" >&2
  echo "[wt-remove]   3) test -s $f && echo ok   # ok と出なければ（空のファイル）バックアップは取れていない" >&2
}

if [ "$DATA" -ne 0 ] && [ "$DATA" -ne 3 ] && [ -n "$SAME_NAME" ]; then
  echo "[wt-remove] Compose プロジェクト名 '$PROJECT' が別のワークツリーと同じです: $SAME_NAME" >&2
  echo "[wt-remove] データがどちらのものか区別できないため、DANGER_OK=1 でも down -v は実行しません。持ち主の確認と手での片付けは worktree.md §4「止まったときの片付け」に従ってください" >&2
  backup_hint
  exit 2
fi
case "$DATA" in
  0)
    echo "[wt-remove] Compose プロジェクト '$PROJECT' のコンテナ・volume はありません。docker compose down -v は実行しません" ;;
  1)
    if [ "${DANGER_OK:-}" != "1" ]; then
      echo "[wt-remove] Compose プロジェクト '$PROJECT' のコンテナまたは volume が残っています。" >&2
      echo "[wt-remove] docker compose down -v は破壊的操作です（Postgres 開発データ削除を含む）。" >&2
      if [ -z "$c" ]; then
        # volume には作業フォルダのラベルが無いため、持ち主（このワークツリーのものか）を機械で確かめられない
        echo "[wt-remove] コンテナが無く volume だけが残っています。volume には作業フォルダの記録が無いため、このワークツリーのものかを機械で確かめられません。" >&2
        echo "[wt-remove] 名前と作成日時がこのワークツリーを使っていた時期と合うか確かめてから許可してください:" >&2
        while IFS= read -r vol; do
          [ -n "$vol" ] || continue
          echo "[wt-remove]   $vol（作成: $(docker volume inspect -f '{{.CreatedAt}}' "$vol" 2>/dev/null || echo 不明)）" >&2
        done <<EOF3
$v
EOF3
      fi
      backup_hint
      echo "[wt-remove] バックアップのうえ DANGER_OK=1 bash $0 '$WT_ARG' で再実行してください。" >&2
      exit 2
    fi
    # 当該ディレクトリで、プロジェクト名を -p で固定して named volume を回収（§5D）。
    # -p で固定するのは、環境変数・.env・親フォルダの compose ファイルで別のプロジェクト（primary 等）が選ばれないようにするため
    ( cd "$WT_PATH" && docker compose -p "$PROJECT" down -v ) || {
      echo "[wt-remove] docker compose down -v が失敗しました。docker 稼働・compose ファイルを確認し、対処してから再実行してください: $WT_PATH" >&2
      exit 2; } ;;
  2)
    echo "[wt-remove] Compose のプロジェクト名を確定できません（COMPOSE_PROJECT_NAME・.env の COMPOSE_PROJECT_NAME/COMPOSE_FILE・compose の name: 指定・フォルダ名のいずれか）。" >&2
    echo "[wt-remove] 消す相手を確定できないため、DANGER_OK=1 でも撤去しません。指定を外して（unset COMPOSE_PROJECT_NAME・.env や compose の該当行を消してコミットし push）から再実行してください。" >&2
    echo "[wt-remove] 指定していた名前のプロジェクトのデータは、このスクリプトでは消えずに残ります。docker volume ls で確かめ、worktree.md §4「取り残しの発見と削除」で片付けてください" >&2
    exit 2 ;;
  3)
    if [ "${KEEP_DATA:-}" = "1" ]; then
      # docker が使えないので down -v はできない。データが残っていても消さずに撤去する（取り残しは §4 の手順で後から片付ける）
      echo "[wt-remove] ⚠️ docker が使えないため、down -v を実行せずに撤去します（KEEP_DATA=1）。Compose プロジェクト '$PROJECT' のデータが残っていた場合は、docker が使えるときに worktree.md §4「取り残しの発見と削除」で片付けてください" >&2
    else
      echo "[wt-remove] docker が使えない（コマンドが無い・デーモン停止など）ため、データの有無を判定できません。" >&2
      echo "[wt-remove] docker を起動して再実行するか、データを消さずに撤去してよければ KEEP_DATA=1 bash $0 '$WT_ARG' で再実行してください（down -v は実行しません）" >&2
      exit 2
    fi ;;
  4)
    echo "[wt-remove] Compose プロジェクト '$PROJECT' のコンテナの作業フォルダが撤去対象と違います（同じ名前の別のプロジェクト・親フォルダの compose ファイルで起動したもの）。" >&2
    echo "[wt-remove] 別の場所のデータを消してしまうため、DANGER_OK=1 でも down -v は実行しません。持ち主の確認と手での片付けは worktree.md §4「止まったときの片付け」に従ってください" >&2
    backup_hint
    exit 2 ;;
esac

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
