# I431 自動テスト: 学習記録 API・ダッシュボード API の組織の境界

- 関連: docs/issues/open/I431.md / docs/plans/open/plan_I431.md / GitHub #431 / Draft PR #453
- 対象: `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`（新規）
- 実行コマンド（例）: `docker compose exec -T backend python -m pytest studylogs/tests/test_I431_studylogs_tenant_isolation.py -q`（app-1 ワークツリーのコンテナ）。全テストは CI（PR #453）が正。

結果:
- backend:
- frontend: 対象外（変更なし）

## fixture 方針
I166 のテスト（`backend/problems/tests/test_I166_quiz_tenant_isolation.py`）に倣う。乱数に頼らないよう、自組織の候補は 1 件・他組織は 2 件にし、集合で比べる。

```python
@pytest.fixture(autouse=True)
def _clear_caches():
    """Redis があるときに、利用者 ID が同じ別テストの cache を拾わない"""
    for alias in settings.CACHES:
        caches[alias].clear()
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


def _problem(subject, user, question, is_deleted=False):
    problem = Problem.objects.create(
        subject=subject, organization=subject.organization, created_by=user,
        question=question, problem_type="single", difficulty=1,
        explanation=f"{question}の解説", is_deleted=is_deleted,
    )
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    return problem


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI431", slug="test-cat-i431")
    org_a = Organization.objects.create(name="組織I431A", slug="org-i431-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(name="組織I431B", slug="org-i431-b", type="school", category=cat, is_active=True)
    user_a = User.objects.create_user(email="a_i431@example.com", user_id="a_i431", password="pass", organization=org_a, role="user")
    user_b = User.objects.create_user(email="b_i431@example.com", user_id="b_i431", password="pass", organization=org_b, role="user")
    user_noorg = User.objects.create_user(email="n_i431@example.com", user_id="n_i431", password="pass", organization=None, role="user")
    subject_a = Subject.objects.create(name="科目I431A", slug="subj-i431-a", organization=org_a)
    subject_b = Subject.objects.create(name="科目I431B", slug="subj-i431-b", organization=org_b)
    subject_shared = Subject.objects.create(name="共有科目I431", slug="subj-i431-shared", organization=None)
    problem_a = _problem(subject_a, user_a, "問題I431A")
    problem_a_deleted = _problem(subject_a, user_a, "問題I431A削除済み", is_deleted=True)
    problems_b = [_problem(subject_b, user_b, f"問題I431B{i}") for i in (1, 2)]
    problem_shared = _problem(subject_shared, user_a, "問題I431共有")
    return {...}  # 上の値をすべて dict で返す
```
- import の置き場所: まだ無いもの（`problems.services.tenant_scope` の関数）は、モジュールの先頭ではなく使うテストの中で import する（TC-22 など）。`_error_records` もメソッドの呼び出しなので、無ければそのテストだけが失敗する。修正前にファイル全体が import の失敗で ERROR にならず、TC ごとに RED の根拠が取れるようにする（計画レビューの Warning）。
- 共通: `STUDY = "/api/study/"`・`DASH = "/api/dashboard/"`。「存在しない ID」は `Model.objects.order_by("-id").first().id + 1000`。
- `_masked(response, pk)`: `json.dumps(response.json(), ensure_ascii=False).replace(str(pk), "<pk>")`（I166 と同じ）。
- `_items(response)`: 応答が `{"results": [...]}`（ページング）なら `results`、配列ならそのまま。
- `_card(user, problem, due=True)`: `SpacedRepetitionCard.objects.create(user=user, problem=problem, next_review_date=timezone.now() - timedelta(days=1) if due else timezone.now() + timedelta(days=7))`
- `_review(card)`: `SpacedRepetitionReview.objects.create(card=card, user=card.user, problem=card.problem, quality_score=4, response_time_seconds=10, is_correct=True, previous_ease_factor=2.5, previous_interval=1, previous_repetition_count=0, new_ease_factor=2.5, new_interval=1, new_repetition_count=1, next_review_date=timezone.now())`
- `_attempt(user, problem, is_correct)`: `ProblemAttempt.objects.create(user=user, problem=problem, is_correct=is_correct)`
- 「他組織の文言」: `"問題I431B"`（問題文・解説の先頭）と `"科目I431B"`（科目名）。`OTHER_TEXTS = ("問題I431B", "科目I431B")`。応答の本文（`response.content.decode()`）にどちらも含まれないことを `_no_other(response)` で見る。

