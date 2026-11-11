# I431 計画書: 学習記録 API・ダッシュボード API の他組織データ漏れを塞ぐ

## 基本情報
- **計画書ID**: plan_I431
- **関連イシュー**: #431（旧 #331・I196）
- **Draft PR**: #453
- **作成根拠資料**: docs/issues/open/I431.md（GitHub #431 の本文の写し・2026-11-11）
- **実装後評価**: docs/reviews/open/I431_review.md
- **作成日**: 2026-11-11

## 1. 背景/目的
- I166 でクイズの経路の組織の境界を塞いだが、学習記録の API（`/api/study/` の下）とダッシュボードの API（`/api/dashboard/` の下）は対象外だった。I166 の敵対的レビューで、間隔反復のカード作成から他組織の問題文・解説・選択肢が取れることを実測した。
- 目的: この 2 つの API で、ユーザーの組織の科目・問題だけを扱うようにする。他組織の問題文・解説・選択肢・科目名・科目 ID が、応答にも新しく作る記録にも入らない状態にし、直した経路ごとに回帰テストで固定する。
- grill-me の確定（2026-11-11・イシューの設計確認メモ）: 何も消さず、止めもしない。壊れている箇所（difficulty の型・Problem に無い `is_active`）は直さない（I452）。既に作られた他組織の記録は読み出しから外す（データは消さない）。

## 調査結果

### 原因の概要
学習記録とダッシュボードのコードが、科目・問題を「ユーザーの組織のもの」に絞らずに読み書きしている。I166 で作った境界の判定（`QuizService.available_subjects` / `available_problems`）はクイズの中にしか無く、ほかの経路はそれを通っていない。

### 詳細な原因分析
1. 書き込み（他組織の科目・問題を指す記録を作れる）
   - `backend/studylogs/views.py:446` `SpacedRepetitionViewSet.create_card`: `Problem.objects.get(id=problem_id, is_deleted=False)` で組織を見ない。応答の `SpacedRepetitionCardSerializer` は `ProblemSerializer` を入れ子で返す（問題文・解説・選択肢）。
   - `backend/studylogs/serializers.py:27-30` `StudyLogCreateSerializer.subject` と `:10-24` `StudyLogSerializer.subject`: ModelSerializer が作る `PrimaryKeyRelatedField` の queryset は `Subject.objects.all()`。作成（POST）でも更新（PUT/PATCH・`StudyLogViewSet` は ModelViewSet）でも他組織の科目を指定でき、応答の `subject_name` に他組織の科目名が出る。
   - `backend/studylogs/services.py:62-66` `get_new_cards`: 全組織の問題が候補（今は `is_active` の欄が無いため FieldError で止まっている）。`daily_plan` がこの候補でカードを作る。
   - `backend/studylogs/mistake_analysis.py:50-61`（間違いの記録の土台）・`:241`（`Subject.objects.all()`）: ユーザーの記録が他組織の問題を指していると、その科目名入りの MistakePattern・LearningWeakness・LearningSuggestion を作る。
2. 読み出し（他組織の科目・問題の中身や ID を返す）
   - カード一覧 `SpacedRepetitionCardViewSet.get_queryset`（views.py:537-561）・復習対象 `SpacedRepetitionService.get_due_cards`（services.py:34-53）・復習の記録 `SpacedRepetitionReviewViewSet`（views.py:569-589・`problem_question`）・復習の提出 `submit_review`（views.py:389-392・応答に `updated_card`）
   - 学習記録の一覧・詳細 `StudyLogViewSet.get_queryset`（views.py:34-35・`subject_name`）・統計 `overview` の `recent_activity`（views.py:151-152）・`_get_subject_statistics`（views.py:249・登録時の科目 `UserSubjectAccess` を組織で絞らない）・`daily_summary` の `subjects_studied`（serializers.py:38・科目名）
   - 間違い分析の `patterns`・`suggestions`・`weaknesses`（views.py:614-733・`subject_name`）と `MistakeAnalysisService.get_analysis_summary`（mistake_analysis.py:467-481）
   - 適応的学習の `_get_problem_pool`（adaptive_selection.py:293-316・全組織の問題）・`_calculate_subject_proficiency`（同 170・`Subject.objects.all()`。応答の `subject_proficiency` のキーが科目 ID）
   - 非同期処理 `update_user_proficiency_task`（tasks.py:202・`Subject.objects.get(id=subject_id)`）
   - ダッシュボード: `DashboardOverviewView` の `recent_quizzes`（dashboard/views.py:36-54・`quiz.subject.name`）・`active_session`（同 30-33・87）・`_get_subject_progress`（同 134・`UserSubjectAccess`）、`DashboardAnalyticsView` の `subject_distribution`（同 212-218・`subject__name`）、`SubjectRecommendationView` の `subject_performance`（同 273-280・`subject__id`/`subject__name`）と問題数（同 291-294・313-316・`Problem.objects` を組織で絞らない）
3. なぜ起きたか: 学習記録の機能はユーザー単位（`user=request.user`）で絞れば十分と考えて作られ、その記録が指す科目・問題の組織までは見ていなかった。境界の判定が 1 か所に無く、各所が `Problem.objects` / `Subject.objects` を直接使っている。

