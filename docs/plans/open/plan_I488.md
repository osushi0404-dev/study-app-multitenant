# I488 計画書: 学習統計の画面をクイズの記録から出す（analytics の契約の 1 本化・期間と区切り・科目別の内訳）

## 基本情報
- **計画書ID**: plan_I488
- **関連イシュー**: #488
- **Draft PR**: #515
- **作成根拠資料**: docs/issues/open/I488.md（起点イシュー・GitHub #488 の本文の写し・設計確認メモつき）
- **実装後評価**: docs/reviews/open/I488_review.md
- **作成日**: 2026-11-14

## 1. 背景/目的
- 学習統計の画面（`/statistics`）は、クイズを解いても推移・科目別の内訳が空か 0 のまま（#487 の手動テスト No.6 で「学習統計の数字が 0 のままなのは #488」と記録済み）。
- 目的: クイズの答えの記録（`QuizAnswer`）から、選んだ期間の推移・数字・科目別の内訳を出す。#473 の集計（`backend/dashboard/selectors.py`）を使い回してダッシュボードと同じ数え方にし、API の形をシリアライザと OpenAPI の型（#493 の仕組み）で固定する。

### 調査結果
**原因の概要**: 統計画面の数字は、どこからも書き込まれない表（`DailyStudySummary`・`StudyLog`）から数えている。しかも画面が読む名前と API が返す名前がほとんど合っておらず、画面は受け取れなかった値を黙って空の配列で埋めていたので、壊れていることが見えなかった（#473 のダッシュボードと同じ形の不具合）。

**詳細な原因分析**（2026-11-14・develop 88284aaf で確認）:
1. `DashboardAnalyticsView.get`（`backend/dashboard/views.py:43-99`）は `DailyStudySummary` を 1 日ずつ読み（`:63-79`・日数ぶんのクエリ）、`StudyLog` を科目で集計し（`:82-87`）、週ごとに `DailyStudySummary` を集計する（`_get_performance_trends`・`:101-128`・週の数ぶんのクエリ）。応答のキーは `daily_data`・`subject_distribution`・`performance_trends`・`subject_breakdown`（プルダウン用の科目一覧）。
2. 画面（`frontend/src/pages/Statistics.tsx:100-103`）は `study_time_trend`・`accuracy_trend`・`subject_breakdown`・`mistake_patterns` を読み、無ければ `|| []`。名前が合うのは `subject_breakdown` だけで、中身も違う（画面は `subject_name`・`time_spent`・`accuracy`・`problems_solved` を期待）。
3. 画面は `period`（`daily`/`weekly`/`monthly`）と `subject` を送るが（`Statistics.tsx:67-72`）、API は `days` しか読まない（`AnalyticsQuerySerializer`・`backend/dashboard/serializers.py:12-16`）。
4. 「今日」は `timezone.now().date()`（UTC・`views.py:57`）。期間は「今日から `days` 日前〜今日」の `days + 1` 日。
5. 書き出しのボタンは `console.log` だけ（`Statistics.tsx:84-87`）。「間違いパターン」のタブは API が返さないキーを読むだけ（`:367-392`）。
6. 画面の部品 `TabPanel` が描画の中で定義されている（`Statistics.tsx:115-119`）。描くたびに別の部品になり、タブの中身が作り直される。`SubjectSelector` に付けた `mountKey`（`:57-62`）は、最初の 1 回しか変わらないので意味が無い（ダッシュボードは付けずに使っている）。
7. グラフは `recharts`（`Statistics.tsx:17-30`）。`recharts` を使うのはこの画面だけで、ダッシュボードは `chart.js`（`react-chartjs-2`）。

**#473 で作ったもの（使い回す）**: `backend/dashboard/selectors.py` の `_answers(user)`（本人の答えで自組織の科目の問題へのもの・`scope_to_user_org`）・`_counts()`（学習時間〔1 問 300 秒まで〕・解答数・正解数）・`_rate()`（0〜1・小数第 4 位・0 件は `None`）・`_start_of()`（日本時間の 0 時）・`_last_days()`（日ごとの集計を 1 クエリで取り 7 件に並べる）。応答の形はシリアライザで固定し、`backend/core/openapi.py` の `CONTRACT_PATHS` に入れたパスだけが `backend/openapi.yaml` と画面の型（`frontend/src/types/api/schema.d.ts`）に入る（I493。作り直し忘れは CI の `core/tests/test_I493_openapi_contract.py` と `API Types Up To Date` ジョブが止める）。#496 の本文で「統計画面の型は #488 が置き換える」と決まっている。

