# I466 自動テスト: 間違い分析と苦手を優先した出題を画面につなぐ

実行コマンド（例）: `docker compose exec backend python -m pytest problems/tests/test_I466_weakness.py problems/tests/test_I466_weak_mode.py dashboard/tests/test_I466_overview_weakness.py core/tests/test_I466_celery_schedule.py studylogs/tests/test_I466_removed_routes.py -q` / `docker compose exec frontend npm test -- --watchAll=false src/pages/__tests__/Dashboard.test.tsx src/pages/__tests__/QuizSession.weak.test.tsx` / `docker compose --profile e2e run --rm e2e npx playwright test tests/quiz-session.spec.ts --retries=0`
（pytest・Jest・E2E の全件は CI が PR ごとに流す。手元では変えたファイルのテストだけを流す）

共通の準備（BE）: 組織 A・B。A の科目 `数学`（問題 p1〜p6）・`英語`（上級の問題 e1〜e5）、B の科目 `B科目`（問題 b1）。A の利用者 `user_a`・`user_a2`、B の利用者 `user_b`。答えは `QuizSession(user, mode)` と `QuizAnswer(session, problem, is_correct, time_taken)` で作り、`answered_at` は作った後に `update()` で決まった時刻に書き換える。「今」は `2026-11-17 08:00`（日本時間）を関数の `now` に渡す。難易度は 1=初級（easy）・2=中級（medium）・3=上級（hard）。

結果:
- backend（implement・2026-11-17・手元で変えたファイルのテスト）: I466 の新しいテスト 37 件 pass。`problems/tests/`・`dashboard/tests/`・`studylogs/tests/`・`core/tests/test_I446…`・`test_I493…`・`test_I466…` の 733 件 pass（スキーマの作り直しの後）
- frontend（同）: `Dashboard.test.tsx` 54 件・`QuizSession.*.test.tsx` 4 ファイル pass。型チェック（`tsc --noEmit`）エラー 0・ESLint 違反 0
- e2e: CI で流す（TC-40 を `e2e/tests/quiz-session.spec.ts` に追加）

## バックエンド: 苦手の判定（`backend/problems/tests/test_I466_weakness.py`）

| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | `is_weak(answered, correct)` の境界: (4,0)・(5,3)・(5,4)・(10,7)・(5,0)・(0,0) | `False`・`True`（60%）・`False`（80%）・`False`（ちょうど 70%）・`True`・`False`（例外にならない） |
| TC-02 | `weak_difficulties(user_answers(user_a))`: 初級 6 問（正解 5）・中級 5 問（正解 2）・上級 10 問（正解 3）。上級は 数学 と 英語 にまたがる | `[{"difficulty": "hard", "answered_count": 10, "accuracy_rate": 0.3}, {"difficulty": "medium", "answered_count": 5, "accuracy_rate": 0.4}]`（初級は 83% で入らない・正答率の低い順） |
| TC-03 | 同じ正答率の並び・空: ① 初級 5 問（正解 2）・上級 5 問（正解 2）② 答えなし ③ 中級 4 問（正解 0） | ① `difficulty` の並びが `["easy", "hard"]`（同じ 40% は易しい順）② `[]` ③ `[]`（5 問未満） |
| TC-04 | `rushed_mistakes`: 直近 30 日に 20 問（正解 16 問は 40 秒・不正解 2 問は 5 秒・不正解 2 問は 40 秒） | `{"mistake_count": 4, "rushed_count": 2, "rushed_rate": 0.5}`（平均 36.5 秒・半分 18.25 秒未満の間違いが 2） |
| TC-05 | `rushed_mistakes` の境界: ① TC-04 から正解を 1 問消す（19 問）② TC-04 に `time_taken=0` の不正解を 5 問足す ③ 正解 18 問 10 秒・正解 1 問 3000 秒・不正解 1 問 30 秒 ④ 正解 16 問 40 秒・不正解 1 問 5 秒・不正解 3 問 40 秒 ⑤ TC-04 の正解 1 問の `answered_at` を 31 日前にする | ① `None` ② `None`（間違い 9・急いだ 2 で 22%。0 秒の答えは急いだにも平均にも入らない）③ `None`（平均は 300 秒で頭打ちして 25.5 秒・30 秒は急いでいない。頭打ちしないと急いだになる）④ `{"mistake_count": 4, "rushed_count": 1, "rushed_rate": 0.25}`（ちょうど 25% は出す）⑤ `None`（期間内は 19 問） |
| TC-06 | 間違いが 0: 直近 30 日に 20 問すべて正解 | `None` |
| TC-16 | 組織の境界: ① `user_a` の答えは 0 件で、B科目 の問題への `user_a` の答え（不具合で残った想定）を上級・不正解・5 秒で 25 問 ② `user_b` が A の問題に答えた記録は作れないので、`user_a2`（同じ組織の別人）が 上級 を 10 問すべて不正解 | ① `weak_difficulties(user_answers(user_a)) == []`・`rushed_mistakes(user_answers(user_a), now) is None` ② `user_a` の `weak_difficulties` に上級が入らない（本人の答えだけ） |

