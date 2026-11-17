# I492 計画書: 古い学習記録の表（StudyLog など）の片付け

## 基本情報
- **計画書ID**: plan_I492
- **関連イシュー**: #492
- **Draft PR**: #571
- **作成根拠資料**: docs/issues/open/I492.md（GitHub #492 の本文の写し・grill-me 済み）
- **実装後評価**: docs/reviews/open/I492_review.md
- **作成日**: 2026-11-18

## 1. 背景/目的
- I473 で学習の数字の出どころをクイズの答えの記録（`QuizAnswer`）に 1 本化した。古い学習記録の表（`StudyLog`・`DailyStudySummary`・`StudyGoal`）と解答の試行の記録（`ProblemAttempt`）は、画面から書き込む経路が無いのに、モデル・API・管理画面・定期処理が残っている。新しい処理の材料にされるおそれと、保守の手間がある
- 目的: 読み手を移し（または消し）、コードを消し、`SpacedRepetitionReview.study_session` の列を外し、最後に 4 つのテーブルを消す（Danger Ops）。1 つのイシューで行う（grill-me で確定）

### 調査結果
- **原因の概要**: 学習記録の本体が `QuizAnswer` に移ったのに、古い表とそれを読むコードが片付けられずに残っている
- **詳細**:
  - I473 の計画は「表の削除は別イシュー（retro で起票の要否を決める）」としたが、retro で決め損ねた（起票の漏れ）。#466・#488 で統計画面と間違い分析の読み手は移し終えた（2026-11-17 に grep で確認。`backend/dashboard/`・`backend/studylogs/mistake_analysis.py` は古い表を読まない）
  - 残っている読み手・書き手（テストとマイグレーションの外・2026-11-18 の develop〔`4c129c3b`〕で grep）:
    - `backend/studylogs/tasks.py:36`・`:79`: `update_daily_analytics_task`・`send_study_reminders_task` が「最近学習した人」を `study_logs__started_at`（`StudyLog` の逆向きの関連）で判定
    - `backend/studylogs/tasks.py:153-`: `export_user_data_task`（呼び出し元なし・定期処理に未登録・件数を返すだけ）
    - `backend/core/tasks.py:106-`: `generate_system_report_task`（呼び出し元なし・定期処理に未登録）
    - `backend/studylogs/views.py:413-422`: `SpacedRepetitionViewSet.submit_review` が進行中の `StudyLog` を読み、`SpacedRepetitionService.review_card`（`backend/studylogs/services.py:149-`）の `study_session` に渡す
    - `backend/studylogs/views.py:26-347`: `StudyLogViewSet`・`StudyStatisticsViewSet`・`StudyGoalViewSet`、`backend/studylogs/urls.py:9-11` の登録、`backend/studylogs/serializers.py` のシリアライザ、`backend/studylogs/admin.py` の 4 モデルの管理画面
    - `backend/studylogs/models.py:42-147`: 4 モデルと `StudyLogQuerySet`・`ProblemAttemptQuerySet`。`SpacedRepetitionReview.study_session`（`:247`・`on_delete=SET_NULL`）、`ProblemAttempt.study_log`（`:103`・`on_delete=CASCADE`）
  - 画面・E2E からの呼び出し: `frontend/src`・`e2e` に `study/logs`・`study/statistics`・`study/goals`・`submit_review` の呼び出しは無い。OpenAPI（`backend/openapi.yaml`）・画面の型（`frontend/src/types/api/schema.d.ts`）にも 3 つの経路は無い（契約の外。作り直し不要）
  - テスト: `backend/core/tests/test_I446_cross_api_tenant_isolation.py`（経路の表・`StudyLog`/`StudyGoal`/`DailyStudySummary` の作成）・`backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`（学習記録の API と `submit_review` の `study_session`）・`backend/studylogs/tests/test_I455_org_scoped_querysets.py`（`SPECS` の `StudyLog`・`ProblemAttempt`、`OrgScopedQuerySet(model=StudyLog)`）・`backend/dashboard/tests/test_I473_overview.py:308`（`StudyLog` を 1 行作るだけの名残）・`backend/core/tests/test_I466_celery_schedule.py`（定期処理の登録のタスクが実在するか）
  - 安全装置の中の名前: `scripts/claude/hooks/pretooluse_guard.py:770` が `send_study_reminders_task` を外部送信の語として持つ（`scripts/claude/tests/test_pretooluse_container_guard.sh` も）。安全装置は変えない（9 を参照）