### 「同じ型の取得の候補」の全件調査（受け入れ条件 3）
`backend/studylogs/` と `backend/dashboard/` の `Problem.objects`・`Subject.objects`・科目/問題を指すモデル（StudyLog・DailyStudySummary・ProblemAttempt・SpacedRepetitionCard・SpacedRepetitionReview・MistakePattern・LearningSuggestion・LearningWeakness・QuizSession・UserSubjectAccess）の読み書きを、`grep -n "objects\." ` と各ファイルの通読で全件調べた。扱いの基準（下の「扱いの基準」）に当てはめた結果:

| 箇所 | 越境の中身 | 扱い |
|---|---|---|
| views.py:446 `create_card` | 他組織の問題でカードを作り、問題文・解説・選択肢を返す | 塞ぐ（C1） |
| serializers.py:10-30 `StudyLogSerializer`・`StudyLogCreateSerializer` の `subject` | 他組織の科目で記録を作る・変える。`subject_name` | 塞ぐ（C2） |
| views.py:34-35 `StudyLogViewSet.get_queryset` | 他組織の科目を指す記録の一覧・詳細・更新・終了 | 塞ぐ（R1） |
| views.py:151 `overview` の `recent_logs` | `recent_activity` の `subject_name` | 塞ぐ（R2） |
| views.py:249 `_get_subject_statistics` | `by_subject`・`best_subject`・`weakest_subject` の科目名 | 塞ぐ（R3） |
| views.py:190-196 `daily_summary` | `subjects_studied` の科目名 | 塞ぐ（R4） |
| services.py:42-49 `get_due_cards` | 復習対象のカード（問題の中身） | 塞ぐ（R5） |
| services.py:62-66 `get_new_cards` | 新しく学ぶ問題の候補（全組織） | 塞ぐ（C3） |
| views.py:389-392 `submit_review` | 他組織の問題のカードの復習・応答の `updated_card` | 塞ぐ（R6） |
| views.py:537-561 `SpacedRepetitionCardViewSet` | カードの一覧・詳細 | 塞ぐ（R7） |
| views.py:569-589 `SpacedRepetitionReviewViewSet` | `problem_question` | 塞ぐ（R8） |
| views.py:614-633 `patterns`・mistake_analysis.py:467-470 | `subject_name`・`description`（科目名入り） | 塞ぐ（R9） |
| views.py:639-661 `suggestions`・mistake_analysis.py:477-481 | `subject_name`・`title`/`description`（科目名入り） | 塞ぐ（R10） |
| views.py:717-733 `weaknesses`・mistake_analysis.py:472-475 | `subject_name`・`concept_name`（科目名入り） | 塞ぐ（R11） |
| mistake_analysis.py:50-61 `update_mistake_patterns` の土台 | 他組織の科目名入りの MistakePattern を作る | 塞ぐ（C4） |
| mistake_analysis.py:241 `update_learning_weaknesses` | 他組織の科目名入りの LearningWeakness を作る | 塞ぐ（C5） |
| mistake_analysis.py:289-300 `generate_learning_suggestions` | 既にある他組織のパターン・弱点から提案を作る | 塞ぐ（C6） |
| adaptive_selection.py:170 `_calculate_subject_proficiency` | `subject_proficiency` のキー（他組織の科目 ID） | 塞ぐ（R12） |
| adaptive_selection.py:293-316 `_get_problem_pool` | 出題候補（全組織の問題） | 塞ぐ（R13） |
| tasks.py:202 `update_user_proficiency_task` | 他組織の科目で習熟度を計算 | 塞ぐ（R14） |
| dashboard/views.py:30-33 `active_session` | `subject` に他組織の科目名 | 塞ぐ（D1） |
| dashboard/views.py:36-38 `recent_quizzes` | `subject` に他組織の科目名（I166 前の古いセッション） | 塞ぐ（D2） |
| dashboard/views.py:134 `_get_subject_progress` | `subject_name` | 塞ぐ（D3） |
| dashboard/views.py:212-218 `subject_distribution` | `subject__name` | 塞ぐ（D4） |
| dashboard/views.py:273-280 `subject_performance` | `subject_id`・`subject_name` | 塞ぐ（D5） |
| dashboard/views.py:291-294・313-316 おすすめの問題数 | 他組織の科目の問題数（`is_active` の欄が無く今は FieldError） | 塞ぐ（D6） |
| views.py:842・862・886・945・1046 の `subject_service.get_subject_by_id` | 既に組織で絞っている（`core/subject_service.py:95-98`） | 変えない（既に安全）。TC で回帰を固定（TC-10） |
| dashboard/views.py:303 `get_user_subjects` | 既に組織で絞っている（`core/subject_service.py:63`） | 変えない（既に安全） |
| 数だけを返す集計: `overview` の合計・連続日数（views.py:111-136）・`StudyGoalViewSet.update_progress`（:313-333）・`user_statistics`/`update_daily_analytics`/`learning_insights`/`analytics`（services.py:186-393・views.py:463-529）・`improvement_trends`（views.py:765-796）・ダッシュボードの `today`・`weekly_summary`・`daily_data`・`performance_trends`・`study_streak` | 科目・問題の名前・本文・ID を返さない（件数・時間・正答率だけ） | 変えない（扱いの基準 3） |
| `mark_suggestion_read`・`provide_feedback`・`resolve_weakness`（views.py:663-762） | 自分の記録の既読・評価・解決の印を付けるだけ。応答は固定の文言 | 変えない（扱いの基準 3）。中身を返さない |
| tasks.py の `update_daily_analytics_task`・`send_study_reminders_task`・`analyze_mistake_patterns_task`・`bulk_update_spaced_repetition_task`・`export_user_data_task`・`cleanup_expired_suggestions_task` | サービス（上で塞ぐ）を呼ぶか、数だけを返す | 変えない（呼び先の R5・C4〜C6 で塞がる） |

