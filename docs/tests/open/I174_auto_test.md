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
| TC-01 | 新規 `scripts/claude/tests/test_pretooluse_container_guard.sh`（下の TC-01 のケース表を全件） | exit 0（最終行 `pass=N fail=0`） | AC-4〜AC-9 | 2・3 |
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

### TC-01 のケース表（`test_pretooluse_container_guard.sh` に全件入れる）

コンテナ名は `docker-compose.yml` の自動命名（`study-app-multitenant-<サービス>-1`）に合わせる。`...` は直前の行と同じ書き出し（`docker compose exec -T backend python manage.py`）の省略。

**(A) 止める（期待値 2）。DANGER_OK=1 を前置すると ASK（各行を 2 通りで確かめる）**

| # | コマンド | 理由 |
|---|---|---|
| A1 | `docker compose exec -T db psql -U postgres -c "DROP DATABASE migrate_check;"` | 先頭の DROP（既存の見逃しの再現） |
| A2 | `docker compose exec -T db psql -U postgres learning_app -c "TRUNCATE problems_problem;"` | 先頭の TRUNCATE |
| A3 | `docker compose exec -T db psql -U postgres learning_app -c "DELETE FROM problems_problem;"` | WHERE なしの DELETE |
| A4 | `docker compose exec -T db psql -U postgres -c 'DROP DATABASE x;'` | 単一引用符（既存の見逃しの再現） |
| A5 | `docker compose exec -T db psql -U postgres learning_app -c "UPDATE problems_problem SET is_public=false;"` | WHERE なしの UPDATE |
| A6 | `docker compose exec -T db dropdb -U postgres learning_app` | dropdb |
| A7 | `docker compose exec -T db psql -U postgres learning_app < dump.sql` | ダンプの流し込み（`<` 単独） |
| A8 | `docker compose exec -T db psql -U postgres learning_app -f /tmp/x.sql` | SQL ファイルの流し込み |
| A9 | `docker compose exec -T db pg_restore --clean -d learning_app /tmp/x.dump` | pg_restore --clean |
| A10 | `docker compose exec -T backend python manage.py flush --noinput` | DB 全消去 |
| A11 | `... sqlflush` | DB 全消去 |
| A12 | `docker compose exec backend python manage.py migrate problems zero` | 巻き戻し（zero） |
| A13 | `... migrate problems 0003_previous` | 巻き戻し（移動先指定） |
| A14 | `... loaddata fixtures.json` | 上書き |
| A15 | `docker compose exec -T redis redis-cli FLUSHALL` | Redis 全消去 |
| A16 | `docker compose exec -T redis redis-cli flushdb` | Redis 全消去（小文字） |
| A17 | `... shell -c "from problems.models import Problem; Problem.objects.all().delete()"` | shell 内の削除 |
| A18 | `... shell -c "Problem.objects.filter(subject_id=1).update(is_public=False)"` | QuerySet の一括更新 |
| A19 | `... shell -c "Problem.objects.bulk_update(ps, ['title'])"` | 一括更新 |
| A20 | `... shell -c "from django.core.management import call_command; call_command('flush', interactive=False)"` | call_command の flush |
| A21 | `... shell -c "from django.db import connection; connection.cursor().execute('DELETE FROM problems_problem')"` | 文字列リテラルの破壊的 SQL |
| A22 | `docker-compose run --rm backend rm -rf /app/tmp` | ルート以外の rm -rf（通常の危険操作） |
| A23 | `rm -rf node_modules/.cache` | 相対パスの rm -rf（既存どおり） |
| A24 | `rm -rf /tmp/claude-1000/xyz` | 絶対パスの rm -rf（既存では解除不能だった。DANGER_OK=1 で ASK になることが再発防止） |
| A25 | `docker exec study-app-multitenant-db-1 psql -U postgres -c "DROP DATABASE learning_app;"` | 書き出し違い（docker exec） |
| A26 | `docker exec study-app-multitenant-backend-1 python manage.py flush --noinput` | 書き出し違い（docker exec） |
| A27 | `docker exec study-app-multitenant-redis-1 redis-cli FLUSHALL` | 書き出し違い（docker exec） |
| A28 | `backend/.venv/bin/python backend/manage.py flush --noinput` | ホストで直接実行 |
| A29 | `docker compose exec backend sh -c "python manage.py flush --noinput"` | `sh -c` で包んだ形 |
| A30 | `python3 -c "import django; from problems.models import Problem; Problem.objects.all().delete()"` | `python -c` のコード |
| A31 | `git reset --hard HEAD~1` | 既存の危険操作（回帰） |
| A32 | `docker compose down -v` | 既存の危険操作（回帰） |

