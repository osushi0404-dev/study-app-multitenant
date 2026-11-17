# I492 自動テスト: 古い学習記録の表（StudyLog など）の片付け

実行コマンド（例）: `docker compose exec -T backend pytest studylogs/tests/test_I492_remove_legacy_study_logs.py core/tests/test_I466_celery_schedule.py core/tests/test_I446_cross_api_tenant_isolation.py -q`（pytest・Jest・E2E は CI が PR ごとに流すので、test-gate では流し直さない）

結果:
- backend: （実装の後に記入）
- frontend: 変更なし（CI の結果だけを記入）

## テストケース

| TC | 受け入れ条件 | 種別 | 内容 | 期待値 | 結果 |
|---|---|---|---|---|---|
| TC-01 | AC1 | 決定論ゲート | `backend` の `.py`（`tests/`・`migrations/` を除く）に `StudyLog`・`DailyStudySummary`・`StudyGoal`・`ProblemAttempt` の文字が無い | exit 0（一致なし） | 実装前: exit 1（不合格・2026-11-18。`models.py`・`views.py` などに残っている＝失敗の注入の代わり） |
| TC-02 | AC1 | 決定論ゲート | (a) `backend` の `.py`（`tests/`・`migrations/` を除く）に逆向きの関連名 `study_logs__`・`daily_summaries`・`study_goals`・`problem_attempts` が無い。(b) `backend/studylogs` の `.py`（同）に `study_session` が無い | どちらも exit 0 | 実装前: (a) exit 1（`tasks.py:36`・`:79`・`models.py:76`・`:101`・`:128`）、(b) exit 1（`models.py:247`・`services.py`・`views.py`）・2026-11-18 |
| TC-03 | AC2 | 決定論ゲート | `backend` の `.py`（`tests/` を除く）に `send_study_reminders_task`・`export_user_data_task`・`generate_system_report_task`・`send-study-reminders` が無い | exit 0 | 実装前: exit 1（2026-11-18） |
| TC-04 | AC2 | pytest | `core/tests/test_I466_celery_schedule.py`: `REMOVED` に `"send-study-reminders"` を足す。`test_removed_schedules_are_gone`（登録に無い）・`test_every_scheduled_task_exists`（登録したタスクが実在。タスクだけ消して登録を残すと落ちる＝既存の失敗の注入 `test_checks_catch_interval_and_missing_task`） | 4 件とも passed | 実装前のため未実行（実装で、`REMOVED` に足して登録を消す前に `test_removed_schedules_are_gone` が落ち、消した後に通ることを記録する） |
| TC-05 | AC3 | pytest | `test_I492_remove_legacy_study_logs.py::test_daily_analytics_targets_quiz_and_review_learners`。`studylogs.tasks.SpacedRepetitionService` を、呼ばれた利用者の ID を記録する代わりの物に差し替え、`update_daily_analytics_task.run()` を呼ぶ。利用者: A＝6 日 23 時間前にクイズに答えた（`QuizAnswer.answered_at` を `update()` で設定）、B＝1 日前に復習（`SpacedRepetitionReview.reviewed_at`）、C＝7 日 1 時間前にだけ答えた、D＝何も無い、E＝2 日前に答え・復習の両方（答え 2 件） | 呼ばれた ID が `{A, B, E}` で、E は 1 回だけ。戻り値が `{'updated_count': 3, 'error_count': 0, 'total_users': 3}` | 実装前のため未実行（ステップ 2 で、直す前の判定で落ちる〔A・E が漏れる〕ことを記録する） |
| TC-06 | AC4 | pytest | `test_submit_review_records_review`。本人のカード（自組織の問題）に `POST /api/study/spaced-repetition/submit_review/` `{"card_id": <id>, "quality_score": 4, "response_time_seconds": 10}` | 201。本文の `message` が `'復習を記録しました'`、`review.quality_score` が 4、`updated_card.total_reviews` が 1。`SpacedRepetitionReview` が 1 件増える | 実装前のため未実行 |
| TC-07 | AC5・AC7 | pytest | `test_migration_0002_drops_legacy_tables_and_keeps_reviews`。`settings.MIGRATION_MODULES = {}` で本物のマイグレーションを読み（`MigrationLoader`）、`0002_remove_legacy_study_logs` を取る。(1) 操作が `[('RemoveField', 'spacedrepetitionreview', 'study_session'), ('DeleteModel', 'ProblemAttempt'), ('DeleteModel', 'DailyStudySummary'), ('DeleteModel', 'StudyGoal'), ('DeleteModel', 'StudyLog')]` と同じ。(2) `0001_initial` の時点の状態で `unapply` してテーブルと列を作り、`SpacedRepetitionReview` を 2 件（1 件は `StudyLog` を指す）と、`ProblemAttempt`（その `StudyLog` を指す）・`DailyStudySummary`・`StudyGoal` を 1 件ずつ、0001 の時点のモデルで作る。(3) `SET CONSTRAINTS ALL IMMEDIATE` の後に `apply`。(4) もう一度 `unapply`（戻し方の試し）。(5) `finally` で `apply` してテストの DB を今の形に戻す | (3) の後: 4 テーブル（と `studylogs_dailystudysummary_subjects_studied`）が無く、`studylogs_spacedrepetitionreview` に `study_session_id` の列が無く、`SpacedRepetitionReview` が 2 件のまま。(4) の後: テーブルと列が戻り、4 テーブルは 0 件、`StudyLog` を 1 件入れ直せる、`SpacedRepetitionReview` は 2 件のまま | 実装前のため未実行（失敗の注入: ステップ 4 で `0002` に一時的に `RunSQL("DELETE FROM studylogs_spacedrepetitionreview WHERE study_session_id IS NOT NULL", RunSQL.noop)` を足すと (1) と件数の確かめで落ちることを確かめ、Edit で戻す） |
| TC-08 | AC6 | pytest | `test_removed_study_routes_are_404`（`parametrize`）。本人でログインした API クライアントで `GET /api/study/logs/`・`GET /api/study/logs/1/`・`POST /api/study/logs/`・`GET /api/study/statistics/overview/`・`GET /api/study/statistics/by_subject/`・`GET /api/study/statistics/daily_summary/`・`GET /api/study/goals/`・`POST /api/study/goals/update_progress/` | どれも `status_code == 404`（URL の設定に経路が無いので Django の既定の 404。本文の形は DRF を通らないので見ない） | 実装前のため未実行（今のコードではどれも 404 以外＝この TC は実装の前に落ちる） |
| TC-09 | AC6 | pytest | `core/tests/test_I446_cross_api_tenant_isolation.py` の全件（`test_route_table_matches_urlconf` で経路の表と URL の設定が一致する） | passed | 実装前のため未実行 |
| TC-10 | AC8 | CI | backend（pytest 全件・ruff・bandit・`makemigrations --check`）・frontend（Jest・型・ESLint）・E2E | すべて success | 実装前のため未実行 |