- **開発の DB（このワークツリー専用のコンテナ `app-1-*`・2026-11-17 に読むだけで数えた）**: `StudyLog` 0・`DailyStudySummary` 0・`StudyGoal` 0・`ProblemAttempt` 0・`SpacedRepetitionReview` 6（`study_session` が入っているもの 0）・`QuizAnswer` 217。本番環境はまだ無い
- **環境の前提**: `docker compose ps` で `app-1-backend-1`・`app-1-db-1` が動いている（2026-11-18 に確認）。backend のコンテナは `./backend` を `/app` につなぎ、起動のたびに `python manage.py migrate` を流す（`docker-compose.yml:68-70`）。つまり、マイグレーションのファイルを足した後にコンテナを起こし直すと、承認の前に開発の DB のテーブルが消える（8 の R1）
- **スパイク（未知のリスクの実証・成立）**: pytest は `--no-migrations`（`backend/pytest.ini`）で、テストの DB はモデルから作られる。マイグレーションの流し・戻しをテストで確かめられるかを、コンテナの一時フォルダに置いた使い捨てのテスト（手元のファイルは変えていない）で確かめた。`settings.MIGRATION_MODULES = {}` で本物のマイグレーションを読み、`connection.schema_editor()` で「列の削除＋4 モデルの削除」の操作を `apply`→`unapply` した。結果: `apply` で 4 テーブルと `study_session_id` の列が消え、`SpacedRepetitionReview` の件数（`StudyLog` を指す行を含む）は変わらない。`unapply` でテーブルと列が戻り、行を入れ直せる。テストの `atomic`（PostgreSQL は DDL も取り消せる）の中で動き、ほかのテストの DB に残らない。行を入れた後に DDL を流す前に `SET CONSTRAINTS ALL IMMEDIATE` が要る（遅延の外部キーの検査が残ると `ALTER TABLE` が失敗するため）→ 1 passed（2026-11-18）

## 2. 受け入れ条件
（イシューの受け入れ条件と同じ。番号は計画の中の参照用）
- [ ] AC1: `StudyLog`・`DailyStudySummary`・`StudyGoal`・`ProblemAttempt` を読む・書くコードが、テストとマイグレーション以外に無い（→ TC-01・TC-02）
- [ ] AC2: `send_study_reminders_task`・`export_user_data_task`・`generate_system_report_task` が無く、`backend/core/celery.py` に `send-study-reminders` の登録が無い（→ TC-03・TC-04）
- [ ] AC3: `update_daily_analytics_task` が、直近 7 日にクイズに答えた人・復習をした人を対象にする（→ TC-05）
- [ ] AC4: 間隔反復の復習の提出（`submit_review`）が今までどおり動く（→ TC-06）
- [ ] AC5: `SpacedRepetitionReview` の行が、列を外す・テーブルを消す前後で 1 件も減らない（→ TC-07）
- [ ] AC6: 消した API が 404 になり、#446 の横断テストが通る（→ TC-08・TC-09）
- [ ] AC7: テーブルの削除の前に、4 つの表の件数を記録し、バックアップを取り、復元の手順を試し、承認の記録がある。削除のマイグレーションは逆向き（戻す）も動く（→ TC-07・手動 M1〜M3・9 の Danger Ops）
- [ ] AC8: 既存のテスト・E2E に退行が無い（→ TC-10）

## 3. 影響範囲
- Backend: `backend/studylogs/`（`models.py`・`views.py`・`urls.py`・`serializers.py`・`services.py`・`admin.py`・`tasks.py`・`migrations/0002_*.py`〔新規〕・`tests/`）・`backend/core/tasks.py`・`backend/core/celery.py`・`backend/core/tests/test_I446_cross_api_tenant_isolation.py`・`backend/core/tests/test_I466_celery_schedule.py`・`backend/dashboard/tests/test_I473_overview.py`
  - 変えない: `backend/dashboard/` の本体・`backend/studylogs/mistake_analysis.py`（#488・#466 で移行済み）・`backend/core/middleware.py:102`（`/api/study/` の操作名 `'study_session'` は記録用の文字で、`/api/study/spaced-repetition/` などに引き続き使う）
- Frontend: なし（呼び出し・型に 3 つの経路が無いことを確認済み）
- DB: `studylogs_spacedrepetitionreview.study_session_id` の列の削除、`studylogs_studylog`・`studylogs_dailystudysummary`（と多対多の `studylogs_dailystudysummary_subjects_studied`）・`studylogs_studygoal`・`studylogs_problemattempt` のテーブルの削除（Danger Ops）
- Config/Infra: Celery の定期処理の登録から `send-study-reminders` を外す。依存ファイル（`requirements*.txt`・`package*.json`）・Dockerfile・`docker-compose.yml` は変えない