## バックエンド: ダッシュボード（`backend/dashboard/tests/test_I466_overview_weakness.py`）

| TC | 内容 | 期待値 |
|---|---|---|
| TC-07 | 契約: `user_a` に初級 6 問（正解 5）・中級 5 問（正解 2）・上級 10 問（正解 3。うち不正解 4 問は 5 秒・ほかは 40 秒）で `GET /api/dashboard/overview/`。未認証でも 1 回 | status 200。最上位のキーの集合が `{"has_data","today","streak","totals","last_7_days","weak_subjects","recommendations","weak_difficulties","rushed_mistakes"}`。`weak_difficulties == [{"difficulty": "hard", "answered_count": 10, "accuracy_rate": 0.3}, {"difficulty": "medium", "answered_count": 5, "accuracy_rate": 0.4}]`、`rushed_mistakes == {"mistake_count": 11, "rushed_count": 4, "rushed_rate": 0.3636}`（21 問・平均 33.3 秒）。未認証は 401 |
| TC-08 | 科目の選択に関係しない: TC-07 のデータで `?subject_id=<数学>` | `weak_difficulties` と `rushed_mistakes` が `subject_id` なしの応答と同じ |
| TC-09 | 当てはまらない: 答えの無い `user_a2` | `weak_difficulties == []`・`rushed_mistakes is None` |
| TC-34 | スキーマ: `core/tests/test_I493_openapi_contract.py`（作り直した `backend/openapi.yaml` と一致）と CI の `API Types Up To Date` | pass |

## バックエンド: 苦手を優先の出題（`backend/problems/tests/test_I466_weak_mode.py`）

