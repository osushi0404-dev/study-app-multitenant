# I174 自動テスト: 確認が必要な操作の見直し（docker compose exec 等の一律確認をやめ、コンテナ内の危険操作だけを見張りで止める）

- 関連: docs/issues/open/I174.md / docs/plans/open/plan_I174.md / GitHub #292 / Draft PR #293
- テストレベル: 決定論の単体テスト（フックに JSON を入れて exit code と `permissionDecision=ask` の JSON を確かめる bash スクリプト）と、ファイルの静的検査。アプリのコードを変えないため、pytest・Jest・E2E は対象外
- 判定の書き方: 既存の `test_pretooluse_push_guard.sh` と同じく、`run`（exit code）と `runj`（exit 0 かつ stdout に `"permissionDecision": "ask"` があれば `ASK`、それ以外は exit code）を使う。期待値は `2`（止める）・`ASK`（人の確認）・`0`（素通し・ask も無し）の 3 種類

実行コマンド（例）: `bash scripts/claude/tests/test_pretooluse_container_guard.sh`

結果:
- backend: 対象外（アプリのコード変更なし）
- frontend: 対象外

## TC 一覧

| TC | 内容 | 合格条件 | 対応 AC | ステップ |
|---|---|---|---|---|
| TC-01 | 新規 `scripts/claude/tests/test_pretooluse_container_guard.sh`（下の TC-01 のケース表を全件・242 ケース。2026-10-16 の設計変更〔計画書 0 章〕で作り直し） | exit 0（最終行 `pass=242 fail=0`） | AC-4〜AC-9・AC-13・AC-14 | 2・3 |
| TC-13 | 新規 `scripts/claude/tests/test_settings_permissions.sh`（settings.json の ask・allow・deny の中身を JSON として確認。後退を注入した複製で不合格になることも確認） | exit 0 | AC-1〜AC-3・AC-14 | 4 |
| TC-02 | `scripts/claude/tests/test_pretooluse_push_guard.sh`（DOK1〜3・P6・P7・P23・P24・P26・P31 を ASK に更新） | exit 0 | AC-5・AC-10 | 2 |
| TC-03 | `scripts/claude/tests/test_pretooluse_checkout_guard.sh`（`runj` を追加し G7 を ASK に更新） | exit 0 | AC-5・AC-10 | 2 |
| TC-04 | `scripts/claude/tests/test_pretooluse_worktree_guard.sh`（変更なし。A19 は exit 2 のまま） | exit 0 | AC-10 | 2 |
| TC-05 | `scripts/claude/tests/test_adversarial_trigger.sh`（変更なし） | exit 0 | AC-10 | 2 |
| TC-06 | `.claude/settings.json` の JSON 構文 | exit 0 | AC-1〜AC-3 | 4 |
| TC-07 | ask から外した行が無い（`! grep -qF`）・残す 7 行がある（`grep -qF`）。exec は `Bash(docker compose exec` / `Bash(docker-compose exec` の前方一致で、ask の 2 行と allow の 10 行（どのサービスの行でも）をまとめて不在確認する | すべて exit 0 | AC-1・AC-2 | 4 |
| TC-08 | `Write(` が settings.json に無い | exit 0 | AC-3 | 4 |
| TC-09 | danger-ops.md に追記した語句がある | すべて exit 0 | AC-11 | 5 |
| TC-10 | `pretooluse_guard.py` の構文 | exit 0 | — | 2・3 |
| TC-11 | 新規テストの構文 | exit 0 | — | 2 |
| TC-12 | I146 マージ後の `scripts/claude/tests/test_pretooluse_gh_pr_guard.sh`（I146 が足すテスト。DANGER_OK=1 の解除経路があれば期待値を ASK に揃える） | exit 0 | AC-10 | 6 |

TC-12 は、I146 のマージ前は対象ファイルが本ブランチに無いので、下の決定論ゲートには入れない。ステップ 6 の取り込み後に、この文書のゲートへ `bash scripts/claude/tests/test_pretooluse_gh_pr_guard.sh` を加えて実行する。

### TC-01 のケース表（`test_pretooluse_container_guard.sh` から自動生成・1 対 1）

`$M` は `docker compose exec -T backend python manage.py`、`$RM` は `rm -r`＋`f`、`${NL}` は改行。コマンド欄はテストスクリプトの記述そのまま。

**(A) 危険操作（2。DANGER_OK=1 を前置すると ASK。各行を 2 通りで確かめる）**

