# I473 計画書: ダッシュボードの数字をクイズの記録から出す（API 契約の 1 本化・科目フィルタ・おすすめの統合）

## 基本情報
- **計画書ID**: plan_I473
- **関連イシュー**: #473
- **Draft PR**: #489
- **作成根拠資料**: docs/issues/open/I473.md（起点イシュー・GitHub #473 の本文の写し・設計確認メモつき）
- **実装後評価**: docs/reviews/open/I473_review.md
- **作成日**: 2026-11-13

## 1. 背景/目的
- ダッシュボード（`/dashboard`）の数字・グラフ（今日の学習時間・連続学習日数・解答問題数・正答率・週の推移・間違いやすい分野・おすすめ）が、クイズを解いても 0 か空のまま。2026-11-13 に Playwright で実画面を確かめ、e2e_user_a で 1 問正解した直後もすべて 0 のまま（今日の復習のカードだけ動く）であることを確認した（`.evidence/I473/dashboard-a-2-after-answer.png`）。
- 目的: クイズの答えの記録（`QuizAnswer`）から数字を出し、画面と API の受け渡しの形（API 契約）を 1 本にしてテストで固定する。

### 調査結果
**原因の概要**: ダッシュボードの数字は、どこからも書き込まれていない表（学習ログ `StudyLog`・日ごとのまとめ `DailyStudySummary`）から数えている。しかも画面が読む名前と API が返す名前が 1 つも合っておらず、画面は受け取れなかった値を黙って 0 で埋めていたので、壊れていることが見えなかった。

**詳細な原因分析**:
1. クイズに答えると `POST /api/quiz/<pk>/submit_answer/` が `QuizAnswer` を作る（`backend/problems/views.py:921-948`。`time_taken` は画面が問題を出してから答えるまでの秒数〔`frontend/src/pages/QuizSession.tsx:213-217`〕）。`StudyLog` / `DailyStudySummary` には書かれない。
2. `DashboardOverviewView.get`（`backend/dashboard/views.py:19-107`）は `StudyLog` / `DailyStudySummary` を集計し、`today`・`active_session`・`study_streak`・`weekly_summary`・`recent_quizzes`・`subject_progress`・`upcoming_goals` を返す。
3. 画面（`frontend/src/pages/Dashboard.tsx:125-147`）は `stats`・`weekly_progress`・`subject_progress`・`recommendations`・`recent_sessions` を読み、無ければ 0 と空の配列で埋める。`subject_progress` は名前だけ一致するが、正答率の単位（画面 0〜1・API 0〜100）と中身のキー（画面 `problems_solved`・API `total_problems`）が違う。
4. 科目の選択: 画面は `subject_id` を送るが（`Dashboard.tsx:127-130`）、`DashboardOverviewView.get` は `query_params` を読まない。
5. おすすめ: `SubjectRecommendationView`（`views.py:277-328`・`GET /api/dashboard/recommendations/`）は画面から呼ばれていない（`frontend/src/services/dashboard.service.ts:17-30` の `getRecommendations` は未使用）。
6. データ 0 件のとき、正答率のドーナツは `[0, 100]` で赤一色になる（`Dashboard.tsx:242-251`）。
7. クエリ数: 連続日数は 1 日ごとに 1 クエリ（`views.py:109-137`）、科目別は科目ごとに 3 クエリ（`views.py:139-167`）。

**引き継ぎ 3 件（#467 の「I190 への引き継ぎ」）の今の状態**:
- 引き継ぎ 1: `SubjectRecommendationView` の `exclude(id__in=studied_subject_ids)`（`views.py:309-315`）。科目が空の `StudyLog` があると NOT IN に NULL が混ざり、未学習の科目が消える。→ 経路ごと消し、新しいおすすめは `QuizAnswer` から出す（`problem__subject` は NULL にならない〔`Problem.subject` は必須・`backend/problems/models.py:117`〕）。
- 引き継ぎ 2: `StudyLogViewSet.create`（`backend/studylogs/views.py:46-52`）が、組織で絞らずに本人の進行中の記録をすべて閉じる。
- 引き継ぎ 3: `SubjectService.get_user_selected_subjects`（`backend/core/subject_service.py:131-144`）。キャッシュに当たった経路だけ `order_by('name')` が無い。キャッシュのキー `user_subjects_{user.id}_count_{annotate_count}` に組織が無い（無効化は `backend/problems/signals.py:17-39` が同じ形のキーで消す）。

