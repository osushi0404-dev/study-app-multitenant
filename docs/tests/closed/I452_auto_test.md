# I452 自動テスト: クイズの回答から復習の予定を作り、ダッシュボードから今日の復習を始められるようにする

- 関連: docs/issues/open/I452.md / docs/plans/open/plan_I452.md / GitHub #452 / Draft PR #464
- 対象: `backend/studylogs/tests/test_I452_quiz_review.py`（新規）・`backend/core/tests/test_I446_cross_api_tenant_isolation.py`（xfail を外す・経路を足す）・`frontend/src/components/__tests__/TodayReviewCard.test.tsx`（新規）・`frontend/src/pages/__tests__/QuizSession.review.test.tsx`（新規）と、守りにする既存のテスト（I431・I166・I455・クイズの画面の既存のテスト）
- 実行場所: app-1 ワークツリーのコンテナ（`docker compose exec -T backend ...`・`docker compose exec -T frontend ...`）。全テストは CI（PR #464）が正。手元では下の TC のファイルだけを流す
- 合否は終了コード（合格=0・不合格=非ゼロ）。否定・不在の TC は失敗の注入（FG）で非ゼロになることを確かめる
- 下の表の `PYT` は `docker compose exec -T backend python -m pytest studylogs/tests/test_I452_quiz_review.py -q`、`JEST` は `docker compose exec -T frontend npx react-scripts test --watchAll=false` の略

結果:
- backend: 新しいテスト 28 件と守りのテスト（I431・I455・I166・I158・#446・problems の views）が 247 passed（xfailed 0）。失敗の注入はすべて FAIL。CI は review-gate で確かめた（`CI_WAIT: OK`）
- frontend: 新しい 2 ファイルと既存のクイズの 2 ファイルが 20 passed。型チェック・lint（警告 0）も合格

## 決定論ゲート（自動実走）
```bash
! grep -q STUDYLOGS_BASE_URL frontend/src/services/dashboard.service.ts
! grep -q getStudyStats frontend/src/services/dashboard.service.ts
! grep -q getRecentSessions frontend/src/services/dashboard.service.ts
! grep -q getWeeklyProgress frontend/src/services/dashboard.service.ts
! grep -q getSubjectProgress frontend/src/services/dashboard.service.ts
! grep -q startStudySession frontend/src/services/dashboard.service.ts
! grep -q endStudySession frontend/src/services/dashboard.service.ts
! grep -q recordProblemAttempt frontend/src/services/dashboard.service.ts
! grep -q XFAIL_452 backend/core/tests/test_I446_cross_api_tenant_isolation.py
```

