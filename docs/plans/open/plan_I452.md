# 計画書: I452 クイズの回答から復習の予定を作り、ダッシュボードから今日の復習を始められるようにする

## 基本情報
- **計画書ID**: plan_I452
- **関連イシュー**: #452
- **Draft PR**: #464
- **作成根拠資料**: docs/issues/open/I452.md（GitHub #452 の本文の写し）と、#452 のコメント 5 件（I431・#446・I455 からの同梱）
- **実装後評価**: docs/reviews/open/I452_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
イシューの「背景/目的」と同じ。学習記録の機能（間隔反復・間違い分析・適応的な問題選択）はクイズの回答を材料にしておらず、画面からも呼ばれず、一部は 500 になる。このイシューでは、クイズの回答から間隔反復のカードを作る・更新する経路と、ダッシュボードの「今日の復習」から復習のクイズを始める画面を作る（間隔反復を端から端まで通す）。間違い分析と適応的な問題選択は 500 を直してテストで固定する（画面は別イシュー）。存在しないアドレスを指す画面側の関数を消す。

### 調査結果
**原因の概要**: 学習記録の機能はバックエンドだけが作られ、クイズの機能と別の記録（`ProblemAttempt`・`SpacedRepetitionReview`）を材料にしていた。クイズの回答（`QuizAnswer`）からその記録を作る経路も、画面からの呼び出しもテストも無かったため、問題モデルとのずれ（難易度の型）に誰も気づかなかった。

**詳細**（2026-11-12 時点の develop `72ffe57a`）:
1. **材料が書き込まれない**: クイズの回答は `backend/problems/views.py:893-977` の `submit_answer` が `QuizAnswer` だけを作る。間隔反復のカード（`SpacedRepetitionCard`）・復習記録（`SpacedRepetitionReview`）を作る処理は、画面から呼ばれない API（`/api/study/spaced-repetition/create_card/`・`submit_review/`）にしか無い
2. **難易度の型**: `Problem.difficulty` は数字（`backend/problems/models.py:106-110・129`。1=初級・2=中級・3=上級）。一方、次の箇所が `'easy'/'medium'/'hard'` の文字で扱う:
   - 数字の欄を文字で絞る（500 の原因）: `adaptive_selection.py:136・138`（`problem__difficulty=difficulty`）・`mistake_analysis.py:153・159`・`services.py:322-325`
   - 数字を文字の表のキーとして読む（500 にはならないが結果が常に 0・既定値）: `adaptive_selection.py:387-397`（`difficulty_weights`）・`:441-445`（`p.difficulty == difficulty_preference`）・`:510-511`（`difficulty_counts[difficulty]` は KeyError で 500）・`mistake_analysis.py:139-146`
   - `views.py:963-1105`（学習の道筋・難易度の配分）は習熟度の辞書のキー（`'easy'` など）を読むだけで、上の直しで正しく動く
   - 文字と数字の対応は、すでに `backend/problems/serializers.py:82-84・137-` に別の写し（`difficulty_map = {1: 'easy', 2: 'medium', 3: 'hard'}`）がある
3. **Problem に無い `is_active` での絞り込み**: イシューの「現状の問題 4」の箇所は、I431（PR #453）で `available_problems` に置き換え済みで、今は残っていない（`grep -n "is_active" backend/studylogs/adaptive_selection.py backend/studylogs/services.py backend/dashboard/views.py` で Problem の `is_active` を参照する行が無いことを確かめた）。このイシューでの直しは不要
4. **#446 からの同梱**: `backend/core/tests/test_I446_cross_api_tenant_isolation.py:111-114・235-236・249-250・263-267` が 9 ケースを `xfail(strict=True)` にしている（`learning_insights` の KeyError・`update_analytics`・`mistake-analysis/analyze`・`refresh_analysis`・`adaptive-learning` の 4 つの GET と `select_problems`）。`learning_insights` の KeyError は、`SpacedRepetitionService.get_learning_insights`（`services.py:360-361`）が分析の記録が無いとき `period_days`・`analytics_data` の無い辞書を返し、`LearningInsightsSerializer`（`serializers.py:186-191`）が必須の欄として読むため
5. **間違い分析の既存の不具合（I431 の同梱）**: `mistake_analysis.py:317-374` の `_generate_pattern_based_suggestions` が全種類の文言を先に組み立てるので、科目が空のパターン（`time_pressure`・`problem_type`）で `pattern.subject.name` が `AttributeError` になる
6. **今のクイズは終わらない**: `QuizService.get_next_problem`（`backend/problems/services/quiz_service.py:78-145`）は、科目の問題をすべて答えると既出の問題をランダムに出し続ける（`is_review_mode`。画面は `QuizSession.tsx:93-98・383-388` で「全○問を解き終えました。既出問題から再度出題しています。」）。セッションに「復習のクイズ」を表す欄は無い
7. **時刻**: `TIME_ZONE = 'Asia/Tokyo'`・`USE_TZ = True`（`backend/core/settings.py:119-121`）。利用者ごとの時刻の設定は無い（`backend/accounts/models.py` に欄なし）。「その日」はアプリの地域の日付（`timezone.localdate()`）で数える
8. **間隔反復の計算**: `SpacedRepetitionCalculator.calculate_next_review`（`spaced_repetition.py:31-75`）は SM-2。品質 3 以上で連続回数を 1 つ進め、間隔は連続 1 回目 1 日・2 回目 6 日・3 回目以降は前回の間隔×難易度係数。品質 3 未満で連続回数 0・間隔 1 日。次の復習日は「前回の復習の時刻＋間隔」（日付の境目にそろっていない）
9. **カードのキャッシュ（I431 の同梱 F3・SECURITY=yes）**: `get_due_cards`（`services.py:35-53`）と習熟度（`adaptive_selection.py:72-125`）のキャッシュのキーが利用者の番号だけで、組織を移った直後は最大 5 分、前の組織の結果が返りうる（`backend/core/cache_service.py:187-201・238-248`）
10. **画面側の使われていない関数**: `frontend/src/services/dashboard.service.ts` の `getStudyStats`・`getRecentSessions`・`getWeeklyProgress`・`getSubjectProgress`・`startStudySession`・`endStudySession`・`recordProblemAttempt` と `STUDYLOGS_BASE_URL`（7 行目）。どれも `frontend/src` のほかの場所から呼ばれない（`grep -rn` で確かめた）。`QuizSession.tsx` は `quiz.service.ts` を使わず `apiClient` を直接呼ぶ