| # | 内容 | 期待値 | テストの記述 |
|---|---|---|---|
| A1 | psql DROP 先頭 | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db psql -U postgres -c "DROP DATABASE migrate_check;"'` |
| A2 | psql TRUNCATE 先頭 | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db psql -U postgres learning_app -c "TRUNCATE problems_problem;"'` |
| A3 | psql DELETE WHERE なし | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db psql -U postgres learning_app -c "DELETE FROM problems_problem;"'` |
| A4 | psql 単一引用符 | 2 / +DANGER_OK=1 で ASK | `"docker compose exec -T db psql -U postgres -c 'DROP DATABASE x;'"` |
| A5 | psql UPDATE WHERE なし | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db psql -U postgres learning_app -c "UPDATE problems_problem SET is_public=false;"'` |
| A6 | dropdb | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db dropdb -U postgres learning_app'` |
| A7 | psql < dump | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db psql -U postgres learning_app < dump.sql'` |
| A8 | psql -f | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db psql -U postgres learning_app -f /tmp/x.sql'` |
| A9 | pg_restore --clean | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db pg_restore --clean -d learning_app /tmp/x.dump'` |
| A10 | flush | 2 / +DANGER_OK=1 で ASK | `"$M flush --noinput"` |
| A11 | sqlflush | 2 / +DANGER_OK=1 で ASK | `"$M sqlflush"` |
| A12 | migrate zero | 2 / +DANGER_OK=1 で ASK | `'docker compose exec backend python manage.py migrate problems zero'` |
| A13 | migrate 移動先 | 2 / +DANGER_OK=1 で ASK | `"$M migrate problems 0003_previous"` |
| A14 | loaddata | 2 / +DANGER_OK=1 で ASK | `"$M loaddata fixtures.json"` |
| A15 | redis FLUSHALL | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T redis redis-cli FLUSHALL'` |
| A16 | redis flushdb 小文字 | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T redis redis-cli flushdb'` |
| A17 | shell .delete() | 2 / +DANGER_OK=1 で ASK | `"$M shell -c \"from problems.models import Problem; Problem.objects.all().delete()\""` |
| A18 | shell 一括 update | 2 / +DANGER_OK=1 で ASK | `"$M shell -c \"Problem.objects.filter(subject_id=1).update(is_public=False)\""` |
| A19 | shell bulk_update | 2 / +DANGER_OK=1 で ASK | `"$M shell -c \"Problem.objects.bulk_update(ps, ['title'])\""` |
| A20 | shell call_command flush | 2 / +DANGER_OK=1 で ASK | `"$M shell -c \"from django.core.management import call_command; call_command('flush', interactive=False)\""` |
| A21 | shell 文字列の SQL | 2 / +DANGER_OK=1 で ASK | `"$M shell -c \"from django.db import connection; connection.cursor().execute('DELETE FROM problems_problem')\""` |
| A22 | compose run rm-rf | 2 / +DANGER_OK=1 で ASK | `"docker-compose run --rm backend $RM /app/tmp"` |
| A23 | 相対 rm-rf | 2 / +DANGER_OK=1 で ASK | `"$RM node_modules/.cache"` |
| A24 | 絶対 rm-rf（解除可） | 2 / +DANGER_OK=1 で ASK | `"$RM /tmp/claude-1000/xyz"` |
| A25 | docker exec psql | 2 / +DANGER_OK=1 で ASK | `'docker exec study-app-multitenant-db-1 psql -U postgres -c "DROP DATABASE learning_app;"'` |
| A26 | docker exec flush | 2 / +DANGER_OK=1 で ASK | `'docker exec study-app-multitenant-backend-1 python manage.py flush --noinput'` |
| A27 | docker exec redis | 2 / +DANGER_OK=1 で ASK | `'docker exec study-app-multitenant-redis-1 redis-cli FLUSHALL'` |
| A28 | ホスト直接 flush | 2 / +DANGER_OK=1 で ASK | `'backend/.venv/bin/python backend/manage.py flush --noinput'` |
| A29 | sh -c flush | 2 / +DANGER_OK=1 で ASK | `'docker compose exec backend sh -c "python manage.py flush --noinput"'` |
| A30 | python -c delete | 2 / +DANGER_OK=1 で ASK | `'python3 -c "import django; from problems.models import Problem; Problem.objects.all().delete()"'` |
| A31 | reset --hard（回帰） | 2 / +DANGER_OK=1 で ASK | `'git reset --hard HEAD~1'` |
| A32 | down -v（回帰） | 2 / +DANGER_OK=1 で ASK | `'docker compose down -v'` |
| A33 | 付着 ; の rm-rf | 2 / +DANGER_OK=1 で ASK | `"echo hi;$RM backend"` |
| A34 | ( ) の rm-rf | 2 / +DANGER_OK=1 で ASK | `"($RM backend)"` |
| A35 | \$( ) の rm-rf | 2 / +DANGER_OK=1 で ASK | `"echo \$($RM backend)"` |
| A36 | バッククォートの rm-rf | 2 / +DANGER_OK=1 で ASK | `"ls \`$RM backend\`"` |
| A37 | 付着 ; の FLUSHALL | 2 / +DANGER_OK=1 で ASK | `'true;redis-cli FLUSHALL'` |
| A38 | 付着 ; の dropdb | 2 / +DANGER_OK=1 で ASK | `'true;dropdb app'` |
| A39 | python -m django flush | 2 / +DANGER_OK=1 で ASK | `'docker compose exec backend python3 -m django flush --noinput'` |
| A40 | django-admin flush | 2 / +DANGER_OK=1 で ASK | `'docker compose exec backend django-admin flush --noinput'` |
| A41 | bash -lc flush | 2 / +DANGER_OK=1 で ASK | `'docker compose exec backend bash -lc "python manage.py flush --noinput"'` |
| A42 | sh -ec flush | 2 / +DANGER_OK=1 で ASK | `'docker compose exec backend sh -ec "python manage.py flush"'` |
| A43 | git -C reset --hard | 2 / +DANGER_OK=1 で ASK | `'git -C /mnt/c/app/study-app-multitenant reset --hard origin/develop'` |
| A44 | git --no-pager reset | 2 / +DANGER_OK=1 で ASK | `'git --no-pager reset --hard'` |
| A45 | compose -f down -v | 2 / +DANGER_OK=1 で ASK | `'docker compose -f docker-compose.yml down -v'` |
| A46 | compose -p down --volumes | 2 / +DANGER_OK=1 で ASK | `'docker compose -p study down --volumes'` |
| A47 | docker volume rm | 2 / +DANGER_OK=1 で ASK | `'docker volume rm study_postgres_data'` |
| A48 | system prune --volumes | 2 / +DANGER_OK=1 で ASK | `'docker system prune -a --volumes -f'` |
| A49 | compose rm -sfv | 2 / +DANGER_OK=1 で ASK | `'docker compose rm -sfv db'` |
| A50 | git clean -fdx | 2 / +DANGER_OK=1 で ASK | `'git clean -fdx'` |
| A51 | find -delete | 2 / +DANGER_OK=1 で ASK | `"find . -name '*.pyc' -delete"` |
| A52 | psql -c 付着 | 2 / +DANGER_OK=1 で ASK | `'docker compose exec db psql -U postgres -c"drop table x"'` |
| A53 | pg_restore -cd | 2 / +DANGER_OK=1 で ASK | `'docker compose exec db pg_restore -cd app dump'` |
| A54 | seed_e2e --flush | 2 / +DANGER_OK=1 で ASK | `"$M seed_e2e --scenario login --password x --flush"` |
| A55 | ヒアドキュメント psql | 2 / +DANGER_OK=1 で ASK | `"docker compose exec -T db psql -U postgres <<'EOF'${NL}DROP TABLE accounts_user CASCADE;${NL}EOF"` |
| A56 | ヒアドキュメント shell | 2 / +DANGER_OK=1 で ASK | `"$M shell <<'EOF'${NL}from accounts.models import User${NL}User.objects.all().delete()${NL}EOF"` |
| A57 | ./manage.py shell -c | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T backend ./manage.py shell -c "Problem.objects.all().delete()"'` |
| A58 | shell --command= | 2 / +DANGER_OK=1 で ASK | `"$M shell --command=\"Problem.objects.all().delete()\""` |
| A59 | dbshell -- -c DROP | 2 / +DANGER_OK=1 で ASK | `"$M dbshell -- -c \"DROP TABLE x\""` |
| A60 | dbshell < dump | 2 / +DANGER_OK=1 で ASK | `"$M dbshell < dump.sql"` |
| A61 | FOO=1 前置 | 2 / +DANGER_OK=1 で ASK | `"FOO=1 $M flush --noinput"` |
| A62 | eval の展開 | 2 / +DANGER_OK=1 で ASK | `"eval \"$M flush --noinput\""` |
| A63 | rm -R -f | 2 / +DANGER_OK=1 で ASK | `'rm -R -f build'` |
| A64 | call_command migrate zero | 2 / +DANGER_OK=1 で ASK | `"$M shell -c \"call_command('migrate', 'problems', 'zero')\""` |
| A65 | reset_db | 2 / +DANGER_OK=1 で ASK | `"$M reset_db"` |
| A66 | ALTER TABLE | 2 / +DANGER_OK=1 で ASK | `'docker compose exec -T db psql -U postgres -c "ALTER TABLE x DROP COLUMN y"'` |
| A67 | 変数経由の update | 2 / +DANGER_OK=1 で ASK | `"$M shell -c \"qs = User.objects.all(); qs.update(is_active=False)\""` |
| A68 | bash -s ヒアドキュメント | 2 / +DANGER_OK=1 で ASK | `"docker compose exec -T backend bash -s <<'EOF'${NL}$RM /app/media${NL}EOF"` |
| A69 | ヒアドキュメント redis | 2 / +DANGER_OK=1 で ASK | `"docker compose exec -T redis redis-cli <<'EOF'${NL}FLUSHALL${NL}EOF"` |
| A70 | -o 付き bash -c | 2 / +DANGER_OK=1 で ASK | `"bash -o pipefail -c \"$RM build\""` |