## 4. 変更点一覧（具体）

### 修正アプローチ
読み手を先に移す（または消す）→ API・管理画面を消す → モデルを消してマイグレーションを足す、の順に進める。モデルを消すと参照が import の失敗になるので、モデルの削除は最後のステップで、参照がすべて無くなってから行う。データを書き換えるマイグレーションは無い（消す表は空。`SpacedRepetitionReview` の行は列を外すだけで残る）。

| ファイル | 関数・クラス | 変更内容 |
|---|---|---|
| `backend/studylogs/tasks.py` | `update_daily_analytics_task` | 対象の利用者を `Q(quiz_sessions__answers__answered_at__gte=active_since) \| Q(sr_reviews__reviewed_at__gte=active_since)` の `.distinct()` にする（`active_since` は今のまま `timezone.now() - timedelta(days=7)`）。ほかは変えない |
| `backend/studylogs/tasks.py` | `send_study_reminders_task`・`export_user_data_task` | 関数ごと消す。使わなくなる import（`send_mail`・`settings`・`LearningAnalytics`・`StudyLog`）を消す |
| `backend/core/tasks.py` | `generate_system_report_task` | 関数ごと消す |
| `backend/core/celery.py` | `app.conf.beat_schedule` | `'send-study-reminders'` の項目と、その上のコメントを消す |
| `backend/studylogs/views.py` | `SpacedRepetitionViewSet.submit_review` | 進行中の `StudyLog` を読む 2 行と、`review_card(..., study_session=...)` の引数を消す |
| `backend/studylogs/services.py` | `SpacedRepetitionService.review_card` | 引数 `study_session` と、`SpacedRepetitionReview.objects.create(... study_session=...)` の指定を消す。`StudyLog` の import を消す |
| `backend/studylogs/views.py` | `StudyLogViewSet`・`StudyStatisticsViewSet`・`StudyGoalViewSet` | クラスごと消す。使わなくなる import（シリアライザ・`Prefetch`・`Sum`・`datetime` など、ruff の F401 で決まるもの）を消す |
| `backend/studylogs/urls.py` | `router.register` | `logs`・`statistics`・`goals` の 3 行と import を消す |
| `backend/studylogs/serializers.py` | `StudyLogSerializer`・`StudyLogCreateSerializer`・`StudyLogEndSerializer`・`DailyStudySummarySerializer`・`StudyGoalSerializer`・`StudyStatisticsSerializer`・`SubjectStatisticsSerializer` | クラスごと消す（ほかから使われていないことは `grep` で確認済み）。モデルの import を消す |
| `backend/studylogs/admin.py` | `StudyLog`・`DailyStudySummary`・`ProblemAttempt`・`StudyGoal` の管理画面 | 4 つの登録を消す（ほかの登録は無い） |
| `backend/studylogs/models.py` | `StudyLogQuerySet`・`ProblemAttemptQuerySet`・`StudyLog`・`DailyStudySummary`・`ProblemAttempt`・`StudyGoal`・`SpacedRepetitionReview.study_session` | 4 モデルと 2 つの QuerySet と、`study_session` の列を消す |
| `backend/studylogs/migrations/0002_remove_legacy_study_logs.py`（新規） | `Migration` | 依存: `('studylogs', '0001_initial')`。操作は順に `RemoveField('spacedrepetitionreview', 'study_session')`→`DeleteModel('ProblemAttempt')`→`DeleteModel('DailyStudySummary')`→`DeleteModel('StudyGoal')`→`DeleteModel('StudyLog')` の 5 つだけ。`makemigrations studylogs` で作り、中身を上の 5 つと照らす（Danger Ops） |
| `backend/studylogs/tests/test_I492_remove_legacy_study_logs.py`（新規） | TC-05〜TC-08 | 下の 6 のとおり |
| `backend/core/tests/test_I466_celery_schedule.py` | `REMOVED` | `"send-study-reminders"` を足す |
| `backend/core/tests/test_I446_cross_api_tenant_isolation.py` | 経路の表・`world` の作成・失敗の注入の表 | `api/study/logs/`・`statistics`・`goals` の行（`:212-227`・`:273`）と、`log`・`goal` の物の作成（`:64-65`・`:351-353`）、`DailyStudySummary`・`StudyLog` を作るテスト（`:409-419` のテスト）、`StudyGoalViewSet` の失敗の注入（`:636-642`）を消す。消した後も `test_route_table_matches_urlconf` が URL の設定と表の一致を確かめる |
| `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py` | 学習記録の API のテスト・`test_submit_review_does_not_link_other_org_study_log` | 消した API のテスト（`StudyLog`・`DailyStudySummary` を作るもの）と、`study_session` を確かめる TC-04b を消す（`study_session` の列そのものが無くなる） |
| `backend/studylogs/tests/test_I455_org_scoped_querysets.py` | `SPECS`・`test_base_without_subject_paths_raises` | `SPECS` の `"StudyLog"`・`"ProblemAttempt"` を消す。`OrgScopedQuerySet(model=StudyLog)` を `OrgScopedQuerySet(model=LearningAnalytics)`（境界の決まりを持たないモデル）に替える。`:277-290` の文字列（コメントの検査の入力の例文で、コードではない）はそのまま |
| `backend/dashboard/tests/test_I473_overview.py` | `test_recommendations` | `StudyLog` を 1 行作る名残の行（`:308`）と import を消す（おすすめの集計は `StudyLog` を読まない） |

