# I488 自動テスト: 学習統計の画面をクイズの記録から出す

実行コマンド（例）: `docker compose exec backend python -m pytest dashboard/tests/test_I488_analytics.py dashboard/tests/test_I459_analytics_zero_division.py dashboard/tests/test_I473_overview.py -q` / `docker compose exec frontend npm test -- --watchAll=false src/pages/__tests__/Statistics.test.tsx`
（pytest・Jest の全件は CI が PR ごとに流す。手元では変えたファイルのテストだけを流す）

共通の準備（BE）: 組織 A・B、A の科目 `数学`（問題 3 問）・`英語`（問題 3 問）、B の科目 `B科目`（問題 1 問）、A の利用者 `user_a`・`user_a2`（答え無し）、B の利用者 `user_b`。答えは `QuizSession(user, mode)` と `QuizAnswer(session, problem, is_correct, time_taken)` で作り、`answered_at` は作った後に `update()` で決まった時刻に書き換える（`QuizAnswer` は `(session, problem)` が一意なので、答えごとにセッションを作る）。「今」は `2026-11-14 08:00`（日本時間・土曜）を `build_analytics(..., now=...)` に渡す。API を呼ぶテストは本物の「今」で動くので、日付は `timezone.localdate()` からの相対で作る。

結果:
- backend（手元・2026-11-14・implement）: `dashboard/`・`test_I431`・`test_I455`・`test_I446`・`test_I493` の 248 件 pass（/simplify の後に `dashboard/` 55 件 pass）。CI の結果は review-gate で書く
- frontend（手元・2026-11-14・implement）: `Statistics.test.tsx`・`Dashboard.test.tsx` の 39 件 pass・`tsc --noEmit` OK・ESLint 違反 0。CI の結果は review-gate で書く

## バックエンド（`backend/dashboard/tests/test_I488_analytics.py`）

| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | 契約: 答えのある `user_a` で `GET /api/dashboard/analytics/` | status 200。最上位のキーの集合が `{"has_data","period","totals","trend","subject_breakdown"}` と一致。`period` のキーが `{"days","start_date","end_date","granularity"}`、`totals` が `{"study_seconds","answered_count","correct_count","accuracy_rate","studied_days"}`、`trend[i]` が `{"start_date","end_date","study_seconds","answered_count","correct_count","accuracy_rate"}`、`subject_breakdown[i]` が `{"subject_id","subject_name","study_seconds","answered_count","correct_count","accuracy_rate"}`。`daily_data`・`subject_distribution`・`performance_trends`・`mistake_patterns` のキーが無い |
| TC-02 | 期待値と 300 秒の上限（`build_analytics(user_a, 30, now=…)`）: 11-14 に 数学 3 問（正解・正解・不正解、`time_taken` 10・20・400）、11-10 に 英語 1 問（正解・30 秒）、10-15（30 日の範囲の外・1 日前）に 数学 1 問 | `period == {"days": 30, "start_date": date(2026,10,16), "end_date": date(2026,11,14), "granularity": "day"}`。`totals == {"study_seconds": 360, "answered_count": 4, "correct_count": 3, "accuracy_rate": 0.75, "studied_days": 2}`。`len(trend) == 30`・古い順・最初の `start_date == end_date == 2026-10-16`。11-14 の区切りが `{"study_seconds": 330, "answered_count": 3, "correct_count": 2, "accuracy_rate": 0.6667}`。答えの無い区切り（例 10-16）は 0・0・0・`accuracy_rate is None`。`has_data is True` |
| TC-03 | 区切りの境目: ① 90 日（`week`）: 11-08（日）に 1 問・11-09（月）に 2 問・08-17（期間の最初の日・月曜）に 1 問・08-16（範囲の外）に 1 問 ② 365 日（`month`）: 2025-11-15（期間の最初の日）に 1 問・2025-11-14（範囲の外）に 1 問・10-31 に 1 問・11-01 に 2 問 | ① `granularity == "week"`、`len(trend) == 13`、最初の区切り `08-17〜08-23` の `answered_count == 1`、`11-02〜11-08` が 1、最後の区切り `11-09〜11-14` が 2。08-16 の答えはどこにも入らない（合計 4）。② `granularity == "month"`、`len(trend) == 13`、最初の区切り `2025-11-15〜2025-11-30` が 1、`2026-10-01〜10-31` が 1、最後の区切り `2026-11-01〜11-14` が 2。合計 4 |
| TC-04 | 日本時間の日付の境界（7 日）: 答えの時刻を `2026-11-13 23:30`（日本時間）と `2026-11-14 00:30`（日本時間＝ UTC では 11-13 15:30） | `granularity == "day"`・`len(trend) == 7`（11-08〜11-14）。11-13 の区切りが 1・11-14 の区切りが 1。`totals.studied_days == 2` |
| TC-05 | `days` ごとの区切り（`_granularity`）: 1・7・30・31・32・90・180・181・365 | `day`・`day`・`day`・`day`・`week`・`week`・`week`・`month`・`month` |
| TC-06 | 科目の選択: 期間内に 数学 2 問（正解 2）・英語 4 問（正解 1）→ `?subject_id=<数学>` | `totals.answered_count == 2`・`totals.accuracy_rate == 1.0`・`trend` の合計の `answered_count` が 2。`subject_breakdown` は `subject_id` なしの応答と同じ（数学・英語の 2 件） |
| TC-07 | 不正な入力: `subject_id` が `abc`・`B科目` の ID・全体共有の科目（`organization=None`）の ID・存在しない ID（最大の ID + 1000）／`days=abc` と `subject_id=abc` を同時に | `subject_id` の 4 つはどれも status 400、body が `{"error": {"main_message": "科目の指定が正しくありません", "sub_message": "学習統計の科目の選択からやり直してください", "details": {}}}` と一致。組織に属さない利用者が A の `数学` の ID を送っても同じ 400 と同じ body。同時に不正なときは期間の 400 の body（`"期間の指定が正しくありません"`） |
| TC-08 | 認可と境界: ① 未認証 ② `user_b`（B）の答え・`user_a2` の答えを作り、`user_a` の答えも 1 問 ③ `user_a` の B科目 の問題への答え（不具合で残った想定）を 3 問 ④ 組織に属さない利用者（自分の答えを A の問題に 1 問持つ想定） | ① status 401 ② `user_a` の `totals.answered_count == 1`（②の他人の答え・③を含まない）③ 応答の JSON の文字列に `B科目` が含まれず、`subject_breakdown` の `subject_id` に B の ID が無い ④ status 200・`has_data is False`・`totals.answered_count == 0`・`subject_breakdown == []` |
| TC-09 | データ無し: 答えの無い `user_a2` で `GET …?days=7` | `has_data is False`、`totals == {"study_seconds": 0, "answered_count": 0, "correct_count": 0, "accuracy_rate": None, "studied_days": 0}`、`trend` が 7 件すべて 0 と `None`、`subject_breakdown == []` |
| TC-10 | 期間に答えが無い（全期間ではある）: 40 日前に 1 問 → `days=30` | `has_data is True`・`totals.answered_count == 0`・`subject_breakdown == []` |
| TC-11 | 科目別の並びと値: 期間内に 数学 3 問（`time_taken` 100・100・100・正解 2）・英語 2 問（`time_taken` 400・400〔300 秒で数える〕・正解 0）・理科 1 問（100 秒・正解 1）・化学 1 問（100 秒・正解 0）。理科・化学は組織 A にこのテストで作る（同じ学習時間・同じ解答数で、科目名の順を確かめるため） | `subject_breakdown` の科目名の並びが `["英語"(600秒), "数学"(300秒), "化学"(100秒・1 問), "理科"(100秒・1 問)]` — 学習時間の多い順、同じなら解答数の多い順、さらに同じなら科目名順（`化学` < `理科`）。英語 `accuracy_rate == 0.0`・数学 `0.6667` |
| TC-12 | クエリ数: 小さいデータ（1 科目・1 問）と大きいデータ（3 科目・200 日にわたり 120 問）で、`days=7` と `days=365`、`subject_id` なしとあり、の組み合わせで `CaptureQueriesContext` で 1 回のクエリ数を数える（キャッシュは各回の前に消す） | `subject_id` なしの 4 つの本数が等しく、`subject_id` ありの 4 つの本数が等しい（`==`）。加えて、本数が `subject_id` なしで `<= 3`・ありで `<= 4`（2026-11-14 に実測。日ごと・科目別・有無の 3 本と、科目の確かめ 1 本） |
| TC-13 | 境界の横断テスト（既存の合わせ込み）: `test_I431_studylogs_tenant_isolation.py` の TC-18 を答えで書き直したもの（自組織の科目の答え・他組織の問題への答え）、`test_I446_cross_api_tenant_isolation.py` の表（analytics に `ListCheck()` と `IdCheck("user", "query", "subject_id", "subject", 400)`） | すべて pass。TC-18 は他組織の科目名が応答に出ない（`_no_other(response)`）・`subject_breakdown` の科目名が `{"科目I431A"}` |
| TC-14 | I459 の合わせ込み（`test_I459_analytics_zero_division.py`）: TC-03（不正な `days` は同じ 400）・TC-04（省略・空 → `period.days == 30`・`len(trend) == 30`・`granularity == "day"`／`"1"` → `len(trend) == 1`／`"365"` → `period.days == 365`・`granularity == "month"`）・TC-06（401） | すべて pass。TC-01・02（`DailyStudySummary` の週の正答率）は消す |
| TC-15 | overview の退行（`test_I473_overview.py`） | 変えずにすべて pass（`_last_days` を `_daily_rows` に移しても overview の応答は同じ） |
| TC-16 | スキーマの作り直し（`test_I493_openapi_contract.py`） | 変えずにすべて pass（`backend/openapi.yaml` が作り直したものと同じ・警告 0） |

