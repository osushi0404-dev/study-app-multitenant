# I466 計画書: 間違い分析と苦手を優先した出題を画面につなぐ

## 基本情報
- **計画書ID**: plan_I466
- **関連イシュー**: #466
- **Draft PR**: #564
- **作成根拠資料**: docs/issues/open/I466.md（GitHub #466 の本文の写し。設計確認メモ 2026-11-17）
- **実装後評価**: docs/reviews/closed/I466_review.md
- **作成日**: 2026-11-17

## 1. 背景/目的
- **背景**: 間違い分析（`/api/study/mistake-analysis/`）と適応的な問題選択（`/api/study/adaptive-learning/`）は、どの画面からも呼ばれていない。材料の `ProblemAttempt` はどこからも作られず、結果を保存する作り（`MistakePattern` など）は実行のたびに同じ間違いを足し込む。定期処理は開発用の間隔（30 秒・1 分・5 分）のままで、学習リマインダーのメールが 1 分ごとに送られうる。一方、ダッシュボードには I473・I487 で「間違いやすい分野（科目別）」「おすすめ」が `QuizAnswer` から出ている。
- **目的**: 間違い分析のうち今は無い情報（難易度別の苦手・急いで答えた間違い）をダッシュボードのカードに出し、苦手を優先した出題をクイズのモード `weak` として使えるようにする。材料を `QuizAnswer` にそろえ、使われない分析・API・定期処理を片付ける。

### 調査結果
**原因の概要**: 2 つの機能は、クイズとは別の記録を材料にする前提で裏側だけ先に作られ、画面にも、実際の回答の記録にもつながらないまま残っていた。

**詳細な原因分析**
1. クイズの回答（`POST /api/quiz/<pk>/submit_answer/`・`backend/problems/views.py:909-`）が作るのは `QuizAnswer` と、I452 からの `SpacedRepetitionReview`（`views.py:985` の `record_quiz_answer`）だけ。`ProblemAttempt` を作る経路は無い（`grep -rn "ProblemAttempt.objects.create" backend` は tests だけ）。
2. `backend/studylogs/mistake_analysis.py` の `_analyze_subject_difficulties`（82-131 行）・`_analyze_problem_type_errors`（133-180 行）などは、`get_or_create` した `MistakePattern` に `occurrence_count += ...` で同じ期間の数を足し込む。`backend/core/celery.py` の `analyze-mistake-patterns`（5 分ごと）で回すたびに膨らむ。
3. `_generate_general_suggestions`（446-473 行）は `StudyLog` の件数で「学習習慣の確立」を作るが、`StudyLog` を書く画面の経路は無い（I473 で表は残すと決定）ので、いつも作られる。
4. `backend/studylogs/adaptive_selection.py` の `_calculate_problem_score`（383-437 行）は候補の問題ごとに `ProblemAttempt` を数える（I455 F4）。
5. 画面: `frontend/src/` に `mistake-analysis`・`adaptive-learning` を呼ぶところは無い（grep 0 件）。クイズの出題は `QuizService.get_next_problem`（`backend/problems/services/quiz_service.py:94-164`）が `order_by('?')` で選ぶ。モードは `normal`・`review` の 2 つ（`backend/problems/models.py:206-221`）。
6. ダッシュボードの `weak_subjects`（`backend/dashboard/selectors.py:141-160`）は `QuizAnswer` の全期間から「5 問以上・正答率 70% 未満」で出している（定数 `WEAK_MIN_ANSWERED`・`WEAK_ACCURACY_BELOW`・20-22 行）。
7. 消す機能を使っているところ（`grep`・2026-11-17）:
   - `backend/studylogs/views.py`（`MistakeAnalysisViewSet` 614 行〜・`AdaptiveLearningViewSet` 838 行〜末尾・import 7-28 行）、`urls.py` 16-17 行、`serializers.py` 215 行〜末尾（`MistakePatternSerializer`〜`SelectedProblemsSerializer`）
   - `backend/studylogs/tasks.py`（`analyze_mistake_patterns_task`・`cleanup_expired_suggestions_task`・`update_user_proficiency_task`・`generate_learning_insights_task`。後ろ 2 つはどこからも呼ばれていない）
   - `backend/core/cache_service.py`（`*_mistake_patterns_cache`・`*_learning_suggestions_cache`・`*_proficiency_cache`。317-319 行・381-383 行の無効化の呼び出し）
   - テスト: `backend/core/tests/test_I446_cross_api_tenant_isolation.py`（`MA`・`AL` の行・133-134 行と表）、`backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`（271・279・291・310・436・577 行のテスト）、`backend/studylogs/tests/test_I452_quiz_review.py`（25-39 行の import と、`MA`・`AL`・`MistakeAnalysisService`・`AdaptiveProblemSelector` を使うテスト）
   - `POST /api/problems/generate_adaptive/`（AI の問題の生成）は名前が似ているが別の機能で、対象外
8. 応答の契約: `/api/dashboard/overview/` は `backend/core/openapi.py` の `CONTRACT_PATHS` に入っている。シリアライザを変えたら `backend/openapi.yaml` と `frontend/src/types/api/schema.d.ts` を作り直す（`docs/runbooks/common-commands.md`「API の形を変えたとき」）。画面は `frontend/src/services/dashboard.service.ts` の `isDashboardOverview` で形を確かめる。
9. 環境: `docker compose ps` で backend・db・frontend・redis が動いている（2026-11-17）。celery の worker・beat はふだん起動していない（定期処理の確認は設定の読み込みで行う）。
10. 関連: #470（回答の記録をサービスへ）・#471（`QuizSession` の分割）はどちらも OPEN（2026-11-17）。先にマージされたら、その形に合わせる。