**扱いの基準**（Claude が決めた。理由は 9 章）:
1. 他組織の科目・問題を指す記録を**作る・変える**入力は、存在しない ID と同じ応答で断る。
2. 他組織の科目・問題の**名前・本文・解説・選択肢・ID を返しうる読み出し**は、他組織の科目・問題を指す記録を土台の queryset から外す（既にある記録も含む）。科目が空（null）の記録は残す（他組織の中身を含まないため）。
3. **数だけを返す集計**（件数・時間・正答率・連続日数）と、中身を返さない印付けは変えない。漏れる中身が無く、変えると自組織の数字まで変わるおそれがあるため。

### 動いていない経路（`is_active` の欄が無い・difficulty の型）の扱い
- grill-me の確定: 直さない（I452）。境界は塞ぐ。
- ただし `get_new_cards`（C3）・`_get_problem_pool`（R13）・おすすめの問題数（D6）は、絞り込みの土台を境界の判定（`available_problems`）に置き換える。`available_problems` は「未削除」を `is_deleted=False` で含むため、存在しない `is_active=True` の条件はこの置き換えで消える。結果として、この 3 か所は FieldError で止まらなくなる（`daily_plan` の新しいカード・ダッシュボードのおすすめ API は動き始める）。境界の判定を通す以上避けられない副作用で、機能を直すための変更ではない（9 章の自律判断に記録）。
- 適応的な問題選択（`select_problems`・`proficiency_analysis` など）は、`_calculate_difficulty_proficiency`（adaptive_selection.py:131-135 の `problem__difficulty='easy'`）が先に例外を出すため、API はエラーのまま（受け入れ条件 2 の「エラーのままで他組織の問題も返らない」）。間違い分析の `analyze`・`refresh_analysis` も `_analyze_problem_type_errors`（mistake_analysis.py:144-153）で例外のまま。
- 復習の提出 `submit_review` は、自分の組織のカードでも `update_daily_analytics`（services.py:319-322）の difficulty で 400 になる（I452）。このイシューのテストは他組織のカードと存在しないカードの比較（どちらも 404）だけを見る。

### 既存データ（dev DB）の調査
- 計画の段階ではコンテナが動いていない（`docker ps` が空・2026-11-11）。test-gate の手動テスト No.1 で、primary の dev DB を読み取りだけで数える（件数を計画書と review に記録）。0 でなければ、件数と種類を記録する（読み出しから外れるので、データは消さない。消す必要が出たら Danger Ops として承認を取る）。

### 環境前提
- `docker`（`docker ps` が動く）・`gh`（Draft PR #453 を作成済み）は確認済み。テストは CI（`.github/workflows/ci.yml:84-85` の `pytest`）が正。手元では新しいテストファイルと I166 のテストファイルだけを流す（全テストは流さない）。
- テストの cache: `core/settings.py:220-232` は Redis（`IGNORE_EXCEPTIONS: True`）。Redis があると利用者 ID が同じ別テストの cache が残りうるため、新しいテストは各テストの前後で全 cache を消す fixture を持つ。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの受け入れ条件と同じ（docs/issues/open/I431.md）。この計画での合格の基準:
- [ ] AC1: 他組織の問題 ID で間隔反復のカードを作ると、存在しない問題 ID と同じ応答（404・`{"error": "問題が見つかりません"}`）で断られ、カードが作られず、問題文・解説・選択肢が返らない（TC-01）
- [ ] AC2: 適応的な問題選択（科目の指定あり・なし）で他組織の問題・科目が返らない。API はエラーのまま（difficulty の型の不具合は直さない）で、応答に他組織の問題文が含まれない。候補の取得（`_get_problem_pool`）と科目の取得（`_calculate_subject_proficiency`）を直接テストし、自組織の問題・科目だけが対象（TC-08〜TC-10）
- [ ] AC3: 「同じ型の取得の候補」すべての調査結果と扱いが、この計画書の「調査結果」の表に記録され、越境するものが塞がれている
- [ ] AC4: 直した経路ごとに、他組織の ID と存在しない ID で同じ応答になること（作る・変える入力）、または他組織の記録が読み出しに出ないこと（読み出し）を確かめる回帰テストがある（TC-01〜TC-22）
- [ ] AC5: 既に存在する他組織の問題のカードが、カードの一覧（`GET /api/study/sr-cards/`）と復習対象（`GET /api/study/spaced-repetition/due_cards/`）に出ず、問題文・解説が返らない（TC-03）
- [ ] AC6: 自組織のデータでは、従来どおり学習記録・ダッシュボードを使える（TC-02・TC-12・TC-15〜TC-19 の自組織の側・手動 No.2）
- [ ] AC7: 全テストが pass する（CI。既存テストの件数を減らさない。I166 のテストを含む）
- [ ] AC8: dev DB の既存データの調査結果が記録されている（手動 No.1）

