# I473 自動テスト: ダッシュボードの数字をクイズの記録から出す

実行コマンド（例）: `docker compose exec backend python -m pytest dashboard/tests/test_I473_overview.py -q` / `docker compose exec frontend npm test -- --watchAll=false src/pages/__tests__/Dashboard.test.tsx` / `docker compose --profile e2e run --rm e2e npx playwright test tests/quiz-session.spec.ts --retries=0`
（pytest・Jest・E2E の全件は CI が PR ごとに流す。手元では変えたファイルのテストだけを流す）

共通の準備（BE）: 組織 A・B、A の科目 `数学`（問題 5 問）・`英語`（問題 5 問）・`理科`（問題 0 問）、B の科目 `B科目`（問題 1 問）、A の利用者 `user_a`（`UserSubjectAccess` で 数学・英語・理科 を選択）・`user_a2`、B の利用者 `user_b`。答えは `QuizSession(user, mode)` と `QuizAnswer(session, problem, is_correct, time_taken)` で作り、`answered_at` は作った後に `update()` で決まった時刻に書き換える。「今」は `2026-11-13 08:00`（日本時間）を `build_overview(..., now=...)` に渡す。

結果:
- backend: （実装後に CI の結果を書く）
- frontend: （実装後に CI の結果を書く）
- e2e: （実装後に CI の結果を書く）

## バックエンド（`backend/dashboard/tests/test_I473_overview.py`）

| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | 契約: 答えのある `user_a` で `GET /api/dashboard/overview/` | status 200。最上位のキーの集合が `{"has_data","today","streak","totals","last_7_days","weak_subjects","recommendations"}` と一致。`today` のキーが `{"study_seconds","answered_count","correct_count","accuracy_rate"}`、`streak` が `{"current_days"}`、`totals` が `{"answered_count","correct_count","accuracy_rate"}`、`last_7_days[i]` が `{"date","study_seconds","answered_count","correct_count"}`、`weak_subjects[i]` が `{"subject_id","subject_name","answered_count","accuracy_rate"}`、`recommendations[i]` が `{"kind","subject_id","subject_name","reason"}`。`subject_id` は int、`has_data` は bool |
| TC-02 | 期待値と 300 秒の上限: 今日（日本時間）に 3 問（正解・正解・不正解、`time_taken` 10・20・400）、11-10 に 1 問（正解・30 秒） | `today == {"study_seconds": 330, "answered_count": 3, "correct_count": 2, "accuracy_rate": 0.6667}`、`totals == {"answered_count": 4, "correct_count": 3, "accuracy_rate": 0.75}`、`has_data is True` |
| TC-03 | 日本時間の日付の境界: 答えの時刻を `2026-11-12 23:30`（日本時間）と `2026-11-13 00:30`（日本時間＝ UTC では 11-12 15:30）にする | `today.answered_count == 1`。`last_7_days` の `2026-11-12` が 1・`2026-11-13` が 1 |
| TC-04 | 連続日数: ① 11-12・11-11 に答え・今日なし → 2 ② ①に今日を足す → 3 ③ 11-13・11-11（11-12 なし）→ 1 ④ 11-10 だけ → 0 ⑤ 答えなし → 0 | 各 `streak.current_days` が 2・3・1・0・0 |
| TC-05 | 直近 7 日: 11-07（6 日前・範囲の最初の日）に 1 問・11-06（範囲外）に 1 問・11-13 に 2 問 | `len(last_7_days) == 7`、日付が `2026-11-07`〜`2026-11-13` の古い順、11-07 が 1・11-13 が 2・ほかは `answered_count == 0` かつ `study_seconds == 0`。11-06 の答えはどこにも入らない |
| TC-06 | 今日の復習の回を含める: `mode='review'` のセッションで今日 2 問（正解 1） | `today.answered_count == 2`・`today.correct_count == 1`・`totals.answered_count == 2` |
| TC-07 | データ無し: 答えの無い `user_a2` | `has_data is False`、`today == {"study_seconds": 0, "answered_count": 0, "correct_count": 0, "accuracy_rate": None}`、`totals.accuracy_rate is None`、`streak.current_days == 0`、`last_7_days` が 7 件すべて 0、`weak_subjects == []` |
| TC-08 | 科目の選択: 今日 数学 2 問（正解 2）・英語 6 問（正解 1） → `?subject_id=<数学>` | `today.answered_count == 2`・`totals.accuracy_rate == 1.0`・`last_7_days` の今日が 2。`weak_subjects` と `recommendations` は `subject_id` なしの応答と同じ（英語が weak に入る） |
| TC-09 | 不正な `subject_id`: `abc`・`B科目` の ID・全体共有の科目（`organization=None` で作る）の ID・存在しない ID（最大の ID + 1000） | どれも status 400、body が `{"error": {"main_message": "科目の指定が正しくありません", "sub_message": "ダッシュボードの科目の選択からやり直してください", "details": {}}}` と一致（4 つの body が同じ） |
| TC-10 | 間違いやすい分野の境界: 科目 P（4 問・0 正解）・Q（5 問・3 正解＝60%）・R（10 問・7 正解＝70%）・S（5 問・0 正解）・T（6 問・3 正解＝50%）・U（5 問・1 正解＝20%） | `weak_subjects` の `subject_name` が `[S, U, T]`（0%・20%・50% の低い順・最大 3 件）。P（4 問）・R（ちょうど 70%）は入らず、Q は 4 件目で切られる。`accuracy_rate` は `0.0`・`0.2`・`0.5` |
| TC-11 | おすすめ: `user_a` が 英語 を 5 問（正解 1）今日・数学は 10 日前に 5 問（正解 5）・理科（問題 0 問）は答え無し。加えて `StudyLog(user_a, subject=None)` を 1 件作る（引き継ぎ 1） | `recommendations == [{"kind": "weak_subject", "subject_id": 英語, "subject_name": "英語", "reason": "正答率が 20% です。復習しましょう"}, {"kind": "unstudied_subject", "subject_id": 数学, "subject_name": "数学", "reason": "この 7 日間、解いていません"}]`（理科は問題が無いので出ない。科目が空の StudyLog があっても数学が消えない） |
| TC-11b | おすすめの上限: weak が 3 科目・unstudied が 2 科目ある | `len(recommendations) == 3` で、3 件とも `kind == "weak_subject"` |
| TC-12 | クエリ数: 小さいデータ（1 科目・1 問）と大きいデータ（3 科目・30 日にわたり 60 問）で、`CaptureQueriesContext` で overview 1 回のクエリ数を数える（キャッシュは各回の前に消す） | 2 つの本数が等しい（`==`）。かつ本数が 15 以下（実装後に数えた本数をここに書き足す） |
| TC-13 | 認可と境界: ① 未認証 ② `user_b`（B）の答え・`user_a2` の答えを作り、`user_a` の答えも 1 問 ③ `user_a` の B科目 の問題への答え（不具合で残った想定）を 3 問 ④ 組織に属さない利用者（自分の答えを A の問題に 1 問持つ想定） | ④ status 200・`has_data is False`・`totals.answered_count == 0`・`weak_subjects == []`・`recommendations == []`。① status 401 ② `user_a` の `totals.answered_count == 1`（①③の答えを含まない）③ 応答の JSON の文字列に `B科目` が含まれず、`weak_subjects`・`recommendations` の `subject_id` に B の ID が無い |
| TC-14 | 経路の削除: 認証して `GET /api/dashboard/recommendations/` | status 404 |
| TC-16 | 引き継ぎ 3: ① `get_user_selected_subjects(user_a)` を 2 回（1 回目でキャッシュに入れ、2 回目はキャッシュから）② `UserSubjectAccess` を 1 件足す ③ キーの関数 | ① 2 回目（キャッシュの経路）の科目 ID の並びが、1 回目（DB の経路・`order_by('name')`）の並びと一致し、`Subject.objects.filter(...).order_by('name')` の並びとも一致する（科目は名前の順と作った順がずれるように作る）② 足した後の呼び出しに新しい科目が入る（signals がキーを消した）③ `user_subjects_cache_key(1, 7, False) == "user_subjects_1_org_7_count_False"` |

## バックエンド（既存のテストの合わせ込み・追加）