## 2. 受け入れ条件
- [ ] AC1: ダッシュボードの「間違いやすい分野（全科目）」のカードに、初級・中級・上級のうち 5 問以上答えて正答率 70% 未満の難易度が、正答率と解答数つきで出る（当てはまらなければ見出しごと出ない）（TC-02・TC-03・TC-20）
- [ ] AC2: 直近 30 日に 20 問以上答え、間違いのうち自分の平均の解答時間の半分未満で答えたものが 25% 以上のとき、カードに「急いで答えた問題の間違いが多めです（間違いの ◯%）。落ち着いて解きましょう」が出る（当てはまらなければ出ない）（TC-04〜TC-06・TC-21）
- [ ] AC3: ダッシュボードの「苦手を優先して始める」と、おすすめの「間違いやすい分野」の「練習する」から、モード `weak` のクイズが始まる（TC-22〜TC-24・TC-26）
- [ ] AC4: モード `weak` の次の問題は、最後に間違えた問題 → 苦手な難易度の問題 → 未回答・しばらく答えていない問題の順に優先され、同じ回で続けて同じ問題が出ない。その科目の解答が 5 問未満なら通常と同じ順で出て、クイズの画面に「この科目はまだ解答が少ないため、いつもの順で出題しています」が出る（TC-10〜TC-14・TC-25）
- [ ] AC5: 苦手の基準（5 問以上・正答率 70% 未満）が、科目別・難易度別・苦手を優先の出題で `backend/problems/services/weakness.py` の 1 か所の定数から読まれている（TC-31b・TC-31c・コードレビュー）
- [ ] AC6: 2 機能の材料が `QuizAnswer` で、`ProblemAttempt` を読まない。`MistakePattern`・`LearningWeakness`・`LearningSuggestion` に書き込む経路が無い（TC-31a）
- [ ] AC7: `/api/study/mistake-analysis/` と `/api/study/adaptive-learning/` の下の経路が 404 になる（TC-30）
- [ ] AC8: `backend/core/celery.py` の定期処理がすべて時刻（`crontab`）で決まり、間違いパターンの分析・期限切れの提案の掃除の定期処理が無く、登録したタスクがすべて実在する（TC-32）
- [ ] AC9: 苦手を優先の次の問題を選ぶ問い合わせの数が、候補の問題の数に比例しない（TC-15）
- [ ] AC10: I431・I446・I452・I455・I473 の回帰テストがすべて pass する（消した経路の分は新しい経路に合わせて直す）（TC-33）
- [ ] AC11: 全テストが pass する（CI）

## 3. 影響範囲
- Backend:
  - 新規 `backend/problems/services/weakness.py`（苦手の基準・難易度別の苦手・急いだ間違い・苦手を優先の並べ方）
  - `backend/problems/models.py`（`QuizSession.MODE_WEAK`）・`backend/problems/migrations/0023_quizsession_mode_weak.py`（新規）・`backend/problems/services/quiz_service.py`・`backend/problems/views.py`（`next_problem` の応答に `is_weak_fallback`）
  - `backend/dashboard/selectors.py`・`backend/dashboard/serializers.py`（overview に `weak_difficulties`・`rushed_mistakes`）・`backend/openapi.yaml`（作り直し）
  - `backend/studylogs/views.py`・`urls.py`・`serializers.py`・`tasks.py`（消す）、`backend/studylogs/mistake_analysis.py`・`backend/studylogs/adaptive_selection.py`（ファイルごと消す）
  - `backend/core/cache_service.py`（使われなくなるキャッシュの関数を消す）・`backend/core/celery.py`（定期処理）
- Frontend:
  - `frontend/src/components/dashboard/WeakSubjectsCard.tsx`・`frontend/src/components/dashboard/StartQuizCard.tsx`・`frontend/src/components/dashboard/RecommendationsCard.tsx`・`frontend/src/pages/QuizSession.tsx`
  - `frontend/src/services/dashboard.service.ts`（形の確かめ）・`frontend/src/constants/routes.ts`（`quizPath`）・`frontend/src/types/api/schema.d.ts`（作り直し）・`frontend/src/types/quiz.ts`（`QuizMode` に `weak`・`Problem.is_weak_fallback`）
  - 新規 `frontend/src/utils/difficulty.ts`（難易度の表示名。`QuizSession.tsx` の `getDifficultyLabel` と共通にする）
- DB: `QuizSession.mode` の選択肢に `('weak', '苦手を優先')` を足す（`AlterField`。DB の制約・データは変わらない）。表は消さない
- Config/Infra: celery beat の定期処理の間隔（本番の値へ）。依存ライブラリの変更なし（`celery.schedules.crontab` は導入済みの celery の機能）
- ドキュメント: `docs/issues/open/I466.md`（Draft PR の番号）

## 4. 変更点一覧（具体）

### 修正アプローチ
苦手の判定を 1 つのモジュール（`backend/problems/services/weakness.py`）にまとめ、ダッシュボードの集計とクイズの出題の両方がそれを使う。材料は `QuizAnswer.objects.for_user(user)` だけ。結果は保存せず、読むたびに数本の集計クエリで計算する。使われない分析（保存型・2 つの API・その定期処理・キャッシュ）は消し、表は残す。

### 4.1 `backend/problems/services/weakness.py`（新規）
**修正方針**: 苦手の基準の定数と計算をここだけに置く（AC5）。どの関数もクエリの数が回答・問題の件数で変わらない。