## 3. 影響範囲
- Backend:
  - `backend/problems/services/tenant_scope.py`（新規・境界の判定）
  - `backend/problems/services/quiz_service.py`（`available_subjects` / `available_problems` を新しいモジュールへ委ねる）
  - `backend/studylogs/views.py`・`serializers.py`・`services.py`・`adaptive_selection.py`・`mistake_analysis.py`・`tasks.py`
  - `backend/dashboard/views.py`
  - `backend/studylogs/tests/__init__.py`・`backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`（新規）
- Frontend: なし（画面から呼ぶのは `dashboard/overview/`・`analytics/` だけで、応答の形は変えない。他組織の記録が一覧から消えるだけ）
- DB: なし（スキーマ変更なし・マイグレーションなし。dev DB は読み取りの調査だけ）
- Config/Infra: なし（依存の追加なし）

## 4. 変更点一覧

### 修正アプローチ
境界の判定を `problems/services/tenant_scope.py` の 3 つの関数に集め、学習記録・ダッシュボードの全経路（調査結果の表の「塞ぐ」）をそれに通す。作る・変える入力は境界の queryset から引くことで「存在しない」と同じ応答にし、読み出しは土台の queryset を境界で絞る。クイズの `QuizService` も同じ関数に委ねて、判定を 1 か所にする。

### 4-1. 境界の判定（新規 `backend/problems/services/tenant_scope.py`）
**修正方針**: I166 の判定（キャッシュを通さない・組織に属さないユーザーは空・全体共有科目〔`Subject.organization` が空〕は含めない・問題の組織は `subject__organization_id` で判定）をそのまま移し、記録の queryset を絞る関数を足す。

```python
"""組織の境界（ユーザーの組織の科目・問題）の判定。境界の判定のためキャッシュは使わない。"""
from typing import Optional

from django.db.models import Q, QuerySet

from problems.models import Problem, Subject


def available_subjects(user) -> QuerySet[Subject]:
    """ユーザーの組織の科目。組織に属さないユーザーは空。全体共有科目は含めない"""
    if user.organization_id is None:
        return Subject.objects.none()
    return Subject.objects.filter(organization_id=user.organization_id)


def available_problems(user, subject: Optional[Subject] = None) -> QuerySet[Problem]:
    """ユーザーの組織の未削除の問題（科目の指定があればその科目）。組織は subject 経由で判定"""
    if user.organization_id is None:
        return Problem.objects.none()
    problems = Problem.objects.filter(
        is_deleted=False, subject__organization_id=user.organization_id
    )
    if subject is not None:
        problems = problems.filter(subject=subject)
    return problems


def scope_to_user_org(
    queryset: QuerySet, user, *, subject_path: str, allow_null: bool = False
) -> QuerySet:
    """
    記録の queryset を、ユーザーの組織の科目を指すものに絞る。

    subject_path は記録から科目への経路（例: 'subject'・'problem__subject'）。
    allow_null=True のとき、科目が空の記録も残す（他組織の中身を含まないため）。
    組織に属さないユーザーは、allow_null なら科目が空の記録だけ、そうでなければ空。
    """
    null_cond = Q(**{f'{subject_path}__isnull': True})
    if user.organization_id is None:
        return queryset.filter(null_cond) if allow_null else queryset.none()
    cond = Q(**{f'{subject_path}__organization_id': user.organization_id})
    if allow_null:
        cond |= null_cond
    return queryset.filter(cond)
```

### 4-2. `backend/problems/services/quiz_service.py`
**修正方針**: 判定を 1 か所にするため、`QuizService.available_subjects` / `available_problems` の本体を `tenant_scope` の呼び出しに置き換える（名前と引数は変えない。呼び出し元〔`problems/serializers.py:314`・`problems/views.py:912`・同ファイル 88・114 行目〕は変えない）。
```python
from problems.services import tenant_scope
...
    @staticmethod
    def available_subjects(user) -> QuerySet[Subject]:
        """クイズで指定してよい科目（tenant_scope.available_subjects と同じ）"""
        return tenant_scope.available_subjects(user)

    @staticmethod
    def available_problems(user, subject: Optional[Subject]) -> QuerySet[Problem]:
        """クイズで出題・回答してよい問題（tenant_scope.available_problems と同じ）"""
        return tenant_scope.available_problems(user, subject)
```