**関係するテスト（古い形を前提にしているもの）**:
- `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py:501-548`（TC-17 は `recent_quizzes`・`active_session`・`subject_progress` を、TC-19 は `/recommendations/` を見る）
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py:267-269`（経路の表）
- `backend/dashboard/tests/test_I459_analytics_zero_division.py:135-151`（`/recommendations/` の 0 で割らないテスト）
- `backend/studylogs/tests/test_I455_org_scoped_querysets.py:253-298`（dashboard で `StudyLog` などを絞らずに読むときの理由のコメントを見張る。`QuizAnswer` は対象外のモデル）

**環境の前提**: `docker compose ps` で backend・db・frontend・redis が動いている（2026-11-13 確認）。設定は `TIME_ZONE = 'Asia/Tokyo'`・`USE_TZ = True`（`backend/core/settings.py:119-121`）。時刻を止めるライブラリ（freezegun など）は入っていない → 「今」は関数の引数で渡せるようにする（`review_summary(now=None)` と同じ形・`backend/studylogs/services.py:128`）。既存テストの手元での全件実行はしない（CI が正・関係するテストだけ CI で見る）。

## 2. 受け入れ条件
（イシューの受け入れ条件と同じ。番号は TC との対応のため）
- [ ] AC1 クイズを解いた結果が、今日の学習時間・解答問題数・正答率・連続学習日数・直近 7 日の推移・間違いやすい分野に反映される（期待値テストで固定）。今日の復習の回も含める
- [ ] AC2 学習時間は `QuizAnswer.time_taken` の合計で、1 問あたり 300 秒を上限に切り詰める
- [ ] AC3 「今日」・連続日数・直近 7 日は日本時間の日付で数える。連続日数は今日まだ答えていなくても昨日まで続いていれば途切れない。直近 7 日は答えが無い日も 0 で 7 件返す
- [ ] AC4 「間違いやすい分野」は 5 問以上答えた科目のうち正答率 70% 未満を低い順に最大 3 件。おすすめは最大 3 件で科目の ID を持ち、「練習する」でその科目のクイズへ進む
- [ ] AC5 `GET /api/dashboard/overview/` の応答のキーと型が契約（5 章）どおり（BE テストで固定）
- [ ] AC6 画面が契約どおりのキーを読み、キーの欠落を 0 で埋めずエラーとして扱う（FE テストで固定）
- [ ] AC7 学習データ 0 件のユーザーで「不正解 100%」の赤い円が出ない（「データ無し」と区別される）
- [ ] AC8 科目を選ぶと今日・連続日数・直近 7 日・正答率がその科目だけで数えられる。「間違いやすい分野」とおすすめは科目の選択に関係なく全科目から出る。不正な `subject_id`（数字でない・他組織・全体共有〔組織なし〕・存在しない）は同じ 400 と同じ文言
- [ ] AC9 おすすめが画面に出る（overview に統合・`/api/dashboard/recommendations/` は削除）
- [ ] AC10 1 回の表示あたりのクエリ数が、データの量に依らない定数本
- [ ] AC11 本人以外・他組織の答えが集計に入らない・未認証は 401。#446 の横断テストが通る
- [ ] AC12 今日の復習のカードがこれまでどおりダッシュボードのいちばん上（科目の選択の下）に出る
- [ ] AC13 #467 の引き継ぎ 3 件が直っている
- [ ] AC14 クイズに答える → ダッシュボードの数字に反映される E2E が通る
- [ ] AC15 既存機能に退行が無い（CI の全テスト・E2E が通る）

## 3. 影響範囲
- Backend: `backend/dashboard/`（overview の作り直し・セレクタとシリアライザの新設・recommendations の経路の削除・テスト）、`backend/studylogs/views.py`（引き継ぎ 2）、`backend/core/subject_service.py`・`backend/problems/signals.py`（引き継ぎ 3）、境界テストの表（I431・I446・I459 のテスト）
- Frontend: `frontend/src/pages/Dashboard.tsx`・`frontend/src/services/dashboard.service.ts`・`frontend/src/services/types.ts`・新しいテスト `frontend/src/pages/__tests__/Dashboard.test.tsx`
- E2E: `e2e/tests/quiz-session.spec.ts` に 1 本
- DB: 変更なし（マイグレーション無し。`StudyLog`・`DailyStudySummary`・`StudyGoal` は残す）
- Config/Infra: なし。依存の追加なし
- 変えない（意図的に対象外）: `backend/studylogs/mistake_analysis.py`・`backend/studylogs/tasks.py`・`backend/core/tasks.py`（`StudyLog` を読み続けるが、表を残すので影響しない）、統計画面（`DashboardAnalyticsView`・`Statistics.tsx`・#488）、見た目・使い勝手（#487）

## 4. 変更点一覧（具体）

### 修正アプローチ
数字の出どころを `QuizAnswer`（本人のクイズの答え・組織の境界で絞る）に 1 本化する。数える処理は読み取り専用のセレクタ（`backend/dashboard/selectors.py`）にまとめ、ビューは入力の確かめ・セレクタの呼び出し・シリアライザでの出力だけにする。応答の形はシリアライザで固定し、画面は同じ形の型で読む。画面は受け取った形を確かめ、欠けていればエラーの表示にする。

### 4.1 API 契約（`GET /api/dashboard/overview/`）
- 認証: `permission_classes = [permissions.IsAuthenticated]`（未認証は 401）
- クエリ: `subject_id`（省略可・整数・自組織の科目だけ。`OrgSubjectField(required=False)`）
- 400（`subject_id` が数字でない・他組織・存在しない）: `core.exceptions.create_error_response('科目の指定が正しくありません', 'ダッシュボードの科目の選択からやり直してください', 400)` → body `{"error": {"main_message": "科目の指定が正しくありません", "sub_message": "ダッシュボードの科目の選択からやり直してください", "details": {}}}`（`review_summary` と同じ文言）
- 200 の body（キーは全部必須。比率は 0〜1 を小数第 4 位で丸めた数・答えが 0 件なら `null`）:
```json
{
  "has_data": true,
  "today": {"study_seconds": 330, "answered_count": 3, "correct_count": 2, "accuracy_rate": 0.6667},
  "streak": {"current_days": 2},
  "totals": {"answered_count": 12, "correct_count": 9, "accuracy_rate": 0.75},
  "last_7_days": [
    {"date": "2026-11-07", "study_seconds": 0, "answered_count": 0, "correct_count": 0}
  ],
  "weak_subjects": [
    {"subject_id": 3, "subject_name": "英語", "answered_count": 10, "accuracy_rate": 0.5}
  ],
  "recommendations": [
    {"kind": "weak_subject", "subject_id": 3, "subject_name": "英語", "reason": "正答率が 50% です。復習しましょう"},
    {"kind": "unstudied_subject", "subject_id": 4, "subject_name": "数学", "reason": "この 7 日間、解いていません"}
  ]
}
```
- 範囲: `has_data`・`today`・`streak`・`totals`・`last_7_days` は `subject_id` があればその科目だけ。`weak_subjects`・`recommendations` は常に全科目
- `has_data`: 範囲内の答えが 1 件以上あるか（= `totals.answered_count > 0`）
- `last_7_days`: 今日（日本時間）を含む直近 7 日・古い順・必ず 7 件
- `GET /api/dashboard/recommendations/` は削除（404 になる）

### 4.2 数え方の決まり（`backend/dashboard/selectors.py` の定数）
| 定数 | 値 | 意味 |
|---|---|---|
| `STUDY_SECONDS_CAP_PER_ANSWER` | 300 | 1 問あたりの学習時間の上限（秒） |
| `RECENT_DAYS` | 7 | 直近の日数（推移・「この 7 日間解いていない」） |
| `WEAK_MIN_ANSWERED` | 5 | 間違いやすい分野に入れる最低の解答数 |
| `WEAK_ACCURACY_BELOW` | 0.7 | 間違いやすい分野の正答率のしきい値（未満） |
| `LIST_LIMIT` | 3 | 間違いやすい分野・おすすめの最大件数 |

- 答えの範囲: `QuizAnswer.objects.filter(session__user=user)` を `scope_to_user_org(qs, user, subject_path='problem__subject')`（`backend/problems/querysets.py:11`）で自組織の科目の問題だけに絞る。セッションの `mode`（通常・今日の復習）は問わない
- 科目: 答えの科目は `problem__subject`（問題の科目。セッションの科目は「すべて」で空のことがあるため使わない）
- 学習時間: `Sum(Least('time_taken', Value(300)))`
- 日付: `TruncDate('answered_at')`（`USE_TZ` で現在のタイムゾーン＝日本時間）・今日は `timezone.localdate(now)`
- 連続日数: 答えのある日付（重複なし・新しい順）を 1 クエリで取り、今日から（今日が無ければ昨日から）続く日数を数える
- 間違いやすい分野: 科目ごとに件数・正解数を数え、`answered_count >= 5` かつ `correct / answered < 0.7` を正答率の低い順（同じなら科目名順）に 3 件
- おすすめ: ① 間違いやすい分野の科目（`kind='weak_subject'`）→ ② 利用者が選んだ科目（`subject_service.get_user_selected_subjects`）のうち、直近 7 日に答えが無く、自組織の未削除の問題が 1 問以上ある科目を科目名順（`kind='unstudied_subject'`）。合わせて最大 3 件・同じ科目は 1 回だけ
- `reason` の文言: weak は `正答率が {四捨五入した %} % です。復習しましょう`、unstudied は `この 7 日間、解いていません`

### 4.3 ファイルごとの変更
1. **`backend/dashboard/selectors.py`（新設）**
   - 方針: 読み取り専用の集計をビューから外に出す（規約 6 章のセレクタ・Fat View にしない）。`#488` の統計画面でも使い回す
   - `build_overview(user, subject=None, *, now=None) -> dict`: 4.1 の形の dict を返す。中で `_answers(user)`（範囲の土台）・`_summary(qs)`・`_last_7_days(qs, today)`・`_current_streak(qs, today)`・`_weak_subjects(qs)`・`_recommendations(user, base_qs, weak, today)` を呼ぶ
   - 比率は `_rate(correct, answered)`（0 件なら `None`・小数第 4 位）