### 環境前提
- app-1 のコンテナ（backend・db・redis・frontend）が動いている（2026-11-12 `docker compose ps`）。`gh` は Draft PR #464 の作成で確かめた
- 日付を固定する道具（freezegun など）は入っていない（`backend/requirements*.txt`）。日付に関わる計算は、サービスに「今」を渡せる形にしてテストする（4-2）
- テストは CI が正。手元では新しいテストと、守りにする I431・I166・I446・I455 のテストのファイルだけを流す

## 2. 受け入れ条件（Acceptance Criteria）
イシューの受け入れ条件と同じ。この計画での合格の基準（イシューの「正解なら前回より間隔が広がり」は、4-2 の SM-2 の決まりで具体化した）:
- [ ] AC1: クイズで 1 問答えると、その問題の間隔反復のカードが作られる・更新される。次の復習日は「答えた日の翌日以降の 0 時（アプリの地域の時刻）」で、正解なら連続回数が 1 つ進み、間隔は連続 1 回目 1 日・2 回目 6 日・3 回目以降は前回の間隔×難易度係数（四捨五入・1 日以上）。不正解なら連続回数 0・翌日（TC-01・TC-03）
- [ ] AC2: 同じ日に同じ問題を 2 回以上答えても、カードを更新するのはその日の最初の回答だけ（2 回目以降は復習記録も作らない）（TC-02）
- [ ] AC3: ダッシュボードのいちばん上（科目の選択の下・数字の並びの上）に「今日の復習 ○問」と「復習を始める」が出る。件数は上部の科目の選択に合わせる（科目を選べばその科目だけ・「すべて」なら全科目）（TC-04・TC-16・手動 No.1）
- [ ] AC4: 「復習を始める」を押すと、復習する日が来た問題だけで、上限なしにすべてを出題するクイズが始まる（科目を選んでいればその科目だけ・「すべて」なら全科目を混ぜる）（TC-05・TC-17・手動 No.2）
- [ ] AC5: 復習のクイズで対象をすべて答え終えると「今日の復習が終わりました（○問中○問正解）」と「ダッシュボードへ戻る」が出て、それ以上は出題されない。いつものクイズの出し続ける動きは変わらない（TC-05・TC-17・手動 No.2・No.4）
- [ ] AC6: 復習が 0 問のときは「今日の復習はありません（次は ○月○日）」（次の復習日が無いときは「今日の復習はありません」）。次の日付は選んでいる科目の中で最も近いもの（TC-04・TC-16）
- [ ] AC7: 復習を途中で中断すると、答えた問題は次の復習日が更新され、答えなかった問題は対象に残る（TC-06・手動 No.3）
- [ ] AC8: この変更より前のクイズの回答からは、復習の対象が作られない（TC-07）
- [ ] AC9: 他組織の問題・削除した問題・自組織で解けなくなった問題は、復習の件数にも出題にも入らない。他組織の科目を指定すると 400（TC-04・TC-08）
- [ ] AC10: 間違い分析・適応的な問題選択・学習洞察・分析の更新の API が、自組織のデータで 500 にならずに結果を返す。#446 の 9 ケースの xfail の印を外し、他組織・同じ組織の別の利用者の中身が出ないこと（`ListCheck`）を確かめる状態に戻す（TC-09〜TC-11・TC-14）
- [ ] AC11: 存在しないアドレスを指す画面側の関数 7 つと `STUDYLOGS_BASE_URL` が残っていない（TC-19）
- [ ] AC12: 間違い分析・適応的な問題選択を画面につなぐ別イシューが起票されている（plan-issue の段階で起票し、番号を 9 章に書く）
- [ ] AC13: I431・I166・I446・I455 の回帰テストがすべて pass する（組織の境界を緩めていない）（TC-14）
- [ ] AC14: 全テストが pass する（CI・TC-20）

## 3. 影響範囲
- Backend:
  - `backend/problems/difficulty.py`（新規・難易度の数字と文字の対応の 1 か所）
  - `backend/problems/models.py`（QuizSession に `mode` の欄）・`backend/problems/migrations/0022_quizsession_mode.py`（新規）
  - `backend/problems/serializers.py`（`QuizSessionSerializer` に `mode`・難易度の写しを `difficulty.py` に置き換え）
  - `backend/problems/services/quiz_service.py`（復習のクイズの開始・次の問題）
  - `backend/problems/views.py`（`submit_answer` からカードを更新・`next_problem` の復習の終わり）
  - `backend/studylogs/spaced_repetition.py`（クイズの正誤から品質への対応・日付の境目）
  - `backend/studylogs/services.py`（クイズの回答からカードを更新・今日の復習の件数と次の日付・復習の出題の候補・学習洞察の KeyError・キャッシュのキー）
  - `backend/studylogs/views.py`（`review_summary` の追加・印付けの 3 経路を `for_user` に）
  - `backend/studylogs/serializers.py`（`review_summary` の入力と応答）
  - `backend/studylogs/adaptive_selection.py`・`mistake_analysis.py`（難易度の型・科目が空のパターン・分母の組織の絞り込み・キャッシュのキー）
  - `backend/studylogs/tasks.py`（`export_user_data_task` の理由のコメントを実態に合わせる）
  - `backend/core/cache_service.py`（習熟度のキャッシュのキーに組織）
  - `backend/core/tests/test_I446_cross_api_tenant_isolation.py`（9 ケースの xfail を外す・新しい経路 `review_summary` を表に足す）
  - `backend/studylogs/tests/test_I452_quiz_review.py`（新規）
- Frontend:
  - `frontend/src/components/TodayReviewCard.tsx`（新規）・`frontend/src/components/__tests__/TodayReviewCard.test.tsx`（新規）
  - `frontend/src/services/review.service.ts`（新規・今日の復習の件数の取得）
  - `frontend/src/pages/Dashboard.tsx`（カードを科目の選択の下・数字の並びの上に置く）
  - `frontend/src/pages/QuizSession.tsx`（復習のクイズの開始・終わりの表示）・`frontend/src/pages/__tests__/QuizSession.review.test.tsx`（新規）
  - `frontend/src/types/quiz.ts`（セッションの `mode`）
  - `frontend/src/services/dashboard.service.ts`（関数 7 つと `STUDYLOGS_BASE_URL` を消す）
- DB: `problems_quizsession` に `mode`（文字・既定 `'normal'`・NOT NULL）を足す（10 章）。既存のデータは書き換えない（過去の回答からカードを作らない）
- Config/Infra: なし（依存の追加なし）