```python
WEAK_MIN_ANSWERED = 5          # 苦手と判定する最低の解答数
WEAK_ACCURACY_BELOW = 0.7      # 苦手とみなす正答率（未満）
ANSWER_SECONDS_CAP = 300       # 1 問の解答時間の上限（放置した時間を数えない。ダッシュボードの学習時間と同じ）
RUSHED_WINDOW_DAYS = 30        # 急いだ間違いを見る期間
RUSHED_MIN_ANSWERED = 20       # その期間の最低の解答数
RUSHED_TIME_RATIO = 0.5        # 平均の解答時間に対する「急いだ」の比（未満）
RUSHED_SHARE_AT_LEAST = 0.25   # 間違いに占める急いだ間違いの割合（以上）で出す

def user_answers(user) -> QuerySet[QuizAnswer]:
    """本人の、自組織の科目の問題への答え（QuizAnswer.objects.for_user）"""

def is_weak(answered: int, correct: int) -> bool:
    """answered >= WEAK_MIN_ANSWERED かつ correct / answered < WEAK_ACCURACY_BELOW"""

def weak_difficulties(answers) -> list[dict]:
    """難易度ごとに集計（1 クエリ・values('problem__difficulty').annotate(Count)）し、is_weak のものを
    正答率の低い順（同じなら易しい順）で返す。要素は {'difficulty': 'easy'|'medium'|'hard',
    'answered_count': int, 'accuracy_rate': float（小数第 4 位）}。数字と文字の対応は既存の
    backend/problems/difficulty.py（LABEL_BY_LEVEL・LEVEL_BY_LABEL・label_of）だけを使い、ここに対応表を作らない。
    label_of が None の難易度（1〜3 以外）は捨てる"""

def rushed_mistakes(answers, now) -> Optional[dict]:
    """直近 RUSHED_WINDOW_DAYS 日（now から遡る）の答えについて:
    1 クエリ目: 解答数・間違いの数・平均の解答時間（time_taken > 0 の答えだけ・Least(time_taken, 300) で頭打ち）
    （当てはまらなくても 2 クエリ目は流す。クエリの数をデータで変えない・I473）
    2 クエリ目: 間違いのうち 0 < time_taken < 平均 × 0.5 の数
    割合 = 急いだ間違い / 間違い。0.25 以上なら {'mistake_count', 'rushed_count', 'rushed_rate'（小数第 4 位）}、未満なら None"""

def order_weak_first(problems, user, subject) -> tuple[QuerySet[Problem], bool]:
    """苦手を優先の並べ方。戻り値は (並べた問題, いつもの順にしたか)
    - 判定の材料: user_answers(user)（subject があればその科目）の件数が WEAK_MIN_ANSWERED 未満なら
      (problems.order_by('?'), True)
    - そうでなければ、問題ごとに本人の最後の答え（Subquery・answered_at の新しい順・同じなら id）の
      answered_at と is_correct を注釈し、Case で段を付けて並べる:
        段 0: 最後の答えが不正解
        段 1: 難易度が weak_difficulties(user_answers(user)) に入る（全科目で判定・ダッシュボードの表示と同じ。
              文字を数字に戻すのは LEVEL_BY_LABEL）
      最後の答えの Subquery も user_answers(user)（本人・自組織だけ）から作る
        段 2: それ以外
      order_by('段', F('最後の答えの時刻').asc(nulls_first=True), 'id') → (並べた問題, False)
    - クエリ: 件数 1 本・難易度別の集計 1 本・本体 1 本（Subquery を含む 1 本）。候補の数で変わらない（AC9）"""
```
- 理由: ダッシュボードの `weak_subjects` と同じ基準を同じ定数で読ませ（`backend/dashboard/selectors.py` は `WEAK_MIN_ANSWERED`・`WEAK_ACCURACY_BELOW`・`STUDY_SECONDS_CAP_PER_ANSWER` の定義を消して、このモジュールから import する）、画面ごとの判定の食い違いを無くす。置き場所を `problems` にするのは、材料の `QuizAnswer` が `problems` のモデルで、`dashboard` → `problems`・`problems` 内の参照だけになり、循環 import を作らないため。

### 4.2 クイズのモード `weak`
**修正方針**: 通常のクイズと同じ進み方（同じ回では未回答の問題を先に出し、全部答えたら既出の問題から出す・総問題数は科目の問題数）のまま、選ぶ順だけを `order_weak_first` にする。
- `backend/problems/models.py`: `MODE_WEAK = 'weak'`、`MODE_CHOICES` に `(MODE_WEAK, '苦手を優先')` を足す
- `backend/problems/migrations/0023_quizsession_mode_weak.py`: `makemigrations` で作る `AlterField`（選択肢だけ）
- `backend/problems/services/quiz_service.py`:
  - `get_next_problem` の戻り値を `NextProblem`（`typing.NamedTuple`: `problem`・`is_review_mode`・`total_problems_in_subject`・`is_weak_fallback`）にする。通常・復習の回は `is_weak_fallback=False`
  - `mode == MODE_WEAK` のとき、未回答の問題（`exclude(id__in=回答済み)`）と、全部答えた後の既出の問題（`filter(id__in=回答済み).exclude(id__in=最近の 5 問)`、それも無ければ `filter(id__in=回答済み)`）の両方で、`order_by('?')` の代わりに `order_weak_first(..., session.user, session.subject)` の並びの先頭を取る。`is_weak_fallback` は `order_weak_first` の 2 つ目の戻り値
  - `start_session` は変えない（`weak` の `total_problems` は通常と同じく科目の問題数・既存の `else` の枝）
