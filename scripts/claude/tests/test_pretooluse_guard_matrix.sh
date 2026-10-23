#!/usr/bin/env bash
# I174（plan_I174.md 0-12）: 危険な操作 × 書き方 を総当たりで guard に流し、どれも素通し（0）にならない
# （2＝停止 か ASK＝確認）ことを確かめる。書き方の読み落としが素通しになる穴（fail-open）を構造的に防ぐ。
# 実行: bash scripts/claude/tests/test_pretooluse_guard_matrix.sh
# 新しい危険な操作・書き方は、下の OPS / TPLS に 1 行足すと表が広がる。
set -uo pipefail
# 見張りの「信頼する場所」の起点（I174 0-16）。外から渡された値で一時リポジトリが信頼されなくならないよう消す
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
cd "$REPO_ROOT" || exit 1

json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
runj() { local out code; out=$(json "$1" | python3 "${2:-$GUARD}" 2>/dev/null); code=$?;
         if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; \
         then echo "ASK"; else echo "$code"; fi; }

RM="rm -r""f"   # ソース上の連続表記を避ける（このファイルを検索・編集するコマンドへの誤反応防止）
# 危険な操作と、期待する結果（「期待|操作」。2＝停止〔危険操作・解除不可〕／ASK＝確認〔秘密情報・外部送信〕）。
# 書き方によらず、そのまま書いたときと同じ結果になること（安全網で拾っても停止を確認に格下げしない）。
# 引用符は二重引用符だけを使う（bash -c '...' の中に入れるため）
OPS=(
  "2|$RM backend/media"
  "2|git reset --hard origin/develop"
  "2|git clean -fdx"
  "2|dd if=/dev/zero of=backend/db.sqlite3"
  "2|shred -u backend/db.sqlite3"
  "2|docker compose exec -T backend python manage.py flush --noinput"
  "2|docker compose exec -T db psql -U postgres -c \"DROP DATABASE app\""
  "ASK|cat backend/.env"
  "ASK|printenv"
  "ASK|docker compose exec -T backend python manage.py shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\""
  # I182: 秘密情報の検査を飛ばすコミット（停止）・リモートブランチの削除（確認）
  "2|git commit --no-verify -m wip"
  "2|git commit -anm wip"
  "ASK|git push origin --delete feature/old"
)
# 書き方（@@ が操作に置き換わる）
TPLS=(
  "@@"
  "true && @@"
  "true; @@"
  "false || @@"
  "true
@@"
  "A=1 @@"
  "(@@)"
  "{ @@; }"
  "if true; then @@; fi"
  "if false; then :; else @@; fi"
  "for f in a; do @@; done"
  "while true; do @@; break; done"
  "until false; do @@; done"
  "case x in x) @@;; esac"
  "f() { @@; }; f"
  "function f { @@; }; f"
  "echo \$(@@)"
  "diff <(@@) /dev/null"
  "bash -c '@@'"
  "sh -c '@@'"
  "sudo @@"
  "timeout 60 @@"
  "nohup @@"
  "time @@"
  "env A=1 @@"
  "nice -n 5 @@"
  "coproc @@"
  "echo a | xargs @@"
  "find . -maxdepth 0 -exec @@ \\;"
)

pass=0; fail=0
for entry in "${OPS[@]}"; do
  want="${entry%%|*}"; op="${entry#*|}"
  for tpl in "${TPLS[@]}"; do
    cmd="${tpl//@@/$op}"
    got="$(runj "$cmd")"
    if [ "$got" = "$want" ]; then
      pass=$((pass+1))
    else
      printf 'FAIL want=%s got=%s :: %s\n' "$want" "$got" "$cmd"; fail=$((fail+1))
    fi
  done
  # 行の継続（\ と改行）で操作の途中を折り返す書き方（各操作の最初の空白で折り返す。例: rm \⏎  -rf …・git \⏎  reset --hard …。
  # 危険なフラグや引数を折り返しの後ろに置き、継続をつながないと判定できない形にする）
  cont="${op%% *} \\
  ${op#* }"
  got="$(runj "$cont")"
  if [ "$got" = "$want" ]; then pass=$((pass+1)); else printf 'FAIL want=%s got=%s :: %s\n' "$want" "$got" "$cont"; fail=$((fail+1)); fi
done

# 偽合格の防止: 何でも素通しにする guard では 0 と判別されること（runj の判別が働いている）
TMP="$(mktemp -d)"; trap 'rm -r "$TMP"' EXIT
printf 'import sys\nsys.stdin.read()\nsys.exit(0)\n' > "$TMP/noop_guard.py"
fg="$(runj "$RM backend/media" "$TMP/noop_guard.py")"
if [ "$fg" = "0" ]; then pass=$((pass+1)); else printf 'FAIL FALSEGREEN noop guard: got=%s\n' "$fg"; fail=$((fail+1)); fi

echo "---"
echo "pass=$pass fail=$fail（${#OPS[@]} 操作 × (${#TPLS[@]} 書き方 + 行の継続 1) + 偽合格の防止 1）"
[ "$fail" = "0" ]