**関係するテスト（古い形を前提にしているもの）**:
- `backend/dashboard/tests/test_I459_analytics_zero_division.py`（TC-01・02 は `DailyStudySummary` と `performance_trends`、TC-04 は `daily_data` の件数を見る）
- `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py:525-536`（TC-18 は `StudyLog` と `subject_distribution` を見る）
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py:269`（経路の表は `LIST` だけ）

**環境の前提**: `docker compose ps` で backend・db・frontend・redis が動いている（2026-11-14 確認）。設定は `TIME_ZONE = 'Asia/Tokyo'`・`USE_TZ = True`。時刻を止めるライブラリは入っていない → #473 と同じく「今」を関数の引数で渡す。型の作り直しの道具は `tools/api-types`（`docs/runbooks/common-commands.md`「API の形を変えたとき」）。既存テストの手元での全件実行はしない（CI が正）。

## 2. 受け入れ条件
（イシューの受け入れ条件と同じ。番号は TC との対応のため）
- [ ] AC1 クイズの結果が、統計画面の学習時間・正答率の推移と科目別の内訳に出る（既知のクイズ記録に対する期待値テストで固定）。数字の決まりはダッシュボード（#473）と同じ
- [ ] AC2 `GET /api/dashboard/analytics/` の応答のキーと型が契約どおり（BE テストで固定）。画面が契約どおりのキーを読み、欠落を空で埋めない（FE テストで固定）
- [ ] AC3 期間を「直近 7 日・30 日・90 日・1 年」（既定 30 日）から選べ、グラフの区切りが 7・30 日＝日ごと、90 日＝週ごと、1 年＝月ごとになる（BE の期待値テスト・FE テストで固定）
- [ ] AC4 数字のカードが期間の合計の学習時間・正答率（正解の合計 ÷ 解答の合計。答え 0 件は「—」）・解いた問題数・学習した日数を出す（期待値テストで固定）
- [ ] AC5 科目を選ぶと、推移・カードがその科目だけで数えられる。不正・他組織の `subject_id` は 400
- [ ] AC6 学習データが 0 件のユーザーで「まだ記録がありません」とクイズを始める導線が出て、空のグラフは出ない。期間に答えが無いときは「この期間の記録はありません」が出る（FE テストで固定）
- [ ] AC7 1 回の表示あたりのクエリ数が、期間（`days`）に依らない定数本に収まる
- [ ] AC8 不正な `days` は今までどおり 400（I459 のテストが新しい契約で通る）
- [ ] AC9 本人以外のデータが集計に入らない・未認証は 401。#446 の横断テストが通る
- [ ] AC10 「間違いパターン」のタブと「データをエクスポート」のボタンが画面に無く、API も `mistake_patterns` を返さない
- [ ] AC11 既存機能に退行が無い

## 3. 影響範囲
- Backend: `backend/dashboard/selectors.py`（期間の集計を足す・日ごとの集計を共通化）・`backend/dashboard/serializers.py`（入力に科目・応答の形）・`backend/dashboard/views.py`（`DashboardAnalyticsView` の作り直し）・`backend/core/openapi.py`（契約に analytics を入れる）・`backend/core/settings.py`（区切りの選択肢の名前）・`backend/openapi.yaml`（作り直し）・テスト（新設 1・合わせ込み 3）
- Frontend: `frontend/src/pages/Statistics.tsx`（作り直し）・新しい部品 `frontend/src/components/statistics/`（3 ファイル）・新しいフック `frontend/src/hooks/useStatistics.ts`・`frontend/src/services/dashboard.service.ts`（`getAnalytics` と形の確かめ）・`frontend/src/services/types.ts`（手書きの `AnalyticsFilters`・`AnalyticsData` を消す）・`frontend/src/types/api/index.ts`・`frontend/src/types/api/schema.d.ts`（作り直し）・新しいテスト `frontend/src/pages/__tests__/Statistics.test.tsx`
- DB: 変更なし（マイグレーション無し。`StudyLog`・`DailyStudySummary` は残す）
- Config/Infra: なし。依存の追加・削除なし（`recharts` は残す・9 章）
- 変えない（意図的に対象外）: ダッシュボードの画面（#487・#513）・overview の応答の形（日ごとの集計の共通化は中だけで、応答は同じ）・間違い分析（#466）・`backend/dashboard/services.py` は作らない（#473 の集計は `selectors.py` にある）

## 4. 変更点一覧（具体）

### 修正アプローチ
数字の出どころを、ダッシュボードと同じ `_answers(user)`（本人の答え・自組織の科目の問題）に 1 本化する。期間の日ごとの集計を 1 クエリで取り、週・月の区切りへのまとめと合計は Python で行う（区切りの数は最大 365 日ぶんなので軽い）。科目別は期間の答えを科目で 1 クエリで集計する。応答の形はシリアライザで固定して OpenAPI の契約に入れ、画面は作った型で読み、受けるところで形を確かめる（欠けたキーを空で埋めない）。画面は取得をフック（React Query）に、表示を部品に分ける。

### 4.1 API 契約（`GET /api/dashboard/analytics/`）
- 認証: `permission_classes = [permissions.IsAuthenticated]`（未認証は 401）
- クエリ:
  - `days`（省略可・整数 1〜365・省略時 30。I459 のまま）。画面は 7・30・90・365 だけを送る
  - `subject_id`（省略可・整数・自組織の科目だけ。`OrgSubjectField(required=False)`）
- 400:
  - `days` が不正（数字でない・1 未満・365 超）: 今と同じ `create_error_response('期間の指定が正しくありません', '日数は 1〜365 の整数で指定してください', 400)` → body `{"error": {"main_message": "期間の指定が正しくありません", "sub_message": "日数は 1〜365 の整数で指定してください", "details": {}}}`
  - `subject_id` が不正（数字でない・他組織・全体共有〔組織なし〕・存在しない）: `create_error_response('科目の指定が正しくありません', '学習統計の科目の選択からやり直してください', 400)` → body `{"error": {"main_message": "科目の指定が正しくありません", "sub_message": "学習統計の科目の選択からやり直してください", "details": {}}}`（4 つとも同じ body）
  - 両方とも不正なら `days` の 400（先に確かめる）
- 200 の body（キーは全部必須。比率は 0〜1 を小数第 4 位で丸めた数・答えが 0 件なら `null`）:
```json
{
  "has_data": true,
  "period": {"days": 30, "start_date": "2026-10-16", "end_date": "2026-11-14", "granularity": "day"},
  "totals": {"study_seconds": 1530, "answered_count": 15, "correct_count": 10, "accuracy_rate": 0.6667, "studied_days": 5},
  "trend": [
    {"start_date": "2026-10-16", "end_date": "2026-10-16", "study_seconds": 0, "answered_count": 0, "correct_count": 0, "accuracy_rate": null}
  ],
  "subject_breakdown": [
    {"subject_id": 3, "subject_name": "英語", "study_seconds": 900, "answered_count": 7, "correct_count": 5, "accuracy_rate": 0.7143}
  ]
}
```
- `has_data`: 本人の答え（自組織の科目の問題・全科目・全期間）が 1 件以上あるか。科目・期間で変わらない（「まだ一度も解いていない」と「この期間・科目は 0」を分けるため）
- `period`: `end_date` は今日（日本時間・`timezone.localdate(now)`）、`start_date` は `end_date - (days - 1)`（今日を含む `days` 日）。`granularity` は `day`・`week`・`month` のどれか
- `totals`: `subject_id` があればその科目だけ。期間の合計。`studied_days` は答えが 1 件以上ある日（日本時間）の数
- `trend`: `subject_id` があればその科目だけ。期間を区切ったもの・古い順・答えが無い区切りも 0 で入れる（`accuracy_rate` は `null`）
- `subject_breakdown`: **`subject_id` に関係なく全科目**。期間に答えがある科目だけ。学習時間の多い順（同じなら解答数の多い順、さらに同じなら科目名順）
- 今の `daily_data`・`subject_distribution`・`performance_trends`・プルダウン用の `subject_breakdown` は返さない。`mistake_patterns` も返さない

### 4.2 期間と区切りの決まり（`backend/dashboard/selectors.py` の定数と関数）
| 定数 | 値 | 意味 |
|---|---|---|
| `TREND_DAY_MAX_DAYS` | 31 | `days` がこれ以下なら日ごと |
| `TREND_WEEK_MAX_DAYS` | 180 | `days` がこれ以下なら週ごと、超えたら月ごと |

- 画面の 4 つの値では 7・30 → `day`、90 → `week`、365 → `month`。間の値（API に直接送ったとき）も同じしきい値で決まる
- 週は月曜始まり（ISO 週・日本の手帳・学校の週の数え方。Django の `TruncWeek` と同じ）。月は暦の月（1 日始まり）
- 端の区切りは期間で切る: 最初の区切りの `start_date` は期間の `start_date`、最後の区切りの `end_date` は今日。例: 今日 2026-11-14（土）・90 日 → 期間 2026-08-17（月）〜11-14。区切りは 08-17〜08-23、…、11-02〜11-08、11-09〜11-14（13 件）。例: 365 日 → 期間 2025-11-15〜2026-11-14。区切りは 2025-11-15〜11-30、2025-12-01〜12-31、…、2026-11-01〜11-14（13 件）
- 各区切りの値は、その区切りに入る日の値の合計（`accuracy_rate` は合計の正解数 ÷ 合計の解答数）

### 4.3 ファイルごとの変更
1. **`backend/dashboard/selectors.py`**
   - 方針: 期間の集計を読み取り専用のセレクタに足す（規約のセレクタ・Fat View にしない）。日ごとの集計の取り出しは overview と共通にする（同じ数え方を 2 か所に書かない）
   - `_daily_rows(answers, first: date, last: date) -> dict[date, dict]`（新設）: `first`〜`last`（両端を含む・日本時間）の答えを `TruncDate('answered_at')` で日ごとに `_counts()` で集計し、`{日付: {'study_seconds', 'answered_count', 'correct_count'}}` を返す（1 クエリ）。今の `_last_days` の中の集計をここへ移し、`_last_days` はこれを呼んで 7 件に並べる（overview の応答は変わらない）
   - `_granularity(days: int) -> str`（新設）: 4.2 のしきい値で `'day'`・`'week'`・`'month'`
   - `_buckets(first: date, last: date, granularity: str) -> list[tuple[date, date]]`（新設）: 4.2 の区切り（端は期間で切る）
   - `build_analytics(user, days: int, subject=None, *, now=None) -> dict`（新設）: 4.1 の形の dict を返す。中で `_answers(user)`（土台）→ 科目で絞った `scoped` → `_daily_rows(scoped, first, today)` → 区切りごとの合計 → `totals`（区切りの合計・`studied_days` は `answered_count > 0` の日の数）→ `subject_breakdown`（`answers` を期間で絞り `values('problem__subject_id', 'problem__subject__name')` で `_counts()`・1 クエリ）→ `has_data`（`answers.exists()`・1 クエリ）
   - 定数 `GRANULARITY_DAY = 'day'`・`GRANULARITY_WEEK = 'week'`・`GRANULARITY_MONTH = 'month'` を置く（シリアライザの選択肢の正）
2. **`backend/dashboard/serializers.py`**
   - `AnalyticsQuerySerializer` に `subject_id = OrgSubjectField(required=False)` を足す（context に request が要る）。`days` はそのまま
   - 応答のシリアライザ（部品の名前は `DashboardAnalytics…` で始める）: `AnalyticsPeriodSerializer`（`days` int・`start_date` date・`end_date` date・`granularity` `ChoiceField(GRANULARITY_CHOICES)`）・`AnalyticsTotalsSerializer`（`study_seconds`・`answered_count`・`correct_count`・`studied_days` int・`accuracy_rate` `FloatField(allow_null=True)`）・`AnalyticsBucketSerializer`（`start_date`・`end_date`・`study_seconds`・`answered_count`・`correct_count`・`accuracy_rate` null 可）・`AnalyticsSubjectSerializer`（`subject_id`・`subject_name`・`study_seconds`・`answered_count`・`correct_count`・`accuracy_rate` null 可）・`AnalyticsSerializer`（`has_data`・`period`・`totals`・`trend` many・`subject_breakdown` many）。それぞれ `@extend_schema_serializer(component_name='DashboardAnalytics…')`
   - `GRANULARITY_CHOICES = (GRANULARITY_DAY, GRANULARITY_WEEK, GRANULARITY_MONTH)`
3. **`backend/dashboard/views.py`**
   - `DashboardAnalyticsView.get`: `AnalyticsQuerySerializer(data=request.query_params, context={'request': request})` で確かめ、`errors` に `days` があれば期間の 400、`subject_id` があれば科目の 400（4.1）→ `build_analytics(request.user, days, subject)` → `AnalyticsSerializer(data).data`。`@extend_schema(parameters=[AnalyticsQuerySerializer], responses={200: AnalyticsSerializer})`
   - 消す: `_get_performance_trends`・`_accuracy_percent`・使わなくなる import（`timedelta`・`Avg`・`Sum`・`timezone`・`subject_service`・`DailyStudySummary`・`StudyLog`）
4. **`backend/core/openapi.py`**: `CONTRACT_PATHS` に `'/api/dashboard/analytics/'` を足す（コメント `# I488: 統計画面`）
5. **`backend/core/settings.py`**: `SPECTACULAR_SETTINGS['ENUM_NAME_OVERRIDES']` に `'DashboardAnalyticsGranularityEnum': 'dashboard.serializers.GRANULARITY_CHOICES'` を足す（選択肢の型の名前を固定し、ほかの選択肢と名前がぶつかったときの警告を出さない。overview の `kind` と同じ形）
6. **`backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts`**: `docs/runbooks/common-commands.md`「API の形を変えたとき」の手順で作り直す（手で直さない）
7. **`frontend/src/types/api/index.ts`**: `DashboardAnalytics = Schemas['DashboardAnalytics']`・`DashboardAnalyticsGranularity = Schemas['DashboardAnalyticsGranularityEnum']` を足す
8. **`frontend/src/services/types.ts`**: 手書きの `AnalyticsFilters`・`AnalyticsData` を消す（ほかで使っていないことは grep で確認済み・調査結果）
9. **`frontend/src/services/dashboard.service.ts`**
   - `getAnalytics(params: { days: number; subject_id?: string }): Promise<DashboardAnalytics>`。応答を `isDashboardAnalytics(data: unknown): data is DashboardAnalytics`（最上位・`period`・`totals` のキーと型、`trend`・`subject_breakdown` の各要素のキーと型、`granularity` が 3 つの値のどれか、`trend` が 1 件以上）で確かめ、合わなければ `Error('学習統計の応答の形が違います')` を投げる。区切りの種類の一覧は `Record<DashboardAnalyticsGranularity, true>` で持ち、API の選択肢が変われば型の検査で落ちるようにする（overview の `RECOMMENDATION_KINDS` と同じ形）