## フロントエンド（`frontend/src/pages/__tests__/Statistics.test.tsx`）
準備: `apiClient.get` をモックし、`/api/dashboard/analytics/` に契約どおりの応答を返す。`recharts` の `BarChart`・`LineChart`・`PieChart` はデータを `data-testid` つきの要素に出す軽いモックにする（`ResponsiveContainer` は子をそのまま出す）。`SubjectSelector`・`useAuth` もモックする。`QueryClientProvider`（再試行なし）と `MemoryRouter` で包む。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-20 | 契約どおりの応答（`totals.study_seconds=7530`・`answered_count=15`・`correct_count=10`・`accuracy_rate=0.6667`・`studied_days=5`・`trend` 30 件・`subject_breakdown` 2 件） | 「2時間5分」「67%」「15問」「5日」が出る。期間の範囲 `2026/10/16〜2026/11/14` が出る。棒グラフのモックのデータが 30 件。「データをエクスポート」のボタンと「間違いパターン」のタブが無い（`queryByRole` が null） |
| TC-21 | データ無し（`has_data=false`） | 「まだ記録がありません」と「クイズを始める」が出る。押すと `/quiz` へ進む。数字のカード・タブ・グラフのモックが無い |
| TC-22 | 形の違う応答（`trend` を欠く・`totals` を欠く・`granularity` が `"year"`）と取得の失敗（reject） | どれも「学習統計を読み込めませんでした」の `role="alert"` が出て、数字のカード（「0分」「0問」）とグラフのモックが 1 つも出ない。「再読み込み」を押すともう一度 `apiClient.get` が呼ばれる |
| TC-23 | 期間と科目の送り方: 開いた直後／期間で「直近 90 日」を選ぶ／`SubjectSelector` のモックから `onChange('5')` を呼ぶ | 開いた直後は `('/api/dashboard/analytics/', { params: { days: 30 } })`。90 日を選ぶと `{ params: { days: 90 } }`。科目 5 で `{ params: { days: 90, subject_id: '5' } }` |
| TC-24 | 期間に答えが無い（`has_data=true`・`totals.answered_count=0`・`accuracy_rate=null`・`subject_breakdown=[]`） | カードに「0分」「—」「0問」「0日」。「学習時間」のタブに「この期間の記録はありません」、グラフのモックが無い。「科目別（全科目）」のタブに「この期間の記録はありません」 |
| TC-25 | 区切りのラベル: `granularity="week"` で `trend` の最初が `2026-11-09〜2026-11-14`／`"month"` で `2026-11-01〜2026-11-14`／`"day"` で `2026-11-14` | 棒グラフのモックのラベルが `11/9〜`・`2026/11`・`11/14`（月日の頭に 0 を付けない）。正答率のタブの折れ線のデータで `accuracy_rate=null` の区切りが `null` のまま（0 にしない） |
| TC-26 | 科目別: `subject_breakdown` 2 件（英語 600 秒・7 問・0.7143／数学 300 秒・3 問・null でない 0.6667）・学習時間の合計が 0 の場合（`study_seconds=0` が 2 件） | 「科目別（全科目）」のタブに「英語」「10分」「71%」「7問」と「数学」。円グラフのモックのデータが 2 件。合計が 0 の場合は円グラフのモックが無く「学習時間の記録がありません」、科目のカードは出る |

## 決定論ゲート（自動実走）
<!-- 本イシューは pytest・Jest だけで確かめる（CI が PR ごとに流す）。grep などの決定論ゲートは足さない（写しのテストになるため・plan-writing-rules.md「決定論テストの対象の選び方」） -->

## false-green の確かめ（実装のときに行い、結果を書く）
- TC-12: 実装の途中で、区切りごとに 1 クエリにした形で流すと、7 日と 365 日の本数が違って落ちることを確かめる
- TC-22: `isDashboardAnalytics` を常に true を返す形にすると、TC-22 の「形の違う応答」の少なくとも 1 つ（`trend` を欠く）が落ちることを確かめる
- TC-08: 土台の `scope_to_user_org` を外すと ③ が落ちることを確かめる
- TC-03: 週の始まりを日曜にする（`weekday()` の代わりに `(weekday() + 1) % 7`）と落ちることを確かめる
- 結果（2026-11-14・implement）:
  - TC-12・TC-08・TC-03: 3 つの壊し方（区切りごとに 1 クエリ足す・`_answers` から `scope_to_user_org` を外す・週の始まりを日曜にする）を `backend/dashboard/selectors.py` に入れて流し、`test_query_count_is_constant`・`test_only_own_answers_in_own_org`・`test_user_without_org_sees_nothing`・`test_week_buckets` が FAILED → 元に戻して pass
  - TC-22: `getAnalytics` の形の確かめを外すと、TC-22 の形の違う応答 3 つ（`trend` を欠く・`totals` を欠く・知らない区切り）が FAILED → 元に戻して 12 件 pass
  - 気づき: タブの切り替えを `userEvent.click`（v13）で書いたところ、MUI のタブが切り替わらず、TC-24 の「科目別」の確かめが前のタブの同じ文言で通ってしまう形だった。`fireEvent.click` にして、タブが切り替わったうえで TC-24・25・26 が中身を見ていることを確かめた