イシューの実装対象の表とのずれ: `frontend/src/services/quiz.service.ts` は変えない（クイズの画面はこのファイルを使っていないため。9 章）。代わりに `review.service.ts` を足す。

## 4. 変更点一覧

### 修正アプローチ
1. 間隔反復の決まりは `studylogs` のサービス（`SpacedRepetitionService`）に置き、クイズ（`problems`）のサービス・ビューから呼ぶ。モデルの依存の向き（`studylogs.models` → `problems.models`）は変えない（サービス層の `problems` → `studylogs` の呼び出しは、関数の中の import にして循環を作らない）
2. クイズのセッションに `mode`（`normal`／`review`）を持たせ、復習のクイズは「その時点で復習する日が来ていて、この回でまだ答えていない問題」を毎回問い合わせて出す。答えた問題は次の復習日が明日以降になるので自然に外れ、無くなったら終わり
3. 次の復習日は「答えた日の 0 時＋間隔」にそろえ、「今日の復習」は `next_review_date <= 今` で数える
4. 難易度は `problems/difficulty.py` の 1 か所で数字と文字を対応させ、学習記録の側は文字（`easy`・`medium`・`hard`）のまま扱う（API の応答の形・`MistakePattern.problem_difficulty` の文字の欄を変えない）

### 4-1. 難易度の対応（`backend/problems/difficulty.py`・新規）
**修正方針**: 数字（`Problem.DIFFICULTY_CHOICES`）と文字の対応を 1 か所に置き、`problems/serializers.py` の写しと学習記録の側がこれを使う。
```python
"""問題の難易度の数字（Problem.difficulty）と、表示・分析で使う文字の対応（ここだけに書く）"""
LABEL_BY_LEVEL = {1: 'easy', 2: 'medium', 3: 'hard'}
LEVEL_BY_LABEL = {label: level for level, label in LABEL_BY_LEVEL.items()}
LABELS = tuple(LABEL_BY_LEVEL.values())  # ('easy', 'medium', 'hard')


def label_of(level):
    """数字を文字に。知らない値は None"""
    return LABEL_BY_LEVEL.get(level)
```
- `problems/serializers.py:82-84・137-` の `difficulty_map` を `LABEL_BY_LEVEL`・`LEVEL_BY_LABEL` に置き換える（既定値 `'medium'` などの振る舞いはそのまま）
- 学習記録の側の直し:
  - 数字の欄を絞るところ（`adaptive_selection.py:136・138`・`mistake_analysis.py:153・159`・`services.py:322-325`）は `problem__difficulty=LEVEL_BY_LABEL[label]`
  - 数字を読むところ（`adaptive_selection.py:387`・`:445`・`:510`・`mistake_analysis.py:139・144`）は `label_of(problem.difficulty)`。`None`（知らない値）は数えない
  - `for difficulty in ['easy', 'medium', 'hard']` は `LABELS` を使う

### 4-2. 間隔反復の決まり（`spaced_repetition.py`・`services.py`）
**修正方針**: クイズの正誤から品質の値を決め、次の復習日を日付の境目にそろえる。同じ日の 2 回目以降は更新しない。「今」を引数で渡せるようにして、テストで日をまたぐ。

`spaced_repetition.py`（`SpacedRepetitionCalculator` に定数を足す）:
```python
QUIZ_CORRECT_QUALITY = 4    # 正解（難易度係数は変えない）
QUIZ_INCORRECT_QUALITY = 2  # 不正解（SM-2 の失敗の中で最も軽い。係数を 0.32 下げ、下限 1.3）
```

`services.py`（`SpacedRepetitionService`）:
```python
def _start_of_local_day(now):
    """now のアプリの地域の日付の 0 時（aware）"""
    local = timezone.localtime(now)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)

@transaction.atomic
def record_quiz_answer(self, problem, is_correct, time_taken_seconds, *, now=None):
    """クイズの回答から、その問題のカードを作る・更新する。同じ日の 2 回目以降は何もしない（None を返す）"""
    now = now or timezone.now()
    card, _ = SpacedRepetitionCard.objects.get_or_create(
        user=self.user, problem=problem,
        defaults={...INITIAL..., 'next_review_date': now})
    card = SpacedRepetitionCard.objects.select_for_update().get(pk=card.pk)
    if card.last_reviewed_at and timezone.localdate(card.last_reviewed_at) == timezone.localdate(now):
        return None
    quality = (self.calculator.QUIZ_CORRECT_QUALITY if is_correct
               else self.calculator.QUIZ_INCORRECT_QUALITY)
    return self.review_card(card, quality, time_taken_seconds, now=now)
```
- `review_card` に `now=None` を足し、`calculate_next_review(..., last_review_date=_start_of_local_day(now))`・`card.last_reviewed_at = now` にする（`submit_review` の既存の API も同じ日付の境目になる）。`review_card` の残り（復習記録の作成・キャッシュの無効化）は今のまま
- `get_or_create` の後の `select_for_update` は、同じ問題を同時に 2 つのタブで答えたときに 2 回更新しないため（`unique_together = ['user', 'problem']` で行は 1 つ）
- 今日の復習の件数と次の日付（`review_summary`）と、復習の出題の候補（`due_problems`）:
```python
def due_cards_queryset(self, subject=None, *, now=None):
    """復習する日が来たカード（有効・自組織で解ける問題・科目の指定があればその科目）"""
    now = now or timezone.now()
    problems = available_problems(self.user, subject)
    return SpacedRepetitionCard.objects.for_user(self.user).filter(
        is_active=True, next_review_date__lte=now, problem__in=problems)

def review_summary(self, subject=None, *, now=None):
    """{'due_count': int, 'next_review_date': date | None}（次の日付は今日より後の最も近いもの・アプリの地域の日付）"""
```
  - `next_review_date` は「有効・自組織で解ける問題・指定の科目」のカードのうち `next_review_date > now` の最小を `timezone.localdate()` にしたもの。無ければ `None`
- 学習洞察の KeyError（調査 4）: `get_learning_insights` の分析の記録が無いときの戻り値を `{'insights': [], 'recommendations': [], 'period_days': days, 'analytics_data': []}` にする
- キャッシュのキー（調査 9）: `get_due_cards` のキーを `f"due_cards_{limit}_org{self.user.organization_id}"` にする

### 4-3. クイズのセッションの `mode`（`problems/models.py`・`serializers.py`・`quiz_service.py`・`views.py`）
**修正方針**: 復習のクイズを区別する欄を足し、開始・次の問題・回答をその欄で分ける。いつものクイズ（`normal`）の動きは変えない。