準備（TC-10〜TC-13）: 数学 の p1・p2・p4・p5・p6（初級）と p3・p7（上級）。英語 の上級 e1〜e5 に `user_a` が 5 日前に 5 問答えて正解 1。数学 の答え（古い順）: p5 正解（20 日前）・p5 正解（18 日前）・p6 正解（15 日前）・p3 不正解（10 日前）・p1 正解（9 日前）・p2 不正解（8 日前）・p1 不正解（3 日前）・p6 正解（2 日前）・p2 正解（1 日前）。p4・p7 は未回答。このとき全科目で、上級は 6 問中正解 1（17%・苦手）、初級は 8 問中正解 6（75%・苦手でない）。数学 の本人の答えは 9 件（5 件以上）。
最後の答え: p1 不正解（3 日前）・p2 正解（1 日前）・p3 不正解（10 日前）・p5 正解（18 日前）・p6 正解（2 日前）・p4・p7 なし。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-10 | 並び: `order_weak_first(available_problems(user_a, 数学), user_a, 数学)` | 2 つ目の戻り値が `False`。並びが `[p3, p1, p7, p4, p5, p6, p2]`（段 0: 最後が不正解の p3〔10 日前〕・p1〔3 日前〕を古い順／段 1: 苦手な上級で段 0 でない p7／段 2: 未回答の p4 → 最後の答えの古い順に p5・p6・p2。p2 は前に間違えたが最後は正解なので段 2） |
| TC-11 | API で回を進める: `POST /api/quiz/`（`subject=数学`・`mode="weak"`）→ `GET next_problem` → その問題に正解で `submit_answer` → `GET next_problem` | 開始は 201・`mode == "weak"`・`total_problems == 7`。1 回目の `id == p3`・`is_weak_fallback is False`・`is_review_mode is False`。2 回目の `id == p1`（同じ回で答えた p3 は続けて出ない） |
| TC-12 | 判定できないとき: ① 数学 の `user_a` の答えを 4 件にする ② 5 件にする | ① `next_problem` の `is_weak_fallback is True`（問題は数学のどれか）② `False` |
| TC-13 | 2 周目: `weak` の回で 7 問を並びの順にすべて答え（p3 だけ不正解・ほかは正解）、`next_problem` | `is_review_mode is True`・`id == p3`（最近の 5 問 p7・p4・p5・p6・p2 を除いた残り p3・p1 のうち、最後が不正解の p3 が先。乱数ではなく苦手を優先の並べ方） |
| TC-14 | 開始の検証: ① `mode="bogus"` ② 同じ `Idempotency-Key` で `mode="normal"` の後に `mode="weak"` ③ 他組織の科目（B科目）で `mode="weak"` | ① 400 ② 2 回目は 422（body の `main_message` が「Idempotency-Key が別の内容で使用されています」）③ 通常のモードで他組織の科目を指定したときと同じ status と body |
| TC-15 | クエリ数（F4）: 候補 3 問の科目と 40 問の科目（どちらも本人の答え 10 件以上・最後が不正解の問題を含む）で、`weak` の回の `QuizService.get_next_problem(session)` を `CaptureQueriesContext` で数える | 2 つの本数が等しい（`==`） |
| TC-17 | 組織の境界: TC-10 の準備に、数学の中級の未回答の問題 p8 を足す。① `user_a` の B科目 の中級の問題 b1 への答え 5 件（すべて不正解・不具合で残った想定。数えてしまうと中級が苦手になり p8 が段 1 に上がる）② `user_a2` が p4 に不正解 ③ 科目なしの `weak` の回で、未回答の問題を全部出し切るまで `next_problem` を繰り返す | ①② 並びが `[p3, p1, p7, p4, p8, p5, p6, p2]`（b1 は出ない・p8 は段 2・p4 の段は `user_a2` の答えで変わらない）③ 出た問題の組織がすべて組織 A |
| TC-18 | 通常・復習の回: `mode="normal"` の回の `next_problem` | 応答に `is_weak_fallback` があり `False` |

## バックエンド: 片付け

| TC | 内容 | 期待値 |
|---|---|---|
| TC-30 | 経路の削除（`backend/studylogs/tests/test_I466_removed_routes.py`）: 認証した `user_a` で `GET /api/study/mistake-analysis/analyze/`・`GET /api/study/mistake-analysis/patterns/`・`POST /api/study/mistake-analysis/refresh_analysis/`・`GET /api/study/adaptive-learning/proficiency_analysis/`・`POST /api/study/adaptive-learning/select_problems/`・`GET /api/study/adaptive-learning/learning_path/` | すべて status 404 |
| TC-31a | 材料・書き込みの不在（実装のときに 1 回流す・CI には入れない。plan 9 章）: `bash -c '! grep -rnE "ProblemAttempt|MistakePattern|LearningSuggestion|LearningWeakness|mistake_analysis|adaptive_selection|proficiency_cache" backend --include=*.py --exclude-dir=migrations --exclude-dir=tests --exclude=models.py --exclude=admin.py'` | exit 0 |
| TC-31b | ダッシュボードが苦手の基準を自分で定義していない（同上・1 回）: `bash -c '! grep -nE "^(WEAK_MIN_ANSWERED|WEAK_ACCURACY_BELOW) *=" backend/dashboard/selectors.py'` | exit 0 |
| TC-31c | ダッシュボードが基準を `weakness.py` から読む（同上・1 回）: `bash -c 'grep -q "from problems.services.weakness import" backend/dashboard/selectors.py'` | exit 0 |
| TC-32 | 定期処理（`backend/core/tests/test_I466_celery_schedule.py`）: `core.celery.app.conf.beat_schedule` の全項目 | ① どの項目の `schedule` も `celery.schedules.crontab` のインスタンス（秒の数は無い）② どの項目の `task`（`<module>.<name>`）も `importlib.import_module(<module>)` に `<name>` があり、`.delay` を持つ（消したタスクを指していない）③ 項目の名前に `analyze-mistake-patterns`・`cleanup-expired-suggestions` が無い |
| TC-33 | 回帰: `studylogs/tests/test_I431_studylogs_tenant_isolation.py`・`core/tests/test_I446_cross_api_tenant_isolation.py`（`POST api/quiz/` に `mode: "weak"` の行を追加）・`studylogs/tests/test_I452_quiz_review.py`・`studylogs/tests/test_I455_org_scoped_querysets.py`・`dashboard/tests/test_I473_overview.py`（TC-01 のキーの集合に 2 つを足す） | すべて pass |