10. **`frontend/src/hooks/useStatistics.ts`（新設）**
    - `useStatistics(userId: string, days: number, subjectId: string)`: React Query（`queryKey: ['dashboard', 'analytics', userId, days, subjectId]`）。`subjectId` が `ALL_SUBJECTS`（`useDashboardOverview.ts` から import）なら `subject_id` を送らない。状態は `useDashboardOverview` と同じ 3 つ（`loading`・`error`・`success`）と `retry`。期間・科目を切り替えたら新しいキーは読み込み中（前の数字を出さない・`placeholderData` を使わない）
    - `STATISTICS_PERIODS = [{ days: 7, label: '直近 7 日' }, { days: 30, label: '直近 30 日' }, { days: 90, label: '直近 90 日' }, { days: 365, label: '直近 1 年' }]`・`DEFAULT_STATISTICS_DAYS = 30` を同じファイルに置く
11. **`frontend/src/components/statistics/StatisticsSummaryCards.tsx`（新設）**: 数字のカード 4 枚（4.4）
12. **`frontend/src/components/statistics/StatisticsTrendChart.tsx`（新設）**: 「学習時間」「正答率」の 2 つのタブの中身（4.4）
13. **`frontend/src/components/statistics/SubjectBreakdown.tsx`（新設）**: 「科目別（全科目）」のタブの中身（4.4）
14. **`frontend/src/pages/Statistics.tsx`（作り直し）**: 見出し・絞り込み・状態ごとの出し分け・タブ（4.4）。書き出しのボタン・「間違いパターン」のタブ・`mountKey`・描画の中の `TabPanel` の定義を消す
15. **テスト**: `backend/dashboard/tests/test_I488_analytics.py`（新設）・`frontend/src/pages/__tests__/Statistics.test.tsx`（新設）。6 章・自動テスト文書のとおり
16. **既存テストの合わせ込み**
    - `backend/dashboard/tests/test_I459_analytics_zero_division.py`: TC-01・TC-02（`DailyStudySummary` の週の正答率）を消す（集計元と形が変わるため。0 件で割らないことは新しい TC-03〔答えの無い区切りは `null`〕が受け持つ）。TC-03（400）・TC-06（401）はそのまま。TC-04 を新しい契約に直す（省略・空 → `period.days == 30` で `trend` 30 件・`granularity == "day"`、`"1"` → 1 件、`"365"` → `period.days == 365`・`granularity == "month"`）。冒頭の説明と `DailyStudySummary` の import を直す
    - `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`: TC-18 をクイズの答え（`_quiz_answers`）で書き直す（自組織の科目の答えと、不具合で残った他組織の問題への答えを作り、`_no_other(response)`・`subject_breakdown` の科目名が `{"科目I431A"}`）
    - `backend/core/tests/test_I446_cross_api_tenant_isolation.py`: `"GET api/dashboard/analytics/"` を `[ListCheck(), IdCheck("user", "query", "subject_id", "subject", 400)]` にする（overview と同じ）
    - `backend/core/tests/test_I493_openapi_contract.py`: 変えない（スキーマのファイルが作り直したものと同じかは今のテストが見る）