- `backend/problems/views.py` の `next_problem`: `NextProblem` を受け、応答に `is_weak_fallback`（bool）を足す（通常・復習でも `false` を返す）。`review_complete`・404 の応答は変えない
- 開始の API（`POST /api/quiz/`）は、`QuizSessionSerializer` の `mode`（モデルの選択肢から作られる `ChoiceField`）が `weak` を受けるようになるだけ。知らない値は今と同じ 400（DRF の選択肢の検証）
- 権限: `QuizSessionViewSet` は `permission_classes = [permissions.IsAuthenticated]` のまま。回は `QuizSession.objects.for_user(user)`、問題は `QuizService.available_problems`（自組織・未削除）、答えは `QuizAnswer.objects.for_user(user)` で読む

### 4.3 ダッシュボードの overview
**修正方針**: 応答に 2 つのキーを足す（どちらも全科目から。科目の選択に関係しない・`weak_subjects` と同じ扱い）。
- `GET /api/dashboard/overview/`（`permission_classes = [permissions.IsAuthenticated]`・変更なし）の応答 200 に追加:
  - `weak_difficulties`: `[{ "difficulty": "easy"|"medium"|"hard", "answered_count": int, "accuracy_rate": float }]`（0〜3 件・正答率の低い順）
  - `rushed_mistakes`: `{ "mistake_count": int, "rushed_count": int, "rushed_rate": float }` か `null`
- エラー応答は今のまま（未認証 401・不正な `subject_id` は 400 `{"error": {"main_message": "科目の指定が正しくありません", ...}}`）
- `backend/dashboard/selectors.py` の `build_overview`: `weak_difficulties(answers)`・`rushed_mistakes(answers, now)` を足す（`answers` は今の `_answers(user)`・全科目）
- `backend/dashboard/serializers.py`: `WeakDifficultySerializer`（`extend_schema_serializer(component_name='DashboardWeakDifficulty')`・`difficulty = ChoiceField(choices=[('easy','初級'),('medium','中級'),('hard','上級')])`）、`RushedMistakesSerializer`（`component_name='DashboardRushedMistakes'`）、`OverviewSerializer` に `weak_difficulties = WeakDifficultySerializer(many=True)`・`rushed_mistakes = RushedMistakesSerializer(allow_null=True)`
- `backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts` を手順どおり作り直す。`frontend/src/types/api/index.ts` に `DashboardWeakDifficulty` の短い名前を足す
- `frontend/src/services/dashboard.service.ts` の `isDashboardOverview`: `weak_difficulties` の各要素（難易度が 3 つのどれか・数）と、`rushed_mistakes` が `null` か数 3 つの形かを確かめる（形が違えば今と同じくエラーの表示）

### 4.4 画面
**修正方針**: 新しい画面は作らず、ダッシュボードの 3 枚のカードとクイズの画面を変える。
- `frontend/src/utils/difficulty.ts`（新規）: `DIFFICULTY_LABELS = { easy: '初級', medium: '中級', hard: '上級' }` と `difficultyLabel(value: string): string`（知らない値はそのまま）。`QuizSession.tsx` の `getDifficultyLabel` をこれに置き換える
- `WeakSubjectsCard.tsx`（見出し「間違いやすい分野（全科目）」はそのまま）。上から:
  1. 今の科目別の一覧と空の文（変えない）
  2. `weak_difficulties` が 1 件以上なら、小見出し「難易度別」（`Typography variant="subtitle2" component="h3"`）と、行ごとに 表示名（初級など）・正答率の `Chip`（`Math.round(rate * 100)%`・50% 未満は `error`、それ以外は `warning`・科目の行と同じ）・「解答数: ◯問」
  3. `rushed_mistakes` が `null` でなければ、`Alert severity="info" role="status"` で「急いで答えた問題の間違いが多めです（間違いの ◯%）。落ち着いて解きましょう」（◯ は `Math.round(rushed_rate * 100)`）
- `StartQuizCard.tsx`: 「クイズを始める」の下に、`Button variant="outlined" size="large" fullWidth` の「苦手を優先して始める」（`data-testid="start-weak-quiz-button"`・押せる条件は「クイズを始める」と同じ `canStart`）と、その下に `Typography variant="caption" color="text.secondary"` で「間違えた問題や正答率の低い難易度から出します」。押した後の流れは「クイズを始める」と同じ（対象が 1 件ならすぐ・2 件以上ならダイアログで科目を選ぶ）で、行き先が `/quiz?subject=<id>&mode=weak` になる。ダイアログは押したボタンのモードを覚える（`useState<'normal' | 'weak'>`）
- `RecommendationsCard.tsx`: `kind === 'weak_subject'` の「練習する」は `/quiz?subject=<id>&mode=weak`、`unstudied_subject` は今のまま `/quiz?subject=<id>`
- `QuizSession.tsx`:
  - `?mode=` の読み方を `review`・`weak`・それ以外（通常）の 3 つにする（`requestedMode`）。開始の要求の本文の `mode` に `review`・`weak` を入れる。開始を 1 回にする印（`startedKeyRef`）のキーにモードを入れる
  - 回が `weak` なら、復習の印の位置に `Chip label="苦手を優先" size="small" color="primary"` を出す
  - `next_problem` の応答の `is_weak_fallback` が `true` なら、問題の上に `Alert severity="info"` で「この科目はまだ解答が少ないため、いつもの順で出題しています」
  - 完了画面の「もう一度挑戦」は、終えた回と同じモードで始める（`createNewSession` にモードを引数で渡す）