## 5. 実装手順（ステップ）
1. **開発の DB の件数の記録とバックアップ**（Danger Ops の準備・コードを変える前に行う。ステップ 2 以降の前提）
   - 4 モデルと `SpacedRepetitionReview`（全体と `study_session` が入っている行）の件数を読むだけで数え、レビュー文書の「## 自律判断の記録」と手動テスト M1 に書く → 手動 M1
   - `docker compose exec -T backend python manage.py dumpdata studylogs.StudyLog studylogs.DailyStudySummary studylogs.StudyGoal studylogs.ProblemAttempt --output /tmp/i492_legacy_backup.json` で古いコードのまま書き出し、`docker compose cp backend:/tmp/i492_legacy_backup.json .evidence/I492/legacy_backup.json` で手元の gitignore 済みの場所に置く。`study_session` が入っている `SpacedRepetitionReview` が 1 件以上あれば、`(id, study_session_id)` の組も同じ場所に書き出す（0 件なら書かない）→ 手動 M2
   - 見張りが「DB の中身をまとめて出す操作」「コンテナからの取り出し」として承認画面を出すことがある（出たら許可を求める）
2. **読み手を移す・消す**（ステップ 1 の後。モデルはまだ残す）
   - TC-05（`update_daily_analytics_task` の対象）を先に書き、今のコードで落ちることを確かめてから、`backend/studylogs/tasks.py` の判定を直す → TC-05
   - `send_study_reminders_task`・`export_user_data_task`・`generate_system_report_task` と `send-study-reminders` の登録を消し、`test_I466_celery_schedule.py` の `REMOVED` に足す → TC-03・TC-04
   - `submit_review`・`review_card` から `study_session` を外す。TC-06 を足す → TC-06
3. **API・管理画面を消す**（ステップ 2 の後）
   - `views.py`・`urls.py`・`serializers.py`・`admin.py` から 3 つの ViewSet・7 つのシリアライザ・4 つの管理画面を消す。I446・I431 のテストの該当の行を消す。TC-08 を足す → TC-08・TC-09
4. **モデルを消し、マイグレーションを足す**（ステップ 3 の後。参照が無くなってから）
   - TC-07（マイグレーションの流し・戻し）を先に書く。`models.py` から 4 モデル・2 つの QuerySet・`study_session` を消し、`docker compose exec -T backend python manage.py makemigrations studylogs --name remove_legacy_study_logs` で `0002` を作る（ファイルを作るだけで、開発の DB には流さない）。中身が 4 の表の 5 つの操作だけであることを TC-07 が確かめる → TC-07
   - I455・I473 のテストを直す → TC-10
   - **開発の DB に `migrate` を流さない・コンテナを起こし直さない**（8 の R1）。流すのはマージの後（9 の Danger Ops）
5. **決定論ゲートを流す**（ステップ 4 の後）→ TC-01・TC-02（実装の前は不合格であることを記録済み）
- サービスの再起動: 不要（コードの削除は backend の自動の読み込み直しで反映される。マイグレーションはマージまで流さないので、コンテナを起こし直さない）