2. **`backend/dashboard/serializers.py`**
   - `OverviewQuerySerializer`（`subject_id = OrgSubjectField(required=False)`・context に request が要る）
   - `OverviewSerializer` と入れ子のシリアライザ（`TodaySerializer`・`StreakSerializer`・`TotalsSerializer`・`DaySerializer`・`WeakSubjectSerializer`・`RecommendationSerializer`）。比率は `FloatField(allow_null=True)`・`kind` は `ChoiceField(['weak_subject', 'unstudied_subject'])`
3. **`backend/dashboard/views.py`**
   - `DashboardOverviewView.get`: 入力を `OverviewQuerySerializer` で確かめ（不正なら 4.1 の 400）→ `build_overview(request.user, subject)` → `OverviewSerializer(data).data` を返す。`_calculate_study_streak`・`_get_subject_progress`・`_get_upcoming_goals` を消す
   - `SubjectRecommendationView` を消す。使わなくなる import（`QuizSession`・`available_problems`・`F` など）を消す。`DashboardAnalyticsView` は変えない（#488）
4. **`backend/dashboard/urls.py`**: `dashboard/recommendations/` の行と import を消す
5. **`backend/studylogs/views.py`（`StudyLogViewSet.create`・引き継ぎ 2）**: 閉じる対象を `StudyLog.objects.for_user(request.user).filter(is_active=True)` にする（理由のコメント「組織で絞らない」を消す）
6. **`backend/core/subject_service.py`（`get_user_selected_subjects`・引き継ぎ 3）**: キーを `user_subjects_{user.id}_org_{user.organization_id}_count_{annotate_count}` にする。キャッシュに当たった経路にも `.order_by('name')` を付ける。キーを作る関数 `user_subjects_cache_key(user_id, organization_id, annotate_count)` を同じファイルに置き、signals からも使う
7. **`backend/problems/signals.py`（引き継ぎ 3 の消費箇所）**: 無効化するキーを 6 の関数で作る（`instance.user.organization_id` を使う）
8. **`frontend/src/services/types.ts`**: `StudyStats`・`StudySession`（他で使っていないことを確認して消す）・`DashboardData` を、4.1 と同じ形の `DashboardOverview`（`today`・`streak`・`totals`・`last_7_days`・`weak_subjects`・`recommendations`・`has_data`）に置き換える
9. **`frontend/src/services/dashboard.service.ts`**: `getDashboardData` を `getOverview(params?: { subject_id?: string }): Promise<DashboardOverview>` にし、応答の形を確かめる関数 `isDashboardOverview(data: unknown): data is DashboardOverview`（必須キーと型を見る）で確かめ、合わなければ `Error('ダッシュボードの応答の形が違います')` を投げる。`getRecommendations` を消す
10. **`frontend/src/pages/Dashboard.tsx`**
    - 既定値で埋める処理（`dashboardDataWithDefaults`・展開時の既定値）を消す。取得に失敗したら（形が違うときも）、数字の場所に `Alert severity="error"`「ダッシュボードの数字を読み込めませんでした」を出す（再試行のボタンなど見た目の作り込みは #487）。今日の復習のカードと科目の選択はそのまま出す
    - 数字のカード: 今日の学習時間 = `Math.floor(today.study_seconds / 60)` 分・連続学習日数 = `streak.current_days` 日・解答問題数 = `totals.answered_count`・正答率 = `totals.accuracy_rate` が `null` なら `—`、そうでなければ `Math.round(rate * 100)` %。解答問題数の数字に `data-testid="stat-answered-count"` を付ける（E2E 用）
    - 推移のグラフ: 見出しを「直近 7 日の学習時間」にし、`last_7_days` の 7 件を曜日のラベル・分（`Math.round(study_seconds / 60)`）で描く
    - 正答率のドーナツ: `has_data` が false なら描かず、`まだ解答の記録がありません` の文を出す。true なら `[rate, 1 - rate]` で描く
    - 間違いやすい分野: `weak_subjects` をそのまま並べる（チップ = `Math.round(accuracy_rate * 100)` %・注記 = `解答数: {answered_count}問`）。`has_data` が false なら今の文言「データがありません。まずは問題を解いてみましょう！」、true で 0 件なら `正答率が 70% 未満の科目はありません`
    - おすすめ: `recommendations` を並べる（見出し = `subject_name`・説明 = `reason`）。「練習する」で `/quiz?subject={subject_id}` へ進む
    - 達成のお知らせ（`checkForAchievements`）は新しいキーで同じ判定をする（連続日数 = `streak.current_days`・解答数 = `totals.answered_count`・正答率 = `totals.accuracy_rate`〔null は判定しない〕・今日の分 = `today.study_seconds`）。目標 60 分の固定は #487 で直すので変えない
    - 並び（今日の復習のカードがいちばん上・科目の選択の下）は変えない