- `frontend/src/types/quiz.ts`: `QuizMode = 'normal' | 'review' | 'weak'`、`Problem` に `is_weak_fallback?: boolean`

### 4.5 使われない分析を片付ける
**修正方針**: 画面から呼ばれず、材料も正しくない分析を、表を残して消す（AC6・AC7）。
- `backend/studylogs/views.py`: `MistakeAnalysisViewSet`・`AdaptiveLearningViewSet` と、それだけが使う import（`ProblemAttempt`・`MistakePattern`・`LearningSuggestion`・`LearningWeakness`・2 つのサービス・関係するシリアライザ）を消す
- `backend/studylogs/urls.py`: `mistake-analysis`・`adaptive-learning` の `router.register` を消す（その下の経路はすべて 404 になる）
- `backend/studylogs/serializers.py`: `MistakePatternSerializer`・`LearningSuggestionSerializer`・`LearningWeaknessSerializer`・`MistakeAnalysisSerializer`・`SuggestionFeedbackSerializer`・`ProficiencyAnalysisSerializer`・`PersonalizedRecommendationSerializer`・`AdaptiveProblemSelectionSerializer`・`SelectedProblemsSerializer` を消す（`ProblemAttemptSerializer` はどこからも使われていなければ一緒に消す）
- `backend/studylogs/mistake_analysis.py`・`backend/studylogs/adaptive_selection.py`: ファイルごと消す
- `backend/studylogs/tasks.py`: `analyze_mistake_patterns_task`・`cleanup_expired_suggestions_task`・`update_user_proficiency_task`・`generate_learning_insights_task` と、それだけが使う import を消す
- `backend/core/cache_service.py`: `get/set/invalidate_mistake_patterns_cache`・`get/set/invalidate_learning_suggestions_cache`・`_proficiency_key`・`get/set/invalidate_proficiency_cache` と、317-319 行・381-383 行の呼び出しを消す
- 残す: モデル（`ProblemAttempt`・`MistakePattern`・`LearningSuggestion`・`LearningWeakness`・`StudyLog`）・admin・マイグレーション。表の削除は別イシュー（Danger Ops）

### 4.6 定期処理（`backend/core/celery.py`）
**修正方針**: すべての間隔をコメントにある本番の値（`crontab`）にし、消したタスクの定期処理を外す。
| 名前 | タスク | 間隔 |
|---|---|---|
| `update-daily-analytics` | `studylogs.tasks.update_daily_analytics_task` | `crontab(hour=2, minute=0)` |
| `send-study-reminders` | `studylogs.tasks.send_study_reminders_task` | `crontab(hour=7, minute=0)` |
| `cache-maintenance` | `core.tasks.cache_maintenance_task` | `crontab(minute='*/30')` |
- `analyze-mistake-patterns`・`cleanup-expired-suggestions` は消す。時刻は `app.conf.timezone = 'Asia/Tokyo'`（今のまま）