## 6. テスト計画
### 自動（詳細は `docs/tests/open/I492_auto_test.md`）
- テストの段の選び方: 定期処理の対象・API の 404・復習の提出は pytest の結合テスト（DB と API クライアントを使う）。マイグレーションは pytest の中で `schema_editor` を使う結合テスト（スパイクで成立を確かめた形）。コードの不在は決定論ゲートの `grep`。画面の変更が無いので Jest・E2E は足さない（CI の既存の E2E が退行を見る）
- TC-01: 4 モデルの名前がテストとマイグレーションの外に無い（決定論ゲート）
- TC-02: 逆向きの関連名（`study_logs__`・`daily_summaries`・`study_goals`・`problem_attempts`）と `study_session`（`backend/studylogs` の中）がテストとマイグレーションの外に無い（決定論ゲート）
- TC-03: 消した 3 つのタスクと `send-study-reminders` の名前がテストの外に無い（決定論ゲート）
- TC-04: 定期処理の登録に `send-study-reminders` が無く、登録したタスクがすべて実在する（`test_I466_celery_schedule.py`）
- TC-05: `update_daily_analytics_task` の対象の利用者（クイズの答え・復習・7 日の境目）
- TC-06: 自分のカードの `submit_review` が 201 と本文を返し、復習の記録が 1 件増える
- TC-07: マイグレーション `0002` の操作が 5 つだけで、流すと 4 テーブルと列が消えて `SpacedRepetitionReview` の件数が変わらず、戻すとテーブルと列が戻って行を入れ直せる（復元の手順の試し）
- TC-08: 消した経路が、ログインしていても 404
- TC-09: #446 の横断テスト（経路の表と URL の設定の一致を含む）が通る
- TC-10: CI の backend（pytest・ruff・bandit・`makemigrations --check`）・frontend・E2E がすべて通る
- 認可・組織の境界: 新しい API は無い。消した API の 404（TC-08）と、残る経路の横断テスト（TC-09）で見る。`update_daily_analytics_task` は利用者ごとに既存の `SpacedRepetitionService(user)` を呼ぶだけで、組織を越えた値を混ぜない（変えない）
- 再発防止: このイシューはバグ修正ではないので、再現のテストは無い。不在の決定論ゲート（TC-01〜TC-03）は、実装の前の今のコードで不合格（exit 1）になることを確かめ済み（2026-11-18）
### 手動（詳細は `docs/tests/open/I492_manual_test.md`）
- M1: 実装の前の開発の DB の件数の記録（Claude）
- M2: バックアップのファイルがあり、件数が M1 と合う（Claude）
- M3: 開発の DB に `0002` がまだ流れていない（`showmigrations studylogs` の `[ ] 0002_remove_legacy_study_logs`）・`manage.py check` が通る（Claude）
- 人の手動テストは無い（画面の変更が無い）。Danger Ops の承認は、マージ依頼のときにユーザーが PR に `danger-approved` を付けること（9）

## 7. ロールバック
- **マージ前**: PR を閉じる。開発の DB は `0002` を流していないので、何もしなくてよい
- **マージ後（開発の DB に `0002` が流れた後）**: 次の順で戻す（どれも Danger Ops。ユーザーの承認の後に `DANGER_OK=1` を付けて行う）
  1. I492 のコードのまま `docker compose exec -T backend python manage.py migrate studylogs 0001_initial`（4 テーブルが空で戻り、`study_session_id` の列が空〔NULL〕で戻る。TC-07 が同じ操作を確かめている）
  2. I492 の PR を戻す（revert の PR）
  3. 行を戻す: `docker compose exec -T backend python manage.py loaddata <.evidence/I492/legacy_backup.json をコンテナに送った場所>`（モデルが戻った後でないと読めない。開発の DB は 0 件なので、戻す行は無い）
  4. `study_session` の組を書き出していれば、その組で `study_session_id` を戻す（開発の DB は 0 件）