11. **`backend/dashboard/tests/test_I473_overview.py`（新設）**・**`frontend/src/pages/__tests__/Dashboard.test.tsx`（新設）**・**`e2e/tests/quiz-session.spec.ts`**: 6 章・自動テスト文書のとおり
12. **既存テストの合わせ込み**
    - `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`: TC-17 を新しいキーで書き直す（他組織の科目の答えが `weak_subjects`・`recommendations`・数字に出ない）。TC-19（`/recommendations/`）は overview の `recommendations` を見る形に書き直す
    - `backend/core/tests/test_I446_cross_api_tenant_isolation.py`: `"GET api/dashboard/overview/"` を `[ListCheck(), IdCheck("user", "query", "subject_id", "subject", 400)]` にし、`"GET api/dashboard/recommendations/"` を消す
    - `backend/dashboard/tests/test_I459_analytics_zero_division.py`: `test_recommendations_with_zero_problem_log` と定数 `RECOMMENDATIONS` を消す（経路を消すため。0 で割らないことは新しいセレクタの `_rate` のテスト〔TC-07〕が受け持つ）
    - `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py` に、引き継ぎ 2 のテストを足す（TC-15）。引き継ぎ 3 のテストは `backend/dashboard/tests/test_I473_overview.py` に置く（TC-16）