## 決定論ゲート（自動実走）
```bash
! grep -rq -e StudyLog -e DailyStudySummary -e StudyGoal -e ProblemAttempt --include=*.py --exclude-dir=tests --exclude-dir=migrations backend
! grep -rq -e study_logs__ -e daily_summaries -e study_goals -e problem_attempts --include=*.py --exclude-dir=tests --exclude-dir=migrations backend
! grep -rq -e study_session --include=*.py --exclude-dir=tests --exclude-dir=migrations backend/studylogs
! grep -rq -e send_study_reminders_task -e export_user_data_task -e generate_system_report_task -e send-study-reminders --include=*.py --exclude-dir=tests backend
```

## 失敗の注入（false-green の確かめ）
- TC-01〜TC-03（ゲート）: 実装の前の今のコード（古い名前が残っている状態）で 4 行とも exit 1 になることを確かめた（2026-11-18）。一致が無い場所（`backend/accounts`）に向けると exit 0 になることも確かめた
- TC-04: 既存の `test_checks_catch_interval_and_missing_task` が、消したタスクを指す登録を見つけることを確かめている
- TC-05: 直す前の判定（`study_logs__started_at`）で落ちることを、ステップ 2 で記録する
- TC-07: ステップ 4 で `0002` に復習の記録を消す操作を一時的に足して落ちることを確かめ、Edit で戻す
- TC-08: 実装の前のコードで 404 以外になる（経路が残っている）ことを、ステップ 3 で TC を先に足して確かめる