### 4-3. `backend/studylogs/serializers.py`（C2）
**修正方針**: 学習記録の科目に、リクエストユーザーの組織の科目だけを受け付ける欄を使う（I166 の `QuizSubjectField` と同じ作り）。他組織と存在しない ID は DRF の同じ検証エラー（400・`does_not_exist`）になる。
```python
from problems.models import Subject
from problems.services.tenant_scope import available_subjects


class OrgSubjectField(serializers.PrimaryKeyRelatedField):
    """リクエストユーザーの組織の科目だけを受け付ける（context に request が無ければ何も受け付けない）"""

    def get_queryset(self):
        request = self.context.get('request')
        if request is None:
            return Subject.objects.none()
        return available_subjects(request.user)


class StudyLogSerializer(serializers.ModelSerializer):
    subject = OrgSubjectField(required=False, allow_null=True)
    ...（他は変えない）


class StudyLogCreateSerializer(serializers.ModelSerializer):
    subject = OrgSubjectField(required=False, allow_null=True)
    ...（他は変えない）
```
- `StudyStatisticsViewSet.overview` は `StudyLogSerializer(recent_logs, many=True)` を context なしで使う（views.py:152）。読み出しだけで `get_queryset` は呼ばれないため影響なし（`to_representation` は `pk` を返すだけ）。

### 4-4. `backend/studylogs/views.py`
- **C1 `create_card`（446 行目）**: `Problem.objects.get(id=problem_id, is_deleted=False)` → `available_problems(request.user).get(id=problem_id)`。他組織・削除済み・全体共有科目・存在しない ID は同じ `Problem.DoesNotExist` → 同じ 404 `{'error': '問題が見つかりません'}`。関数の中の `from problems.models import Problem` はそのまま（`Problem.DoesNotExist` に使う）。
- **R1 `StudyLogViewSet.get_queryset`（34-35 行目）**: `scope_to_user_org(StudyLog.objects.filter(user=self.request.user), self.request.user, subject_path='subject', allow_null=True)`。一覧・詳細・更新・削除・`end` で、他組織の科目の記録は存在しない ID と同じ 404。
- **R2 `overview`（151 行目）**: `recent_logs` を同じ `scope_to_user_org(..., subject_path='subject', allow_null=True)` で絞ってから並べる（合計・連続日数の `study_logs` は変えない・扱いの基準 3）。
- **R3 `_get_subject_statistics`（249 行目）**: `subjects = subject_service.get_user_selected_subjects(user, use_cache=True).filter(id__in=available_subjects(user))`。
- **R4 `daily_summary`（190-193 行目）**: `.prefetch_related(Prefetch('subjects_studied', queryset=available_subjects(user)))` を付ける（`DailyStudySummarySerializer.subjects_studied` の `StringRelatedField` は prefetch の結果を使う）。
- **R6 `submit_review`（389-392 行目）**: `SpacedRepetitionCard.objects.get(id=..., user=...)` → `scope_to_user_org(SpacedRepetitionCard.objects.filter(user=request.user), request.user, subject_path='problem__subject').get(id=data['card_id'])`。他組織の問題のカードは存在しないカードと同じ 404 `{'error': 'カードが見つかりません'}`・復習の記録を作らない。
- **R7 `SpacedRepetitionCardViewSet.get_queryset`（538-540 行目）**: 土台を `scope_to_user_org(SpacedRepetitionCard.objects.filter(user=...), user, subject_path='problem__subject')` にする（`select_related` と絞り込みのオプションはそのまま）。
- **R8 `SpacedRepetitionReviewViewSet.get_queryset`（570-572 行目）**: 土台を `scope_to_user_org(SpacedRepetitionReview.objects.filter(user=...), user, subject_path='problem__subject')` にする。
- **R9〜R11 `patterns`・`suggestions`・`weaknesses`（614-617・639-642・717-720 行目）**: それぞれの土台を `scope_to_user_org(..., subject_path='subject', allow_null=True)`（patterns・suggestions は科目が空の記録がある）／`allow_null=False`（weaknesses は `subject` が必須）で絞る。
- import: `from django.db.models import Prefetch, Sum`・`from problems.services.tenant_scope import available_problems, available_subjects, scope_to_user_org`。

### 4-5. `backend/studylogs/services.py`
- **R5 `get_due_cards`（42-49 行目）**: 土台を `scope_to_user_org(SpacedRepetitionCard.objects.filter(user=self.user, is_active=True, next_review_date__lte=...), self.user, subject_path='problem__subject')` にする（並びと件数の上限・キャッシュは変えない）。
- **C3 `get_new_cards`（62-66 行目）**: `Problem.objects.filter(is_active=True)` → `available_problems(self.user)`（`.exclude(...)`・`.select_related('subject')`・`.order_by('?')[:limit]` はそのまま）。

### 4-6. `backend/studylogs/adaptive_selection.py`
- **R12 `_calculate_subject_proficiency`（170 行目）**: `Subject.objects.all()` → `available_subjects(self.user)`。
- **R13 `_get_problem_pool`（293-316 行目）**: `filters = {'is_active': True}`・`Problem.objects.filter(**filters)` → `available_problems(self.user, subject)` を土台にする（`exclude(id__in=recent_problem_ids)`・`select_related('subject')` はそのまま）。