## 5. 実装手順（ステップ）
各ステップは画面まで縦に通す。ステップ 2 は 1 の後、3 は 2 の後。4 は 1〜3 と並べてよい。
1. **土台と今日の数字を縦に通す**（未知のリスクの先出し: `TruncDate` が日本時間で区切られること・`Least` の上限・`scope_to_user_org` を `QuizAnswer` に使えること）: `selectors.py`（範囲の土台・`today`・`totals`・`has_data`）・シリアライザ・ビュー（`subject_id` の 400 を含む）・画面の型・サービス・数字のカードとドーナツ・エラー表示 → TC-01・02・03・06・07・08・09・13・20・21・22・23 参照
2. **直近 7 日・連続日数を足す**（セレクタ・シリアライザ・推移のグラフ）→ TC-04・05・20 参照
3. **間違いやすい分野・おすすめを足し、recommendations の経路を消す**（セレクタ・シリアライザ・URL・画面の 2 枚のカード・I431/I446/I459 のテストの合わせ込み）→ TC-10・11・14・17・20 参照
4. **引き継ぎ 2・3**（`studylogs/views.py`・`subject_service.py`・`signals.py`）→ TC-15・16 参照
5. **クエリ数の固定と E2E**（1〜3 の後）→ TC-12・24 参照
6. `/simplify` で整理し、画面確認（手動テスト No.1〜5）
- サービスの再起動: ファイルの削除は無い。開発サーバーは自動で読み直すので不要