`problems/models.py`（QuizSession）:
```python
MODE_NORMAL = 'normal'
MODE_REVIEW = 'review'
MODE_CHOICES = [(MODE_NORMAL, '通常'), (MODE_REVIEW, '今日の復習')]
mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=MODE_NORMAL)
```
`QuizSessionSerializer`: `fields` に `mode` を足す（書けるのは作成のときだけ・`ChoiceField`・省略時 `normal`。`read_only_fields` には入れない。作成以外の書き込みの API は無い〔`http_method_names` が get・post だけ〕）。

`QuizService.start_session(*, user, subject, client_request_id, mode=QuizSession.MODE_NORMAL)`:
- 冪等の確かめ（`existing.subject_id != ...`）に `existing.mode != mode` を足す（違えば `IdempotencyKeyReusedError`・422）
- `total_problems` は、`normal` なら今と同じ、`review` なら `SpacedRepetitionService(user).due_cards_queryset(subject).count()`

`QuizService.get_next_problem(session)`:
- `review` のとき（新しい関数 `_next_review_problem`）: `due_cards_queryset(session.subject)` からこの回で答えた問題を除き、`next_review_date` の早い順・カードの番号順で最初の問題を返す。無ければ `None`。戻り値は `(問題 or None, False, session.total_problems)`
- `normal` のときは今のまま

`QuizSessionViewSet`:
- `create`: `mode=serializer.validated_data.get('mode', QuizSession.MODE_NORMAL)` を渡す
- `next_problem`: `review` で問題が無ければ `200 {"review_complete": true, "total_problems": <回の total_problems>, "completed_problems": <答えた数>, "correct_answers": <正解数>}`。`normal` で問題が無いときは今と同じ 404
- `submit_answer`: `QuizAnswer` の作成・正誤の判定・回の集計の保存を `transaction.atomic()` で囲み、その中で `SpacedRepetitionService(session.user).record_quiz_answer(problem, is_correct, time_taken)` を呼ぶ（`normal`・`review` の両方。カードの更新に失敗したら回答も保存しない＝回答とカードを食い違わせない）。応答の形は変えない
- 回答してよい問題は今と同じ（`available_problems(user, session.subject)`）

### 4-4. 今日の復習の API（`studylogs/views.py`・`serializers.py`）
**修正方針**: ダッシュボードのカードが読む件数と次の日付を返す。科目の指定は自組織で選べる科目だけを受け付ける。
- `GET /api/study/spaced-repetition/review_summary/`（`SpacedRepetitionViewSet` の `@action(detail=False, methods=['get'])`・`permission_classes = [permissions.IsAuthenticated]`〔ViewSet の既存の設定〕）
- 入力: `subject_id`（省略可。整数）。`ReviewSummaryQuerySerializer` で検証し、`available_subjects(request.user).get(id=…)` に無ければ 400
- 応答 200: `{"due_count": <int>, "next_review_date": "YYYY-MM-DD" | null}`（`ReviewSummarySerializer`。`next_review_date` は `DateField`）
- エラー:
  - 未認証: 401（DRF の既定 `{"detail": "..."}`）
  - `subject_id` が整数でない・他組織・全体共有・存在しない科目: 400 `{"error": {"main_message": "科目の指定が正しくありません", "sub_message": "ダッシュボードの科目の選択からやり直してください", "details": {}}}`（`core.exceptions.create_error_response`）
- キャッシュしない（件数は索引 `user, next_review_date, is_active` で数える軽い問い合わせ）

### 4-5. 間違い分析・適応的な問題選択の 500 と同梱の直し
**修正方針**: 500 の原因だけを直し、計算の考え方は変えない（画面につなぐ別イシューで見直す）。
- 難易度（4-1）
- `_generate_pattern_based_suggestions`（調査 5）: 種類ごとの文言を、当てはまる種類だけ組み立てる（種類ごとの小さな関数の表にする）。科目が要る種類（`subject_difficulty`・`concept_confusion`）で科目が空なら提案を作らない
- `_analyze_problem_type_errors` の分母（I431 の同梱 F5）: `SpacedRepetitionReview`・`ProblemAttempt` を `for_user(self.user)` で数える（分子の間違いの記録はすでに `for_user` なので、分母も同じ範囲にそろえる。理由のコメントを消す）
- 習熟度のキャッシュのキー（I431 の同梱 F3）: `cache_service.get_proficiency_cache`・`set_proficiency_cache` に `organization_id` の引数を足し、キーを `('proficiency', user_id, organization_id, subject_id or 'all')` にする。呼び出し（`adaptive_selection.py:72-75・122-126`）は `self.user.organization_id` を渡す。キーを消す処理（`invalidate_*`）がこのキーの形に依存していないかを実装の時に確かめる（依存していれば同じ形にそろえる）
- 印付けの 3 経路（I455 の BP の同梱）: `studylogs/views.py` の `mark_suggestion_read`・`resolve_weakness`、`mistake_analysis.py` の `provide_suggestion_feedback` の `objects.get(id=…, user=…)` を `objects.for_user(user).get(id=…)` にし、`組織で絞らない` のコメントを消す（他組織の科目を指す自分の古い記録は 404 になる）
- `export_user_data_task` の理由のコメント（I455 の同梱 F1）: 「件数だけの集計」を「本人の記録の書き出し（応答は件数だけ・中身は外に出さない）」に直す（`tasks.py:276-278`）

### 4-6. 画面: 今日の復習のカード（`TodayReviewCard.tsx`・`review.service.ts`・`Dashboard.tsx`）
**修正方針**: ダッシュボードとは独立した部品にし、I190 のダッシュボードの作り直しとぶつかりにくくする。

`review.service.ts`:
```ts
export interface ReviewSummary { due_count: number; next_review_date: string | null; }
export const getReviewSummary = async (subjectId?: string): Promise<ReviewSummary> =>
  (await apiClient.get<ReviewSummary>('/api/study/spaced-repetition/review_summary/',
    { params: subjectId ? { subject_id: subjectId } : {} })).data;
```
`TodayReviewCard`（props: `subjectId: string`。`'all'` なら全科目）:
- 読み込み中: カードの中に `CircularProgress`（小）と「今日の復習を読み込み中…」（`role="status"`）
- `due_count > 0`: 見出し「今日の復習 {N}問」と、ボタン「復習を始める」（`variant="contained"`）。押すと `navigate('/quiz?mode=review' + (subjectId !== 'all' ? '&subject=' + subjectId : ''))`
- `due_count === 0`: 「今日の復習はありません（次は {M}月{D}日）」。`next_review_date` が `null` なら「今日の復習はありません」。日付は `YYYY-MM-DD` を分けて数字で組み立てる（端末の時刻の設定でずれないように `Date` に通さない）
- 読み込みの失敗: 9 章の確認待ち U3 の推奨（「今日の復習を読み込めませんでした」と「再読み込み」ボタン。押すと読み直す）
- `subjectId` が変わったら読み直す。古い応答が新しい応答を上書きしないよう、effect の後片付けで捨てる
- ボタンは MUI の既定の大きさ（高さ 36px 以上）・キーボードで押せる。見出しは `Typography component="h2"`