### 4-7. `backend/studylogs/mistake_analysis.py`
- **C4 `update_mistake_patterns`（50-61 行目）**: `sr_errors`・`attempt_errors` を作る部分を新しいメソッド `_error_records(start_date, end_date)` に切り出し、どちらも `scope_to_user_org(..., subject_path='problem__subject')` で絞って返す。`update_mistake_patterns` はそれを使う（以降の 4 つの分析は変えない）。テストで土台を直接確かめるための切り出し（TC-11）。
- **C5 `update_learning_weaknesses`（241 行目）**: `Subject.objects.all()` → `available_subjects(self.user)`。
- **C6 `generate_learning_suggestions`（289-300 行目）**: `active_patterns` を `scope_to_user_org(..., subject_path='subject', allow_null=True)`、`critical_weaknesses` を `scope_to_user_org(..., subject_path='subject')` で絞る。
- **R9〜R11 `get_analysis_summary`（467-481 行目）**: `patterns`（allow_null=True）・`weaknesses`（allow_null=False）・`suggestions`（allow_null=True）を同じく絞る。`_calculate_overall_improvement_rate`（529-532 行目）は数だけなので変えない。
- import: `from problems.services.tenant_scope import available_subjects, scope_to_user_org`。`from problems.models import Subject` は使わなくなるので消す（ruff の F401 を避ける）。

### 4-8. `backend/studylogs/tasks.py`
- **R14 `update_user_proficiency_task`（199-202 行目）**: `Subject.objects.get(id=subject_id)` → `available_subjects(user).get(id=subject_id)`。他組織の科目と存在しない科目は同じ `Subject.DoesNotExist` → 同じ `{'error': 'Subject matching query does not exist.'}`。関数の中の import を `from problems.services.tenant_scope import available_subjects` にする。

### 4-9. `backend/dashboard/views.py`
- **D1 `active_session`（30-33 行目）**: `scope_to_user_org(StudyLog.objects.filter(user=user, is_active=True), user, subject_path='subject', allow_null=True).first()`。
- **D2 `recent_quizzes`（36-38 行目）**: `scope_to_user_org(QuizSession.objects.filter(user=user), user, subject_path='subject', allow_null=True).order_by('-started_at')[:5]`。
- **D3 `_get_subject_progress`（134 行目）**: `get_user_selected_subjects(...).filter(id__in=available_subjects(user))`。
- **D4 `subject_distribution`（212-218 行目）**: 土台を `scope_to_user_org(StudyLog.objects.filter(user=user, started_at__date__gte=start_date), user, subject_path='subject', allow_null=True)` にする。
- **D5 `subject_performance`（273-280 行目）**: 土台を同じく `allow_null=True` で絞る。`studied_subject_ids`（298-301 行目）は除外の ID に使うだけなので変えない。
- **D6 おすすめの問題数（291-294・313-316 行目）**: `Problem.objects.filter(subject_id=..., is_active=True).count()` → `available_problems(user).filter(subject_id=subject['subject__id']).count()`、`Problem.objects.filter(subject=subject, is_active=True).count()` → `available_problems(user, subject).count()`。
- import: `from problems.models import QuizSession`（`Problem` は使わなくなる）・`from problems.services.tenant_scope import available_problems, available_subjects, scope_to_user_org`。

### 4-10. テスト（新規）
- `backend/studylogs/tests/__init__.py`（空）
- `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`（TC-01〜TC-22。中身は docs/tests/open/I431_auto_test.md）

## 5. 実装手順（TDD・垂直スライス）
1. テストファイル（TC-01〜TC-22）を書き、今のコードで流して、境界の不備を突く TC が RED になることを確かめる（RED の一覧を review の「テスト結果」に書く）。→ TC-23 参照
2. `tenant_scope.py` を作り、`quiz_service.py` を委ねる形にする（TC-21・TC-22 と I166 のテストが通る）。ステップ 1 の後。
3. 間隔反復（C1・C3・R5〜R8）を直す（TC-01〜TC-07 が GREEN）。ステップ 2 の後。
4. 学習記録・統計（C2・R1〜R4）を直す（TC-12〜TC-15 が GREEN）。ステップ 2 の後。3 と並行してよい。
5. 適応的学習・間違い分析・非同期処理（R9〜R14・C4〜C6）を直す（TC-08〜TC-11・TC-16・TC-20 が GREEN）。ステップ 2 の後。
6. ダッシュボード（D1〜D6）を直す（TC-17〜TC-19 が GREEN）。ステップ 2 の後。
7. 新しいテストファイルと I166 のテストファイルを流す → TC-23・TC-24 参照。pre-commit（ruff・bandit）→ TC-25 参照。
- 実装後のサービス再起動: 不要（ファイル削除・サービス停止なし。開発サーバーは自動で読み直す）。