**(H) 常に止める（期待値 2。DANGER_OK=1 を前置しても 2）**

| # | コマンド |
|---|---|
| H1 | `rm -rf /` |
| H2 | `rm -rf /*` |
| H3 | `DANGER_OK=1 rm -rf /` |

**(X) 外部送信（期待値 ASK）**

| # | コマンド |
|---|---|
| X1 | `... shell -c "from django.core.mail import send_mail; send_mail('s','b','a@example.com',['x@example.com'])"` |
| X2 | `... shell -c "from studylogs.tasks import send_study_reminders_task; send_study_reminders_task.delay()"` |
| X3 | `... shell -c "from rest_framework.test import APIClient; APIClient().post('/api/auth/register/', {}, HTTP_HOST='localhost')"` |
| X4 | `... shell -c "from rest_framework.test import APIClient; APIClient().post('/api/auth/password-reset/', {}, HTTP_HOST='localhost')"` |
| X5 | `docker compose exec -T celery celery -A core call studylogs.tasks.send_study_reminders_task` |
| X6 | `docker compose exec backend sh -c "python manage.py shell -c 'from django.core.mail import send_mail; send_mail(1,2,3,[4])'"` |
| X7 | `docker compose exec -T backend python manage.py generate_ai_problems` |
| X8 | `... shell -c "from rest_framework.test import APIClient; APIClient().post('/api/problems/generate_ai/', {})"` |
| X9 | `... shell -c "from rest_framework.test import APIClient; APIClient().post('/api/problems/generate_adaptive/', {})"` |
| X10 | `... shell -c "from problems.ai_generator import AIQuestionGenerator; AIQuestionGenerator().generate_question(None)"` |
| X11 | `docker exec study-app-multitenant-backend-1 python manage.py generate_ai_problems` |

**(F) 実行ファイルの中身（テスト内で一時ファイルを作る。期待値は表のとおり）**

| # | ファイルの中身 | コマンド | 期待値 |
|---|---|---|---|
| F1 | `from problems.models import Problem` と `Problem.objects.all().delete()` | `docker compose exec -T backend python manage.py shell < <一時ファイルのホストの絶対パス>` | 2 |
| F2 | 同上 | `... shell <<一時ファイル>`（`<` が付着した形） | 2 |
| F3 | `from django.core.mail import send_mail` と `send_mail(1,2,3,[4])` | `python3 <一時ファイル>.py` | ASK |
| F4 | `print(1)` | `docker compose exec -T backend python manage.py shell < <一時ファイル>` | 0 |
| F5 | 存在しないパス | `docker compose exec -T backend python manage.py shell < /nonexistent/i174.py` | 0（stderr に「中身を確認できませんでした」を含む） |
| F6 | リポジトリの `docs/` 配下に置いた一時ファイル（中身は F1 と同じ・テストの最後に削除） | `docker compose exec -T backend python /app/docs/<相対パス>` | 2（`/app/docs/` → `docs/` の読み替え） |
| F7 | リポジトリの `backend/` 配下に置いた一時ファイル（中身は F3 と同じ・テストの最後に削除） | `docker compose exec -T backend python /app/<相対パス>` | ASK（`/app/` → `backend/` の読み替え） |
| F8 | 中身に `manage.py flush` を含むホストのシェルスクリプト | `bash <一時ファイル>.sh` | 0（ホストの bash スクリプトは中身を見ない） |
| F9 | — | `python3 scripts/claude/hooks/pretooluse_guard.py` | 0（`scripts/claude/` は中身を見ない。guard 自身が判定パターンを含むため） |

