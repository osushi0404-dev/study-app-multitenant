# 敵対的レビュー [I492]（別プロセス・2026-11-18 15:28）

- 見た範囲: origin/develop...d3fe7d75ec86d7f251cdda1e0fcbac13b0fd8c1a
- 所要時間: 32 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（14 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I492.md の「## 必ず確かめる項目」（4 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 25 秒 | 0 | 0 | $0.2436 | ― | ― | ― |
| 2 | 報告あり | 19 秒 | 0 | 0 | $0.2621 | ― | ― | ― |
| 3 | 報告あり | 29 秒 | 0 | 0 | $0.2942 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I492] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説は次のとおり。

- **手で組んだ操作で代用している疑い**
  - `test_migration_0002_drops_legacy_tables_and_keeps_reviews` は、`settings.MIGRATION_MODULES = {}` にしてから `MigrationLoader(connection)` で本物の `0002_remove_legacy_study_logs` を読んでいます。
  - `loader.get_migration(*MIGRATION)` の `operations` を `EXPECTED_OPERATIONS` と完全一致で比べています。
  - その `migration.apply` と `migration.unapply` を、`connection.schema_editor()` で実際の DB に流しています。
  - 手で組んだ `RemoveField` や `DeleteModel` は使っていません。この仮説は成り立ちません。
- **`StudyLog` を指す行が件数の比較に入っていない疑い**
  - 先に `migration.unapply` で DB を 0001 の形（`study_session_id` の列と 4 つの古い表がある形）に戻しています。
  - その上で `_review` を 2 件作り、古いモデル（`old.get_model`）で 1 件の `study_session_id` に `StudyLog` の id を入れています。
  - `reviews == 2` を確かめた後に、`apply` の後と `unapply` の後の 2 回、件数が `reviews` と同じかを比べています。
  - `StudyLog` を指す行は含まれていて、`apply` による CASCADE の影響も見られます。この仮説も成り立ちません。
- **テストが失敗したときに DB が汚れたままになる疑い**
  - `finally` で、`studylogs_studylog` が残っていれば `apply` して今のモデルの形に戻しています。
  - テストの `atomic` の中で動くので、ほかのテストへの影響は小さいと読めます。
  - `SET CONSTRAINTS ALL IMMEDIATE` も入っていて、計画書のスパイクで見つけた失敗の原因に対処しています。
- **`unapply` に渡す state の誤りの疑い**
  - `Migration.unapply` は「その移行より前の state」を受け取る仕様です。
  - `before = loader.project_state(BEFORE)` は 0001 の state なので、仕様と合っています。
  - `_run` は `state.clone()` を渡していて、`old = before.apps` は変わりません。
- **V4 の確認範囲**
  - `_operations` が 5 つの操作だけを確かめているので、`SpacedRepetitionReview` 以外のモデルの削除や `SpacedRepetitionCard` の変更が混ざればテストが落ちます。
  - `unapply` の後に `LEGACY_TABLES <= _tables()`、`study_session_id` の列、`OldLog` の再作成を確かめています。
  - 入れ直しを確かめているのは `StudyLog` だけです。ほかの 3 つの表はテーブルの存在だけを見ています。ここは Low の注意点で、件数には数えません。

実験は出していません。V1 は「読んで可」の項目で、読んで十分に確かめられました。

> ITEM: V1 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I492] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 反証失敗（新規指摘なし） | - | 静的読解 |

反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。

- **TC-05 が古い判定で通ってしまうか**
  - 古い判定は `study_logs__started_at` と `sr_reviews__reviewed_at` の OR だった。
  - テストでは、クイズだけを解いた `quiz_only` は `StudyLog` を持たず、復習も無い。古い判定では対象から漏れ、`sorted(called) == [...]` が落ちる。
  - `too_old` と `idle` が呼ばれないこと、`both` の答えが 2 件でも 1 回だけ呼ばれること（`total_users: 3`）も確かめている。結合の OR で行が重複する退行は捕まえられる。
  - サービスの差し替えは `tasks.SpacedRepetitionService` に対して行っている。タスク内の参照名と一致しているので、素通りして tautology になることは無い。