## 実行記録
| 日時 | コマンド | 終了コード | 結果 |
|---|---|---|---|
| 2026-11-12 | TC-19（実装前・決定論ゲートの 9 行を 1 行ずつ） | 1 | 9 行とも exit 1（消す前の状態で当たる）。これが FG の「消す前」の状態に当たる。実装後に 0 になることを確かめる |
| 2026-11-12 | TC-15（実装前・ベースライン） | 0 | `No changes detected`。migration を足す前の状態。TC-15 の本番（0022 を足した後）は実装の時に行う |
| 2026-11-12 | TC-01〜TC-14・TC-16〜TC-18・TC-20・TC-21（実装前） | — | 実装前のため未実行 |
| 2026-11-12 | ステップ 1: #446 の直した 9 ケース（`-k "learning_insights or update_analytics or analyze or refresh_analysis or adaptive"`） | 0 | 15 passed（xfail の印を外した後・難易度などの直しの後） |
| 2026-11-12 | Red: `PYT`（本体の実装前） | 1 | 21 failed・7 passed（`record_quiz_answer` が無い・`review_summary` が 404 など。通った 7 件はステップ 1 で直した 500 の経路） |
| 2026-11-12 | Green: `PYT` | 0 | 28 passed |
| 2026-11-12 | TC-14（初回） | 1 | I455 の静的テストが `studylogs/services.py` の行のロックの読み出しに理由のコメントが無いことを検出（計画変更記録）。コメントを足して 247 passed |
| 2026-11-12 | TC-15 | 0 | `No changes detected`（0022 を足した後）。0022 は `AddField`（`quizsession.mode`）だけ |
| 2026-11-12 | FG: `adaptive_selection.py` の難易度の絞り込みを文字に戻す | 1 | TC-09・TC-10 と #446 の `adaptive-learning` 5 件が FAIL（7 failed）。戻した |
| 2026-11-12 | FG: 同じ日の判定を外す・`_reviewable_cards` の `available_problems` を `Problem.objects.all()` にする | 1 | TC-02 の 2 件・TC-04・TC-05 の 2 件・TC-06・TC-08 が FAIL（7 failed）。戻した |
| 2026-11-12 | Red: `JEST` の新しい 2 ファイル（部品の実装前） | 1 | 部品が空で FAIL |
| 2026-11-12 | TC-16・TC-17・TC-18 | 0 | 4 suites・20 passed |
| 2026-11-12 | TC-19（決定論ゲートの 9 行） | 0 | 9 行とも exit 0。`frontend/src` 全体でも 7 つの関数名に当たらない |
| 2026-11-12 | /simplify の後に TC-14・TC-15・TC-16〜TC-18（TC-21） | 0 | 247 passed・`No changes detected`・20 passed・型チェック合格・`npm run lint` 警告 0 |
| 2026-11-12 12:55 | review-gate: `bash scripts/claude/code-review.sh I452`（CI 待ちを含む） | 0 | `CI_WAIT: OK`（TC-20）・`FINAL_VERDICT: OK`（Low 7 件）・`ADVERSARIAL_STAGE: REQUIRED` |
| 2026-11-12 13:10 | review-gate の FG: `get_due_cards` のキーから組織を外す・`get_next_problem` の復習の分岐を外す | 1 | TC-12・TC-05 の 2 件・TC-08 が FAIL（4 failed）。戻して差分なし（敵対的レビューの未検証の項目 V3・V6 の裏取り） |

## TC 一覧