### 4.4 画面（`/statistics`）
上から順に:
1. 見出し「学習統計」（`h5`・`component="h1"`。書き出しのボタンは無し）
2. 絞り込み（`Paper` の中に横並び・スマホでは縦）: 「期間」の選択（`直近 7 日`・`直近 30 日`・`直近 90 日`・`直近 1 年`。既定 `直近 30 日`）／「科目」の選択（`SubjectSelector`・「すべて」と自分の科目）。読み込み中・失敗のときも出し続ける
3. 状態ごとの出し分け（絞り込みの下だけを置き換える）:
   - 読み込み中: MUI の `Skeleton`（数字のカード 4 枚ぶんとグラフ 1 つぶんの形）
   - 失敗（取得の失敗・形の違い）: `Alert severity="error"`「学習統計を読み込めませんでした」と「再読み込み」のボタン（ダッシュボードと同じ形）。0 や空のグラフは出さない
   - データ無し（`has_data` が false）: カード 1 枚に「まだ記録がありません」（ダッシュボードの `NO_RECORD_TEXT` を使う）と、補足「クイズを解くと、学習時間と正答率の推移がここに出ます」・ボタン「クイズを始める」（`/quiz` へ）。数字のカード・タブは出さない
   - 成功（`has_data` が true）: 4・5 を出す
4. 数字のカード 4 枚（`期間` の合計。見出しの下に小さく `{start_date}〜{end_date}` を `YYYY/M/D〜YYYY/M/D` で出す）:
   - 「学習時間」: `Math.floor(study_seconds / 60)` 分。60 分以上は `◯時間◯分`（例 `2時間5分`）、60 分未満は `◯分`
   - 「正答率」: `accuracy_rate` が `null` なら `—`、そうでなければ `Math.round(rate * 100)` %
   - 「解いた問題数」: `answered_count` 問
   - 「学習した日数」: `studied_days` 日
5. タブ 3 つ: 「学習時間」「正答率」「科目別（全科目）」
   - 「学習時間」: 棒グラフ（`recharts` の `BarChart`）。横軸は区切りのラベル、縦軸は分（`Math.round(study_seconds / 60)`・0 から・整数の目盛り）。ツールチップは区切りの範囲と `◯分・◯問`
   - 「正答率」: 折れ線（`LineChart`）。縦軸 0〜100%。答えの無い区切りは点を打たず線を切る（`connectNulls` を付けない）。ツールチップは範囲と `◯%`（答えが無い区切りは `—`）
   - 横軸のラベル: 日ごと `M/D`、週ごと `M/D〜`（区切りの始まりの日）、月ごと `YYYY/M`。ツールチップの範囲: 日ごと `YYYY/M/D`、週・月ごと `YYYY/M/D〜M/D`（年をまたぐときは終わりにも年）。日付は文字列を分けて作る（`new Date('YYYY-MM-DD')` の UTC 解釈で日がずれないように）
   - 「科目別（全科目）」: 学習時間の円グラフ（`PieChart`・科目名と %）と、科目ごとのカード（科目名・学習時間・正答率・問題数）。見出しの下に「科目の選択に関係なく、期間の全科目を出します」
   - 期間（と選んだ科目）に答えが無い（`totals.answered_count == 0`）とき、「学習時間」「正答率」のタブの中身はグラフの代わりに「この期間の記録はありません」。「科目別（全科目）」は `subject_breakdown` が空のとき「この期間の記録はありません」。学習時間の合計が 0 秒（答えはあるが `time_taken` が全部 0）のときは円グラフの代わりに「学習時間の記録がありません」を出し、科目ごとのカードは出す
   - `TabPanel` はファイルの外（部品の外）で定義し、`role="tabpanel"`・`aria-labelledby` を付ける（MUI の例と同じ）

## 5. 実装手順（ステップ）
各ステップは画面まで縦に通す。ステップ 2 は 1 の後、3 は 2 の後、4 は 3 の後。
1. **土台・日ごとの推移・数字を縦に通す**（未知のリスクの先出し: `ENUM_NAME_OVERRIDES` を足した契約が `--fail-on-warn` で作れること・作った型の名前が 4.3 の 7 のとおりになること）: `selectors.py`（`_daily_rows` の共通化・`build_analytics` の `day` の区切り・`totals`・`has_data`）・シリアライザ・ビュー（`days`・`subject_id` の 400）・`openapi.py`・`settings.py`・スキーマと型の作り直し・画面の型・サービス・フック・`Statistics.tsx`（絞り込み・状態ごとの出し分け・数字のカード・学習時間のタブ）→ TC-01・02・04・05・06・07・08・09・10・20・21・22・23・24 参照
2. **週・月の区切りと正答率のタブを足す**（`_granularity`・`_buckets`・正答率の折れ線・横軸のラベル）→ TC-03・25 参照
3. **科目別の内訳を足す**（`subject_breakdown` の集計・シリアライザ・「科目別（全科目）」のタブ）→ TC-11・26 参照
4. **既存テストの合わせ込みとクエリ数の固定**（I459・I431・I446 のテスト・クエリ数のテスト）→ TC-12・13・14 参照
5. `/simplify` で整理し、画面確認（手動テスト No.1〜7）
- サービスの再起動: ファイルの削除は無い。開発サーバーは自動で読み直すので不要