- **直す前に落ちたことの記録があるか**
  - `docs/tests/open/I492_auto_test.md` の TC-05 の行に記録がある。「直す前の判定（`study_logs__started_at`）では落ちた: 呼ばれたのが復習をした 2 人だけで、クイズだけを解いた A が漏れた」。
  - 期待する落ち方（クイズだけの人が漏れる）と一致している。
- **テストが実装の再確認になっていないか**
  - 期待値はテストの中で決めた日時と人から作っている。実装のクエリを写してはいない。7 日の境界も 6 日 23 時間前と 7 日 1 時間前で両側を確かめている。

軽微な点が 1 つだけある。7 日の境界は、ちょうどの時刻ではなく 1 時間の余裕を持たせた値で確かめている。時刻のずれでテストが不安定になることは無い。これは欠陥ではない。

> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I492] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。

1. **消した名前が残っていないか（V3）**
   - 検索語は `StudyLog`・`DailyStudySummary`・`StudyGoal`・`ProblemAttempt`・`study_session`・`study_logs`・`send_study_reminders`・`export_user_data_task`・`generate_system_report`・`StudyStatistics` です。`backend/` のテスト以外を探すと、ヒットは `0001_initial.py` と `0002_*.py`（マイグレーション）だけでした。
   - `core/middleware.py:102` の `'study_session'` は、操作名を表す文字列のままです。計画書も変えないと書いています。`study_logs`・`problem_attempts`・`daily_summaries`・`study_goals` といった逆向きの関連名も、`backend/` のテスト以外には残っていません。
   - `apps.get_model` を使うのは `accounts` と `problems` のデータ移行だけです。`studylogs` の古い表を文字列で読むコードはありません。
   - `frontend/src` のヒットは `useDailyStudyGoal` などの別名だけです。API 呼び出しや型はありません。
   - `scripts/.../pretooluse_guard.py` が `send_study_reminders_task` を語として持つ点は、計画書が「変えない」と決めています。`docs/tests/closed/I151_celery_probe.py` は過去イシューの記録です。ここは見ていません。
   - `core/celery.py` の `beat_schedule` から `send-study-reminders` は外れています。`test_I466_celery_schedule.py` の `REMOVED` にも追加済みです。
2. **TC-07 の網羅（V4）**
   - `_operations(migration) == EXPECTED_OPERATIONS` で、本物の 0002 の操作がちょうど 5 つ（`RemoveField` 1 つと `DeleteModel` 4 つ）かを厳密に比べています。`SpacedRepetitionReview` や `SpacedRepetitionCard` を消す操作が混ざれば落ちます。
   - `apply` の後に、旧 5 テーブルが無いこと、`study_session_id` の列が無いこと、復習の件数が 2 で変わらないことを確かめています。
   - `unapply` の後に、テーブルと列が戻ること、`OldLog.objects.count() == 0` を確かめています。そのうえで行を作り直して `count() == 1` を確かめています。
   - `finally` で DB をモデルの形に戻します。
3. **エッジケース**
   - TC-05 は、7 日を 1 時間超えた人、何もない人、答えと復習の両方がある人を、対象に入れるかどうかで確かめています。重複も見ています。
   - TC-08 は、消した経路が 404 になることを 8 本で確かめています。

軽微な点が 1 つあります。TC-07 は ProblemAttempt などの行が `apply` でどうなるかを見ていません。ただし `apply` が通ることと、`DeleteModel` が 4 つあることは確かめているので、重大度は付けません。

> ITEM: V3 RESULT=read
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: d3fe7d75ec86d7f251cdda1e0fcbac13b0fd8c1a
ROUNDS: 1
VERDICT: OK