- 学習リマインダーのメールは、2 の revert で処理と登録が戻る

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: マイグレーションを足した後に backend のコンテナが起こし直されると、起動の `migrate` で、承認の前に開発の DB のテーブルが消える | ステップ 1 でコードを変える前にバックアップを取る。このイシューの中でコンテナを起こし直さない（画面の確かめも無い）。M3 で `0002` が流れていないことを確かめ、マージ依頼の直前（close）にも `showmigrations studylogs` を流し直して未適用であることをマージ依頼に書く。開発の DB はこのワークツリー専用のコンテナ（`app-1-db-1`）で、ほかのワークツリー・CI は別の DB を使う。万一流れても 4 つの表は 0 件で、7 の 1 でテーブルを戻せる | 回避 |
| R2: 消したモデルの逆向きの関連（`user.study_logs` など）を読むコードが残り、実行のときに落ちる | 逆向きの関連名もゲート（TC-02）で見る。モデルの名前の参照は import の失敗で CI が止める | 回避 |
| R3: マイグレーションのテスト（TC-07）が、ほかのテストの DB の形を変えたまま残す | テストを `django_db`（`atomic`）の中で動かす。PostgreSQL は DDL も取り消せるので、テストの終わりに元に戻る（スパイクで確認）。念のため `finally` で `apply` まで戻してから終える | 回避 |
| R4: `SpacedRepetitionReview` の行が、列の削除・テーブルの削除で消える（`study_session` の `SET_NULL`、`ProblemAttempt.study_log` の `CASCADE`） | 列の削除を先に置き、`ProblemAttempt` も一緒に消す（`CASCADE` で消える相手がいない）。TC-07 が `StudyLog` を指す行を含めて件数を比べる | 回避 |
| R5: 学習リマインダーのメールが届かなくなる | ユーザーの決定（grill-me・「メールはいったん不要」）。本番は無い。要るときは送る相手・文面を決め直して別イシュー | 受け入れ |
| R6: Celery の作業者に、消す前に積まれた `send_study_reminders_task` の依頼が残っていると、「登録されていないタスク」のエラーが 1 回ログに出る | 開発環境だけの一時的なもの。害は無い | 受け入れ |
| R7: 見張り（`scripts/claude/hooks/pretooluse_guard.py:770`）と、そのテストに `send_study_reminders_task` の名前が残る | 安全装置は変えない（止める条件 2）。残っても、無いタスクの名前に確認を出すだけで害は無い。retro で一覧（`docs/reviews/backlog/`）に Low として回す | 受け入れ |
| R8: `update_daily_analytics_task` の新しい判定（クイズの回・答えをたどる結合と `distinct`）が重くなる | 夜 2 時に 1 回だけ。7 日の範囲で絞る。今の利用者数（開発の DB の答え 217 件）では問題にならない | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 1〜4（読み手の移行・コードの削除・列の削除・テーブルの削除）を本イシューで全部行う。消す前の件数の記録・バックアップ・戻し方の確認・承認は省かない
- `StudyGoal` と `ProblemAttempt` も消す（目標は `UserSettings.daily_study_goal_minutes` に一本化）
- `export_user_data_task`・`generate_system_report_task` を消す。本当の書き出しは #570
- `send_study_reminders_task` と `send-study-reminders` の登録を消す。作り直しの起票はしない
- `update_daily_analytics_task` の対象は、直近 7 日に `QuizAnswer.answered_at` か `SpacedRepetitionReview.reviewed_at` がある人
- `submit_review` は `study_session` を渡さず、`review_card` の `study_session` 引数を消す

Claude が決めた（技術的な選択と理由）:
- マイグレーションは 1 本（`0002_remove_legacy_study_logs`）にし、列の削除を先、テーブルの削除を後に並べる — PostgreSQL ではマイグレーション 1 本が 1 つのトランザクションで、途中で失敗しても全部戻る。2 本に分けても戻し方は同じで、得るものが無い
- マイグレーションのテストは `schema_editor` で本物の `0002` を `apply`/`unapply` する（スパイクで成立） — pytest が `--no-migrations` のため、`MigrationExecutor` で流す形はテストの DB の記録と合わない
- 復元の手順の試しは、テストの DB で TC-07 が行う（テーブルと列を戻し、行を入れ直す）。開発の DB では試さない — 開発の DB の 4 つの表は 0 件で、試す操作（`migrate studylogs 0001_initial`・`loaddata`）はどちらも Danger Ops。同じスキーマの操作を TC-07 が毎回 CI で確かめる
- バックアップは `dumpdata`（JSON）で、古いコードのままステップ 1 で取る — モデルを消した後は `dumpdata` で書き出せない。戻すときもモデルが戻った後に `loaddata` で読む（7）
- 開発の DB への `0002` の適用は、マージの後のコンテナの起動の `migrate` に任せる。Claude は `DANGER_OK=1` の操作をしない（I539 と同じ） — 本番が無く、承認はマージ依頼のときの `danger-approved`（ユーザー）で記録に残る
- 不在の確かめは pytest でなく決定論ゲートの `grep` にする — 消したモデルを参照し直すと import の失敗で CI が止まるので、テストとして残し続ける価値は低い。一方、受け入れ条件 AC1 は「grep で確かめる TC」なので、review-gate で 1 回実走する
- 見張り（`pretooluse_guard.py`）の `send_study_reminders_task` は変えない — 安全装置そのものの変更になる（止める条件 2）。害が無いので一覧へ回す（R7）
- `submit_review` の `except Exception as e` で `str(e)` を応答に入れている箇所（規約 §7 に反する）は直さない — 本イシューの範囲（古い表の片付け）の外。retro で一覧（`docs/reviews/backlog/`）に回す
- `update_daily_analytics_task` の再試行・時間の上限（規約 §12）は変えない — 判定の 1 行を替えるだけで、タスクの作りは範囲の外
- 一覧 `docs/reviews/backlog/I223.md` B1〜B4・`docs/reviews/backlog/I224.md` F9（`FILE=-`）: 残す — どれもハーネスの事柄で、本イシューの変更点と関係が無い。実装対象のファイルに当たる行は無い