## 6. テスト計画
### 自動（詳細は `docs/tests/open/I488_auto_test.md`）
- レベルの分け方: 数え方・区切り・日付の境界はセレクタを直接呼ぶ BE のテスト（`now` を渡す）／契約・400・401・境界・クエリ数は API を呼ぶ BE のテスト／画面が契約を読むこと・状態ごとの表示・欠落時のエラー・期間と科目の送り方は FE のテスト（`apiClient` をモック）
- 再発防止（元の不具合: 画面と API の形の不一致を空で隠した）: TC-01（応答のキーの集合）・TC-02（答えると数字に出る）・TC-22（欠けた応答はエラーの表示で空のグラフにしない）。加えて、型を OpenAPI から作るので、画面が無いキーを読むと型の検査（CI）で落ちる
- 認可・境界: TC-08・TC-09・TC-13・TC-14（#446・I431 の横断テスト）
- E2E は足さない: 元の不具合は「画面と API の形のずれ」で、契約のテスト（BE）・作った型（CI の型の検査）・形の確かめ（FE）の 3 つで止める。実際の流れ（クイズを解く → 統計画面に出る）は手動テスト No.5 で Claude が確かめる。E2E を足すと実行時間が増えるわりに、上の 3 つで止められない種類のずれが無い
- 実行: pytest・Jest は CI が PR ごとに流す（手元では変えたファイルのテストだけ）。決定論ゲートの追加は無い
### 手動（`docs/tests/open/I488_manual_test.md`）
- すべて Claude が Playwright MCP で確かめる（データ無し・複数の日にまたがる答え・期間の切り替えと区切り・科目の切り替え・クイズを解いた後の増え方・スマホ幅・コンソール）

## 7. ロールバック
- PR を revert する（DB の変更・マイグレーション・設定の値の変更が無いので、コードを戻すだけで元に戻る）。スキーマと型のファイルも同じ PR で戻る

## 8. Risk & 回避策
- R1 区切りの境目（月曜・月初・期間の端）のずれ → TC-03 で、日曜と月曜・月末と月初・期間の最初の日と前日の答えを入れて固定する
- R2 日本時間の 0〜9 時の答えが前の日になる → `_daily_rows` は overview と同じ `TruncDate`（現在のタイムゾーン）。TC-04 で 0:30 と 23:30（日本時間）を入れて固定する
- R3 他組織の問題への答え（過去の不具合で残ったもの）が数字や科目名に混ざる → 土台 `_answers(user)` を必ず通す（`QuizAnswer` を読むのは `_answers` だけ・#473 の必須条件）。TC-08・TC-13 で固定する
- R4 クエリ数が日数・区切りの数・科目数で増える → 日ごとの集計 1 回・科目別 1 回・有無 1 回にし、区切りへのまとめは Python。TC-12 で 7 日と 365 日・小さいデータと大きいデータのクエリ数が同じことを固定する
- R5 画面が形の違う応答を黙って受ける（元の不具合の再発）→ `isDashboardAnalytics` で確かめ、TC-22 で固定する。型は OpenAPI から作る
- R6 `_last_days` の中を `_daily_rows` に移したことで overview の数字が変わる → 既存の `test_I473_overview.py` がそのまま通ること（CI）で確かめる
- R7 日付の文字列を `new Date()` に渡して、ブラウザのタイムゾーンで日がずれる → ラベルは文字列を分けて作る（4.4）。TC-25 で `2026-11-09` のラベルが `11/9〜` になることを固定する

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 集計元は `QuizAnswer`。数え方はダッシュボード（#473）と同じ。集計は `backend/dashboard/selectors.py` に足す
- 期間は 7・30・90・365 日（既定 30 日）。区切りは 7・30 日＝日ごと、90 日＝週ごと、1 年＝月ごと。期間の末日は今日（`timezone.localdate()`）で今日を含む `days` 日。`days` の入力は I459 の `AnalyticsQuerySerializer`（1〜365）を残す
- カードは期間の合計の学習時間・正答率（正解の合計 ÷ 解答の合計・0 件は「—」）・解いた問題数・学習した日数。科目の絞り込みは `subject_id`（`OrgSubjectField`・不正なら 400）。「科目別」は学習時間の円グラフと科目ごとの学習時間・正答率・問題数
- 「間違いパターン」のタブ・書き出しのボタンは外す。`mistake_patterns` は返さない
- データ 0 件は「まだ記録がありません」とクイズを始める導線・空のグラフは出さない。期間に答えが無ければ「この期間の記録はありません」
- 応答の形をシリアライザで固定し、単位をキー名に入れる・比率は 0〜1・データ無しを区別する