`Dashboard.tsx`: 科目の選択（`SubjectSelector` の `Box`）の直後・「Stats Cards」の `Grid` の直前に `<Box sx={{ mb: 3 }}><TodayReviewCard subjectId={selectedSubject} /></Box>` を置く。ほかは変えない。

### 4-7. 画面: 復習のクイズ（`QuizSession.tsx`・`types/quiz.ts`）
**修正方針**: いつものクイズの画面を使い、`?mode=review` のときだけ開始の内容と終わりの表示を変える。
- `const mode = searchParams.get('mode') === 'review' ? 'review' : 'normal'`。`createNewSession` は `mode === 'review'` のとき送る内容に `mode: 'review'` を足す。開始を 1 回に限る `startedSubjectRef` のキーを「科目＋mode」にする
- `loadNextProblem`: 応答が `review_complete: true` なら、`POST /api/quiz/<id>/end/` を呼んで回を終え（失敗しても表示は続ける）、`reviewResult = {total: completed_problems, correct: correct_answers}` を持って終わりの表示にする
- 終わりの表示（`mode === 'review'` のとき・既存の「クイズ完了！」の表示は使わない）:
  - 答えた数が 1 以上: 「今日の復習が終わりました（{答えた数}問中{正解数}問正解）」
  - 0（開いた時点で対象が無い）: 「今日の復習はありません」
  - ボタン「ダッシュボードへ戻る」（押すと `/dashboard`）だけ。「もう一度挑戦」は出さない
- 回答の後のボタン: `review` では答えた数にかかわらず次へ進むボタンを出す（今の「`answered_problems < total_problems` のときだけ『次の問題』」は、復習の最後の問題で先へ進めなくなるため）。最後の問題（答えた数＝`total_problems`）のときのラベルは 9 章の確認待ち U1 の推奨（「結果を見る」）。押すと次の問題を読み、`review_complete` で終わりの表示になる
- 復習中の印: 9 章の確認待ち U2 の推奨（進み具合の行の左に `Chip`「今日の復習」）
- `types/quiz.ts` の `QuizSession` に `mode?: 'normal' | 'review'` を足す
- 「中断」は今と同じ（ダッシュボードへ戻る。回は終えない）

### 4-8. 画面側の使われていない関数の削除（`dashboard.service.ts`）
`getStudyStats`・`getRecentSessions`・`getWeeklyProgress`・`getSubjectProgress`・`startStudySession`・`endStudySession`・`recordProblemAttempt` と `STUDYLOGS_BASE_URL` を消す。使わなくなった型の import（`StudyStats`・`StudySession`）を消す（`types.ts` の型の定義は I190 の扱いなので残す）。`getRecommendations` は I190 に任せて残す。

### 4-9. テスト
**`backend/studylogs/tests/test_I452_quiz_review.py`（新規）**: データの作り方は I431・I455 のテストにそろえる（組織 A・B、各組織の科目・問題、組織に属さない利用者、各テストの前後で cache を消す）。日付は `record_quiz_answer(..., now=...)` に渡すか、カードの `last_reviewed_at`・`next_review_date` を直接書いて作る。中身は 6 章の TC 表のとおり。

**`backend/core/tests/test_I446_cross_api_tenant_isolation.py`**: 9 ケースの `xfail=XFAIL_452…` を外し、使わなくなった定数 `XFAIL_452`・`XFAIL_452_INSIGHTS` を消す。`ROUTE_TABLE` に `f"GET {SR}review_summary/": [ListCheck(), IdCheck("user", "query", "subject_id", "subject", 400)]` を足す（全経路の表に無い経路があると、このファイルのテストが落ちる作り）。

**フロント**: `TodayReviewCard.test.tsx`（新規）・`QuizSession.review.test.tsx`（新規）。既存の `QuizSession.test.tsx`・`QuizSession.start.test.tsx` は変えない（いつものクイズの無退行）。

## 5. 実装手順
- ステップ 1（未知リスク先行・ステップ 2 以降の前提）: 4-1 と 4-5 の 500 の直し → #446 の 9 ケースの xfail を外して流す（TC-14 の一部）。難易度を直しても別の原因で 500 が残る経路があれば、ここで見つけて直す（直し方が 4-5 の「原因だけを直す」を超えるなら計画変更記録に書いてから）→ TC-09〜TC-11・TC-13
- ステップ 2（垂直スライス・ステップ 1 と並行可）: 4-2・4-3 のうち「回答でカードを更新する」部分（`record_quiz_answer`・`submit_answer`）と migration → TC-01〜TC-03・TC-07・TC-15
- ステップ 3（ステップ 2 が前提）: 4-2 の `review_summary`・4-4 の API・4-6 のカードとダッシュボードへの配置 → TC-04・TC-08・TC-12・TC-16
- ステップ 4（ステップ 3 が前提）: 4-3 の復習のクイズ（開始・次の問題・終わり）と 4-7 の画面 → TC-05・TC-06・TC-17
- ステップ 5（独立）: 4-8 の削除 → TC-19
- ステップ 6: #446 の表に `review_summary` を足し、守りのテストを流す → TC-14
- ステップ 7: /simplify の後に TC-14・TC-15・TC-19 を流し直す（→ TC-21）

## 6. テスト計画
- 自動: docs/tests/open/I452_auto_test.md
  - 単体（サービス）: 間隔の決まり・同じ日の扱い・件数と次の日付・キャッシュのキー（日付は引数で渡す）
  - 結合（API）: 回答 → カード、今日の復習の API（科目・組織・入力の誤り・未認証）、復習のクイズの開始〜終わり、中断、過去の回答、間違い分析・適応的な問題選択・学習洞察の 200、#446 の横断の越境テスト
  - フロント（Jest）: カードの表示の 5 状態と遷移先、復習のクイズの開始・終わりの表示
  - 新しい E2E は足さない — 復習する日が来たカードを作るには日付をまたぐ必要があり、E2E からは DB の日付を動かせない。画面の通しの動きは手動 No.1〜No.4（Claude が Playwright MCP と `manage.py shell` で日付を前に倒して確かめる）で見る