セキュリティ・BP の確認:
- 入力の検証: 新しい入力は無い。消すだけ
- 認証・認可: 新しい API・権限の変更は無い。消した 3 つの経路は 404 になる（攻撃面が減る）。残る `SpacedRepetitionViewSet` の `permission_classes = [permissions.IsAuthenticated]` は変えない
- 機密データ: 中身を出さない書き出し（`export_user_data_task`）を消す。ログに個人情報を足さない（`update_daily_analytics_task` のログは今のまま利用者の ID だけ）
- OWASP: 新しい入出力が無いので該当なし
- 依存ライブラリ: 変えない（pip-audit・npm audit の対象の変化なし）
- 静的検査の基準: bandit は MEDIUM 以上を直す（LOW は `# nosec` で抑える）。npm audit は high/critical を直す（本イシューでは frontend を変えない）

要件適合・業務ロジック:
- 受け入れ条件の外の仕様の追加は無い
- マルチテナント: `update_daily_analytics_task` は利用者を選ぶだけで、組織を越えた値を混ぜない（選んだ利用者ごとに既存の `SpacedRepetitionService(user)` が本人の記録を集計する）。利用者の選び方に組織の絞り込みは要らない（夜間に全組織の利用者を対象にする処理で、今も同じ）
- エッジケース: 7 日のちょうど境目（`__gte`）、クイズの答えと復習の両方がある人（`distinct` で 1 回）、どちらも無い人（対象外）を TC-05 で見る

Danger Ops（有無/手順/ロールバック）:
- 有: `studylogs_spacedrepetitionreview.study_session_id` の列の削除と、4 つのテーブル（と多対多の表）の削除（マイグレーション `0002`）
- 消す前: ステップ 1 で件数を記録し（M1）、`dumpdata` でバックアップを取る（M2）。戻し方は 7、その試しは TC-07
- 承認: ユーザーが grill-me で「本イシューで全部行う・承認は省かない」と決めた（2026-11-17）。マイグレーションは PR のレビューとマージで入り、開発の DB にはマージの後のコンテナの起動の `migrate` で流れる。Claude は、このマイグレーションのために `DANGER_OK=1` の操作をしない。マージ依頼のときに、消える表と件数（M1）・バックアップの場所（M2）・戻し方（7）・コンテナの起動で流れることを書き、PR に `danger-approved` のラベルを付けてもらう（付けるのはユーザー。これが承認の記録になる）
- ロールバック: 7

P3/P5/P8: P3（データ整合性）は 10、P5（運用）は 11 に書いた。P8（コスト）は影響なし（新しい資源・外部サービスは無い）
P6: 画面の変更は無い。性能は 8 の R8 と 13
P9: 15 に書いた（個人情報の新しい扱いは無い・テナントの越境は無い）

## 10. データ整合性設計
- 制約: 新しい制約は無い。消すのは外部キー 1 つ（`SpacedRepetitionReview.study_session`・`SET_NULL`・NULL 可）と 4 つのテーブル（とその外部キー・索引・一意の制約）
- 順番: `ProblemAttempt.study_log`（`CASCADE`）が `StudyLog` を指すので、`ProblemAttempt` を `StudyLog` より先に消す。`SpacedRepetitionReview.study_session` を最初に外す（`StudyLog` を消す時点で指す列が無い）。`makemigrations` の出す並びが 4 の表と違えば、表の順に並べ直す
- トランザクション: PostgreSQL ではマイグレーション 1 本が 1 つのトランザクション（`atomic = True` の既定のまま）。途中で失敗すれば全部戻る
- 冪等性・同時更新: スキーマの変更だけで、データの書き換えは無い。消す表には書き込む経路が無い（API はステップ 3 で消える）
- 後方互換: マージの後、古いコード（I492 の前）は消えた表を読もうとして落ちる。戻すときは 7 の順（先にスキーマを戻してからコードを戻す）
- 逆向き: `RemoveField`（NULL 可の外部キー）と `DeleteModel` は Django が逆向きを作れる（テーブルと列が空で戻る）。TC-07 が確かめる