| TC | 内容 | コマンド | 期待値 | 対応 AC |
|---|---|---|---|---|
| TC-01 | `test_schedule_*`（サービス）: `record_quiz_answer(problem, is_correct, 10, now=...)` を日をまたいで呼ぶ。(a) 新しいカードで正解（11-12 10:00）→ 連続 1・間隔 1・次の日付 11-13 00:00（Asia/Tokyo）(b) 続けて 11-13 に正解 → 連続 2・間隔 6・次 11-19 00:00 (c) 11-19 に正解 → 連続 3・間隔 `round(6 × 係数)`（係数 2.5 なら 15）・次 12-04 00:00 (d) その後に不正解 → 連続 0・間隔 1・次は翌日 0 時・係数が 0.32 下がる（下限 1.3）(e) 23:59 に答えたカードは翌日 0:00 に「今日の復習」に入り、23:59 の時点では入らない | `PYT -k schedule` | exit 0。各段の `repetition_count`・`interval_days`・`next_review_date`（aware・Asia/Tokyo の 0 時）・`ease_factor` が左の値と一致。(d) の後に `SpacedRepetitionReview` が回答の数だけある | AC1 |
| TC-02 | `test_same_day_second_answer_*`: 同じ日に同じ問題を 2 回答える（1 回目正解・2 回目不正解。いつものクイズの別の回でも、同じ回の別の問題の後でも）| `PYT -k same_day` | exit 0。2 回目の後もカードの欄（次の日付・連続回数・係数・`total_reviews`）が 1 回目の後と同じ。`SpacedRepetitionReview` は 1 件。`record_quiz_answer` の戻り値は `None` | AC2 |
| TC-03 | `test_submit_answer_updates_card`（API）: いつものクイズを始め、`POST /api/quiz/<id>/submit_answer/` で正解と不正解を 1 問ずつ答える（回答とカードの更新が 1 つのトランザクションであることは、テストのための差し替えを作らず、計画の V5 としてコードを読んで確かめる）| `PYT -k submit_answer` | exit 0。応答 200 で `is_correct` は送った正誤どおり。正解した問題のカードは連続 1・次の日付は翌日 0 時、不正解は連続 0・翌日 0 時。回答の応答の欄（`is_correct`・`explanation`・`correct_choices`・`session`・`session_stats`）は今と同じ | AC1 |
| TC-04 | `test_review_summary_*`（API `GET /api/study/spaced-repetition/review_summary/`）: 組織 A の `user_a` に、科目 S1 の期限が来たカード 2 枚・S2 の期限が来たカード 1 枚・S1 の 3 日後のカード 1 枚・S2 の 10 日後のカード 1 枚・無効（`is_active=False`）の期限が来たカード 1 枚・削除した問題（`is_deleted=True`）の期限が来たカード 1 枚を作る | `PYT -k review_summary` | exit 0。(a) 指定なし → 200 `{"due_count": 3, "next_review_date": "<3 日後>"}` (b) `subject_id=S1` → `{"due_count": 2, "next_review_date": "<3 日後>"}` (c) `subject_id=S2` → `{"due_count": 1, "next_review_date": "<10 日後>"}` (d) カードの無い科目 → `{"due_count": 0, "next_review_date": null}` (e) `subject_id=abc`・他組織の科目・存在しない番号 → 400 で `error.main_message` が「科目の指定が正しくありません」(f) 未認証 → 401 | AC3・AC6・AC9 |
| TC-05 | `test_review_session_*`（API）: TC-04 と同じデータで `POST /api/quiz/` `{"mode": "review", "subject": S1}` → `next_problem` と `submit_answer` を対象がなくなるまで繰り返す。「すべて」（`subject` なし）でも同じ。あわせて、いつものクイズ（`mode` なし）で科目の問題をすべて答えた後も `next_problem` が問題を返し続けること | `PYT -k review_session` | exit 0。開始は 201 で `mode` が `"review"`・`total_problems` が 2（「すべて」なら 3）。`next_problem` は期限が来た S1 のカードの問題だけを返し（`is_review_mode` は `false`・`total_problems_in_subject` は `total_problems`）、答えた問題を二度返さない。全部答えた後の `next_problem` は 200 `{"review_complete": true, "total_problems": 2, "completed_problems": 2, "correct_answers": <正解数>}`。いつものクイズは全問の後も 200 で問題を返し `is_review_mode` が `true` | AC4・AC5 |
| TC-06 | `test_review_interrupted`: 期限が来たカード 3 枚で復習の回を始め、1 問だけ答えて回を終える（`end`）| `PYT -k interrupted` | exit 0。答えた 1 枚は次の日付が翌日以降に変わり、残り 2 枚は変わらない。`review_summary` の `due_count` が 2 | AC7 |
| TC-07 | `test_past_answers_do_not_create_cards`: この変更の前の回答に当たる `QuizAnswer` を ORM で直接作る（API を通さない）| `PYT -k past_answers` | exit 0。`SpacedRepetitionCard` が 0 件で、`review_summary` が `{"due_count": 0, "next_review_date": null}` | AC8 |
| TC-08 | `test_review_tenant_*`: (a) `user_a` が組織 B の問題のカード（I431 より前の古いデータ）を持つ (b) 同じ組織 A の `user_a2` のカード (c) 組織に属さない利用者 (d) 復習の回を `Idempotency-Key` つきで始め、同じキーで `mode` を変えて送る (e) 復習の回を組織 B の科目で始める (f) `mode` に `"other"` を送る | `PYT -k review_tenant` | exit 0。(a)(b) のカードは `review_summary` の件数にも復習の回の出題にも入らない (c) は `{"due_count": 0, "next_review_date": null}` で、復習の回は 201・`total_problems` 0・最初の `next_problem` が `review_complete` (d) 2 回目は 422 (e) 400 で回を作らない（`QuizSession` の件数が変わらない）(f) 400 | AC9 |
| TC-09 | `test_difficulty_*`: (a) `problems.difficulty.LABEL_BY_LEVEL` のキーが `Problem.DIFFICULTY_CHOICES` の値の集合と一致する (b) 難易度 1〜3 の問題の復習記録・試行記録を作り、`AdaptiveProblemSelector(user).analyze_user_proficiency()` の `difficulty_proficiency` の `easy`・`medium`・`hard` の件数がそれぞれ作った数と一致する (c) `MistakeAnalyzer(user)` の難易度別の分母が自組織の記録だけを数える（組織 B の問題の記録を足しても変わらない）(d) `problems` の問題の応答の `difficulty` が今と同じ文字（`easy` など）| `PYT -k difficulty` | exit 0 | AC10 |
| TC-10 | `test_learning_endpoints_ok`: TC-09 のデータで、`GET /api/study/spaced-repetition/learning_insights/`（分析の記録なし・あり）・`POST .../update_analytics/`・`GET /api/study/mistake-analysis/analyze/`・`POST .../refresh_analysis/`・`GET /api/study/adaptive-learning/{proficiency_analysis,personalized_recommendation,learning_path,difficulty_distribution}/`・`POST .../select_problems/` を呼ぶ | `PYT -k learning_endpoints` | exit 0。すべて 200。`learning_insights` の分析の記録なしは `{"insights": [], "recommendations": [], "period_days": 7, "analytics_data": []}`。`difficulty_distribution` の応答に `easy`・`medium`・`hard` のキーがある | AC10 |
| TC-11 | `test_pattern_without_subject`: 科目が空の `MistakePattern`（`time_pressure`・`problem_type`）と科目のある `subject_difficulty` を作って提案を作る | `PYT -k pattern_without_subject` | exit 0（例外が出ない）。科目が空の 2 つの提案が作られ、文言に科目名を含まない。科目が空の `subject_difficulty`（古いデータ）からは提案が作られない | AC10 |
| TC-12 | `test_cache_key_has_org`: `get_due_cards()` と `analyze_user_proficiency()` を呼んでキャッシュさせた後、利用者の組織を A から B に変えて再び呼ぶ | `PYT -k cache_key` | exit 0。2 回目の結果に組織 A の問題のカード・科目が含まれない（5 分のキャッシュの期限の前でも） | AC9 |
| TC-13 | `test_mark_routes_scoped`: `user_a` の、組織 B の科目を指す自分の提案・弱点で `mark_suggestion_read`・`provide_feedback`・`resolve_weakness` を呼ぶ。自組織のものでも呼ぶ | `PYT -k mark_routes` | exit 0。組織 B を指すものは 404 で、記録は変わらない。自組織のものは 200 で印が付く | AC10・AC13 |
| TC-14 | 守りの既存テストと #446 の横断テスト（9 ケースの xfail を外し、`review_summary` の経路を足した後） | 下の「TC-14 のコマンド」 | exit 0（failed 0・xfailed 0・xpassed 0） | AC10・AC13 |
| TC-15 | migration が 1 つ増え、モデルとずれない | `docker compose exec -T backend python manage.py makemigrations --check --dry-run` | exit 0（`No changes detected`）。`backend/problems/migrations/0022_quizsession_mode.py` があり、中身は `AddField`（`quizsession.mode`）だけ。FG: `0022` の `default` を `'review'` に一時的に書き換えると exit 1（ずれを検出）。戻す | AC14 |
| TC-16 | `TodayReviewCard.test.tsx`: `apiClient.get` を差し替えて (a) 読み込み中に「今日の復習を読み込み中…」(b) `{due_count: 3}` で見出し「今日の復習 3問」とボタン「復習を始める」。押すと `subjectId="all"` なら `/quiz?mode=review`、`"5"` なら `/quiz?mode=review&subject=5` へ遷移し、`"5"` のときは `subject_id: "5"` を送る (c) `{due_count: 0, next_review_date: "2026-11-15"}` で「今日の復習はありません（次は 11月15日）」(d) `next_review_date: null` で「今日の復習はありません」だけ (e) 失敗で「今日の復習を読み込めませんでした」と「再読み込み」。押すと読み直して (b) の表示になる (f) `subjectId` を変えると読み直し、古い応答が後から来ても新しい表示を上書きしない | `JEST src/components/__tests__/TodayReviewCard.test.tsx` | exit 0 | AC3・AC6 |
| TC-17 | `QuizSession.review.test.tsx`: `?mode=review&subject=1` で開く。(a) 開始の要求の本文が `{subject: "1", mode: "review"}` (b) 最後より前の問題に答えた後は「次の問題」、最後の問題に答えた後（`answered_problems === total_problems`）は「結果を見る」のボタンが出る(c) `next_problem` が `{review_complete: true, completed_problems: 3, correct_answers: 2}` を返すと `POST /api/quiz/<id>/end/` を呼び、「今日の復習が終わりました（3問中2問正解）」と「ダッシュボードへ戻る」が出て、「もう一度挑戦」は出ない。押すと `/dashboard` へ (d) `completed_problems: 0` なら「今日の復習はありません」(e) 復習中は印「今日の復習」が出て、いつものクイズ（`mode` なし）では出ない (f) `end` が失敗しても (c) の表示は出る | `JEST src/pages/__tests__/QuizSession.review.test.tsx` | exit 0 | AC4・AC5 |
| TC-18 | いつものクイズの画面の無退行（既存のテストのファイルを変えずに流す） | `JEST src/pages/__tests__/QuizSession.test.tsx src/pages/__tests__/QuizSession.start.test.tsx` | exit 0 | AC5 |
| TC-19 | 画面側の関数 7 つと `STUDYLOGS_BASE_URL` が残らない・#446 の xfail の定数が残らない | 上の「決定論ゲート」の 9 行 | 各行 exit 0。FG: 実装前の状態（消す前）では各行 exit 1（実行記録の 1 行目）。実装後に `getStudyStats` を含むコメントの行を一時的に足すと exit 1。戻す | AC11・AC10 |
| TC-20 | CI の全テスト | `gh pr checks 464` | 全ジョブ pass（`Backend Tests` に `test_I452_quiz_review.py` の結果、`Frontend Tests` に新しい 2 ファイルの結果が出る） | AC14 |
| TC-21 | /simplify の後の流し直し | TC-14・TC-15・TC-16・TC-17・TC-19 のコマンド | すべて exit 0 | AC10・AC13・AC14 |

### TC-14 のコマンド
```
docker compose exec -T backend python -m pytest studylogs/tests/test_I452_quiz_review.py studylogs/tests/test_I431_studylogs_tenant_isolation.py studylogs/tests/test_I455_org_scoped_querysets.py problems/tests/test_I166_quiz_tenant_isolation.py problems/tests/test_I158_quiz_session_start.py core/tests/test_I446_cross_api_tenant_isolation.py -q -rxX
```
- 合否は exit code だけで決める。xfail の印の残りは、決定論ゲートの `! grep -q XFAIL_452 backend/core/tests/test_I446_cross_api_tenant_isolation.py`（印に使う定数を消した＝9 ケースすべての印を外した）が exit code で確かめる。印を外し忘れて直っていたケースは `strict=True` の XPASS でこのコマンドが非ゼロになる。`-rxX` の一覧は記録のために出す（合否には使わない）
- FG: `adaptive_selection.py` の難易度の直し（4-1）を 1 か所だけ一時的に元の文字の絞り込みに戻すと、#446 の `adaptive-learning` のケースと TC-09・TC-10 が FAIL（exit 1）。戻す
