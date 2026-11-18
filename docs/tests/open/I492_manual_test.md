# I492 手動テスト: 古い学習記録の表（StudyLog など）の片付け

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | 実装の前（ステップ 1・コードを変える前）に、開発の DB で `docker compose exec -T backend python manage.py shell -c "from studylogs.models import StudyLog, DailyStudySummary, StudyGoal, ProblemAttempt, SpacedRepetitionReview; print(StudyLog.objects.count(), DailyStudySummary.objects.count(), StudyGoal.objects.count(), ProblemAttempt.objects.count(), SpacedRepetitionReview.objects.count(), SpacedRepetitionReview.objects.exclude(study_session=None).count())"` を流し、6 つの数をレビュー文書の「## 自律判断の記録」に書く | 6 つの整数が出る（2026-11-17 の値は `0 0 0 0 6 0`）。値をレビュー文書に記録した | Claude | OK（2026-11-18・実装の前: `0 0 0 0 6 0`） | 読むだけ |
| M2 | ステップ 1 で `dumpdata`（4 モデル）を `/tmp/i492_legacy_backup.json` に書き出し、`docker compose cp` で `.evidence/I492/legacy_backup.json` に置く。M1 の 6 つ目が 1 以上なら `(id, study_session_id)` の組も同じフォルダに置く | `.evidence/I492/legacy_backup.json` があり、JSON として読め（`python3 -m json.tool`）、中の件数がモデルごとに M1 の 1〜4 つ目の数と同じ（0 件なら `[]`） | Claude | OK（2026-11-18・`.evidence/I492/legacy_backup.json` を作成。`json.tool` で読め、中身は `[]`〔0 件〕で M1 と一致。`study_session` の組は 0 件なので書き出さない。`git status` に出ない〔gitignore 済み〕） | 見張りの承認画面が出ることがある（DB の中身の書き出し・コンテナからの取り出し） |
| M3 | 実装の後（ステップ 4 の後）に、`docker compose exec -T backend python manage.py showmigrations studylogs` と `docker compose exec -T backend python manage.py check` を流す | `showmigrations` が `[X] 0001_initial` と `[ ] 0002_remove_legacy_study_logs` を出す（開発の DB にはまだ流れていない）。`check` が `System check identified no issues (0 silenced).` を出す | Claude | OK（2026-11-18・実装の後: `[X] 0001_initial`・`[ ] 0002_remove_legacy_study_logs`、`System check identified no issues (0 silenced).`） | 承認の前に開発の DB のテーブルが消えていないことの確かめ（計画書 8 の R1） |

人の手動テストは無い（画面の変更が無い）。Danger Ops の承認は、マージ依頼のときにユーザーが PR に `danger-approved` のラベルを付けること（計画書 9）。

## 画面確認
frontend/src を変えないので不要。

結論: OK / NG