**(H) 常に止める（2。DANGER_OK=1 でも 2）**

| # | 内容 | 期待値 | テストの記述 |
|---|---|---|---|
| H1 | rm-rf / | 2 | `"$(runj "$RM /")"` |
| H2 | rm-rf /* | 2 | `"$(runj "$RM /*")"` |
| H3 | DANGER_OK rm-rf / | 2 | `"$(runj "DANGER_OK=1 $RM /")"` |
| H4 | DANGER_OK rm-rf /* | 2 | `"$(runj "DANGER_OK=1 $RM /*")"` |

**(X) 外部送信（ASK）**

| # | 内容 | 期待値 | テストの記述 |
|---|---|---|---|
| X1 | send_mail | ASK | `"$(runj "$M shell -c \"from django.core.mail import send_mail; send_mail('s','b','a@example.com',['x@example.com'])\"")"` |
| X2 | リマインダー .delay | ASK | `"$(runj "$M shell -c \"from studylogs.tasks import send_study_reminders_task; send_study_reminders_task.delay()\"")"` |
| X3 | 登録 API | ASK | `"$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/register/', {}, HTTP_HOST='localhost')\"")"` |
| X4 | 再設定依頼 API | ASK | `"$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/password-reset/', {}, HTTP_HOST='localhost')\"")"` |
| X5 | celery call | ASK | `"$(runj 'docker compose exec -T celery celery -A core call studylogs.tasks.send_study_reminders_task')"` |
| X6 | sh -c 内の send_mail | ASK | `"$(runj "docker compose exec backend sh -c \"python manage.py shell -c 'from django.core.mail import send_mail; send_mail(1,2,3,[4])'\"")"` |
| X7 | generate_ai_problems | ASK | `"$(runj "$M generate_ai_problems")"` |
| X8 | generate_ai API | ASK | `"$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/problems/generate_ai/', {})\"")"` |
| X9 | generate_adaptive API | ASK | `"$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/problems/generate_adaptive/', {})\"")"` |
| X10 | AIQuestionGenerator | ASK | `"$(runj "$M shell -c \"from problems.ai_generator import AIQuestionGenerator; AIQuestionGenerator().generate_question(None)\"")"` |
| X11 | docker exec AI | ASK | `"$(runj 'docker exec study-app-multitenant-backend-1 python manage.py generate_ai_problems')"` |
| X12 | apply_async | ASK | `"$(runj "$M shell -c \"from x.tasks import t; t.apply_async()\"")"` |
| X13 | mail_admins | ASK | `"$(runj "$M shell -c \"from django.core import mail; mail.mail_admins('s','b')\"")"` |
| X14 | EmailMessage | ASK | `"$(runj "$M shell -c \"from django.core.mail import EmailMessage as E; E('s','b','a',['x']).send()\"")"` |
| X15 | openai. | ASK | `"$(runj "$M shell -c \"import openai; openai.ChatCompletion.create(model='x', messages=[])\"")"` |
| X16 | sendtestemail | ASK | `"$(runj "$M sendtestemail x@example.com")"` |
| X17 | send_mail の別名 | ASK | `"$(runj "$M shell -c \"from django.core.mail import send_mail as s; s('a','b','c',['x@y'])\"")"` |
| X18 | email_user | ASK | `"$(runj "$M shell -c \"u=User.objects.get(pk=1); u.email_user('s','b')\"")"` |
| X19 | python -c の send_mail | ASK | `"$(runj "python3 -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")"` |
| X20 | タスク関数の直接実行 | ASK | `"$(runj "$M shell -c \"from studylogs.tasks import bulk_update_spaced_repetition_task as t; bulk_update_spaced_repetition_task()\"")"` |

**(S) 秘密情報（ASK）と秘密でないもの（0）**

| # | 内容 | 期待値 | テストの記述 |
|---|---|---|---|
| S1 | コンテナ cat .env | ASK | `"$(runj 'docker compose exec backend cat .env')"` |
| S2 | コンテナ printenv | ASK | `"$(runj 'docker compose exec backend printenv')"` |
| S3 | コンテナ env | ASK | `"$(runj 'docker compose exec backend env')"` |
| S4 | ホスト cat backend/.env | ASK | `"$(runj 'cat backend/.env')"` |
| S5 | docker compose config | ASK | `"$(runj 'docker compose config')"` |
| S6 | grep e2e/.env.e2e | ASK | `"$(runj 'grep KEY e2e/.env.e2e')"` |
| S7 | .env.example は読める | 0 | `"$(runj 'cat backend/.env.example')"` |

**(C) コンテナ内で安全と確かめられない操作（ASK）**

| # | 内容 | 期待値 | テストの記述 |
|---|---|---|---|
| C1 | createsuperuser | ASK | `"$(runj "$M createsuperuser")"` |
| C2 | npm install | ASK | `"$(runj 'docker compose exec frontend npm install')"` |
| C3 | パイプで psql | ASK | `"$(runj 'echo "drop table x" \| docker compose exec -T db psql -U postgres')"` |
| C4 | パイプで shell | ASK | `"$(runj "echo 'User.objects.all().delete()' \| $M shell")"` |
| C5 | パイプで redis-cli | ASK | `"$(runj "printf 'FLUSHALL\\n' \| docker compose exec -T redis redis-cli")"` |
| C6 | dbshell（対話） | ASK | `"$(runj "$M dbshell")"` |
| C7 | 一覧にないコマンド | ASK | `"$(runj 'docker compose exec backend some_unknown_cmd --flag')"` |
| C8 | 書き込みの SQL | ASK | `"$(runj 'docker compose exec -T db psql -U postgres learning_app -c "DELETE FROM problems_problem WHERE id=1;"')"` |
| C9 | pip install | ASK | `"$(runj 'docker compose exec backend pip install requests')"` |
| C10 | bash -lc 一覧外 | ASK | `"$(runj 'docker compose exec backend bash -lc "python manage.py seed_e2e"')"` |
| C11 | python -m pip install | ASK | `"$(runj 'docker compose exec backend python -m pip install x')"` |
| C12 | seed_e2e（flush なし） | ASK | `"$(runj "$M seed_e2e --scenario login --password x")"` |

**(F) 実行ファイルの中身**

| # | 内容 | 期待値 | テストの記述 |
|---|---|---|---|
| F1 | shell < 削除ファイル | 2 | `"$(runj "$M shell < $TMP/del.py")"` |
| F2 | shell <付着形 | 2 | `"$(runj "$M shell <$TMP/del.py")"` |
| F3 | python 送信ファイル | ASK | `"$(runj "python3 $TMP/mail.py")"` |
| F4 | shell < 無害ファイル | 0 | `"$(runj "$M shell < $TMP/ok.py")"` |
| F5 | 存在しないファイル | ASK | `"$(runj "$M shell < /nonexistent/i174.py")"` |
| F5b | 確認できなかった旨を出す | YES | `"$(printf '%s' "$f5err" \| grep -q '中身を確認できませんでした' && echo YES \|\| echo NO)"` |
| F6 | /app/docs/ の読み替え | 2 | `"$(runj "docker compose exec -T backend python /app/docs/${PROBE_DOCS#docs/}")"` |
| F7 | /app/ の読み替え | ASK | `"$(runj "docker compose exec -T backend python /app/${PROBE_BACKEND#backend/}")"` |
| F8 | ホストの bash は見ない | 0 | `"$(runj "bash $TMP/host.sh")"` |
| F9 | scripts/claude は見ない | 0 | `"$(runj 'python3 scripts/claude/hooks/pretooluse_guard.py')"` |
| F10 | コンテナ sh スクリプト危険 | 2 | `"$(runj "docker compose exec -T backend sh /app/${PROBE_SH_BAD#backend/}")"` |
| F11 | コンテナ sh スクリプト安全 | 0 | `"$(runj "docker compose exec -T backend sh /app/${PROBE_SH_OK#backend/}")"` |

**(P) 素通し（0）**

| # | 内容 | 期待値 | テストの記述 |
|---|---|---|---|
| P1 | pytest | 0 | `"$(runj 'docker compose exec -T backend python -m pytest -q')"` |
| P2 | ruff | 0 | `"$(runj 'docker compose exec -T backend ruff check .')"` |
| P3 | pip-audit | 0 | `"$(runj 'docker compose exec -T backend pip-audit -r requirements.txt')"` |
| P4 | npm audit | 0 | `"$(runj 'docker compose exec -T frontend npm audit --audit-level=critical --omit=dev')"` |
| P5 | makemigrations --check | 0 | `"$(runj "$M makemigrations --check --dry-run")"` |
| P6 | migrate --noinput | 0 | `"$(runj "$M migrate --noinput")"` |
| P7 | migrate <app> | 0 | `"$(runj "$M migrate problems")"` |
| P8 | migrate --database 値 | 0 | `"$(runj "$M migrate --database default problems")"` |
| P9 | psql \\dt | 0 | `"$(runj 'docker compose exec -T db psql -U postgres learning_app -c "\dt"')"` |
| P10 | CREATE DATABASE | 0 | `"$(runj 'docker compose exec -T db psql -U postgres -c "CREATE DATABASE migrate_check;"')"` |
| P11 | psql SELECT | 0 | `"$(runj 'docker compose exec -T db psql -U postgres learning_app -c "SELECT count(*) FROM problems_problem;"')"` |
| P12 | 読み取りの shell | 0 | `"$(runj "$M shell -c \"from problems.models import Problem; print(Problem.objects.filter(subject_id=1).count())\"")"` |
| P13 | dict.update | 0 | `"$(runj "$M shell -c \"d={}; d.update({'a':1}); print(d)\"")"` |
| P14 | 1 件の更新 | 0 | `"$(runj "$M shell -c \"u=User.objects.get(pk=1); u.set_password('x'); u.save()\"")"` |
| P15 | ログイン API | 0 | `"$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/login/', {}, HTTP_HOST='localhost')\"")"` |
| P16 | 再設定の確定 API | 0 | `"$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().post('/api/auth/password-reset-confirm/', {})\"")"` |
| P17 | 一覧の取得 | 0 | `"$(runj "$M shell -c \"from rest_framework.test import APIClient; APIClient().get('/api/problems/')\"")"` |
| P18 | redis ping | 0 | `"$(runj 'docker compose exec -T redis redis-cli ping')"` |
| P19 | redis KEYS | 0 | `"$(runj "docker compose exec -T redis redis-cli KEYS 'rl:*'")"` |
| P20 | dumpdata | 0 | `"$(runj "$M dumpdata problems")"` |
| P21 | grep の検索文字列 | 0 | `"$(runj "grep -n \"$RM\" scripts/claude/tests/test_pretooluse_checkout_guard.sh")"` |
| P22 | send_mail の検索 | 0 | `"$(runj 'grep -rn send_mail backend')"` |
| P23 | manage.py flush の検索 | 0 | `"$(runj 'grep -rn "manage.py flush" docs')"` |
| P24 | ヒアドキュメント本文 | 0 | `"$(runj "cat > /tmp/i174_x.sh <<'EOF'${NL}#!/bin/sh${NL}$RM /app${NL}EOF")"` |
| P25 | pytest ファイル指定 | 0 | `"$(runj 'docker compose exec -T backend python -m pytest -q problems/tests/test_I103_cross_org_create.py')"` |
| P26 | python -W -m pytest | 0 | `"$(runj 'docker compose exec -T backend python -W error -m pytest -q')"` |
| P27 | ヒアドキュメント shell 読み取り | 0 | `"$(runj "$M shell <<'EOF'${NL}from problems.models import Problem${NL}print(Problem.objects.count())${NL}EOF")"` |
| P28 | bash -lc 一覧内 | 0 | `"$(runj 'docker compose exec backend bash -lc "python -m pytest -q && ruff check ."')"` |
| P29 | SQL リテラル内の drop | 0 | `"$(runj "docker compose exec -T db psql -U postgres -c \"select 'drop' as x\"")"` |
| P30 | curl localhost | 0 | `"$(runj "docker compose exec -T backend curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/login/")"` |
| P31 | migrate 2>&1 | 0 | `"$(runj "$M migrate problems 2>&1")"` |
| P32 | sed -n | 0 | `"$(runj 'docker compose exec -T backend sed -n 1,5p core/settings.py')"` |
| P33 | pip check | 0 | `"$(runj 'docker compose exec -T backend pip check')"` |
| P34 | ヒアドキュメント psql 読み取り | 0 | `"$(runj "docker compose exec -T db psql -U postgres learning_app <<'EOF'${NL}SELECT count(*)${NL}FROM problems_problem;${NL}\\dt${NL}EOF")"` |
| P35 | git -C status | 0 | `"$(runj 'git -C . status')"` |
| P36 | docker compose logs | 0 | `"$(runj 'docker compose logs --tail=50 backend')"` |
| P37 | パイプで出力を絞る | 0 | `"$(runj 'docker compose exec -T backend python -m pytest -q 2>&1 \| tail -5')"` |
| P38 | npm test | 0 | `"$(runj 'docker compose exec -T frontend npm test -- --watchAll=false')"` |

**(G) 偽合格の防止**

| # | 内容 | 期待値 | テストの記述 |
|---|---|---|---|
| G0 | 複製に置換が入った | YES | `"$( (! cmp -s "$GUARD" "$BROKEN_D") && (! cmp -s "$GUARD" "$BROKEN_X") && (! cmp -s "$GUARD" "$BROKEN_C") && (! cmp -s "$GUARD" "$BROKEN_H") && echo YES \|\| ec` |
| G1 | 危険判定を外すと A10 素通し | 0 | `"$(rungj "$BROKEN_D" "$M flush --noinput")"` |
| G2 | 実体では A10 を止める | 2 | `"$(runj "$M flush --noinput")"` |
| G3 | 外部判定を外すと X1 素通し | 0 | `"$(rungj "$BROKEN_X" "$M shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")"` |
| G4 | 実体では X1 を確認 | ASK | `"$(runj "$M shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")"` |
| G5 | 許可リストを外すと C7 素通し | 0 | `"$(rungj "$BROKEN_C" 'docker compose exec backend some_unknown_cmd --flag')"` |
| G6 | 実体では C7 を確認 | ASK | `"$(runj 'docker compose exec backend some_unknown_cmd --flag')"` |
| G7 | hard を外すと H4 は確認止まり | ASK | `"$(rungj "$BROKEN_H" "DANGER_OK=1 $RM /*")"` |
| G8 | 実体では H4 を止める | 2 | `"$(runj "DANGER_OK=1 $RM /*")"` |

<!-- 行数: 172（A は 2 通りずつ数えると 242 ケース） -->

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_pretooluse_container_guard.sh
bash scripts/claude/tests/test_settings_permissions.sh
bash scripts/claude/tests/test_pretooluse_push_guard.sh
bash scripts/claude/tests/test_pretooluse_checkout_guard.sh
bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
bash scripts/claude/tests/test_adversarial_trigger.sh
python3 -m json.tool .claude/settings.json
! grep -qF "Bash(git merge *)" .claude/settings.json
! grep -qF "Bash(git reset *)" .claude/settings.json
! grep -qF "Bash(git cherry-pick *)" .claude/settings.json
! grep -qF "Bash(docker compose exec" .claude/settings.json
! grep -qF "Bash(docker-compose exec" .claude/settings.json
! grep -qF "Bash(docker compose run *)" .claude/settings.json
! grep -qF "Bash(docker compose down *)" .claude/settings.json
! grep -qF "Bash(docker-compose run *)" .claude/settings.json
! grep -qF "Bash(docker-compose down *)" .claude/settings.json
grep -qF "Bash(git rebase *)" .claude/settings.json
grep -qF "Bash(psql *)" .claude/settings.json
grep -qF "Bash(rm *)" .claude/settings.json
grep -qF "Bash(mv *)" .claude/settings.json
grep -qF "Bash(cp *)" .claude/settings.json
grep -qF "Bash(chmod *)" .claude/settings.json
grep -qF "Bash(chown *)" .claude/settings.json
! grep -qF "Write(" .claude/settings.json
grep -qF "redis-cli FLUSHALL" docs/runbooks/danger-ops.md
grep -qF "manage.py flush" docs/runbooks/danger-ops.md
grep -qF "loaddata" docs/runbooks/danger-ops.md
grep -qF "DANGER_OK=1 を付けても" docs/runbooks/danger-ops.md
grep -qF "見張りを避ける書き方" docs/runbooks/danger-ops.md
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
bash -n scripts/claude/tests/test_pretooluse_container_guard.sh
bash -n scripts/claude/tests/test_settings_permissions.sh
```

## 実施記録

### 計画時の偽合格チェック（2026-10-16・実装前）
TC-07・TC-08・TC-09 は「違反がある状態で不合格になる」ことを、実装前のファイルに対して実行して確かめた。TC-01 と TC-11 は、対象のテストファイルがまだ無いので、実装前は必ず不合格（ファイル不在）になる。TC-01 の偽合格の防止は、(G) で実装時に確かめる。

実行: 上の決定論ゲートを 1 行ずつ実行（`! grep` は code-review.sh の `run_one_gate` と同じく、一致なし＝合格・それ以外＝不合格として扱う）。

| 対象 | 実装前の結果 | 判断 |
|---|---|---|
| TC-01（container テスト）・TC-11（その構文） | exit 127（ファイル不在） | 想定どおり（実装前） |
| TC-02〜TC-05（既存テスト 4 本） | exit 0（push 87・checkout 14・worktree 27・adversarial 40） | ベースライン。ステップ 2 で TC-02・TC-03 の期待値を変える |
| TC-06（JSON 構文） | exit 0 | 実装前も合格（構文を壊さないことの回帰確認） |
| TC-07 のうち「外した行が無い」9 行 | すべて不合格（exit 1。ask 9 行と exec の allow がまだある） | 違反を検出できる（偽合格でない）。2026-10-16 の計画レビュー（Warning 1）を受け、exec の確認を前方一致の 2 行にまとめ直した。まとめ直した 2 行も、実装前は不合格（exit 1）であることを再実行で確認（下の追記） |
| TC-07 のうち「残す行がある」7 行 | すべて exit 0 | 実装後も合格のはず。行を消せば不合格になる（存在の判定） |
| TC-08（`Write(` が無い） | 不合格（exit 1。`Write(` が 10 行ある） | 違反を検出できる |
| TC-09（danger-ops.md の 5 語句） | すべて不合格（exit 1。まだ追記していない） | 違反を検出できる |
| TC-10（guard の構文） | exit 0 | 回帰確認 |

追記（2026-10-16・計画レビュー後）: exec の確認を `! grep -qF "Bash(docker compose exec" .claude/settings.json` と `! grep -qF "Bash(docker-compose exec" .claude/settings.json` の 2 行にまとめ直し、ゲート全行を再実行した。この 2 行は実装前は exit 1（不合格）で、ほかの行の結果も上の表と同じだった。

### 実装後（2026-10-16・/implement ステップ 2〜5）
決定論ゲート全 30 行を 1 行ずつ実行し、**すべて exit 0**。

| TC | 結果 |
|---|---|
| TC-01 `test_pretooluse_container_guard.sh` | pass=118 fail=0（(A) 32 件×2 通り・(H) 3・(X) 11・(F) 10・(P) 25・(G) 5） |
| TC-02 `test_pretooluse_push_guard.sh` | pass=87 fail=0（DOK1〜3・P6・P7・P23・P24・P26・P31 は `runj` で ASK） |
| TC-03 `test_pretooluse_checkout_guard.sh` | pass=14 fail=0（G7 は `runj` で ASK） |
| TC-04 `test_pretooluse_worktree_guard.sh` | pass=27 fail=0（A19 は exit 2 のまま） |
| TC-05 `test_adversarial_trigger.sh` | pass=40 fail=0 |
| TC-06〜TC-11 | すべて exit 0 |
| TC-12 | 未実施（I146 のマージ後・ステップ 6） |

- 実装中の気づき: 初回の実行で TC-01 の F6 が不合格（期待 2・実際 ASK）。テストのコマンドが `/app/docs/` でなく `/app/` を指していて、`backend/` 側のテスト用ファイル（中身はメール送信）が読まれていた。テストを正しいパスに直し、読み替えが設計どおり動いていることを確認した。
- 実装中に見つけた穴: 既存の DOK3（`DANGER_OK=1 eval "git push --force origin x"`）が、先頭の `DANGER_OK=1` のせいで `eval` の検出をすり抜け、確認なしで通っていた。判定を `DANGER_OK=1` を外したコマンドで行うように直し、DOK3 は ASK になった（計画書 4-2(1) に追記）。

### 設計変更後（2026-10-16・敵対的レビュー第 1 周への対応・計画書 0 章）
決定論ゲート全 32 行を 1 行ずつ実行し、**すべて exit 0**。

| TC | 結果 |
|---|---|
| TC-01 `test_pretooluse_container_guard.sh` | pass=242 fail=0（作り直し。(A) 70 件×2 通り・(H) 4・(X) 20・(S) 7・(C) 12・(F) 12・(P) 38・(G) 9） |
| TC-13 `test_settings_permissions.sh` | pass=5 fail=0（後退を注入した 4 つの複製がすべて不合格になることを含む） |
| TC-02〜TC-05 | push 87・checkout 14・worktree 27・adversarial 40（すべて fail=0） |
| TC-06〜TC-11 | すべて exit 0 |

- 作り直しの途中で見つけた誤り: `python -W ... -m pytest` の `-W` を読み飛ばす処理が `-m` まで読み飛ばし、pytest が「安全と確かめられない」扱いになっていた（P1・P25 が ASK）。インタプリタのオプションだけを読み飛ばすように直した。
- 新しい方式で期待値が変わったケース: WHERE 付きの DELETE（旧 P11 → C8）と、存在しないファイルの流し込み（F5）は、コンテナ内で安全と確かめられないため ASK にした（計画書 0-1 の 4.）。