- 手動: docs/tests/open/I452_manual_test.md（すべて Claude）
- 再発防止: #446 の 9 ケースを `ListCheck` に戻し、間違い分析・適応的な問題選択の経路が CI で毎回呼ばれる（今回の 500 は「その経路を通るテストが無い」ことが原因）。難易度の対応と `Problem.DIFFICULTY_CHOICES` の一致もテストで固定する（TC-09）

## 7. ロールバック
- コードは PR を revert する
- DB: migration `0022_quizsession_mode` を戻す（`python manage.py migrate problems 0021`）と `mode` の欄が消える（中身は「通常」か「今日の復習」の区別だけで、失って困るデータは無い）。間隔反復のカード・復習記録は、残っても既存の画面・API を壊さない（今は画面から使われていないテーブル）
- サービスの再起動は通常のデプロイだけ（migration を含むので、デプロイの手順で `migrate` を流す）

## 8. Risk & 回避策
- R1 難易度を直しても、間違い分析・適応的な問題選択に別の 500 が残る → ステップ 1 で #446 の 9 ケースと TC-10・TC-11 を先に流して見つける。直し方が「原因だけを直す」を超える場合は計画変更記録に書く
- R2 回答のたびの書き込みが増え、回答が遅くなる → 1 回の回答で増える問い合わせはカードの取得・ロック・更新と復習記録の作成の数本（索引あり）。`update_daily_analytics` は回答ごとには呼ばない（既存の定期処理に任せる）
- R3 同じ問題を同時に答えたときの二重更新 → `select_for_update` と「同じ日の 2 回目は更新しない」で 1 回だけにする（TC-02）
- R4 日付の境目のずれ（UTC と地域の時刻）→ 次の日付は地域の 0 時（aware）で保存し、比べるのは `next_review_date <= now`。テストで 23:59・0:00 をまたぐ（TC-01）
- R5 復習のクイズの途中で別のタブから回答し、対象が減る → 毎回その時点の対象を問い合わせるので、減った分は出ない。表示の「○問中」は答えた数で出す（開始の時の件数とずれても破綻しない）
- R6 I190 と同じファイル（`Dashboard.tsx`・`dashboard.service.ts`）を触る → カードは独立した部品にし、`Dashboard.tsx` の変更は 1 か所の差し込みだけ。消すのは使われていない関数だけ
- R7 回答とカードの更新を 1 つのトランザクションにしたことで、カードの側の不具合が回答を止める → 食い違い（回答はあるのにカードが無い）を作らないほうを優先する（C7 フェールセーフ: 失敗を隠さない）。カードの更新は単純な処理で、TC-01〜TC-03 で固定する
- R8 `mode` の欄の追加の migration → 文字の欄を既定値つきで足すだけ（既存の行は `'normal'`）。PostgreSQL では表の書き換えなしで終わる

## 9. 確定事項と自律判断
**イシューに明記されていること**（設計確認メモ・2026-11-12）:
- クイズの回答のたびにカードを作る・更新し、次の復習日を正誤から自動で決める（自己評価のボタンは置かない）。同じ日の最初の回答だけで決める
- 画面までつなぐのは復習だけ。間違い分析・適応的な問題選択は 500 を直してテストを付けるところまで。両者を画面につなぐ別イシューを Claude が起票する
- ダッシュボードのいちばん上に「今日の復習 ○問」と「復習を始める」。0 問の文言。件数と出題は上部の科目の選択に合わせる。上限なし。中断可
- 対象をすべて答え終えたら「今日の復習が終わりました（○問中○問正解）」と「ダッシュボードへ戻る」。いつものクイズの動きは変えない
- 過去の回答からは作らない。おすすめ・`logs`・`statistics`・`goals` は I190 に任せる。関数 7 つと `STUDYLOGS_BASE_URL` を消す

**画面の細部で、イシューに無く計画で決めたもの（ユーザーの確認待ち・計画レビューの前に確かめる）**:
- U1 復習の最後の問題に答えた後の、先へ進むボタンのラベル: 推奨「結果を見る」（今の「次の問題」のままだと、次の問題が無いのに「次の問題」と出る）
- U2 復習中であることの印: 推奨「進み具合の行の左に『今日の復習』の小さな印（Chip）を出す」（いつものクイズと見分けられるように）
- U3 カードの読み込みに失敗したとき: 推奨「今日の復習を読み込めませんでした」と「再読み込み」ボタン（`docs/runbooks/ux-rules.md` の「明確な次のアクション」）