| TC | 内容 | 期待値 |
|---|---|---|
| TC-15 | 引き継ぎ 2（`backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py` に追加）: `user_a` の進行中の記録を 自組織の科目・科目なし・他組織の科目 の 3 件作り、`POST /api/study/logs/` で新しい記録を作る | status 201。自組織の科目・科目なしの 2 件は `is_active == False`、他組織の科目の 1 件は `is_active == True` のまま |
| TC-17 | 境界の横断テスト: `test_I431_studylogs_tenant_isolation.py` の TC-17（overview）・TC-19（おすすめ）を新しいキーで書き直したもの、`test_I446_cross_api_tenant_isolation.py` の表（overview に `IdCheck("user", "query", "subject_id", "subject", 400)`・recommendations の行を削除）、`test_I455_org_scoped_querysets.py`、`test_I459_analytics_zero_division.py`（recommendations のテストを削除） | すべて pass。TC-17 は他組織の科目名が応答に出ない（`_no_other(response)`）・`weak_subjects` の科目が自組織だけ。TC-19 は `recommendations` の `subject_id` が自組織の科目だけ |

## フロントエンド（`frontend/src/pages/__tests__/Dashboard.test.tsx`）
準備: `apiClient.get` をモックし、`/api/dashboard/overview/` に契約どおりの応答を返す。`react-chartjs-2` の `Line`・`Doughnut` はラベルとデータを `data-testid` つきの要素に出す軽いモックにする。`SubjectSelector`・`TodayReviewCard`・`useAuth`・`useNotifications` もモックする。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-20 | 契約どおりの応答（`today.study_seconds=330`・`streak.current_days=2`・`totals.answered_count=12`・`accuracy_rate=0.75`・`last_7_days` 7 件・`weak_subjects` 1 件〔英語・0.5・10 問〕・`recommendations` 1 件〔数学・id 4〕） | 「5分」「2日」「12」「75%」が出る。見出し「直近 7 日の学習時間」がある。推移のグラフのデータが 7 件。間違いやすい分野に「英語」と「50%」と「解答数: 10問」。おすすめの「練習する」を押すと `navigate('/quiz?subject=4')` が呼ばれる。`data-testid="stat-answered-count"` の文字が `12` |
| TC-21 | データ無し（`has_data=false`・比率 `null`・7 件すべて 0・一覧が空） | 「まだ解答の記録がありません」が出て、ドーナツのモックが描かれない。正答率のカードが「—」。間違いやすい分野に「データがありません。まずは問題を解いてみましょう！」 |
| TC-22 | 形の違う応答（`totals` を欠く）と取得の失敗（reject） | どちらも「ダッシュボードの数字を読み込めませんでした」の `role="alert"` が出て、数字のカード（「0分」「0日」「0%」）が 1 つも出ない |
| TC-23 | 科目の選択: `SubjectSelector` のモックから `onChange('5')` を呼ぶ | `apiClient.get` が `('/api/dashboard/overview/', { params: { subject_id: '5' } })` で呼ばれる。`'all'` のときは `{ params: {} }` |
| TC-25 | 正答率 70% 未満の科目が無い（`has_data=true`・`weak_subjects=[]`） | 「正答率が 70% 未満の科目はありません」が出る |

## E2E（`e2e/tests/quiz-session.spec.ts` に追加）

| TC | 内容 | 期待値 |
|---|---|---|
| TC-24 | `e2e_user_a` で `/dashboard` を開き、`data-testid="stat-answered-count"` の数を読む → 「クイズを始める」→「E2E Quiz Subject」→ 選択肢を 1 つ選び結果が出るまで待つ → `/dashboard` を開き直す | `stat-answered-count` の数が、前に読んだ数 + 1 になる（E2E の DB は流すたびに答えが増えるので、前後の差で見る） |

## 決定論ゲート（自動実走）
<!-- 本イシューは pytest・Jest・E2E だけで確かめる（CI が PR ごとに流す）。grep などの決定論ゲートは足さない（写しのテストになるため・plan-writing-rules.md「決定論テストの対象の選び方」） -->

## false-green の確かめ（実装のときに行い、結果を書く）
- TC-12: 実装の途中で、連続日数を 1 日 1 クエリにした形（今の作り）で流すと、2 つの本数が違って落ちることを確かめる
- TC-22: `isDashboardOverview` を常に true を返す形にすると、TC-22 の「形の違う応答」が落ちることを確かめる
- TC-13: 土台の `scope_to_user_org` を外すと ③ が落ちることを確かめる
- TC-03: `TruncDate` に `tzinfo=datetime.timezone.utc` を渡すと落ちることを確かめる
- 実装前のため未実行（実装の後でないと動かない）