## 6. テスト計画
### 自動（docs/tests/open/I431_auto_test.md）
- レベル: API の結合テスト（APIClient・pytest-django）を主にし、API が別の不具合（difficulty の型）で例外になる経路だけ、サービスのメソッドを直接呼ぶ単体テストにする（TC-08・TC-09・TC-11・TC-20）。
- 再発防止: 作る・変える入力は「他組織の ID と存在しない ID の応答を、ID を伏せて完全一致で比べる」（I166 と同じ）。読み出しは「他組織の記録を DB に直接作り、応答に出ないこと（ID・科目名・問題文）」と「自組織の記録は出ること」を両方見る（空を返すだけの実装で通らないように）。
- 乱数に頼らない: `get_new_cards` は `order_by('?')` だが、自組織の候補を 1 件・他組織を 2 件にして、件数の上限を十分大きくし、集合で比べる。
- 認可: 組織に属さないユーザー（TC-21）・全体共有科目（TC-01・TC-12・TC-22）・削除済みの問題（TC-01・TC-06）を含める。
- 全テスト: CI（PR #453）が正。手元では新しいファイルと I166 のファイルだけ（TC-23・TC-24）。

### 手動（docs/tests/open/I431_manual_test.md）
- No.1: primary の dev DB の越境データの件数（読み取りだけ・Claude）
- No.2: ダッシュボード・統計の画面が従来どおり表示される（Playwright MCP・Claude）

## 7. ロールバック
- PR #453 の revert（コードとテストだけ。マイグレーション・データ変更なし）。revert すると漏れが戻るため、revert は回帰が見つかったときに、原因の 1 か所だけを戻す形を優先する。

## 8. Risk & 回避策
- R-a 自組織の機能の無退行: 絞り込みを足すだけで、自組織の記録の扱いは変えない。自組織の側を各 TC で確かめる（AC6）。
- R-b 科目が空の記録の扱い: 学習記録・提案・パターンは科目が空のものがある。`allow_null=True` で残す（TC-13・TC-16・TC-21）。弱点（`LearningWeakness.subject` は必須）とカード・復習（`problem` は必須）は `allow_null=False`。
- R-c キャッシュ: `get_due_cards` の結果（利用者ごと・5 分）と習熟度（同 5 分）は、デプロイ直後の最大 5 分、絞る前の結果が返りうる。dev のみで本番は無いため受け入れる（他の対応はしない）。テストは毎回 cache を消す。
- R-d 副作用で動き始める経路（C3・R13・D6）: `daily_plan` が新しいカードを自組織の問題で作り始め、おすすめ API が 200 を返し始める。どちらも画面から呼ばれていない。境界の判定の中だけで動く（TC-06・TC-19）。
- R-e 組織を移ったユーザー: 古い組織の記録は読み出しから外れる（I166 と同じく、今の組織で判定）。データは消さない。
- R-f 見落とし: 調査結果の表で `studylogs`・`dashboard` の全 queryset を挙げた。横断の機械的な検査は #446。

## 13. 性能・UX設計
- 絞り込みは JOIN 1 つ（`subject__organization_id`・`problem__subject__organization_id`）を足すだけで、件数・ページングは変えない。`daily_summary` の prefetch はクエリを 1 本足すが、科目名の取得の N+1 を減らす。画面の変更は無い（P6 影響なし）。

## 14. 学習効果設計
- 影響なし（間隔反復・出題・難易度のアルゴリズムは変えない。対象を自組織に絞るだけ）。

## 15. プライバシー・コンプライアンス設計
- テナントのデータ（他組織の問題・解説・科目名）が別の組織の利用者に渡ることを止める（C4・C8・P9 のテナント分離）。個人情報の扱い（保持・削除）は変えない。既存の越境データは消さず、読み出しから外す（削除が必要になれば Danger Ops で承認を取る）。

## セキュリティ・ベストプラクティスチェック
- 入力の検証: 科目は `PrimaryKeyRelatedField` の queryset を境界に絞り、DRF の検証に任せる。問題・カードの ID は境界の queryset の `.get(id=...)` で引く（ORM のパラメータ化・SQL インジェクションなし）。
- 認証・認可: `permission_classes = [permissions.IsAuthenticated]` は変えない。組織の境界を全経路に足す（最小権限）。存在の有無を漏らさないため、他組織と存在しない ID は同じ応答（404 または 400）。
- 機密データ: 他組織の問題文・解説・選択肢・科目名・科目 ID を返さない。新しく機密を扱う処理は無い。
- OWASP: A01 Broken Access Control の是正。XSS・CSRF は変更なし（API のみ・JSON）。
- 依存: 追加なし（pip-audit・npm audit の対象変更なし）。
- スキャン: bandit は MEDIUM 以上を直す・LOW は `# nosec` で抑える。npm audit は対象外（frontend 変更なし）。
- フレームワーク: Django ORM と DRF の標準（queryset の絞り込み・`PrimaryKeyRelatedField.get_queryset`）。

## 高リスク判定
- Yes（テナントの越境の是正・認可の変更）。計画レビューの後に design-security-review 段階を通す。