## 6. テスト計画
### 自動（詳細は `docs/tests/open/I473_auto_test.md`）
- レベルの分け方: 数え方の決まり（境界値・日付・上限）はセレクタを直接呼ぶ BE のテスト（`now` を渡す）／契約・400・401・境界・クエリ数は API を呼ぶ BE のテスト／画面が契約を読むこと・データ無し・欠落時のエラーは FE のテスト（`apiClient` をモック）／元の不具合（答えても 0 のまま）は E2E 1 本
- 再発防止: TC-02（答えると数字が増える）・TC-22（欠落を 0 で埋めない）・TC-24（E2E）
- 認可・境界: TC-09・TC-13・TC-17（#446・I431 の横断テスト）
- 実行: pytest・Jest・E2E は CI が PR ごとに流す（手元での全件の流し直しはしない）。決定論ゲートの追加は無い
### 手動（`docs/tests/open/I473_manual_test.md`）
- すべて Claude が Playwright MCP で確かめる（答える前後の数字・データ無しのユーザー・科目の切り替え・おすすめの遷移・コンソール）

## 7. ロールバック
- PR を revert する（DB の変更・マイグレーション・設定の変更が無いので、コードを戻すだけで元に戻る）
- キャッシュのキーが変わる（引き継ぎ 3）が、古いキーは期限で消え、新しいキーは使われなくなるだけなので、戻しても害は無い

## 8. Risk & 回避策
- R1 `TruncDate` が UTC で区切ると、日本時間の 0〜9 時の答えが前の日になる → TC-03 で 0:30 と 23:30（日本時間）の答えを入れて固定する
- R2 他組織の問題への答え（過去の不具合で残ったもの）が数字や科目名に混ざる → 土台で `scope_to_user_org(subject_path='problem__subject')` を必ず通し、TC-13・TC-17 で固定する
- R3 クエリ数が日数・科目数で増える → 連続日数は日付の一覧を 1 回で取り、科目別は 1 回の集計にする。TC-12 で小さいデータと大きいデータのクエリ数が同じことを固定する
- R4 画面が形の違う応答を黙って受ける（元の不具合の再発）→ `isDashboardOverview` で確かめ、TC-22 で固定する
- R5 `/recommendations/` を消すことで、ほかに呼んでいるところが壊れる → 画面では未使用（`grep` で確認済み・調査結果 5）。テストの参照は 4.3 の 12 で直す
- R6 キャッシュのキーを変えたことで無効化の漏れ → signals と同じ関数でキーを作り、TC-16 で保存したら消えることを固定する

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 集計元は `QuizAnswer`。学習時間は `time_taken` の合計・1 問 300 秒上限。日本時間。今日の復習の回も含める
- 連続日数は「今日まだでも昨日まで続いていれば途切れない」。直近 7 日は 0 の日も 7 件
- 間違いやすい分野は 5 問以上・70% 未満・低い順に 3 件。おすすめは 3 件・科目の ID つき・その科目のクイズへ
- 科目の選択は今日・連続日数・推移・正答率に効き、間違いやすい分野とおすすめは全科目から
- 不正な `subject_id` は `review_summary` と同じ 400
- `StudyLog` などはダッシュボードから外すだけで残す。`/recommendations/` と `getRecommendations` は消す
- 応答の形はシリアライザで固定し、OpenAPI からの型の自動生成は入れない
- 見出しは「直近 7 日の学習時間」
- 統計画面は #488、見た目・使い勝手と目標時間は #487
- クイズに答える → 反映の E2E を 1 本