## フロントエンド（`frontend/src/pages/__tests__/Dashboard.test.tsx` に追加）
準備: 既存の TC-20 の準備と同じ（`apiClient.get` のモック・チャートの軽いモック）。応答に `weak_difficulties`・`rushed_mistakes` を足す。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-20 | `weak_difficulties = [{difficulty: "hard", answered_count: 12, accuracy_rate: 0.3}, {difficulty: "medium", answered_count: 6, accuracy_rate: 0.65}]` | 「間違いやすい分野（全科目）」のカードの中に、見出し（level 3）「難易度別」・「上級」「30%」「解答数: 12問」（科目の行の「解答数: 10問」と重ならない数）・「中級」「65%」「解答数: 6問」。`weak_difficulties = []` の応答では「難易度別」が無い |
| TC-21 | `rushed_mistakes = {mistake_count: 4, rushed_count: 2, rushed_rate: 0.5}` / `null` | `role="status"` で「急いで答えた問題の間違いが多めです（間違いの 50%）。落ち着いて解きましょう」が出る / 出ない |
| TC-22 | 「苦手を優先して始める」: 科目を選んだ状態（科目 4・問題あり） | ボタン（`data-testid="start-weak-quiz-button"`）と「間違えた問題や正答率の低い難易度から出します」が出る。押すと `navigate('/quiz?subject=4&mode=weak')` |
| TC-23 | 「すべて」で対象が 2 件: 「苦手を優先して始める」→ ダイアログで 2 件目の科目 → 閉じて「クイズを始める」→ ダイアログで 1 件目の科目 | 1 回目は `navigate('/quiz?subject=<2件目>&mode=weak')`、2 回目は `navigate('/quiz?subject=<1件目>')`（ダイアログが押したボタンのモードを使う） |
| TC-24 | 始められない（学ぶ科目に問題が無い） | 「苦手を優先して始める」が `disabled` |
| TC-26 | おすすめ: `recommendations = [{kind: "weak_subject", subject_id: 4, ...}, {kind: "unstudied_subject", subject_id: 5, ...}]` の「練習する」をそれぞれ押す | `navigate('/quiz?subject=4&mode=weak')`・`navigate('/quiz?subject=5')` |
| TC-27 | 形の違う応答: ① `weak_difficulties` を欠く ② `difficulty: "extreme"` ③ `rushed_mistakes: {mistake_count: 4}`（欠けた数） | どれも「ダッシュボードの数字を読み込めませんでした」の `role="alert"` が出る |

## フロントエンド（`frontend/src/pages/__tests__/QuizSession.weak.test.tsx`・新規）
準備: `QuizSession.review.test.tsx` と同じモック（`apiClient`・`react-router-dom` の `useNavigate`）。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-25 | `/quiz?subject=1&mode=weak` で開く。`POST /api/quiz/` は `{id: 9, mode: "weak", ...}`、`next_problem` は ① `is_weak_fallback: true` ② `false` | `apiClient.post` が `('/api/quiz/', {subject: '1', mode: 'weak'}, ...)` で 1 回呼ばれる。「苦手を優先」の印が出る。① 「この科目はまだ解答が少ないため、いつもの順で出題しています」が出る ② 出ない。「今日の復習」の印は出ない |
| TC-28 | 終えた `weak` の回を開く（`/quiz/9`・`GET /api/quiz/9/` が `{is_active: false, mode: "weak", subject: 1, ...}`）→「もう一度挑戦」 | `apiClient.post` の本文が `{subject: 1, mode: 'weak'}` |
| TC-29 | いつものクイズ（`/quiz?subject=1`） | 開始の本文に `mode` が無い。「苦手を優先」の印が出ない（既存の `QuizSession.review.test.tsx` の「いつものクイズでは印を出さず…」も pass） |