Claude が決めた（技術的な選択と理由）:
- 区切りのしきい値（31 日以下は日・180 日以下は週・それより上は月）— 仮定で決めた。画面の 4 つの値が設計確認メモのとおりに分かれ、API に間の値を直接送ったときも棒の数が多くなりすぎない（日ごと最大 31 本・週ごと最大 26 本・月ごと最大 13 本）
- 週は月曜始まり・端の区切りは期間で切る（4.2）— 仮定で決めた（設計確認メモで「計画で決める」とされた点）。月曜始まりは ISO 週・日本の学校や手帳の週の数え方で、Django の `TruncWeek` とも同じ。端を期間で切るのは、期間の外の日を数えないため（「直近 90 日」の合計とグラフの合計を一致させる）
- `subject_breakdown` は科目の選択に関係なく全科目・見出しを「科目別（全科目）」— 仮定で決めた。科目を選んだときに 1 科目だけの円グラフになるのは意味が無く、ダッシュボードの「間違いやすい分野（全科目）」と同じ見せ方にそろえる。設計確認メモの「科目を選ぶと、推移・カードがその科目だけ」とは矛盾しない（推移・カードは科目で絞る）
- `has_data` は全科目・全期間の答えの有無 — 仮定で決めた。設計確認メモの「学習データが 0 件のユーザー」と「選んだ期間（と科目）に答えが無いとき」を分けるため。科目と期間で絞った「無い」は `totals.answered_count == 0` で表す
- 文言（「学習統計を読み込めませんでした」・「クイズを解くと、学習時間と正答率の推移がここに出ます」・「科目の選択に関係なく、期間の全科目を出します」・「学習時間の記録がありません」・期間の選択のラベル「直近 7 日」など・タブ名「科目別（全科目）」・科目の 400 の補足「学習統計の科目の選択からやり直してください」）— 仮定で決めた。設計確認メモの状態の出し分けを満たす最小の文言で、ダッシュボードの言い回し（「◯◯を読み込めませんでした」・「（全科目）」）にそろえた。ユーザーの指示「BP,UI/UX の観点でベストなやり方で進めて」の範囲と判断し、止めない
- 学習時間の表記（60 分以上は `◯時間◯分`）— 仮定で決めた。期間が 1 年になると分だけでは読みにくい。今の画面の `◯h ◯m` を日本語にした
- 推移のグラフは学習時間を棒・正答率を折れ線（答えの無い区切りは線を切る）— 仮定で決めた。学習時間は区切りごとの量なので棒（#513 の設計確認メモと同じ理由）。正答率は区切りをまたぐ傾向を見るもので、答えの無い区切りを 0% として描くと誤解を招くので線を切る
- グラフの道具は `recharts` のまま — 仮定で決めた。画面の作り直しで道具まで替えると差分が大きくなり、このイシューの目的（数字を正しく出す）と関係しない。ダッシュボードの `chart.js` に寄せて `recharts` の依存を外すのは、retro で別イシューにするか決める
- 期間の日ごとの集計を 1 クエリで取り、週・月へのまとめは Python — 仮定で決めた。DB の `TruncWeek`・`TruncMonth` で集めると、端を期間で切る処理と `studied_days` のために別のクエリが要る。日ごとの行は最大 365 行で軽い
- `_last_days` の集計を `_daily_rows` に移して共通にする — 仮定で決めた。同じ数え方（300 秒の上限・日本時間）を 2 か所に書くと片方だけ変わるおそれがある
- 応答の形を受けるところで確かめる（`isDashboardAnalytics`）— 仮定で決めた。型は実行時に消えるので、overview（I493）と同じく受けるところで形を確かめる
- 取得は React Query のフック・表示は部品に分ける — 仮定で決めた。規約 6.3（非同期データは useQuery）と、ダッシュボード（I487）と同じ分け方。今の 400 行の 1 ファイルを分ける（巨大な部品にしない）
- E2E を足さない（6 章）— 仮定で決めた
- クエリ数の上限の本数は実装後に数えて TC-12 に書く — 仮定で決めた（#473 と同じ。目安は 6 本以下: 科目の確かめ・日ごと・科目別・有無と、認証まわり）

セキュリティ・BP の確認:
- 入力: `days` は `IntegerField(min_value=1, max_value=365)`。`subject_id` は `OrgSubjectField`（自組織の科目だけ）。他組織・全体共有・存在しない・数字でないは同じ 400 で違いを見せない（存在の推測を防ぐ）。値を `int()` などで直接変換しない
- 認証・認可: `IsAuthenticated` のまま。集計は本人（`session__user=user`）かつ自組織の科目（`scope_to_user_org`）に限る（最小権限）。利用者を入力から受け取らない
- 機密: 応答は本人の件数・秒数・正答率・自組織の科目 ID と名前だけ。ログは足さない（取得の失敗の `console.error` はダッシュボードと同じく残す）
- OWASP: SQL は ORM の式だけ（生の SQL・`extra()` なし）。画面は React の通常の描画で `dangerouslySetInnerHTML` を使わない（科目名はテキストとして出す。`recharts` のラベルも SVG のテキスト）。GET だけで CSRF の対象の書き込みは無い
- 資源の消費: `days` の上限 365・クエリ数は定数本・返す行は区切りと科目の数ぶん
- 依存: 追加・削除なし（pip-audit・npm audit の対象の変化なし）
- スキャンの重大度: bandit は MEDIUM 以上を直す（LOW は `# nosec` で理由つき）。npm audit は high/critical を直す。どちらも CI の既存の設定のまま
- P3/P5/P8（DB 変更・外部 API・非同期・インフラ・依存）: 影響なし
- P6（性能・UX）: 13 章に書く
- P9（プライバシー）: 本人の学習データだけを本人に返す。テナントをまたぐ読み出しを土台で禁止（15 章は「個人情報の新しい扱いが無い」ため省略。境界は TC-08・TC-13）
- 高リスクの見込み: 入力（`subject_id`）で組織の境界を扱うため、計画レビューで高リスクに当たりうる。「必ず確かめる項目」を書く

台帳の残りの一覧:
- 一覧 `docs/reviews/backlog/I223.md` B1〜B4・`docs/reviews/backlog/I224.md` F9（`FILE=-`）: 残す — どれもハーネス（bot の PR・鍵・計測）の話で、本イシューの変更と関係しない
- 実装対象のファイル（4.3）に当たる行: 一覧の該当なし

Danger Ops（有無/手順/ロールバック）:
- 無（DB・データの削除・大量更新・強制 push は無い）。手動テストで確かめ用の利用者 `verify_i487` のパスワードを入れ直すのは 1 件の保存だけ

（10 章〔DB 変更〕・11 章〔外部 API・非同期〕・12 章〔インフラ・コスト〕・15 章〔個人情報の新しい扱い〕は該当なしのため省略）

## 13. 性能・UX設計
- クエリ: 科目の確かめ（`subject_id` があるとき 1 回）・日ごとの集計 1 回・科目別 1 回・有無 1 回。期間・区切り・科目の数で本数が増えない（TC-12）。日ごとの行は最大 365 行
- 取得: React Query のキーに利用者・期間・科目を入れる（前の利用者のキャッシュを出さない）。`staleTime` は既定の 0 のまま（`frontend/src/App.tsx` の `QueryClient` の既定・ダッシュボードと同じ）: 前に開いた組み合わせに戻ると、キャッシュの数字をすぐ出し、裏で 1 回だけ取り直す（クイズを解いた後に戻ってきたときに古い数字のままにしない）。新しい組み合わせは読み込み中の形を出して 1 回取る
- ローディング: 絞り込みは残し、下だけ `Skeleton`（画面全体を「読み込み中...」にしない）
- 空状態: データ無しは「まだ記録がありません」と「クイズを始める」。期間・科目に答えが無ければグラフの場所に「この期間の記録はありません」（カードは 0 と「—」）
- エラー状態: `Alert` と「再読み込み」。0・空のグラフで埋めない
- 破壊的操作: 無い
- スマホ幅（390）: 絞り込みは縦に並べ、カードは 2 列（`xs=6`）、グラフは `ResponsiveContainer` で幅に合わせる。横にはみ出さない（手動テスト No.6）
- アクセシビリティ: 選択は MUI の `Select`（ラベルつき）・タブは MUI の `Tabs`（`aria-controls`）と `role="tabpanel"`。色だけで意味を伝えない（円グラフには科目名と %、カードには数字）

