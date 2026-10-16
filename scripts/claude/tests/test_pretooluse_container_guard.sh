#!/usr/bin/env bash
# I174: pretooluse_guard.py の危険操作・外部送信の判定を決定論検証する。
# 実行: bash scripts/claude/tests/test_pretooluse_container_guard.sh
#
# フックへ stdin JSON を投入して判定だけを見る（コマンド自体は実行しない）。期待値は 3 種類:
#   2   = 止める（exit 2）
#   ASK = 人の確認（exit 0 ＋ stdout に permissionDecision=ask）
#   0   = 素通し（exit 0・ask なし）
# ケースの一覧は docs/tests/open/I174_auto_test.md の「TC-01 のケース表」と 1 対 1 で対応する。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
cd "$REPO_ROOT" || exit 1

TMP="$(mktemp -d)"
PROBE_DOCS="docs/.i174_guard_probe_$$.py"        # F6: /app/docs/ → docs/ の読み替え用
PROBE_BACKEND="backend/.i174_guard_probe_$$.py"  # F7: /app/ → backend/ の読み替え用
trap 'rm -rf "$TMP"; rm -f "$REPO_ROOT/$PROBE_DOCS" "$REPO_ROOT/$PROBE_BACKEND"' EXIT

json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
run()  { json "$1" | python3 "$GUARD" >/dev/null 2>&1; echo $?; }
# ask 判別版（test_pretooluse_push_guard.sh と同じ定義）
runj() { local out code; out=$(json "$1" | python3 "$GUARD" 2>/dev/null); code=$?;
         if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; \
         then echo "ASK"; else echo "$code"; fi; }