**Claude が技術的に決めたこと（理由）**:
- クイズの正誤から品質の値への対応は、正解 4・不正解 2 — 正解 4 は SM-2 で難易度係数を変えない値で、正誤だけからは「簡単だったか」を判断できない。不正解 2 は失敗の中で最も軽い値（係数を 0.32 下げる）で、1 回の誤答で間隔が伸びにくくなりすぎない。既存の `get_quality_score_from_performance`（回答時間を使う）は、平均の回答時間の定義がクイズの側に無いので使わない
- 次の復習日を「答えた日の 0 時＋間隔」にそろえた — 「今日の復習」を日付で数えるため（時刻のままだと、昨日の夕方に答えた問題が今日の夕方まで出てこない）。アプリの地域の時刻（`Asia/Tokyo`）で数える（利用者ごとの時刻の設定が無い・調査 7）
- 「その日の最初の回答だけ」の判定は `last_reviewed_at` の地域の日付で行う（欄を足さない）。2 回目以降は復習記録も作らない（間違い分析の材料も 1 日 1 回にそろう）
- 復習のクイズを `QuizSession.mode` の欄で表した — 開始・次の問題・回の一覧で区別が要り、回の外（URL など）に持つと、読み直し（`/quiz/<id>`）で区別が失われる。新しいモデル・別のエンドポイントにすると、回答・終了・越境のテスト（#446）の経路が増える
- 復習の出題は毎回その時点の対象を問い合わせる（開始の時の一覧を保存しない）— 答えた問題は次の日付が明日以降になって自然に外れ、別タブの回答や問題の削除にも追従する。保存しないのでデータの形を増やさない
- 復習の終わりは、`next_problem` が `200 {"review_complete": true, ...}` を返し、画面が `end` を呼ぶ形にした — GET に回を終える副作用を持たせない。404 を「終わり」に使うと、いつものクイズの「問題が無い」と区別できない
- 回答とカードの更新を 1 つのトランザクションにした（R7）
- カードの更新の処理は `studylogs` のサービスに置き、`problems` のビュー・サービスから関数の中の import で呼ぶ — 間隔反復の決まりを 1 か所に保つ。モデルの依存の向き（`studylogs.models` → `problems.models`）は変えず、循環 import を作らない（I455 の「判定の部品は problems に置き、problems から studylogs への依存を作らない」は組織の判定の部品の置き場所の決まりで、サービスの呼び出しには当たらない）
- 今日の復習の API を `SpacedRepetitionViewSet` の `review_summary` にした — 既存の `due_cards` は件数の上限（`limit`）つきの一覧でキャッシュを使い、科目で絞れず次の日付も返さない。ダッシュボードには件数と日付だけで足りる
- 他組織の科目の指定は 400 — ダッシュボードの科目の選択に出ない値なので「入力の誤り」として扱う。I190 の計画（不正な `subject_id` は 400）とそろえる。#446 の表もこの値で固定する
- 難易度の対応を `problems/difficulty.py` に置き、`problems/serializers.py` の写しも置き換える — 写しが 2 つになると再びずれる。学習記録の側は文字のまま扱い、`MistakePattern.problem_difficulty`（文字の欄）と API の応答の形を変えない（migration を増やさない）
- 間違い分析・適応的な問題選択は、500 の原因だけを直し、計算の考え方（しきい値・重み）は変えない — 画面につなぐ別イシューで、表示と合わせて見直すため
- フロントの今日の復習の取得は `review.service.ts` に置き、`quiz.service.ts` は変えない — クイズの画面は `quiz.service.ts` を使っていない（調査 10）。イシューの実装対象の表とのずれとして記録する
- 新しい E2E を足さない（6 章）
- テストの置き場所は `backend/studylogs/tests/test_I452_quiz_review.py`（クイズの側の経路もここ）— 間隔反復の決まりが主役で、I431・I455 のテストと同じ場所にそろえる

**同梱の扱い**（#452 のコメント 5 件）:
- I431 の F1・I455 の F3（`SubjectRecommendationView` の `studied_subject_ids` の NOT IN と NULL）: I190 に渡す — おすすめは I190 の担当（設計確認メモ）
- I431 の F2（`StudyLogViewSet.create` が他組織の科目の進行中の記録も閉じる）: I190 に渡す — `logs` の存廃は I190 の担当
- I431 の F3（キャッシュのキーに組織・SECURITY=yes）: 同梱（4-2・4-5）
- I431 の F4（`get_user_selected_subjects` のキャッシュの並び順・組織）: I190 に渡す — ダッシュボードの科目の一覧の経路で、このイシューの変更点と関係しない
- I431 の F5（難易度の誤答率の分母）: 同梱（4-5）
- I431 の F6（`QuizService.available_*` の中継）: 残す — 振る舞いに関係せず、呼び出し元を広く変えるため。retro で処遇を決める
- I431 の既存の不具合（科目が空のパターンで `AttributeError`）: 同梱（4-5）
- I431 の敵対的レビューの Low・I455 の F1（`export_user_data_task`）: 理由のコメントを実態に合わせる（4-5）。書き出しの実装はしない
- #446 の `learning_insights` の KeyError と 9 ケースの xfail: 同梱（4-2・4-9）
- I455 の F4（問題ごとのスコアの集計で JOIN が増える）: 別イシュー（適応的な問題選択を画面につなぐもの）に渡す — 画面につなぐときに性能を見直す
- I455 の F5（`scope_to_user_org` の import 元が 2 つ）: 残す — I431 のテストのファイルを触らないため
- I455 の静的テストの残り（F2・F8〜F11）・検討案（`owned_by`・`__init_subclass__`・QuizAnswer の QuerySet）: 残す — 静的テストの仕組みの改善で、このイシューの変更点と関係しない。retro で処遇を決める。このイシューで足す読み出しは `for_user` を使い、静的テストに従う
- I455 の BP（印付けの 3 経路を `for_user` に）: 同梱（4-5）
- 「I190 に渡す」もの: I190 は primary のワークツリーの手元のイシューファイル（`docs/issues/open/I190.md`）で管理されていて、このワークツリーから直接書かない（トラックの境界）。retro で引き継ぎの方法を決める

**起票した別イシュー**: （起票の後に番号を書く）間違い分析・適応的な問題選択を画面につなぐ

**要件適合性・業務ロジック**: 受け入れ条件を超える仕様の追加は無い（U1〜U3 はユーザーに確かめる）。閲覧範囲: 本人のカードで、自組織で解ける問題（`available_problems`）のものだけ。科目の指定は自組織で選べる科目だけ。状態の遷移: カードの次の日付は 4-2 の決まり、回は「開始 → 回答 → 終わり（`end`）」で、復習の回は対象が無くなったら画面が `end` を呼ぶ。境界の値: 対象 0 件・次の日付なし・同じ日の 2 回目・日付の境目（23:59・0:00）・問題の削除・組織の移動・組織に属さない利用者（`available_problems` が空で件数 0）。

**セキュリティ・BP**: 入力の検証は `subject_id`（整数・自組織の科目）と `mode`（選択肢）を DRF のシリアライザで行う。認可は既存の `IsAuthenticated` と、本人の回（`for_user`）・本人のカード（`for_user`）・自組織の問題（`available_problems`）で絞る（最小権限は変えない）。機密データは扱わない（応答は件数と日付）。OWASP: A01 は #446 の横断テストと TC-08 で確かめる。SQL は ORM のまま。XSS は React の既定のエスケープ（`dangerouslySetInnerHTML` を使わない）。依存の追加なし。bandit は MEDIUM 以上を直す・LOW は `# nosec` で抑える。npm audit は high・critical を直す（依存を変えないので新しい検出は無い見込み）。

**P3（データ整合性）**: 10 章。**P5（運用）**: 非同期処理・外部 API は変えない（11 章は不要）。**P8（コスト）**: インフラ・外部サービスの追加なし（12 章は不要）。
**P6（性能・UX）**: 13 章。
**P9（プライバシー）**: 15 章。

**台帳の残りの一覧**:
- 一覧 I224.md F9: 残す — ハーネスの項目で、このイシューの変更点と関係しない（`FILE=-`）
- 一覧 I223.md B1〜B4: 残す — bot の停止に関する項目で、このイシューの変更点と関係しない（`FILE=-`）
- 実装対象のファイルに当たる行は無し