## 各種チェック結果
- 要件適合性: 受け入れ条件の範囲内。副作用で動き始める経路（R-d）は境界の判定を通す結果で、仕様の追加ではない。
- マルチテナント: 閲覧・操作の範囲は「ユーザーの組織の科目・問題」。全体共有科目は含めない（I166 と同じ）。組織に属さないユーザーは、科目が空の記録だけ（または何も）扱える。
- P3/P5/P8: DB 変更なし・外部 API なし・新しい資源なし → 影響なし。非同期処理（tasks.py）は 1 か所の取得を絞るだけで、運用設計（ログ・リトライ）は変えない。
- P6: 影響なし（画面変更なし・性能は 13 章）。
- P9: 15 章。
- 設計品質: 判定を 1 か所（tenant_scope）に集める。Fat View を増やさない（ビューは関数を呼ぶだけ）。null（科目が空）の扱いを `allow_null` で統一。定数のハードコードなし。

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・本文）:
- 何も消さず、止めもしない。対象は `/api/study/` の下の全部と `dashboard` の全ビュー（grill-me 2026-11-11）
- difficulty の型の不具合・Problem に無い `is_active` は直さない（I452）。適応的な問題選択は候補の取得と科目の取得を直接テストする
- 既に作られた他組織の記録は読み出しから外し、データは消さない（2 回目の grill-me）
- 他組織の ID は存在しない ID と同じ応答で断る（404 か 400 かは API ごと）
- 境界の判定は I166 と同じ考え方（キャッシュを通さない・組織に属さないユーザーは空・全体共有科目は含めない・問題の組織は `subject__organization_id`）
- 横断の越境テストは #446。このイシューは直した経路ごとの回帰テスト

Claude が決めた（技術的な選択と理由）:
- 判定の置き場所は `backend/problems/services/tenant_scope.py`（関数 3 つ）。科目・問題は problems アプリのモデルで、I166 の判定もここにあるため。`core/subject_service.py` は科目のキャッシュを使う作りで、境界の判定（キャッシュを通さない）と混ぜない。`QuizService` は委ねる形にして呼び出し元を変えない（変更の範囲を小さくする）
- 扱いの基準（調査結果の 1〜3）。数だけの集計を変えないのは、漏れる中身が無く、変えると自組織の数字まで変わるおそれがあるため
- 応答: カード作成・復習の提出は既存の 404 の文言をそのまま使う（他組織も同じ文言になる）。学習記録の科目は DRF の検証エラー（400）。読み出しの詳細は 404（DRF の `get_object`）
- `get_new_cards`・`_get_problem_pool`・おすすめの問題数は、土台を `available_problems` に置き換えた結果 `is_active` の条件が消える（R-d）。grill-me の「`is_active` は直さない」とは、機能を直すための変更をしないという意味で、境界の判定を通すことで条件が消えるのは避けられない副作用と判断した。わざと壊れた条件を残す作りにはしない
- `mistake_analysis.py` に `_error_records` を切り出す（API が別の不具合で例外になるため、土台をテストで直接確かめる）
- キャッシュの最大 5 分の古い結果は受け入れる（R-c）
- テストは 1 ファイル（`backend/studylogs/tests/`）にまとめる（ダッシュボードの経路も同じ fixture を使うため）

一覧（docs/reviews/backlog/）:
- 一覧 I224.md F9: 残す — ハーネスの項目で、このイシューの変更点と関係しない（`FILE=-`）
- 一覧 I223.md B1〜B4: 残す — bot の停止に関する項目で、このイシューの変更点と関係しない（`FILE=-`）

Danger Ops（有無/手順/ロールバック）:
- 無（コードの修正とテストの追加だけ。dev DB は読み取りの調査だけ。既存データの削除が必要と分かったら、その時点で計画書に追加して承認を取る）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 組織 A の利用者が組織 B の問題 ID で `POST /api/study/spaced-repetition/create_card/` すると、存在しない ID と同じ 404・同じ本文で、カードが作られない（TC-01） |
| V2 | 1 | 実験必須 | 組織 A の利用者が組織 B の科目で学習記録を作る（POST）・変える（PATCH）と、存在しない科目と同じ 400 で、記録が作られない・変わらない（TC-12・TC-14） |
| V3 | 1 | 実験必須 | 既にある組織 B の問題のカード・復習の記録が、`sr-cards`（一覧・詳細）・`due_cards`・`sr-reviews`・`submit_review` から読めない（TC-03〜TC-05） |
| V4 | 3 | 読んで可 | 調査結果の表が `backend/studylogs/` と `backend/dashboard/` の、科目・問題を指す queryset と `Problem.objects`・`Subject.objects` を漏れなく挙げている（変更後のコードで grep して、絞っていない読み出しが「変えない」の行の理由に当たる） |
| V5 | 2 | 読んで可 | 読み出しのテストが、他組織が出ないことと自組織が出ることを両方見ていて、空を返すだけの実装で通らない（TC-03・TC-13・TC-15〜TC-19） |
| V6 | 1 | 実験必須 | 適応的な問題選択の候補（`_get_problem_pool`）と科目（`_calculate_subject_proficiency`）に他組織の問題・科目が入らない（TC-08・TC-09） |
| V7 | 3 | 読んで可 | 組織に属さない利用者・全体共有科目・削除済みの問題で、境界が開かない（TC-01・TC-21・TC-22） |
| V8 | 2 | 読んで可 | 新しいテストが今のコードで RED になる（TC-23 の RED の記録）。cache を消す fixture があり、テストの順番で結果が変わらない |