### 4.7 既存のテストの合わせ込み
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py`: `MA`・`AL` の定数と表の行、それだけが使う準備（`ProblemAttempt`・`MistakePattern`・`suggestion`・`weakness` の作成）を消す。`"POST api/quiz/"` の行（194 行・`_subj_body(...)`）に、本文に `mode: "weak"` を足した同じ形の行を 1 つ足す（他組織の科目を指定したときの扱いが通常と同じであることを確かめる）
- `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`: 消した機能を確かめる 6 つのテスト（271・279・291・310・436・577 行）を消す。代わりの境界のテストは TC-16・TC-17
- `backend/studylogs/tests/test_I452_quiz_review.py`: 消したモジュール・経路を使うテストと import を消す（復習の記録のテストは残す）
- `backend/dashboard/tests/test_I473_overview.py`: TC-01 の最上位のキーの集合に `weak_difficulties`・`rushed_mistakes` を足す（スキーマの一致は作り直した `backend/openapi.yaml` で `core/tests/test_I493_openapi_contract.py` が確かめる）
- `get_next_problem` の呼び出し元は `backend/problems/views.py:884` だけ（grep・2026-11-17。テストは API 経由）なので、テストの合わせ込みは無い

## 5. 実装手順（ステップ）
各ステップは backend → API → 画面を縦に通す。
1. **苦手の判定とダッシュボード**（4.1 のうち `is_weak`・`weak_difficulties`・`rushed_mistakes`、4.3、4.4 の `difficulty.ts`・`WeakSubjectsCard.tsx`）→ TC-01〜TC-06・TC-16・TC-20・TC-21 参照。API の形を変えるので、スキーマと型の作り直しもこのステップで行う
2. **苦手を優先の出題**（4.1 の `order_weak_first`、4.2、4.4 の `StartQuizCard.tsx`・`RecommendationsCard.tsx`・`QuizSession.tsx`・`quiz.ts`）→ TC-10〜TC-15・TC-17・TC-22〜TC-26 参照。ステップ 1 の `weakness.py` が前提
3. **片付け**（4.5・4.6・4.7）→ TC-30〜TC-33 参照。ステップ 1・2 とは独立（並行可）だが、`test_I446` の合わせ込みはステップ 2 の後
4. 実装後にサービスの再起動が必要: backend（マイグレーションの適用 `python manage.py migrate`・消したモジュール）。celery の beat を動かしている環境では beat も再起動する

## 6. テスト計画
### 自動
- テストのレベル: 判定の計算（境界値）と出題の順・クエリ数・組織の境界は pytest（結合: DB を使う）。API の形は pytest（APIClient）。画面の出し分けと遷移は Jest（React Testing Library）。ダッシュボードから苦手を優先のクイズを始める流れは E2E（Playwright）1 本
- 認可・組織の境界: 他組織の答え・問題が、難易度別の苦手・急いだ間違い・苦手を優先の並びに入らないこと（TC-16・TC-17）。未認証は 401（TC-07）
- 再発防止: 定期処理の間隔が開発用に戻る・消したタスクを参照する（TC-32）、候補の問題ごとの問い合わせ（TC-15）、回数の足し込み（保存をやめることで構造的に無くなる。TC-31a）
- 詳細は `docs/tests/open/I466_auto_test.md`
### 手動
- Playwright MCP で、ダッシュボードのカードの表示・苦手を優先の開始・案内の 1 行・スマホ幅・コンソールを確かめる（実施者はすべて Claude）。`docs/tests/open/I466_manual_test.md`

## 7. ロールバック
- PR を revert する。マイグレーション `0023` は選択肢の変更だけなので、`python manage.py migrate problems 0022` で戻せる（データの変更なし）。戻した後に残る `mode='weak'` の回は、コードが知らない値として通常の回と同じに扱われる（`get_next_problem` は `review` 以外を通常の順で出す）
- 消したファイル・経路は revert で戻る。表は消していないので、データは失われない

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 苦手を優先の並びに、他組織の問題・答えが混ざる | 問題は `available_problems`、答えは `QuizAnswer.objects.for_user` だけから読む。TC-17 で他組織の答え（不具合で残った想定を含む）が段を変えないこと・他組織の問題が出ないことを固定 | 回避 |
| R2: 候補の問題ごとに問い合わせが増える（F4 の再発） | Subquery の注釈で 1 本にまとめる。TC-15 で候補 3 問と 40 問のクエリ数が等しいことを固定 | 回避 |
| R3: 経路を消したことで、見えていない呼び出し元が壊れる | 画面・e2e・backend を grep して呼び出し元が無いことを確かめた（調査結果 7）。TC-30 で 404 を固定 | 回避 |
| R4: `get_next_problem` の戻り値の形の変更で既存の呼び出しが壊れる | 呼び出し元は `views.py` の `next_problem` だけ（grep）。そこを直し、CI の全テスト（API 経由のクイズのテスト）で確かめる | 回避 |
| R5: 解答時間 0 の古い答えで「急いだ」が誤判定される | 平均と急いだ間違いの数の両方で `time_taken > 0` の答えだけを使い、平均は 300 秒で頭打ちにする。TC-05 で固定 | 回避 |
| R6: 定期処理の時刻を変えたことで、開発中にリマインダー・日次の分析の動きを確かめにくくなる | 手で動かすときは `celery call` かタスクの直接呼び出しで足りる。開発の便のために本番の値を変えない | 受け入れ |
| R7: #470・#471 と同じファイル（`quiz_service.py`・`views.py`・`QuizSession.tsx`）に触れて衝突する | 先にマージされた側に合わせて解消する。どちらもまだ着手していない（2026-11-17） | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 新しい画面は作らず、ダッシュボードの「間違いやすい分野」のカードに難易度別の苦手と急いだ間違いを足す。結果は保存せず読むたびに計算する
- クイズに 3 つ目のモード `weak`（苦手を優先）を足す。入り口は「学習を開始」の副ボタン「苦手を優先して始める」と説明「間違えた問題や正答率の低い難易度から出します」、おすすめの「間違いやすい分野」の「練習する」。細かい設定は画面に出さない。出題は 1 問ずつ・終わりは利用者が決める
- 優先の順: 最後に間違えた問題 → 苦手な難易度 → 未回答・しばらく答えていない。同じ回で続けて同じ問題を出さない。科目の解答が 5 問未満なら通常の順と案内「この科目はまだ解答が少ないため、いつもの順で出題しています」
- 苦手の基準はダッシュボードと同じ 5 問以上・正答率 70% 未満で、定数を共有する
- 急いだ間違い: 直近 30 日に 20 問以上・平均の解答時間の半分未満で答えた間違いが間違いの 25% 以上で 1 行（文言はイシューのとおり）
- 材料は `QuizAnswer`。`ProblemAttempt` は読まない。表は消さない（Danger Ops 無し）
- `StudyLog` に頼る提案は外す。使われない 2 つの API の経路は消す
- 定期処理はすべて本番の値に。間違いパターンの分析・期限切れの提案の掃除は止める

Claude が決めた（技術的な選択と理由）:
- 置き場所: 苦手の判定は `backend/problems/services/weakness.py` に 1 つ（材料のモデルが `problems` にあり、`dashboard` → `problems` の向きだけで循環しない）。ダッシュボードの定数はここから import する
- 難易度別の苦手は全科目・全期間で数える（`weak_subjects` と同じ範囲。カードの見出しが「全科目」のため）。苦手を優先の出題の「苦手な難易度」も同じ全科目の判定を使う（ダッシュボードで見た苦手と出題の優先を食い違わせない）
- 解答数 5 問未満の判定は、回の科目（科目なしの回は全科目）の本人の解答数で行う
- 苦手を優先の段の中の順は「最後に答えた時刻の古い順（未回答が先）→ id」。決まった順にしてテストで固定でき、答えるたびに後ろへ回るので同じ問題に偏らない
- 全部答えた後の 2 周目以降も、`weak` の回は同じ並べ方（最近の 5 問を除く）にする。答えるたびに最後の答えが変わるので、まだ間違えている問題が先に戻る
- 急いだ間違いの平均と数は `time_taken > 0` の答えだけ・平均は 300 秒で頭打ち（解答時間を記録していない古い答えと、放置した答えで判定がゆがまないように。ダッシュボードの学習時間の上限と同じ値）
- `get_next_problem` の戻り値は `NamedTuple`（`NextProblem`）にする（4 つ目の値を足すため。位置で受ける書き方を名前で読めるようにする）
- `next_problem` の応答の `is_weak_fallback` は全モードで返す（画面が有無で分岐しなくて済む）。`next_problem` は契約（`CONTRACT_PATHS`）の外なので、スキーマの作り直しは overview の分だけ
- 開始の要求のモードの検証は、モデルの選択肢から作られる DRF の `ChoiceField` に任せる（知らない値は 400）
- 消すキャッシュの関数・タスクは、呼び出し元が消す機能だけのもの（grep で確認）。`update_user_proficiency_task`・`generate_learning_insights_task` はどこからも呼ばれていない
- 定期処理のテストは「全部が `crontab`」「登録したタスクが import できる」の 2 点だけにし、時刻の値そのものはテストに写さない（plan-writing-rules.md「決定論テストの対象の選び方」。開発の値に戻す・消したタスクを残す、の 2 つが気づきにくく被害が大きい）
- 材料・書き込みの不在（AC6）は、消したモジュールの再導入が意図的な変更でしか起きないので CI のテストにせず、実装のときの 1 回の確かめ（TC-31a〜c・失敗の注入つき）とコードレビューで見る
- E2E は「ダッシュボードの『苦手を優先して始める』→ クイズの画面に『苦手を優先』の印」の 1 本だけ（遷移とモードの受け渡しは結合でしか見えない。順の正しさは pytest が受け持つ）

一覧（`docs/reviews/backlog/`）:
- 一覧 I224.md F9・I223.md B1〜B4（`FILE=-`）: 残す — ハーネスの話で、このイシューの変更点と関係しない
- 実装対象のファイルに当たる行は無し

セキュリティ・ベストプラクティス:
- 入力: 新しい入力は `POST /api/quiz/` の `mode` の値 `weak` だけで、DRF の選択肢の検証で受ける。`?mode=` は画面の中で 3 つの値に読み替えるだけ（それ以外は通常）
- 認証・認可: 変更なし（`IsAuthenticated`）。読み出しは本人・自組織だけ（`for_user`・`available_problems`）。最小権限は保たれる
- 機密データ: 新しく出すのは本人の正答率・件数・割合だけ。他人・他組織の値は出さない
- OWASP: SQL は ORM だけ（Raw SQL 無し）。画面は文字を React で描く（`dangerouslySetInnerHTML` を使わない）ので XSS の経路は増えない。CSRF は今の API の扱いのまま
- 依存: 追加・更新なし
- スキャンの基準: bandit は MEDIUM 以上を直す（LOW は `# nosec` と理由）。npm audit は high/critical を直す。`order_by('?')` は暗号ではないので bandit の対象外
- 消す API に認可の穴の修正は含まれない（消すだけ）