Claude が決めた（技術的な選択と理由）:
- 集計の置き場所を `services.py` ではなく `selectors.py` にする — 仮定で決めた。規約 6 章で読み取り専用の処理はセレクタに置くため（イシューの「services.py（新設する前提）」の名前だけを変える。#488 の本文も同じ集計を使い回す前提なので、置き場所の名前の違いは #488 の計画で読み替える）
- 答えの科目は問題の科目（`problem__subject`）— 仮定で決めた。セッションの科目は「すべて」で空になることがあり、科目別に数えられないため
- 他組織の問題への答えは、数だけの集計も含めて全部除く — 仮定で決めた。I431 の扱いの基準 3（数だけなら絞らない）は「科目が空の記録まで消えて自組織の数字が変わる」おそれへの配慮だったが、`Problem.subject` は必須で空にならないので、絞っても自組織の数字は変わらない。土台を 1 つにしたほうが漏れにくい
- 「科目別の進み具合」は `weak_subjects`（間違いやすい分野）で表す — 仮定で決めた。今の画面で科目ごとの数字を出すのはこのカードだけで、使わない科目別の一覧を API に足すのは不要な機能になるため
- おすすめの「今の決まり」の読み方 — 仮定で決めた。今の `SubjectRecommendationView` の 2 本立て（苦手な科目・最近 7 日に学習していない科目）を残し、苦手の判定は間違いやすい分野と同じ決まり（5 問以上・70% 未満）にそろえる。今の実装は「直近 7 日・件数の下限なし」で、1 問だけ間違えた科目まで苦手になるため。問題が 0 問の科目は進んでも解けないので出さない
- `reason` の文言（4.2）— 仮定で決めた。今の文言（「正答率が{x}%と低めです。復習をお勧めします。」「最近学習していない科目です。定期的な復習をお勧めします。」）を短くしただけで、意味は同じ。UI の配置・流れは変えない
- 間違いやすい分野が 0 件のときの文言 `正答率が 70% 未満の科目はありません`・データ無しのドーナツの文言 `まだ解答の記録がありません`・取得失敗の文言 `ダッシュボードの数字を読み込めませんでした` — 仮定で決めた。設計確認メモの「データ無しと区別する」「欠損をエラーとして扱う」を満たす最小の文言で、空状態・エラー状態の作り込み（案内のボタン・再試行・スケルトン）は #487 が決める。ユーザーの指示「BP・UI/UX の観点で問題ないやり方で進めて」の範囲と判断し、止めない
- 正答率の表示: 答えが 0 件なら `—`（0% と区別する）— 仮定で決めた。AC7 の「データ無しと区別」を数字のカードにも当てはめた
- 「今」を引数で渡す（`build_overview(..., now=None)`）— 仮定で決めた。時刻を止めるライブラリが無く、依存を増やさずに日付の境界を確かめるため（`review_summary` と同じ形）
- 画面の形の確かめは手書きの型ガード — 仮定で決めた。zod などの依存を足さない。キーは 7 つで、入れ子も浅い
- 引き継ぎ 3 のキャッシュのキーは関数にして signals と共有 — 仮定で決めた。キーの文字列を 2 か所に書くと、片方だけ直して無効化が漏れるため
- クエリ数の上限は「データの量で変わらない」ことをテストで固定し、上限の本数そのものは実装後に数えて TC-12 に書く — 仮定で決めた。本数を先に決め打ちすると意味のない調整が要るため。目安は 15 本以下

セキュリティ・BP の確認:
- 入力: `subject_id` は `OrgSubjectField`（自組織の科目だけ）。他組織・存在しない・数字でないは同じ 400 で違いを見せない（存在の推測を防ぐ）
- 認証・認可: `IsAuthenticated` のまま。集計は本人（`session__user=user`）かつ自組織の科目（`scope_to_user_org`）に限る（最小権限）
- 機密: 応答は本人の件数・時間・正答率・自組織の科目名だけ。個人情報・他人のデータを含まない。ログには何も足さない
- OWASP: SQL は ORM だけ（生の SQL なし）。画面は React の通常の描画で `dangerouslySetInnerHTML` を使わない（科目名・理由の文はテキストとして出す）。GET だけで CSRF の対象の書き込みは無い
- 依存: 追加なし（pip-audit・npm audit の対象の変化なし）
- スキャンの重大度: bandit は MEDIUM 以上を直す（LOW は `# nosec` で理由つき）。npm audit は high/critical を直す。どちらも CI の既存の設定のまま
- P3/P5/P8（DB 変更・外部 API・非同期・インフラ・依存）: 影響なし
- P6（性能・UX）: 13 章に書く
- P9（プライバシー）: 本人の学習データだけを本人に返す。テナントをまたぐ読み出しを土台で禁止（15 章は「個人情報の新しい扱いが無い」ため省略。境界は TC-13・TC-17）

