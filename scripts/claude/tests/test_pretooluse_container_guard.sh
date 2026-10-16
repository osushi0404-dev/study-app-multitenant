#!/usr/bin/env bash
# I174: pretooluse_guard.py の危険操作・外部送信・秘密情報・コンテナ内操作の判定を決定論検証する。
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
PROBE_DOCS="docs/.i174_guard_probe_$$.py"          # F6: /app/docs/ → docs/ の読み替え用
PROBE_BACKEND="backend/.i174_guard_probe_$$.py"    # F7: /app/ → backend/ の読み替え用
PROBE_SH_BAD="backend/.i174_guard_probe_bad_$$.sh" # F10: コンテナ内 sh スクリプト（危険）
PROBE_SH_OK="backend/.i174_guard_probe_ok_$$.sh"   # F11: コンテナ内 sh スクリプト（安全）
trap 'rm -rf "$TMP"; rm -f "$REPO_ROOT/$PROBE_DOCS" "$REPO_ROOT/$PROBE_BACKEND" "$REPO_ROOT/$PROBE_SH_BAD" "$REPO_ROOT/$PROBE_SH_OK"' EXIT

json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
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
NL=$'\n'

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
# 敵対的レビュー第 1 周の再現（plan_I174.md 0 章）
ckd "A33 付着 ; の rm-rf"          "echo hi;$RM backend"
ckd "A34 ( ) の rm-rf"             "($RM backend)"
ckd "A35 \$( ) の rm-rf"           "echo \$($RM backend)"
ckd "A36 バッククォートの rm-rf"   "ls \`$RM backend\`"
ckd "A37 付着 ; の FLUSHALL"       'true;redis-cli FLUSHALL'
ckd "A38 付着 ; の dropdb"         'true;dropdb app'
ckd "A39 python -m django flush"   'docker compose exec backend python3 -m django flush --noinput'
ckd "A40 django-admin flush"       'docker compose exec backend django-admin flush --noinput'
ckd "A41 bash -lc flush"           'docker compose exec backend bash -lc "python manage.py flush --noinput"'
ckd "A42 sh -ec flush"             'docker compose exec backend sh -ec "python manage.py flush"'
ckd "A43 git -C reset --hard"      'git -C /mnt/c/app/study-app-multitenant reset --hard origin/develop'
ckd "A44 git --no-pager reset"     'git --no-pager reset --hard'
ckd "A45 compose -f down -v"       'docker compose -f docker-compose.yml down -v'
ckd "A46 compose -p down --volumes" 'docker compose -p study down --volumes'
ckd "A47 docker volume rm"         'docker volume rm study_postgres_data'
ckd "A48 system prune --volumes"   'docker system prune -a --volumes -f'
ckd "A49 compose rm -sfv"          'docker compose rm -sfv db'
ckd "A50 git clean -fdx"           'git clean -fdx'
ckd "A51 find -delete"             "find . -name '*.pyc' -delete"
ckd "A52 psql -c 付着"             'docker compose exec db psql -U postgres -c"drop table x"'
ckd "A53 pg_restore -cd"           'docker compose exec db pg_restore -cd app dump'
ckd "A54 seed_e2e --flush"         "$M seed_e2e --scenario login --password x --flush"
ckd "A55 ヒアドキュメント psql"    "docker compose exec -T db psql -U postgres <<'EOF'${NL}DROP TABLE accounts_user CASCADE;${NL}EOF"
ckd "A56 ヒアドキュメント shell"   "$M shell <<'EOF'${NL}from accounts.models import User${NL}User.objects.all().delete()${NL}EOF"
ckd "A57 ./manage.py shell -c"     'docker compose exec -T backend ./manage.py shell -c "Problem.objects.all().delete()"'
ckd "A58 shell --command="         "$M shell --command=\"Problem.objects.all().delete()\""
ckd "A59 dbshell -- -c DROP"       "$M dbshell -- -c \"DROP TABLE x\""
ckd "A60 dbshell < dump"           "$M dbshell < dump.sql"
ckd "A61 FOO=1 前置"               "FOO=1 $M flush --noinput"
ckd "A62 eval の展開"              "eval \"$M flush --noinput\""
ckd "A63 rm -R -f"                 'rm -R -f build'
ckd "A64 call_command migrate zero" "$M shell -c \"call_command('migrate', 'problems', 'zero')\""
ckd "A65 reset_db"                 "$M reset_db"
ckd "A66 ALTER TABLE"              'docker compose exec -T db psql -U postgres -c "ALTER TABLE x DROP COLUMN y"'
ckd "A67 変数経由の update"        "$M shell -c \"qs = User.objects.all(); qs.update(is_active=False)\""
ckd "A68 bash -s ヒアドキュメント" "docker compose exec -T backend bash -s <<'EOF'${NL}$RM /app/media${NL}EOF"
ckd "A69 ヒアドキュメント redis"   "docker compose exec -T redis redis-cli <<'EOF'${NL}FLUSHALL${NL}EOF"
ckd "A70 -o 付き bash -c"          "bash -o pipefail -c \"$RM build\""