P3/P5/P8: データ整合性は 10 章、運用は 11 章。コスト（12）は対象外（新しいインフラ・外部サービス無し。定期処理は減る）
P6: 13 章。P9: 15 章（本人の学習データの集計だけ。新しい保存・外部送信なし）

Danger Ops（有無/手順/ロールバック）:
- 無。表は消さない。マイグレーションは選択肢の変更（`AlterField`）だけでデータは変わらない

## 10. データ整合性設計
- DB の変更は `QuizSession.mode` の `choices` の追加だけ（`CharField(max_length=10)`・`default='normal'`・null 不可は今のまま。`'weak'` は 4 文字で収まる）。DB の制約は変わらない
- 書き込みは今と同じ（回の作成・回答）。新しい計算は読み取りだけで、トランザクション・冪等性・同時更新の扱いは変わらない
- 開始の冪等性: 同じ `Idempotency-Key` で別のモードを送ると今と同じ 422（`start_session` がモードを比べている）
- マイグレーションは後方互換（古いコードは `weak` を知らないだけ）。戻せる（7 章）

## 11. 運用設計
- 定期処理: 3 つを毎日 2 時・毎日 7 時・30 分ごと（日本時間）にし、2 つを止める。タスクの中身・ログ・リトライ（`max_retries=3`）は変えない
- 止めた 2 つのタスク名が beat の保存済みの予定に残っていても、beat は設定（`beat_schedule`）から予定を作るので、再起動で消える（`django_celery_beat` は使っていない・`backend/core/celery.py` が正）
- Feature Flag・段階リリースは不要（画面の追加は副ボタンと表示の追加で、既存の流れを変えない）

## 13. 性能・UX設計
- 性能: overview に足すクエリは常に 3 本（難易度別 1・急いだ間違い 2。当てはまらなくても 2 本目を流し、I473 の「クエリ数がデータの量で変わらない」を保つ。`test_I473_overview.py` の TC-12 の本数を 8 → 11 にする）。`next_problem` の `weak` は 3 本前後（件数・難易度別・本体）で、候補の数で増えない（TC-15）。キャッシュは使わない（読むたびに正しい値。件数は本人の答えだけ）
- 読み込み中・エラー: ダッシュボードは今の overview の読み込み中（スケルトン）・失敗（再読み込み）の表示に乗る。クイズは今の読み込み中・失敗の扱いのまま
- 空の状態: 難易度別の苦手・急いだ間違いは、当てはまらなければ何も出さない（科目別の一覧の空の文はそのまま残り、次にすることの導線〔問題を解く〕もそのまま）
- 破壊的な操作: 無し
- アクセシビリティ: 副ボタンは MUI の `Button`（キーボードで押せる・`size="large"` で 44px 以上）。急いだ間違いの 1 行は `role="status"`。正答率は色（Chip の色）に加えて数字で出す。小見出しは `h3`（カードの見出し `h2` の下）。スマホ幅（360px）ではみ出さない（手動 No.5）