## 14. 学習効果設計
- 期間を選んで、学習時間と正答率の推移を振り返れる（C1）。数え方はダッシュボードと同じ（1 問 5 分まで・日本時間・今日の復習の回を含む）なので、2 つの画面の数字が食い違わない
- 正答率は「合計の正解 ÷ 合計の解答」で、解いた数の少ない日が強く効く日ごとの平均にしない。答えの無い区切りは 0% にせず線を切り、学習していない期間を「成績が悪い」と見せない

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 他組織の科目の問題への答え・他人の答えを入れても、analytics のどの数字・科目名にも出ない（TC-08・TC-13） |
| V2 | 1 | 読んで可 | `subject_id` が数字でない・他組織・全体共有（組織なし）・存在しないのどれでも、同じ 400 と同じ body になる（TC-07） |
| V3 | 2 | 読んで可 | TC-12 が「期間を 7 日と 365 日にしても・データを増やしてもクエリ数が同じ」ことを比べていて、片方だけを数える形になっていない |
| V4 | 2 | 読んで可 | TC-22 がキーを 1 つ欠いた応答で「空のグラフ・0 が出ない・エラーの文が出る」ことを見ていて、正常な応答だけで通る形になっていない（形の確かめを外すと落ちる） |
| V5 | 3 | 読んで可 | 区切りの境目（日曜と月曜・月末と月初・期間の最初の日と前日）・日本時間の 0〜9 時の答え・300 秒を超える答えがテストにある（TC-02・TC-03・TC-04） |

## セキュリティレビュー結果

**実施日**: 2026-11-14

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | マルチテナント | `build_analytics` の中で、土台 `_answers(user)` を通さずに `QuizAnswer.objects` から直接数える処理（例: 科目別の内訳だけ別に書く）を足すと、不具合で残った他組織の問題への答えの科目名・数が応答に出る。`QuizAnswer` は `OrgScopedQuerySet` のモデルではないので、I455 の静的な見張りは効かない | 必須: `selectors.py` で `QuizAnswer` を読むのは `_answers(user)` の 1 か所のまま。`trend`・`totals` は `scoped`（`_answers` を科目で絞ったもの）、`subject_breakdown`・`has_data` は `_answers(user)` の戻り値から作る。科目名は `problem__subject__name`（土台で自組織に絞った後の結合）だけから取り、`Subject.objects` を別に読まない。TC-08 ③（他組織の問題への答えを入れても科目名・ID・数が出ない）と TC-13（I431 の TC-18）で固定する |
| Medium | 入力検証（IDOR） | `subject_id` を新しく受け付ける。他組織・全体共有の科目の ID で絞った集計が 200 で返ると、他組織の科目の存在や（答えがあれば）数が分かる | 必須: `AnalyticsQuerySerializer` の `subject_id` は `OrgSubjectField(required=False)`（`available_subjects(request.user)`＝自組織の科目だけ）で受け、`context={'request': request}` を必ず渡す（渡し忘れると `Subject.objects.none()` になり全部 400 になるので、TC-06 の 200 が付け忘れを止める）。数字でない・他組織・全体共有・存在しない・組織なしの利用者は同じ 400・同じ body（TC-07）。`query_params` の値を `int()` や `Subject.objects.get()` で直接使わない |
| Low | 認証・認可 | analytics は `IsAuthenticated` のまま。集計の本人は常に `request.user` | 禁止: `AllowAny` への変更・利用者を入力（`user_id` など）から受け取ること。TC-08 ①② |
| Low | マルチテナント | 組織に属さない利用者 | `scope_to_user_org` が空を返す（`allow_null=False`）→ 数字は 0・`has_data=false`・`subject_breakdown=[]`。`subject_id` を送れば `available_subjects` が空なので 400。TC-07・TC-08 ④ |
| Low | 機密情報 | 応答は本人の件数・秒数・正答率・自組織の科目 ID と名前・期間の日付だけ | 禁止: 応答・ログに他の利用者の情報・問題の本文・正解を出すこと。ログ出力は足さない |
| Low | OWASP Top 10 | XSS: 科目名を画面（カード・円グラフのラベル・ツールチップ）に出す。SQLi: 集計 | 画面は React のテキスト・`recharts` の SVG のテキストとして描く（`dangerouslySetInnerHTML` 禁止・ラベルを HTML 文字列で組まない）。SQL は ORM の式（`Sum`・`Least`・`TruncDate`・`Count`）だけで、生の SQL・`extra()`・`RawSQL` を使わない。GET だけで状態を変えない（CSRF の対象なし） |
| Low | OWASP（資源の消費） | `days` を大きくして重くする | `days` は 1〜365 で 400（I459 のまま）。日ごとの集計・科目別・有無の各 1 クエリで、返す行は最大 365 日ぶんと科目の数ぶん。TC-12 で本数が期間・データの量に依らないこと（と上限）を固定する。認証が要る |
| — | ファイル操作 | なし（書き出しのボタンは外す・ファイルを作らない） | — |
| — | 外部通信 | なし | — |
| — | 依存ライブラリ | なし（追加・削除しない。`recharts` は今あるもの） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `GET /api/dashboard/analytics/` | 未認証 | トークン無しで呼ぶ | 401 で何も返さない | Yes: TC-08 ①・TC-14（I459 TC-06） | No | なし | Low |
| 2 | `GET /api/dashboard/analytics/?subject_id=<他組織の科目>` | 一般（組織 A） | 他組織・全体共有の科目の ID を総当たりし、400 と 200 の違い・数字の違いから科目の存在や他組織の学習量を探る | 他組織・全体共有・存在しない・数字でない・組織なしの利用者は同じ 400・同じ body。200 で他組織の科目に絞った集計を返さない | Yes: TC-07・TC-13（I446 の `IdCheck("user", "query", "subject_id", "subject", 400)`） | No | なし | Medium |
| 3 | 同上 | 一般 | 他人の学習量を見ようとする（`user_id` などを付ける） | 入力で利用者を変えられない。集計の本人は常に `request.user` | Yes: TC-08 ② | No | なし（利用者を受け取る入力が無い） | Low |
| 4 | 同上（応答の `subject_breakdown`） | 一般 | 過去の不具合で残った他組織の問題への答えを手がかりに、他組織の科目名を応答に出させる | 土台で `problem__subject` の組織を絞る。科目名は自組織の科目だけ | Yes: TC-08 ③・TC-13（I431 の TC-18 の書き直し・I446 の `ListCheck()`） | No | 土台を通さない読み出しが後から足されること（設計レビューの Medium の必須条件で防ぐ・review-gate で確かめる） | Medium |
| 5 | 同上（`days`） | 一般 | `days=100000`・負の数・小数・文字で重くする／500 を起こす | 1〜365 の整数以外は 400。クエリ数は定数 | Yes: TC-14（I459 TC-03）・TC-12 | No | 1 回のクエリの中の行数は期間の答えの数に比例する（集計は DB 側・返すのは最大 365 行） | Low |
| 6 | 統計画面 | 一般 | 科目名に HTML・スクリプトを入れた科目（管理者が作れる）を表示させる | React のテキスト・SVG のテキストとして描き、実行されない | No（React・`recharts` の既定の動き。`dangerouslySetInnerHTML` を使わないことは review-gate の差分で見る） | No | なし | Low |
| 7 | 統計画面（React Query のキャッシュ） | 一般（同じタブで別の利用者が入り直す） | 前の利用者のキャッシュの数字を見る | キーに利用者の ID を入れる（ダッシュボードと同じ） | No（キーの形は review-gate の差分で見る） | No | ログアウトでキャッシュを消す全体の扱いは #508 の範囲 | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 2件 | 2件 |
| Low     | 5件 | 5件 |