rungj() { local out code; out=$(json "$2" | python3 "$1" 2>/dev/null); code=$?;
          if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; \
          then echo "ASK"; else echo "$code"; fi; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
# 危険操作: そのままなら 2、DANGER_OK=1 を前置すると ASK
ckd() { ck "$1" 2 "$(runj "$2")"; ck "$1 +DANGER_OK" ASK "$(runj "DANGER_OK=1 $2")"; }

M='docker compose exec -T backend python manage.py'
RM="rm -r""f"   # ソース上の連続表記を避ける（このファイルを検索・編集するコマンドへの誤反応防止）

# --- (A) 危険操作 ---
ckd "A1 psql DROP 先頭"            'docker compose exec -T db psql -U postgres -c "DROP DATABASE migrate_check;"'
ckd "A2 psql TRUNCATE 先頭"        'docker compose exec -T db psql -U postgres learning_app -c "TRUNCATE problems_problem;"'
ckd "A3 psql DELETE WHERE なし"    'docker compose exec -T db psql -U postgres learning_app -c "DELETE FROM problems_problem;"'
ckd "A4 psql 単一引用符"           "docker compose exec -T db psql -U postgres -c 'DROP DATABASE x;'"
ckd "A5 psql UPDATE WHERE なし"    'docker compose exec -T db psql -U postgres learning_app -c "UPDATE problems_problem SET is_public=false;"'
ckd "A6 dropdb"                    'docker compose exec -T db dropdb -U postgres learning_app'
ckd "A7 psql < dump"               'docker compose exec -T db psql -U postgres learning_app < dump.sql'
ckd "A8 psql -f"                   'docker compose exec -T db psql -U postgres learning_app -f /tmp/x.sql'
ckd "A9 pg_restore --clean"        'docker compose exec -T db pg_restore --clean -d learning_app /tmp/x.dump'
ckd "A10 flush"                    "$M flush --noinput"
ckd "A11 sqlflush"                 "$M sqlflush"
ckd "A12 migrate zero"             'docker compose exec backend python manage.py migrate problems zero'
ckd "A13 migrate 移動先"           "$M migrate problems 0003_previous"
ckd "A14 loaddata"                 "$M loaddata fixtures.json"
ckd "A15 redis FLUSHALL"           'docker compose exec -T redis redis-cli FLUSHALL'
ckd "A16 redis flushdb 小文字"     'docker compose exec -T redis redis-cli flushdb'
ckd "A17 shell .delete()"          "$M shell -c \"from problems.models import Problem; Problem.objects.all().delete()\""
ckd "A18 shell 一括 update"        "$M shell -c \"Problem.objects.filter(subject_id=1).update(is_public=False)\""
ckd "A19 shell bulk_update"        "$M shell -c \"Problem.objects.bulk_update(ps, ['title'])\""
ckd "A20 shell call_command flush" "$M shell -c \"from django.core.management import call_command; call_command('flush', interactive=False)\""
ckd "A21 shell 文字列の SQL"       "$M shell -c \"from django.db import connection; connection.cursor().execute('DELETE FROM problems_problem')\""
ckd "A22 compose run rm-rf"        "docker-compose run --rm backend $RM /app/tmp"
ckd "A23 相対 rm-rf"               "$RM node_modules/.cache"
ckd "A24 絶対 rm-rf（解除可）"     "$RM /tmp/claude-1000/xyz"
ckd "A25 docker exec psql"         'docker exec study-app-multitenant-db-1 psql -U postgres -c "DROP DATABASE learning_app;"'
ckd "A26 docker exec flush"        'docker exec study-app-multitenant-backend-1 python manage.py flush --noinput'
ckd "A27 docker exec redis"        'docker exec study-app-multitenant-redis-1 redis-cli FLUSHALL'
ckd "A28 ホスト直接 flush"         'backend/.venv/bin/python backend/manage.py flush --noinput'
ckd "A29 sh -c flush"              'docker compose exec backend sh -c "python manage.py flush --noinput"'
ckd "A30 python -c delete"         'python3 -c "import django; from problems.models import Problem; Problem.objects.all().delete()"'
ckd "A31 reset --hard（回帰）"     'git reset --hard HEAD~1'
ckd "A32 down -v（回帰）"          'docker compose down -v'

# --- (H) 常に止める（DANGER_OK=1 でも 2） ---
ck "H1 rm-rf /"                2 "$(runj "$RM /")"
ck "H2 rm-rf /*"               2 "$(runj "$RM /*")"
ck "H3 DANGER_OK rm-rf /"      2 "$(runj "DANGER_OK=1 $RM /")"

# --- (X) 外部送信（ASK） ---
ck "X1 send_mail"              ASK "$(runj "$M shell -c \"from django.core.mail import send_mail; send_mail('s','b','a@example.com',['x@example.com'])\"")"
ck "X2 リマインダー .delay"    ASK "$(runj "$M shell -c \"from studylogs.tasks import send_study_reminders_task; send_study_reminders_task.delay()\"")"
ck "X3 登録 API"               ASK "$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/register/', {}, HTTP_HOST='localhost')\"")"
ck "X4 再設定依頼 API"         ASK "$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/password-reset/', {}, HTTP_HOST='localhost')\"")"
ck "X5 celery call"            ASK "$(runj 'docker compose exec -T celery celery -A core call studylogs.tasks.send_study_reminders_task')"
ck "X6 sh -c 内の send_mail"   ASK "$(runj "docker compose exec backend sh -c \"python manage.py shell -c 'from django.core.mail import send_mail; send_mail(1,2,3,[4])'\"")"
ck "X7 generate_ai_problems"   ASK "$(runj "$M generate_ai_problems")"
ck "X8 generate_ai API"        ASK "$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/problems/generate_ai/', {})\"")"
ck "X9 generate_adaptive API"  ASK "$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/problems/generate_adaptive/', {})\"")"
ck "X10 AIQuestionGenerator"   ASK "$(runj "$M shell -c \"from problems.ai_generator import AIQuestionGenerator; AIQuestionGenerator().generate_question(None)\"")"
ck "X11 docker exec AI"        ASK "$(runj 'docker exec study-app-multitenant-backend-1 python manage.py generate_ai_problems')"

# --- (F) 実行ファイルの中身 ---
printf 'from problems.models import Problem\nProblem.objects.all().delete()\n' > "$TMP/del.py"
printf 'from django.core.mail import send_mail\nsend_mail(1,2,3,[4])\n' > "$TMP/mail.py"
printf 'print(1)\n' > "$TMP/ok.py"
printf '#!/bin/sh\ndocker compose exec -T backend python manage.py flush --noinput\n' > "$TMP/host.sh"
cp "$TMP/del.py" "$REPO_ROOT/$PROBE_DOCS"
cp "$TMP/mail.py" "$REPO_ROOT/$PROBE_BACKEND"
ck "F1 shell < 削除ファイル"       2   "$(runj "$M shell < $TMP/del.py")"
ck "F2 shell <付着形"              2   "$(runj "$M shell <$TMP/del.py")"
ck "F3 python 送信ファイル"        ASK "$(runj "python3 $TMP/mail.py")"
ck "F4 shell < 無害ファイル"       0   "$(runj "$M shell < $TMP/ok.py")"
ck "F5 存在しないファイル"         0   "$(runj "$M shell < /nonexistent/i174.py")"
f5err="$(json "$M shell < /nonexistent/i174.py" | python3 "$GUARD" 2>&1 >/dev/null)"
ck "F5b 確認できなかった旨を出す"  YES "$(printf '%s' "$f5err" | grep -q '中身を確認できませんでした' && echo YES || echo NO)"
ck "F6 /app/docs/ の読み替え"      2   "$(runj "docker compose exec -T backend python /app/docs/${PROBE_DOCS#docs/}")"
ck "F7 /app/ の読み替え"           ASK "$(runj "docker compose exec -T backend python /app/${PROBE_BACKEND#backend/}")"
ck "F8 ホストの bash は見ない"     0   "$(runj "bash $TMP/host.sh")"
ck "F9 scripts/claude は見ない"    0   "$(runj 'python3 scripts/claude/hooks/pretooluse_guard.py')"

# --- (P) 素通し ---
ck "P1 pytest"                     0 "$(runj 'docker compose exec -T backend python -m pytest -q')"
ck "P2 ruff"                       0 "$(runj 'docker compose exec -T backend ruff check .')"
ck "P3 pip-audit"                  0 "$(runj 'docker compose exec -T backend pip-audit -r requirements.txt')"
ck "P4 npm audit"                  0 "$(runj 'docker compose exec -T frontend npm audit --audit-level=critical --omit=dev')"
ck "P5 makemigrations --check"     0 "$(runj "$M makemigrations --check --dry-run")"
ck "P6 migrate --noinput"          0 "$(runj "$M migrate --noinput")"
ck "P7 migrate <app>"              0 "$(runj "$M migrate problems")"
ck "P8 migrate --database 値"      0 "$(runj "$M migrate --database default problems")"
ck "P9 psql \\dt"                  0 "$(runj 'docker compose exec -T db psql -U postgres learning_app -c "\dt"')"
ck "P10 CREATE DATABASE"           0 "$(runj 'docker compose exec -T db psql -U postgres -c "CREATE DATABASE migrate_check;"')"
ck "P11 DELETE WHERE あり"         0 "$(runj 'docker compose exec -T db psql -U postgres learning_app -c "DELETE FROM problems_problem WHERE id=1;"')"
ck "P12 読み取りの shell"          0 "$(runj "$M shell -c \"from problems.models import Problem; print(Problem.objects.filter(subject_id=1).count())\"")"
ck "P13 dict.update"               0 "$(runj "$M shell -c \"d={}; d.update({'a':1}); print(d)\"")"
ck "P14 1 件の更新"                0 "$(runj "$M shell -c \"u=User.objects.get(pk=1); u.set_password('x'); u.save()\"")"
ck "P15 ログイン API"              0 "$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/login/', {}, HTTP_HOST='localhost')\"")"
ck "P16 再設定の確定 API"          0 "$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/password-reset-confirm/', {})\"")"
ck "P17 一覧の取得"                0 "$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().get('/api/problems/')\"")"
ck "P18 redis ping"                0 "$(runj 'docker compose exec -T redis redis-cli ping')"
ck "P19 redis KEYS"                0 "$(runj "docker compose exec -T redis redis-cli KEYS 'rl:*'")"
ck "P20 dumpdata"                  0 "$(runj "$M dumpdata problems")"
ck "P21 grep の検索文字列"         0 "$(runj "grep -n \"$RM\" scripts/claude/tests/test_pretooluse_checkout_guard.sh")"
ck "P22 send_mail の検索"          0 "$(runj 'grep -rn send_mail backend')"
ck "P23 manage.py flush の検索"    0 "$(runj 'grep -rn "manage.py flush" docs')"
ck "P24 ヒアドキュメント本文"      0 "$(runj "cat > /tmp/i174_x.sh <<'EOF'
#!/bin/sh
$RM /app
EOF")"
ck "P25 pytest ファイル指定"       0 "$(runj 'docker compose exec -T backend python -m pytest -q problems/tests/test_I103_cross_org_create.py')"

# --- (G) 偽合格の防止: 判定の呼び出しを外した複製では素通し・実体では止まる ---
BROKEN_D="$TMP/guard_no_danger.py"
sed 's/reasons += _segment_danger(toks, ctr)/pass/' "$GUARD" > "$BROKEN_D"
BROKEN_X="$TMP/guard_no_external.py"
sed 's/external = _external_reasons(cmd)/external = []/' "$GUARD" > "$BROKEN_X"
ck "G0 複製に置換が入った"         YES "$( (! cmp -s "$GUARD" "$BROKEN_D") && (! cmp -s "$GUARD" "$BROKEN_X") && echo YES || echo NO)"
ck "G1 判定を外すと A10 素通し"    0   "$(rungj "$BROKEN_D" "$M flush --noinput")"
ck "G2 実体では A10 を止める"      2   "$(runj "$M flush --noinput")"
ck "G3 判定を外すと X1 素通し"     0   "$(rungj "$BROKEN_X" "$M shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")"
ck "G4 実体では X1 を確認"         ASK "$(runj "$M shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