## テストケース（Backend）

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-01 | 他組織・存在しない・削除済み・全体共有科目の問題でのカード作成は同じ 404・カードを作らない（本バグの再発防止・AC1） | `user_a` で `POST STUDY+"spaced-repetition/create_card/"`・`{"problem_id": problems_b[0].id}`・`format="json"`。続けて存在しない ID・`problem_a_deleted.id`・`problem_shared.id` で同じ POST | 4 つとも `status.HTTP_404_NOT_FOUND`・`response.json() == {"error": "問題が見つかりません"}`。`SpacedRepetitionCard.objects.filter(user=user_a).count() == 0`。`_no_other(response)`（他組織の問題文・解説が無い） | Claude |
| TC-02 | 自組織の問題でのカード作成は従来どおり（無退行） | `user_a` で `{"problem_id": problem_a.id}` で POST | `status.HTTP_201_CREATED`・`response.json()["card"]["problem"]["id"] == problem_a.id`・`response.json()["message"] == "カードを作成しました"`。`SpacedRepetitionCard.objects.filter(user=user_a, problem=problem_a).count() == 1` | Claude |
| TC-03 | 既にある他組織の問題のカードは、カードの一覧・詳細・復習対象に出ない（AC5） | `card_a = _card(user_a, problem_a)`・`card_b = _card(user_a, problems_b[0])` を DB に作る。`user_a` で `GET STUDY+"sr-cards/"`・`GET STUDY+f"sr-cards/{card_b.id}/"`・`GET STUDY+f"sr-cards/{<存在しない ID>}/"`・`GET STUDY+f"sr-cards/?subject_id={subject_b.id}"`・`GET STUDY+"spaced-repetition/due_cards/"` | 一覧は 200・`{c["id"] for c in _items(r)} == {card_a.id}`（自組織は出る）・`_no_other(r)`。詳細は 2 つとも 404・`_masked` が一致。`subject_id` の絞り込みは 200・`_items(r) == []`。`due_cards` は 200・`[c["id"] for c in r.json()["cards"]] == [card_a.id]`・`r.json()["count"] == 1`・`_no_other(r)` | Claude |
| TC-04 | 他組織の問題のカードへの復習の提出は、存在しないカードと同じ 404・復習の記録を作らない | `card_b = _card(user_a, problems_b[0])`。`user_a` で `POST STUDY+"spaced-repetition/submit_review/"`・`{"card_id": card_b.id, "quality_score": 4, "response_time_seconds": 10}`。続けて存在しない ID で同じ POST | どちらも 404・`response.json() == {"error": "カードが見つかりません"}`。`SpacedRepetitionReview.objects.count() == 0`。`card_b` を読み直して `total_reviews == 0` | Claude |
| TC-04b | 復習に紐づける進行中の学習記録は、他組織の科目のものを使わない（R15） | `card_a = _card(user_a, problem_a)`・`StudyLog.objects.create(user=user_a, subject=subject_b, is_active=True)`。`user_a` で `{"card_id": card_a.id, "quality_score": 4, "response_time_seconds": 10}` を POST | 応答のステータスは見ない（復習の記録の後の `update_daily_analytics` が difficulty の型で例外になり 400 になるため・I452）。`SpacedRepetitionReview.objects.get(card=card_a).study_session_id is None` | Claude |
| TC-05 | 既にある他組織の問題の復習の記録は、一覧・詳細に出ない | `review_a = _review(_card(user_a, problem_a))`・`review_b = _review(_card(user_a, problems_b[0]))`。`user_a` で `GET STUDY+"sr-reviews/"`・`GET STUDY+f"sr-reviews/{review_b.id}/"`・存在しない ID の詳細 | 一覧は 200・`{r["id"] for r in _items(resp)} == {review_a.id}`・`_no_other(resp)`。詳細は 2 つとも 404・`_masked` が一致 | Claude |
| TC-06 | 新しく学ぶ問題の候補は自組織の未削除の問題だけ（`get_new_cards`・C3） | `SpacedRepetitionService(user_a).get_new_cards(limit=50)` | `{p.id for p in result} == {problem_a.id}`（他組織 2 件・削除済み・全体共有科目を含まない）。現行コードは `is_active` の FieldError で RED | Claude |
| TC-07 | 候補はカードがある問題を除き、組織に属さない利用者は空 | `_card(user_a, problem_a)` を作ってから `SpacedRepetitionService(user_a).get_new_cards(limit=50)`。`SpacedRepetitionService(user_noorg).get_new_cards(limit=50)` | どちらも `list(result) == []` | Claude |
| TC-08 | 適応的な問題選択の候補は自組織の未削除の問題だけ（R13・AC2） | `AdaptiveProblemSelector(user_a)._get_problem_pool(None)` と `._get_problem_pool(subject_a)` | どちらも `{p.id for p in result} == {problem_a.id}`。現行コードは `is_active` の FieldError で RED | Claude |
| TC-09 | 科目別の習熟度は自組織の科目だけ（R12・AC2） | `_attempt(user_a, problem_a, True)`・`_attempt(user_a, problems_b[0], False)`。`AdaptiveProblemSelector(user_a)._calculate_subject_proficiency(ProblemAttempt.objects.filter(user=user_a), SpacedRepetitionReview.objects.filter(user=user_a))` | `set(result.keys()) == {subject_a.id}` | Claude |
| TC-10 | 適応的学習の API は他組織の科目を存在しない科目と同じ 404 で断り、科目なしでも他組織の問題・科目を返さない（AC2） | `user_a` で `POST STUDY+"adaptive-learning/select_problems/"`・`{"subject_id": subject_b.id}` と `{"subject_id": <存在しない ID>}`。`GET STUDY+f"adaptive-learning/proficiency_analysis/?subject_id={subject_b.id}"` と存在しない ID。最後に `_attempt(user_a, problems_b[0], False)` を作ってから `POST .../select_problems/`・`{}` | 科目の指定ありの 4 つは 404・`response.json() == {"error": "科目が見つかりません"}`。科目なしの応答は `_no_other(response)`（difficulty の型の不具合で今はエラー。ステータスは見ない＝I452 で直っても同じ判定が通る） | Claude |
| TC-11 | 間違いの分析の土台は自組織の問題の記録だけ（C4） | `_attempt(user_a, problem_a, False)`・`_attempt(user_a, problems_b[0], False)`・`_review` を自組織と他組織のカードに 1 件ずつ作り、どちらも `is_correct=False` にする。`MistakeAnalysisService(user_a)._error_records(timezone.now() - timedelta(days=30), timezone.now() + timedelta(minutes=1))` | 返る 2 つの queryset（復習・試行）とも、`{x.problem_id for x in qs} == {problem_a.id}` | Claude |
| TC-12 | 他組織・存在しない・全体共有科目での学習記録の作成は同じ 400・作らない／自組織と科目なしは作れる（C2・本バグの再発防止） | `user_a` で `POST STUDY+"logs/"`・`{"subject": subject_b.id}`・存在しない ID・`subject_shared.id`。続けて `{"subject": subject_a.id}` と `{}` | 他組織と存在しないものは 400・`_masked` が一致・`_no_other`。全体共有科目も 400。この 3 つの後、`StudyLog.objects.filter(user=user_a).count() == 0`。自組織は 201・`response.json()["subject"] == subject_a.id`・`["subject_name"] == "科目I431A"`。科目なしは 201・`["subject"] is None` | Claude |
| TC-13 | 既にある他組織の科目の学習記録は、一覧・詳細に出ない／科目なしの記録は出る（R1） | `log_a = StudyLog.objects.create(user=user_a, subject=subject_a)`・`log_b = ...(subject=subject_b)`・`log_none = ...(subject=None)`。`user_a` で `GET STUDY+"logs/"`・`GET STUDY+f"logs/{log_b.id}/"`・存在しない ID の詳細・`POST STUDY+f"logs/{log_b.id}/end/"` | 一覧は 200・`{l["id"] for l in _items(r)} == {log_a.id, log_none.id}`・`_no_other(r)`。詳細は 2 つとも 404・`_masked` が一致。`end` は 404 で `log_b` は `is_active` のまま | Claude |
| TC-14 | 自分の学習記録の科目を他組織の科目に変えられない（C2） | `log_a` を作る。`user_a` で `PATCH STUDY+f"logs/{log_a.id}/"`・`{"subject": subject_b.id}` と `{"subject": <存在しない ID>}` | どちらも 400・`_masked` が一致。`log_a` を読み直して `subject_id == subject_a.id` | Claude |
| TC-15 | 統計の科目別・最近の記録・日次の科目に、他組織の科目が出ない（R2〜R4） | `UserSubjectAccess` を `user_a` に `subject_a` と `subject_b` で作る（組織を移った利用者の古い登録の再現）。`StudyLog` を `subject_a`（`problems_attempted=4, problems_correct=3`）と `subject_b`（同じ値）で作る。`DailyStudySummary(user=user_a, date=今日)` を作り `subjects_studied.add(subject_a, subject_b)`。`user_a` で `GET STUDY+"statistics/overview/"`・`.../by_subject/`・`.../daily_summary/` | 3 つとも 200・`_no_other`。`by_subject` は `[s["subject_id"] for s in r.json()] == [subject_a.id]`。`overview` の `recent_activity` の `subject` の集合が `{subject_a.id}`・`best_subject["subject_id"] == subject_a.id`。`daily_summary` の 1 件目の `subjects_studied == ["科目I431A"]`（`Subject.__str__` は名前・`backend/problems/models.py:73-74`） | Claude |
| TC-16 | 間違い分析の一覧・まとめ・弱点の更新・提案の生成に、他組織の科目が出ない／作られない（R9〜R11・C5・C6） | DB に `user_a` の `MistakePattern`（`subject_a`・`subject_b` は `pattern_type="subject_difficulty"`、科目なしは `pattern_type="time_pressure"` の 3 件・どれも `confidence_score=0.5`・`description` は任意の文言）・`LearningWeakness`（`subject_a`・`subject_b`・`severity="high"`）・`LearningSuggestion`（`subject_a`・`subject_b`・科目なし）を作る。`user_a` で `GET STUDY+"mistake-analysis/patterns/"`・`suggestions/`・`weaknesses/`。続けて `MistakeAnalysisService(user_a).get_analysis_summary()`。次に `LearningSuggestion` を全部消し、`generate_learning_suggestions()` を呼ぶ。最後に `_attempt(user_a, problem_a, False)` と `_attempt(user_a, problems_b[0], False)` を 5 件ずつ作り、`LearningWeakness` を全部消してから `update_learning_weaknesses(timezone.now() - timedelta(days=30), timezone.now() + timedelta(minutes=1))` を呼ぶ | 3 つの API は 200・`_no_other`。`patterns` の `subject` の集合が `{subject_a.id, None}`・`suggestions` も `{subject_a.id, None}`・`weaknesses` は `{subject_a.id}`。まとめの `patterns`・`weaknesses`・`suggestions` の科目も同じ（`suggestions` は未読のものだけ）。提案の生成の後 `LearningSuggestion.objects.filter(user=user_a, subject=subject_b).exists() is False` かつ `subject_a` の提案が 1 件以上。弱点の更新の後 `set(LearningWeakness.objects.filter(user=user_a).values_list("subject_id", flat=True)) == {subject_a.id}` | Claude |
| TC-17 | ダッシュボードの概要に、他組織の科目が出ない（D1〜D3） | `QuizSession` を `user_a` に `subject_a` と `subject_b` で 1 件ずつ作る（`is_active=False`）。`StudyLog(user=user_a, subject=subject_b, is_active=True)` を作る。`UserSubjectAccess` を `subject_a`・`subject_b` で作り、`StudyLog(user=user_a, subject=subject_a, is_active=False, problems_attempted=2, problems_correct=1)` を作る。`user_a` で `GET DASH+"dashboard/overview/"` | 200・`_no_other`。`recent_quizzes` の `subject` の集合が `{"科目I431A"}`。`active_session is None`。`subject_progress` の `subject_name` の集合が `{"科目I431A"}` | Claude |
| TC-18 | ダッシュボードの分析の科目の内訳に、他組織の科目が出ない（D4） | `StudyLog` を `subject_a`・`subject_b`・科目なしで 1 件ずつ作る（`duration=60`）。`user_a` で `GET DASH+"dashboard/analytics/"` | 200・`_no_other`。`{d["subject__name"] for d in r.json()["subject_distribution"]} == {"科目I431A", None}` | Claude |
| TC-19 | おすすめに他組織の科目が出ず、問題数は自組織の未削除の問題だけを数える（D5・D6） | `StudyLog` を `subject_a` と `subject_b` で作る（どちらも `problems_attempted=10, problems_correct=1`・今日）。`user_a` で `GET DASH+"dashboard/recommendations/"` | 200・`_no_other`。`recommendations` の `subject_id` の集合が `{str(subject_a.id)}`・その `recommended_problems == 1`（自組織の未削除 1 件。削除済みを数えない）。現行コードは `is_active` の FieldError で RED | Claude |
| TC-20 | 習熟度の非同期処理は、他組織の科目を存在しない科目と同じに扱う（R14） | `update_user_proficiency_task.apply(args=[user_a.id, subject_b.id]).result` と `[user_a.id, <存在しない ID>]` | 2 つの結果が等しく、どちらも `{"error": "Subject matching query does not exist."}` | Claude |
| TC-21 | 組織に属さない利用者は、問題・科目を扱えず、科目なしの記録だけ読める（fail-closed） | `user_noorg` で `POST .../create_card/`・`{"problem_id": problem_a.id}`。`POST STUDY+"logs/"`・`{"subject": subject_a.id}`。`StudyLog(user=user_noorg, subject=None)` と `(subject=subject_a)` を作り `GET STUDY+"logs/"` | カード作成は 404・`{"error": "問題が見つかりません"}`。学習記録の作成は 400。一覧は科目なしの 1 件だけ | Claude |
| TC-22 | 境界の判定の関数（tenant_scope）の単体 | `available_subjects(user_a)`・`available_problems(user_a)`・`available_problems(user_a, subject_a)`・`available_problems(user_noorg)`・`scope_to_user_org(StudyLog.objects.all(), user_a, subject_path="subject", allow_null=True)`（`subject_a`・`subject_b`・科目なしの記録を作っておく）と `allow_null=False`・`user_noorg` で `allow_null=True` | 科目は `{subject_a.id}`（全体共有科目を含まない）。問題は 2 つとも `{problem_a.id}`。`user_noorg` は空。`allow_null=True` は `subject_a` と科目なし、`False` は `subject_a` だけ、`user_noorg` は科目なしだけ | Claude |
| TC-23 | 新しいテストが今のコードで RED になる（false-green でない） | 実装ステップ 1 で、修正前のコードに対して `docker compose exec -T backend python -m pytest studylogs/tests/test_I431_studylogs_tenant_isolation.py -q` | TC-01・TC-03〜TC-06・TC-08・TC-09・TC-11〜TC-20・TC-22 ・TC-04b が FAIL（TC-11・TC-22 は `_error_records`・`tenant_scope` が無いことによる失敗。ファイル全体の ERROR にはならない）。TC-02・TC-07・TC-10 の科目の指定ありは、今も通りうる（無退行・既に安全な経路の固定）。結果を review の「テスト結果」に書く | Claude |
| TC-24 | 修正後に新しいテストと I166 のテストが通る | `docker compose exec -T backend python -m pytest studylogs/tests/test_I431_studylogs_tenant_isolation.py problems/tests/test_I166_quiz_tenant_isolation.py -q` | すべて pass（I166 は QuizService の委ねる形への変更の無退行） | Claude |
| TC-25 | pre-commit（ruff・bandit を含む）が通る | `pre-commit run --files <変更したファイル>`（commit のときに自動で走る） | すべて Passed。bandit は MEDIUM 以上 0 件 | Claude |