## 14. 学習効果設計
- 優先の順の根拠: 間違えた問題を先に解き直す（想起練習・誤りの訂正のフィードバック）→ 正答率の低い難易度（つまずいている水準の練習）→ しばらく解いていない問題（間隔を空けた練習）。今日の復習（間隔反復・I452）とは別に、利用者が自分で選ぶ練習として置く
- つまずき検知: 難易度別の苦手と急いだ間違いは、科目別の苦手では見えない傾向（難しい問題だけで落ちる・急いで落とす）を見せる
- 学習効果の指標（KPI）の定義は、イシューのとおり対象外

## 15. プライバシー・コンプライアンス設計
- 扱うのは本人の答えの集計だけで、新しく保存するもの・外部に送るものは無い。消す機能は保存型の分析で、保存済みの行（表）は残る（削除・保持期間の扱いは表の削除のイシューで決める）
- テナントの分離: 読み出しはすべて本人・自組織に絞る（R1・TC-16・TC-17）。高リスク判定（未成年データ・越境）の条件に当たる変更は無い

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 苦手を優先の並び・難易度別の苦手・急いだ間違いに、他組織の答え・問題が入らない（TC-16・TC-17 が、他組織の答えを入れたときに段・件数が変わらないことを確かめているか） |
| V2 | 2 | 読んで可 | TC-15 のクエリ数のテストが、候補ごとに問い合わせる形に戻すと落ちる（false-green の確かめの記録） |
| V3 | 3 | 読んで可 | 消した経路の下（`analyze/`・`select_problems/` など）がすべて 404 になり、呼び出し元が画面・e2e・backend に残っていない（TC-30・調査結果 7） |

## 計画変更記録
- 2026-11-17 implement（細部・方式は変えない）:
  - 計画書の記載: 4.4「`StartQuizCard.tsx`: …「苦手を優先して始める」…」／採った方法: ボタンに `TrackChanges` のアイコンを付け、`minHeight: 44` を足した／理由: 主ボタンと見た目をそろえる・360px 幅で実測 42px で ux-rules.md 6 の 44px に届かなかった
  - 計画書の記載: 4.4「行き先が `/quiz?subject=<id>&mode=weak` になる」（`StartQuizCard`・`RecommendationsCard` に別々に書く想定）／採った方法: 道筋を作る関数 `quizPath` と型 `QuizStartMode` を `frontend/src/constants/routes.ts` に置き、2 枚のカードから使う／理由: 画面どうしが互いの部品を読み込まずに同じ値を指す、既存の routes.ts の役割どおり
  - 計画書の記載: 4.3「`WeakDifficultySerializer` … `difficulty = ChoiceField(choices=[('easy','初級'),…])`」／採った方法: `choices=LABELS`（`backend/problems/difficulty.py`）／理由: 対応表を `difficulty.py` の 1 か所に保つ（計画レビュー Warning 1 の方針）
  - テストの補助: `backend/problems/tests/i466_data.py`（組織・問題・答えの作り方）を足し、problems と dashboard の I466 のテストで共有した。既存の `frontend/src/utils/__tests__/dashboardAchievements.test.ts` の準備と `backend/core/tests/test_I493_openapi_contract.py` のキーの集合に 2 つのキーを足した（型・契約のテストが新しいキーを要るため）
  - 手動テストの準備: 確かめ用の利用者に上級の問題と答えを shell のループで足す手順は、見張り（`pretooluse_guard.py`）が「ループでの一括作成」として承認を求めた。承認を求めず、毎回作り直される確かめ用データ（`seed_dashboard_verify`・初級だけ・正答率 60% 前後）のまま、期待値を DB から別の計算で出して見比べる形にした。上級・急いだ間違いが出る形は単体テスト（TC-02・TC-04・TC-20・TC-21）が受け持つ
  - /simplify: 割合・解答数の集計式・答えの読み方を `weakness.py` の `rate`・`answer_counts`・`user_answers` にまとめ、`dashboard/selectors.py` はそれを使う（`_rate`・`_answer_counts`・`STUDY_SECONDS_CAP_PER_ANSWER` を消す）。`backend/core/settings.py` の使われない `CACHE_TIMEOUTS` の 2 キーを消す。画面は難易度の表を `utils/difficulty.ts` の 1 つにし（`isDifficulty` も）、% の表示は既存の `components/statistics/format.ts` の `formatRate` を使う
  - 計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない）
- 2026-11-17 implement: 急いだ間違いの 2 本目のクエリを条件付きにすると、I473 の TC-12（overview のクエリ数がデータの量で変わらない）が落ちた。常に 2 本流す形にし、TC-12 の本数を 8 → 11 にした（4.1・13 章）。方式・範囲・受け入れ条件は変えないので計画レビューのやり直しは不要
- 2026-11-17 計画レビュー（20261117_1432）の Warning 3 件への対応: 難易度の対応は既存の `backend/problems/difficulty.py` を使うと明記（4.1）・4.7 に `test_I473_overview.py` のキーの集合の更新を足す・TC-31 を 3 本に分ける。方式・範囲・受け入れ条件は変えないので計画レビューのやり直しは不要

## レビュー結果
- [20261117_1432 判定: ✅ 完了](../../reviews/closed/I466_plan_review_20261117_1432.md)