**(P) 素通し（期待値 0）**

| # | コマンド | 確かめること |
|---|---|---|
| P1 | `docker compose exec -T backend python -m pytest -q` | テスト |
| P2 | `docker compose exec -T backend ruff check .` | lint |
| P3 | `docker compose exec -T backend pip-audit -r requirements.txt` | 監査 |
| P4 | `docker compose exec -T frontend npm audit --audit-level=critical --omit=dev` | 監査 |
| P5 | `docker compose exec -T backend python manage.py makemigrations --check --dry-run` | 確認 |
| P6 | `docker compose exec -T backend python manage.py migrate --noinput` | 通常の migrate |
| P7 | `docker compose exec -T backend python manage.py migrate problems` | 位置引数 1 つ |
| P8 | `docker compose exec -T backend python manage.py migrate --database default problems` | 値を取るオプションを数えない |
| P9 | `docker compose exec -T db psql -U postgres learning_app -c "\dt"` | 読み取りの psql |
| P10 | `docker compose exec -T db psql -U postgres -c "CREATE DATABASE migrate_check;"` | CREATE |
| P11 | `docker compose exec -T db psql -U postgres learning_app -c "DELETE FROM problems_problem WHERE id=1;"` | WHERE 付きの DELETE |
| P12 | `... shell -c "from problems.models import Problem; print(Problem.objects.filter(subject_id=1).count())"` | 読み取りの shell |
| P13 | `... shell -c "d={}; d.update({'a':1}); print(d)"` | `dict.update(` |
| P14 | `... shell -c "u=User.objects.get(pk=1); u.set_password('x'); u.save()"` | 1 件だけの更新 |
| P15 | `... shell -c "from rest_framework.test import APIClient; APIClient().post('/api/auth/login/', {}, HTTP_HOST='localhost')"` | ログイン |
| P16 | `... shell -c "from rest_framework.test import APIClient; APIClient().post('/api/auth/password-reset-confirm/', {})"` | 再設定の確定 |
| P17 | `... shell -c "from rest_framework.test import APIClient; APIClient().get('/api/problems/')"` | 一覧の取得 |
| P18 | `docker compose exec -T redis redis-cli ping` | Redis の確認 |
| P19 | `docker compose exec -T redis redis-cli KEYS 'rl:*'` | Redis の確認 |
| P20 | `docker compose exec -T backend python manage.py dumpdata problems` | 書き出し |
| P21 | `grep -n "rm -rf" scripts/claude/tests/test_pretooluse_checkout_guard.sh` | grep の検索文字列（既存の止めすぎの再現） |
| P22 | `grep -rn send_mail backend` | 外部送信の語の検索 |
| P23 | `grep -rn "manage.py flush" docs` | 危険操作の語の検索 |
| P24 | ヒアドキュメントで `rm -rf /app` を本文に含むファイルを書く `cat > /tmp/x.sh <<'EOF'`（本文 2 行目に `rm -rf /app`） | ヒアドキュメントの中身（既存の止めすぎの再現） |
| P25 | `docker compose exec -T backend python -m pytest -q problems/tests/test_I103_cross_org_create.py` | テスト（ファイル指定） |

**(G) 偽合格の防止（既存の FALSEGREEN と同じ方式）**

| # | 内容 | 期待値 |
|---|---|---|
| G1 | guard を `sed` で複製し、`reasons += _segment_danger(toks, ctr)` を `pass` に置き換えたもので A10 を実行（G0 で置換が入ったことも確認） | 0（判定を外すと素通しになる） |
| G2 | 実体の guard で A10 を実行 | 2 |
| G3 | 複製で `_external_reasons(cmd)` の呼び出しを `[]` に置き換えたもので X1 を実行 | 0 |
| G4 | 実体の guard で X1 を実行 | ASK |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_pretooluse_container_guard.sh
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