台帳の残りの一覧:
- 一覧 `docs/reviews/backlog/I223.md` B1〜B4・`docs/reviews/backlog/I224.md` F9（`FILE=-`）: 残す — どれもハーネス（bot の PR・鍵・計測）の話で、本イシューの変更と関係しない
- 実装対象のファイル（4.3）に当たる行: 一覧の該当なし

Danger Ops（有無/手順/ロールバック）:
- 無（DB・データの削除・大量更新・強制 push は無い）

## 13. 性能・UX設計
- クエリ: 範囲の土台に対して、今日・全期間・直近 7 日・日付の一覧・科目別・選んだ科目・最近答えた科目・問題のある科目をそれぞれ 1 回の集計で取る（データの量・日数・科目数で本数が増えない）。`answered_at` で範囲を絞る集計は既存の索引の有無に依らず本人の答えの件数（数百〜数千）で十分速い
- ローディング: 今の「ダッシュボードを読み込み中...」のまま（スケルトンは #487）
- 空状態: `has_data` が false なら赤いドーナツを出さず `まだ解答の記録がありません`・正答率は `—`・間違いやすい分野は今の案内文
- エラー状態: 取得の失敗・形の違いで `Alert` の文を出す（数字を 0 で出さない）。今のトーストも残す
- 破壊的操作: 無い
- アクセシビリティ: 新しい文は通常のテキスト（`Typography`）で、`Alert` は role="alert" を持つ。色だけで意味を伝えない（チップには % の数字を出す）

## 14. 学習効果設計
- 学習時間を「問題に向き合った時間（1 問 5 分まで）」にし、放置を数えないので、学習量の指標として信用できる
- 間違いやすい分野は 5 問以上で判定し、たまたまの 1 問で「苦手」と出さない（つまずきの誤検知を減らす）
- 今日の復習の回も数えるので、間隔反復の学習が成果として見える（続ける動機づけ）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 他組織の科目の問題への答え・他人の答えを入れても、overview のどの数字・科目名にも出ない（TC-13・TC-17） |
| V2 | 1 | 読んで可 | `subject_id` が数字でない・他組織・全体共有（組織なし）・存在しないのどれでも、同じ 400 と同じ body になる（TC-09） |
| V3 | 2 | 読んで可 | TC-12 が「データを増やしてもクエリ数が同じ」ことを比べていて、片方だけを数える形（データが少ないと常に通る）になっていない |
| V4 | 2 | 読んで可 | TC-22 がキーを 1 つ欠いた応答で「0 が出ない・エラーの文が出る」ことを見ていて、正常な応答だけで通る形になっていない |
| V5 | 3 | 読んで可 | 日本時間の 0〜9 時の答え（TC-03）・300 秒を超える答え（TC-02）・ちょうど 70% と 4 問の科目（TC-10）の境界がテストにある |

## 計画変更記録
- 計画レビュー（20261113_0841）の Warning・Info への対応（方式・範囲・受け入れ条件は変えないので再レビューはしない）: V1・V2 の確かめ方を「読んで可」に（TC で覆うため）／AC8・TC-09・V2 に全体共有（組織なし・`Subject.organization` は null 可）の科目を足した（`OrgSubjectField` は自組織の科目だけを候補にするので 400 になる）／TC-05 の「7 日前」を「6 日前」に直した／手動テスト No.4 の対象を「E2E Subject A」（e2e_user_a が選んでいて、問題が 1 問あり、答えが無い科目）に固定した／TC-12 の上限は実装後に書き足す
- 「科目別の進み具合」を `weak_subjects` で表すこと（レビューの Warning）: 今の画面で科目ごとの数字を出すのは「間違いやすい分野」のカードだけで（`Dashboard.tsx:453-487` は `subject_progress` を正答率 70% 未満に絞って 3 件出すだけ）、出していた中身は `weak_subjects` で同じ（しきい値の 5 問以上が加わる）。画面から消える表示は無い。イシューの受け入れ条件の読み方として 9 章に書いたとおりで、本文の書き戻しは close 段階の報告でユーザーに伝える

## レビュー結果
- [20261113_0841 判定: ✅ 完了](../../reviews/I473_plan_review_20261113_0841.md)