## E2E（`e2e/tests/quiz-session.spec.ts` に追加）

| TC | 内容 | 期待値 |
|---|---|---|
| TC-40 | `e2e_user_a` で `/dashboard` を開き、「苦手を優先して始める」→（ダイアログが出たら）「E2E Quiz Subject」 | URL が `/quiz?subject=<ID>&mode=weak` で、「苦手を優先」の印と問題文が出る |

## 決定論ゲート（自動実走）
<!-- 本イシューの決定論のテストは pytest（TC-15・TC-32）と、実装のときに 1 回流す TC-31a〜c だけ。TC-31a〜c は消したモジュールの再導入が意図的な変更でしか起きないため CI に入れない（plan-writing-rules.md「決定論テストの対象の選び方」） -->

## false-green の確かめ（実装のときに行い、結果を書く）
- 結果（2026-11-17・implement）:
  - TC-15: 候補ごとに `answers.filter(problem=p).first()` を流す形を `weakness.py` に入れると `assert 8 == 45` で落ちた → 戻して pass
  - TC-16・TC-05 ③: `user_answers` を `filter(session__user=user)` に、平均の頭打ちを外す形にすると、`test_other_org_and_other_people_are_not_counted`・`test_rushed_mistakes_caps_long_answers` が落ちた
  - TC-17: 最初の形（他組織の上級の答え 1 件）は、組織の絞り込みを外しても落ちなかった（上級はもともと苦手で、並びが変わらない false-green）。他組織の中級の答え 5 件と未回答の中級 p8 を足し、外すと p8 が 4 番目に上がって落ちることを確かめた → 戻して pass
  - TC-32: テストの中に失敗の注入（`test_checks_catch_interval_and_missing_task`。秒の間隔・消したタスクを指す予定）を入れ、どちらも見つかることを CI で毎回確かめる
  - TC-31a〜c: `$TMPDIR` の写しに ① `from .models import ProblemAttempt` ② `WEAK_MIN_ANSWERED = 5` ③ import の行を消す、を入れると、3 本とも exit 1。本物のファイルでは 3 本とも exit 0
  - TC-27: `isDashboardOverview` の `weak_difficulties` の確かめを外すと ①② が落ちた → 戻して pass
- TC-15: `order_weak_first` を、候補の問題ごとに最後の答えを問い合わせる形（ループで `QuizAnswer...filter(problem=p).first()`）に一時的に変えると、2 つの本数が違って落ちることを確かめる
- TC-16・TC-17: `user_answers` を `QuizAnswer.objects.filter(session__user=user)`（組織で絞らない）に一時的に変えると落ちることを確かめる
- TC-05 ③: 頭打ち（`Least`）を外すと落ちることを確かめる
- TC-32: `beat_schedule` に ① `'schedule': 30.0` の項目 ② `'task': 'studylogs.tasks.analyze_mistake_patterns_task'` の項目、をテストの中で一時的に足すと（`mock.patch.dict`）、それぞれ落ちることを確かめる
- TC-31a〜c: ① `backend/studylogs/views.py` に `from .models import ProblemAttempt` を足すと TC-31a ② `backend/dashboard/selectors.py` に `WEAK_MIN_ANSWERED = 5` の行を足すと TC-31b ③ `from problems.services.weakness import` の行を消すと TC-31c が、それぞれ exit 1 になることを確かめ、元に戻す
- TC-27: `isDashboardOverview` の `weak_difficulties` の確かめを外すと ① ② が落ちることを確かめる