## 11. 運用設計
- 定期処理: `update_daily_analytics_task`（夜 2 時）は判定の条件だけ替え、ログ・再試行（`max_retries=3`・`countdown=60`）は今のまま。`send-study-reminders`（朝 7 時）は登録ごと消す
- ログ: 新しいログは足さない（今のログは利用者の ID だけ）
- 段階リリース・Feature Flag: 要らない（本番が無い・消すだけ）
- 切り戻し: 7

## 13. 性能・UX設計
- 画面の変更は無い（ローディング・空状態・エラー状態・破壊的操作の確認の導線は該当なし）
- 性能: `update_daily_analytics_task` の利用者の選び方が、`StudyLog` の結合からクイズの回→答えの結合に替わる。`distinct()` で重複を除く。夜間に 1 回で、範囲は 7 日（8 の R8）

## 14. 学習効果設計
- 夜 2 時の学習分析の更新の対象に、クイズだけを解いている人が入るようになる（今は `StudyLog` に書く経路が無く、復習をした人だけが対象だった）。学習の数字の出どころを `QuizAnswer` にそろえる I473 の方針どおり（C1）
- 学習リマインダーのメールを止める（ユーザーの決定）。動機づけの手段としてのリマインダーは、画面のブラウザ通知（`frontend/src/contexts/NotificationContext.tsx`）が残る

## 15. プライバシー・コンプライアンス設計
- 個人情報の新しい扱いは無い。消すのは空の表と、中身を出さない書き出しの処理
- データ主体の権利（開示）は #570 で設計する（本イシューでは扱わない）
- テナントの越境は無い（新しいクエリは利用者を選ぶだけで、応答・ログに組織を越えた値を出さない）
- バックアップ（M2）は gitignore 済みの `.evidence/I492/` に置き、リポジトリ・イシュー・PR に貼らない（開発の DB で 0 件）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | TC-07 が、手で組んだ操作でなく本物の `0002`（`MigrationLoader` で読んだもの）を `apply`/`unapply` していて、`StudyLog` を指す `SpacedRepetitionReview` の行を含めて件数を比べているか |
| V2 | 2 | 読んで可 | TC-05 が、古い判定（`study_logs__started_at`）のままでは落ちるか（クイズだけを解いた人が対象から漏れる）。実装の記録に、直す前に落ちたことが書かれているか |
| V3 | 3 | 読んで可 | 消したモデル・逆向きの関連名・`study_session`・消したタスクの名前が、テストとマイグレーションの外に残っていないか（TC-01〜TC-03 のゲートの実走の結果）。ゲートが見ない書き方（`apps.get_model('studylogs', ...)` の文字列など）で古い表を読むコードが無いか |
| V4 | 3 | 読んで可 | TC-07 が、`0002` の操作が 4 の表の 5 つだけ（`SpacedRepetitionReview`・`SpacedRepetitionCard` などほかのモデルを消さない）であることを確かめているか。戻した後（`unapply`）にテーブルと列が戻り、行を入れ直せることを確かめているか（7 の 1 の戻し方の試し） |

## 計画変更記録
- 計画レビュー（20261118_0232）の Warning（TC-04 の記録）: TC-04 の結果の欄に「`REMOVED` に足す前・登録を消す前は `test_removed_schedules_are_gone` が落ち、消した後は通る」ことを実装で記録すると書いた。計画レビューのやり直し: 不要（findings への対応の追記だけ）
- 計画レビュー（20261118_0232）の Warning（R1 が約束だけに頼る）: R1 の回避策に、マージ依頼の直前にも `showmigrations` で未適用を確かめること・開発の DB がこのワークツリー専用であることを足した。計画レビューのやり直し: 不要（findings への対応の追記だけ）

## レビュー結果
- [20261118_0232 判定: ✅ 完了](../../reviews/I492_plan_review_20261118_0232.md)