### 残余リスク処遇
（retro・2026-11-14 に決定）
- High 以上: 0 件（設計レビュー・シナリオとも）
- Medium（設計 2・シナリオ 2）: どれも実装で必須条件を満たし、テストで固定したので受け入れる（後続イシューにしない）
  - 土台 `_answers(user)` を通さない読み出しが後から足されること（設計 1・シナリオ 4）: `selectors.py` で `QuizAnswer` を読むのは `_answers` の 1 か所のまま（コードレビュー・敵対的レビュー 2 周の V1 で確認）。TC-08 ③・TC-13 が、他組織の問題への答えの科目名・数が出ないことを固定し、土台の絞り込みを外すと落ちることを失敗の注入で確かめた
  - `subject_id` の IDOR（設計 2・シナリオ 2）: `OrgSubjectField` と `context={'request': request}` で受け、TC-07（組織なしの利用者を含む 5 通りが同じ 400）と I446 の `IdCheck` で固定
- Low: 受け入れる（記録だけ）。React Query のキャッシュの、ログアウトのときの消し方（シナリオ 7）は #508 の範囲

## 計画変更記録
- 計画レビュー（20261114_0122）の Warning・Info への対応（方式・範囲・受け入れ条件は変えないので再レビューはしない）: 13 章に `staleTime`（既定の 0）と戻ったときの取得の回数を書き、手動テスト No.7 の期待結果を 1 つに絞った／TC-12 に実測の上限（`<= N`）を足す形にした／10〜12・15 章の省略を 1 行書いた／TC-07 に組織なしの利用者の `subject_id` の 400 を足した
- implement（再レビュー不要・方式・範囲・受け入れ条件は変えない）: ① 日付・時間・正答率の書式を 3 つの部品で共通に使うため `frontend/src/components/statistics/format.ts` を足した（4.3 の 11〜13 の中の関数を 1 か所にまとめただけ） ② シリアライザに件数の共通の親 `AnalyticsCountsSerializer`（`DashboardAnalyticsCounts`）を置き、合計・区切り・科目がそれを継承する（直接は使わないのでスキーマには出ない） ③ TC-12 の上限を実測の本数で固定した（科目なし 3 本・あり 4 本） ④ 科目ごとのカードを `section` にし見出しで名前を付けた（読み上げで区別でき、テストも見出しの名前で探せる） ⑤ 円グラフは秒で描く（分に丸めると 1 分未満の科目が描かれないため。ツールチップは「◯分」の書式） ⑥ 学習時間の棒の高さは 4.4 の `Math.round(study_seconds / 60)` ではなく分の小数第 1 位まで（`Math.round(study_seconds / 6) / 10`）にし、目盛りは整数のまま・ツールチップはカードと同じ「◯時間◯分」の書式にした（画面確認で、1 分未満しか解いていない日の棒が 0 になり「解いたのに空」に見えることに気づいたため。TC-20 に 125.5 分の確かめを足した）
- `/simplify`（再レビュー不要・振る舞いは同じ）: ① 区切りへのまとめを 1 回のなめ方にした（区切り × 日の二重ループをやめる）・学習した日数は `len(by_day)` ② 読み込み中・失敗・成功の 3 つの状態にする処理を `frontend/src/hooks/queryLoadState.ts` の `toLoadState` にまとめ、`useDashboardOverview.ts` と `useStatistics.ts` から使う（同じ決まりを 2 か所に書かない） ③ 応答の形の確かめで、今ある `hasCounts` を使い回す ④ ツールチップの正答率は元の比率から書式にする・円グラフは応答の一覧をそのまま渡す ⑤ スケルトンに読み上げ用の「学習統計を読み込み中」を足した。見送り: 有無のクエリを期間の答えがあるときに省く（クエリ数がデータで変わり AC7 に反する）・科目別だけを別のキーで取る（クエリ 1 本ぶんの節約で、取得を 2 つに分ける複雑さに見合わない）・テストの準備を `conftest.py` に共通化（I473 のテストも変える・既存の書き方）・書式を `utils/` に移してダッシュボードも使う（ダッシュボードの部品を変える・別イシュー向き）・ビューのエラー文言の表（2 つの分岐だけ）・`useUserSubjects` の状態の変換の置き換え（本イシューの差分の外）
- review-gate（コードレビュー 20261114_0200 は OK・止める指摘なし。再レビュー不要〔方式・範囲・受け入れ条件は変えない〕。直した差分はコードレビューの差分のレビューを通す）: ユーザーの「BP の観点で問題ないか」の確認で規約と照らし合わせて見つけた 2 点と、台帳の Low 2 件を直した。① 新しい部品 4 つで `React.FC` を使っていた（規約 5.1「React.FC は使用しない」。既存の画面の置き換えは #510）→ props に型を付ける書き方にした ② タブの切り替えのテストを `fireEvent` で書いていた（規約 12.2 は `userEvent`）→ 原因は、`userEvent.click` の後に切り替わりを待たずに中身を見ていたことだったので、`aria-selected` が true になるのを待ってから見る形で `userEvent` に戻した ③ F1: 棒は分の小数第 1 位まで持つので、縦軸の目盛りも小数を許す（4.4 の「整数の目盛り」を変える。1 分未満の期間で目盛りが 0 と 1 だけにならないように） ④ F2: ファイル名を部品の名前に合わせて `StatisticsTrendChart.tsx` にした。F3（有無のクエリを省く）は、クエリ数をデータで変えないため見送り（`/simplify` の見送りと同じ）
- fix-loop（手動テスト No.2 の NG・診断 `docs/reviews/I488_fix_diagnosis_20261114_0254.md`・再レビュー不要〔方式・範囲・受け入れ条件は変えない。表示の直し〕）: 正答率の折れ線で点が描かれなかった（recharts の `Line` は描き始めの動きの終わりを待って点を描くが、線を切る形では合図が来ない）。正答率の `Line` に `isAnimationActive={false}` を付け、TC-25 にその確かめを足した

## レビュー結果
- [20261114_0122 判定: ✅ 完了](../../reviews/I488_plan_review_20261114_0122.md)