## 10. データ整合性設計
- 欄の追加: `QuizSession.mode = CharField(max_length=10, choices=MODE_CHOICES, default='normal')`（NOT NULL・既定 `'normal'`）。migration `backend/problems/migrations/0022_quizsession_mode.py`（`AddField` だけ）。既存の行は `'normal'` になる（今までの回はすべて通常）。Danger Ops には当たらない（データの削除・書き換え・破壊的な変更が無い）
- 制約: 既存の「利用者ごとに有効な回は 1 つ」（`uniq_active_quizsession_per_user`）はそのまま。復習の回もこの制約に入る（復習を始めると、進行中のいつものクイズは終わる・今の開始の動きと同じ）
- トランザクション: `submit_answer` の回答の作成・正誤・回の集計・カードの更新・復習記録の作成を 1 つにする。カードは `get_or_create` の後に `select_for_update` でロックする
- 冪等性: 同じ問題の同じ日の 2 回目はカードを変えない（AC2）。同じ回で同じ問題を 2 回答える要求は今と同じく 400（`Problem already answered`）
- 同時更新: 2 つのタブで同じ問題を同時に答えたとき、ロックの後の「同じ日の 2 回目」の判定で 1 回だけ更新する
- ロールバック: 7 章（`migrate problems 0021` で欄を消せる）

## 13. 性能・UX設計
**性能**:
- 今日の復習の件数: `SpacedRepetitionCard` の索引（`user, next_review_date, is_active`）と `available_problems` の副問い合わせで 1 本。次の日付も 1 本。キャッシュしない
- 復習のクイズの次の問題: 毎回 1 本（対象の問い合わせと、この回で答えた問題の除外）
- 回答: カードの取得・ロック・更新と復習記録の作成で数本増える（R2）

**UX 設計**（`docs/runbooks/ux-rules.md`）:
- 現在の課題: 復習のしくみが画面に無く、間違えた問題をいつ解き直すかを学習者が自分で覚えておく必要がある
- 改善後の体験: (1) クイズで答える → (2) 翌日以降、ダッシュボードのいちばん上に「今日の復習 ○問」が出る → (3)「復習を始める」で、その日の対象だけを出題 → (4) 全部答えると「今日の復習が終わりました（○問中○問正解）」と「ダッシュボードへ戻る」→ (5) ダッシュボードは「今日の復習はありません（次は ○月○日）」
- 読み込み中: カードの中に小さな読み込み中の表示（ダッシュボードの他の欄を待たせない）
- エラー・例外時:
  - カードの読み込みの失敗: U3（その場で再読み込みできる・ダッシュボードの他の欄はそのまま）
  - 復習のクイズの開始の失敗: 今と同じ（トースト「クイズセッションの作成に失敗しました」とダッシュボードへ戻る）
  - 開いた時点で対象が 0（別のタブで答え終えた等）: 「今日の復習はありません」と「ダッシュボードへ戻る」
  - 終わりの `end` の失敗: 終わりの表示は出す（回は次の開始のときに終わる・今の動きと同じ）
- 破壊的な操作: 無し（削除の操作を足さない）
- アクセシビリティ: カードの見出しは `h2`、読み込み中は `role="status"`、ボタンはキーボードで押せて高さ 36px 以上（MUI の既定）、色だけで状態を表さない（文言で出す）
- 成功指標: 計測の指標（KPI）はイシューの範囲外。手動 No.1〜No.4 で体験の流れが途切れないことを確かめる

## 14. 学習効果設計
- 間隔反復のアルゴリズム: 既存の SM-2（SuperMemo 2）をそのまま使う。正誤の 2 値からの品質の対応（正解 4・不正解 2）と、日付の境目にそろえる直しだけを足す。アルゴリズムの科学的な根拠づけ・効果測定の指標（KPI）の定義はイシューの「含まない」
- 復習のタイミング: 正解を続けると 1 日 → 6 日 → 約 15 日（係数 2.5 のとき）と伸び、間違えると翌日に戻る
- つまずき検知: 間違い分析は 500 を直すところまで（画面は別イシュー）。復習記録（`SpacedRepetitionReview`）が回答から作られるようになるので、間違い分析の材料が実際に貯まり始める
- 参照: 品質基準 C1（`docs/proposals/learning_app_quality_criteria.md:43-49`）

## 15. プライバシー・コンプライアンス設計
- 扱うデータ: 本人の回答から作るカード・復習記録（既存のテーブル）。新しい個人情報の項目は増やさない
- テナント分離: カード・復習記録の読み出しは `for_user`（本人＋自組織の問題）と `available_problems` で絞る。他組織の科目の指定は 400。#446 の横断テストで全経路を確かめる
- 保持期間・削除: 既存の方針のまま（問題の削除でカードも消える〔`on_delete=CASCADE`〕・利用者の削除でも消える）
- 目的外利用: カードは本人の復習の予定にだけ使う。他の利用者・組織管理者に見せる画面は作らない
- 未成年への配慮・保護者の同意・開示請求の導線は、既存の方針から変えない（新しい収集が無い）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 今日の復習の件数・次の日付・復習の出題に、他組織の問題・削除した問題・同じ組織の別の利用者のカードが入らない。他組織・全体共有・存在しない科目の `subject_id` は 400（TC-04・TC-08・TC-14） |
| V2 | 2 | 実験必須 | 次の復習日が 4-2 の決まり（地域の 0 時＋間隔・正解 4／不正解 2 の SM-2）どおりで、同じ日の 2 回目は更新しない。日付の境目（23:59 と 0:00）をまたいでも数え間違えない（TC-01・TC-02） |
| V3 | 1 | 実験必須 | 復習のクイズが、回の科目の指定（「すべて」なら全科目）の範囲の対象だけを出し、対象が無くなったら `review_complete` を返す。いつものクイズは今までどおり出し続ける（TC-05・TC-06） |
| V4 | 2 | 実験必須 | #446 の 9 ケースの xfail を外しても、他組織・別の利用者の中身が出ない（`ListCheck`）。間違い分析・適応的な問題選択・学習洞察が 200（TC-10・TC-11・TC-14） |
| V5 | 2 | 読んで可 | 回答とカードの更新が 1 つのトランザクションで、カードの更新の失敗で回答だけが残らない。同時の回答でカードを 2 回更新しない（4-3・10 章のコードと TC-02） |
| V6 | 1 | 実験必須 | キャッシュのキーに組織が入り、組織を移った直後に前の組織の復習のカード・習熟度が返らない（TC-12） |

## 計画変更記録
（なし）

## レビュー結果
（plan-review 段階が追記する）