# --- (H) 常に止める（DANGER_OK=1 でも 2） ---
ck "H1 rm-rf /"                2 "$(runj "$RM /")"
ck "H2 rm-rf /*"               2 "$(runj "$RM /*")"
ck "H3 DANGER_OK rm-rf /"      2 "$(runj "DANGER_OK=1 $RM /")"
ck "H4 DANGER_OK rm-rf /*"     2 "$(runj "DANGER_OK=1 $RM /*")"

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
ck "X12 apply_async"           ASK "$(runj "$M shell -c \"from x.tasks import t; t.apply_async()\"")"
ck "X13 mail_admins"           ASK "$(runj "$M shell -c \"from django.core import mail; mail.mail_admins('s','b')\"")"
ck "X14 EmailMessage"          ASK "$(runj "$M shell -c \"from django.core.mail import EmailMessage as E; E('s','b','a',['x']).send()\"")"
ck "X15 openai."               ASK "$(runj "$M shell -c \"import openai; openai.ChatCompletion.create(model='x', messages=[])\"")"
ck "X16 sendtestemail"         ASK "$(runj "$M sendtestemail x@example.com")"
ck "X17 send_mail の別名"      ASK "$(runj "$M shell -c \"from django.core.mail import send_mail as s; s('a','b','c',['x@y'])\"")"
ck "X18 email_user"            ASK "$(runj "$M shell -c \"u=User.objects.get(pk=1); u.email_user('s','b')\"")"
ck "X19 python -c の send_mail" ASK "$(runj "python3 -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")"
ck "X20 タスク関数の直接実行"  ASK "$(runj "$M shell -c \"from studylogs.tasks import bulk_update_spaced_repetition_task as t; bulk_update_spaced_repetition_task()\"")"

# --- (S) 秘密情報（ASK）／秘密でないもの（0） ---
ck "S1 コンテナ cat .env"      ASK "$(runj 'docker compose exec backend cat .env')"
ck "S2 コンテナ printenv"      ASK "$(runj 'docker compose exec backend printenv')"
ck "S3 コンテナ env"           ASK "$(runj 'docker compose exec backend env')"
ck "S4 ホスト cat backend/.env" ASK "$(runj 'cat backend/.env')"
ck "S5 docker compose config"  ASK "$(runj 'docker compose config')"
ck "S6 grep e2e/.env.e2e"      ASK "$(runj 'grep KEY e2e/.env.e2e')"
ck "S7 .env.example は読める"  0   "$(runj 'cat backend/.env.example')"

# --- (C) コンテナ内で安全と確かめられない操作（ASK） ---
ck "C1 createsuperuser"        ASK "$(runj "$M createsuperuser")"
ck "C2 npm install"            ASK "$(runj 'docker compose exec frontend npm install')"
ck "C3 パイプで psql"          ASK "$(runj 'echo "drop table x" | docker compose exec -T db psql -U postgres')"
ck "C4 パイプで shell"         ASK "$(runj "echo 'User.objects.all().delete()' | $M shell")"
ck "C5 パイプで redis-cli"     ASK "$(runj "printf 'FLUSHALL\\n' | docker compose exec -T redis redis-cli")"
ck "C6 dbshell（対話）"        ASK "$(runj "$M dbshell")"
ck "C7 一覧にないコマンド"     ASK "$(runj 'docker compose exec backend some_unknown_cmd --flag')"
ck "C8 書き込みの SQL"         ASK "$(runj 'docker compose exec -T db psql -U postgres learning_app -c "DELETE FROM problems_problem WHERE id=1;"')"
ck "C9 pip install"            ASK "$(runj 'docker compose exec backend pip install requests')"
ck "C10 bash -lc 一覧外"       ASK "$(runj 'docker compose exec backend bash -lc "python manage.py seed_e2e"')"
ck "C11 python -m pip install" ASK "$(runj 'docker compose exec backend python -m pip install x')"
ck "C12 seed_e2e（flush なし）" ASK "$(runj "$M seed_e2e --scenario login --password x")"

# --- (F) 実行ファイルの中身 ---
printf 'from problems.models import Problem\nProblem.objects.all().delete()\n' > "$TMP/del.py"
printf 'from django.core.mail import send_mail\nsend_mail(1,2,3,[4])\n' > "$TMP/mail.py"
printf 'print(1)\n' > "$TMP/ok.py"
printf '#!/bin/sh\ndocker compose exec -T backend python manage.py flush --noinput\n' > "$TMP/host.sh"
cp "$TMP/del.py" "$REPO_ROOT/$PROBE_DOCS"
cp "$TMP/mail.py" "$REPO_ROOT/$PROBE_BACKEND"
printf '#!/bin/sh\npython manage.py flush --noinput\n' > "$REPO_ROOT/$PROBE_SH_BAD"
printf '#!/bin/sh\npython -m pytest -q\nruff check .\n' > "$REPO_ROOT/$PROBE_SH_OK"
ck "F1 shell < 削除ファイル"       2   "$(runj "$M shell < $TMP/del.py")"
ck "F2 shell <付着形"              2   "$(runj "$M shell <$TMP/del.py")"
ck "F3 python 送信ファイル"        ASK "$(runj "python3 $TMP/mail.py")"
ck "F4 shell < 無害ファイル"       0   "$(runj "$M shell < $TMP/ok.py")"
ck "F5 存在しないファイル"         ASK "$(runj "$M shell < /nonexistent/i174.py")"
f5err="$(json "$M shell < /nonexistent/i174.py" | python3 "$GUARD" 2>&1 >/dev/null)"
ck "F5b 確認できなかった旨を出す"  YES "$(printf '%s' "$f5err" | grep -q '中身を確認できませんでした' && echo YES || echo NO)"
ck "F6 /app/docs/ の読み替え"      2   "$(runj "docker compose exec -T backend python /app/docs/${PROBE_DOCS#docs/}")"
ck "F7 /app/ の読み替え"           ASK "$(runj "docker compose exec -T backend python /app/${PROBE_BACKEND#backend/}")"
ck "F8 ホストの bash は見ない"     0   "$(runj "bash $TMP/host.sh")"
ck "F9 scripts/claude は見ない"    0   "$(runj 'python3 scripts/claude/hooks/pretooluse_guard.py')"
ck "F10 コンテナ sh スクリプト危険" 2  "$(runj "docker compose exec -T backend sh /app/${PROBE_SH_BAD#backend/}")"
ck "F11 コンテナ sh スクリプト安全" 0  "$(runj "docker compose exec -T backend sh /app/${PROBE_SH_OK#backend/}")"

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
ck "P11 psql SELECT"               0 "$(runj 'docker compose exec -T db psql -U postgres learning_app -c "SELECT count(*) FROM problems_problem;"')"
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
ck "P24 ヒアドキュメント本文"      0 "$(runj "cat > /tmp/i174_x.sh <<'EOF'${NL}#!/bin/sh${NL}$RM /app${NL}EOF")"
ck "P25 pytest ファイル指定"       0 "$(runj 'docker compose exec -T backend python -m pytest -q problems/tests/test_I103_cross_org_create.py')"
ck "P26 python -W -m pytest"       0 "$(runj 'docker compose exec -T backend python -W error -m pytest -q')"
ck "P27 ヒアドキュメント shell 読み取り" 0 "$(runj "$M shell <<'EOF'${NL}from problems.models import Problem${NL}print(Problem.objects.count())${NL}EOF")"
ck "P28 bash -lc 一覧内"           0 "$(runj 'docker compose exec backend bash -lc "python -m pytest -q && ruff check ."')"
ck "P29 SQL リテラル内の drop"     0 "$(runj "docker compose exec -T db psql -U postgres -c \"select 'drop' as x\"")"
ck "P30 curl localhost"            0 "$(runj "docker compose exec -T backend curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/login/")"
ck "P31 migrate 2>&1"              0 "$(runj "$M migrate problems 2>&1")"
ck "P32 sed -n"                    0 "$(runj 'docker compose exec -T backend sed -n 1,5p core/settings.py')"
ck "P33 pip check"                 0 "$(runj 'docker compose exec -T backend pip check')"
ck "P34 ヒアドキュメント psql 読み取り" 0 "$(runj "docker compose exec -T db psql -U postgres learning_app <<'EOF'${NL}SELECT count(*)${NL}FROM problems_problem;${NL}\\dt${NL}EOF")"
ck "P35 git -C status"             0 "$(runj 'git -C . status')"
ck "P36 docker compose logs"       0 "$(runj 'docker compose logs --tail=50 backend')"
ck "P37 パイプで出力を絞る"        0 "$(runj 'docker compose exec -T backend python -m pytest -q 2>&1 | tail -5')"
ck "P38 npm test"                  0 "$(runj 'docker compose exec -T frontend npm test -- --watchAll=false')"

# --- (G) 偽合格の防止: 判定の呼び出しを外した複製では素通し・実体では止まる ---
BROKEN_D="$TMP/guard_no_danger.py"
sed 's/reasons += _analyze(pcmd)\["danger"\]/pass/' "$GUARD" > "$BROKEN_D"
BROKEN_X="$TMP/guard_no_external.py"
sed 's/external = an\["external"\]/external = []/' "$GUARD" > "$BROKEN_X"
BROKEN_C="$TMP/guard_no_container.py"
sed 's/if an\["container"\]:/if False:/' "$GUARD" > "$BROKEN_C"
BROKEN_H="$TMP/guard_no_hard.py"
sed 's/if an\["hard"\]:/if False:/' "$GUARD" > "$BROKEN_H"
ck "G0 複製に置換が入った"         YES "$( (! cmp -s "$GUARD" "$BROKEN_D") && (! cmp -s "$GUARD" "$BROKEN_X") && (! cmp -s "$GUARD" "$BROKEN_C") && (! cmp -s "$GUARD" "$BROKEN_H") && echo YES || echo NO)"
ck "G1 危険判定を外すと A10 素通し" 0   "$(rungj "$BROKEN_D" "$M flush --noinput")"
ck "G2 実体では A10 を止める"      2   "$(runj "$M flush --noinput")"
ck "G3 外部判定を外すと X1 素通し" 0   "$(rungj "$BROKEN_X" "$M shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")"
ck "G4 実体では X1 を確認"         ASK "$(runj "$M shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")"
ck "G5 許可リストを外すと C7 素通し" 0 "$(rungj "$BROKEN_C" 'docker compose exec backend some_unknown_cmd --flag')"
ck "G6 実体では C7 を確認"         ASK "$(runj 'docker compose exec backend some_unknown_cmd --flag')"
ck "G7 hard を外すと H4 は確認止まり" ASK "$(rungj "$BROKEN_H" "DANGER_OK=1 $RM /*")"
ck "G8 実体では H4 を止める"       2   "$(runj "DANGER_OK=1 $RM /*")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
