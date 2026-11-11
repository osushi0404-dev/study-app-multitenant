"""
I431: 学習記録 API（/api/study/）とダッシュボード API（/api/dashboard/）で組織の境界を守る。

- 他組織の問題・科目を指す記録を作る・変える入力は、存在しない ID と同じ応答で断る
- 他組織の科目・問題を指す記録（既にあるものを含む）は、読み出しに出さない
- 組織に属さないユーザーは問題・科目を扱えない（fail-closed）

TC-01〜TC-22（docs/tests/open/I431_auto_test.md）に対応。
まだ無い関数（tenant_scope）は、修正前に TC ごとの RED を取るため、使うテストの中で import する。
"""
import json
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import Choice, Problem, QuizSession, Subject, UserSubjectAccess
from studylogs.adaptive_selection import AdaptiveProblemSelector
from studylogs.mistake_analysis import MistakeAnalysisService
from studylogs.models import (
    DailyStudySummary, LearningSuggestion, LearningWeakness, MistakePattern,
    ProblemAttempt, SpacedRepetitionCard, SpacedRepetitionReview, StudyLog,
)
from studylogs.services import SpacedRepetitionService
from studylogs.tasks import update_user_proficiency_task

User = get_user_model()

STUDY = "/api/study/"
DASH = "/api/dashboard/"
OTHER_TEXTS = ("問題I431B", "科目I431B")


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
    org_a = Organization.objects.create(
        name="組織I431A", slug="org-i431-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織I431B", slug="org-i431-b", type="school", category=cat, is_active=True)
    user_a = User.objects.create_user(
        email="a_i431@example.com", user_id="a_i431", password="pass",
        organization=org_a, role="user",
    )
    user_b = User.objects.create_user(
        email="b_i431@example.com", user_id="b_i431", password="pass",
        organization=org_b, role="user",
    )
    user_noorg = User.objects.create_user(
        email="n_i431@example.com", user_id="n_i431", password="pass",
        organization=None, role="user",
    )
    subject_a = Subject.objects.create(name="科目I431A", slug="subj-i431-a", organization=org_a)
    subject_b = Subject.objects.create(name="科目I431B", slug="subj-i431-b", organization=org_b)
    subject_shared = Subject.objects.create(
        name="共有科目I431", slug="subj-i431-shared", organization=None)
    problem_a = _problem(subject_a, user_a, "問題I431A")
    problem_a_deleted = _problem(subject_a, user_a, "問題I431A削除済み", is_deleted=True)
    problems_b = [_problem(subject_b, user_b, f"問題I431B{i}") for i in (1, 2)]
    problem_shared = _problem(subject_shared, user_a, "問題I431共有")
    return {
        "user_a": user_a, "user_b": user_b, "user_noorg": user_noorg,
        "subject_a": subject_a, "subject_b": subject_b, "subject_shared": subject_shared,
        "problem_a": problem_a, "problem_a_deleted": problem_a_deleted,
        "problems_b": problems_b, "problem_shared": problem_shared,
    }


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _missing_id(model):
    return model.objects.order_by("-id").first().id + 1000


def _masked(response, pk):
    """応答本文の ID 部分を伏せた文字列（他組織と存在しない ID の応答を比べるため）"""
    return json.dumps(response.json(), ensure_ascii=False).replace(str(pk), "<pk>")


def _items(response):
    data = response.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data


def _no_other(response):
    try:
        text = json.dumps(response.json(), ensure_ascii=False)
    except ValueError:
        text = response.content.decode()
    return all(other not in text for other in OTHER_TEXTS)


def _card(user, problem, due=True):
    delta = timedelta(days=-1) if due else timedelta(days=7)
    return SpacedRepetitionCard.objects.create(
        user=user, problem=problem, next_review_date=timezone.now() + delta)


def _review(card, is_correct=True):
    return SpacedRepetitionReview.objects.create(
        card=card, user=card.user, problem=card.problem, quality_score=4 if is_correct else 1,
        response_time_seconds=10, is_correct=is_correct,
        previous_ease_factor=2.5, previous_interval=1, previous_repetition_count=0,
        new_ease_factor=2.5, new_interval=1, new_repetition_count=1,
        next_review_date=timezone.now(),
    )


def _attempt(user, problem, is_correct):
    return ProblemAttempt.objects.create(user=user, problem=problem, is_correct=is_correct)


def _window():
    return timezone.now() - timedelta(days=30), timezone.now() + timedelta(minutes=1)


# ---- TC-01: 他組織・存在しない・削除済み・全体共有科目の問題でのカード作成は同じ 404 ----
def test_create_card_rejects_other_org_like_missing(setup):
    client = _client(setup["user_a"])
    url = STUDY + "spaced-repetition/create_card/"
    for problem_id in (
        setup["problems_b"][0].id, _missing_id(Problem),
        setup["problem_a_deleted"].id, setup["problem_shared"].id,
    ):
        response = client.post(url, {"problem_id": problem_id}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"error": "問題が見つかりません"}
        assert _no_other(response)
    assert SpacedRepetitionCard.objects.filter(user=setup["user_a"]).count() == 0


# ---- TC-02: 自組織の問題でのカード作成は従来どおり ----
def test_create_card_with_own_problem_succeeds(setup):
    response = _client(setup["user_a"]).post(
        STUDY + "spaced-repetition/create_card/",
        {"problem_id": setup["problem_a"].id}, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["card"]["problem"]["id"] == setup["problem_a"].id
    assert response.json()["message"] == "カードを作成しました"
    assert SpacedRepetitionCard.objects.filter(
        user=setup["user_a"], problem=setup["problem_a"]).count() == 1


# ---- TC-03: 既にある他組織の問題のカードは一覧・詳細・復習対象に出ない ----
def test_existing_other_org_cards_are_hidden(setup):
    card_a = _card(setup["user_a"], setup["problem_a"])
    card_b = _card(setup["user_a"], setup["problems_b"][0])
    client = _client(setup["user_a"])

    listed = client.get(STUDY + "sr-cards/")
    assert listed.status_code == status.HTTP_200_OK
    assert {c["id"] for c in _items(listed)} == {card_a.id}
    assert _no_other(listed)

    missing_id = _missing_id(SpacedRepetitionCard)
    other = client.get(STUDY + f"sr-cards/{card_b.id}/")
    missing = client.get(STUDY + f"sr-cards/{missing_id}/")
    assert other.status_code == status.HTTP_404_NOT_FOUND
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert _masked(other, card_b.id) == _masked(missing, missing_id)

    by_subject = client.get(STUDY + f"sr-cards/?subject_id={setup['subject_b'].id}")
    assert by_subject.status_code == status.HTTP_200_OK
    assert _items(by_subject) == []

    due = client.get(STUDY + "spaced-repetition/due_cards/")
    assert due.status_code == status.HTTP_200_OK
    assert [c["id"] for c in due.json()["cards"]] == [card_a.id]
    assert due.json()["count"] == 1
    assert _no_other(due)


# ---- TC-04: 他組織の問題のカードへの復習の提出は存在しないカードと同じ 404 ----
def test_submit_review_rejects_other_org_card_like_missing(setup):
    card_b = _card(setup["user_a"], setup["problems_b"][0])
    client = _client(setup["user_a"])
    url = STUDY + "spaced-repetition/submit_review/"
    for card_id in (card_b.id, _missing_id(SpacedRepetitionCard)):
        response = client.post(
            url, {"card_id": card_id, "quality_score": 4, "response_time_seconds": 10},
            format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"error": "カードが見つかりません"}
    assert SpacedRepetitionReview.objects.count() == 0
    card_b.refresh_from_db()
    assert card_b.total_reviews == 0


# ---- TC-04b: 復習に紐づける進行中の学習記録は他組織の科目のものを使わない ----
def test_submit_review_does_not_link_other_org_study_log(setup):
    card_a = _card(setup["user_a"], setup["problem_a"])
    StudyLog.objects.create(user=setup["user_a"], subject=setup["subject_b"], is_active=True)

    # 復習の後の update_daily_analytics が difficulty の型で例外になり 400 になりうる（I452）ため、
    # ステータスは見ない
    _client(setup["user_a"]).post(
        STUDY + "spaced-repetition/submit_review/",
        {"card_id": card_a.id, "quality_score": 4, "response_time_seconds": 10},
        format="json")

    assert SpacedRepetitionReview.objects.get(card=card_a).study_session_id is None


# ---- TC-05: 既にある他組織の問題の復習の記録は一覧・詳細に出ない ----
def test_existing_other_org_reviews_are_hidden(setup):
    review_a = _review(_card(setup["user_a"], setup["problem_a"]))
    review_b = _review(_card(setup["user_a"], setup["problems_b"][0]))
    client = _client(setup["user_a"])

    listed = client.get(STUDY + "sr-reviews/")
    assert listed.status_code == status.HTTP_200_OK
    assert {r["id"] for r in _items(listed)} == {review_a.id}
    assert _no_other(listed)

    missing_id = _missing_id(SpacedRepetitionReview)
    other = client.get(STUDY + f"sr-reviews/{review_b.id}/")
    missing = client.get(STUDY + f"sr-reviews/{missing_id}/")
    assert other.status_code == status.HTTP_404_NOT_FOUND
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert _masked(other, review_b.id) == _masked(missing, missing_id)


# ---- TC-06: 新しく学ぶ問題の候補は自組織の未削除の問題だけ ----
def test_new_cards_are_own_org_problems_only(setup):
    result = SpacedRepetitionService(setup["user_a"]).get_new_cards(limit=50)

    assert {p.id for p in result} == {setup["problem_a"].id}


# ---- TC-07: 候補はカードがある問題を除き、組織に属さない利用者は空 ----
def test_new_cards_exclude_existing_and_noorg_is_empty(setup):
    _card(setup["user_a"], setup["problem_a"])

    assert list(SpacedRepetitionService(setup["user_a"]).get_new_cards(limit=50)) == []
    assert list(SpacedRepetitionService(setup["user_noorg"]).get_new_cards(limit=50)) == []


# ---- TC-08: 適応的な問題選択の候補は自組織の未削除の問題だけ ----
def test_adaptive_problem_pool_is_own_org_only(setup):
    selector = AdaptiveProblemSelector(setup["user_a"])

    assert {p.id for p in selector._get_problem_pool(None)} == {setup["problem_a"].id}
    assert {p.id for p in selector._get_problem_pool(setup["subject_a"])} == {setup["problem_a"].id}


# ---- TC-09: 科目別の習熟度は自組織の科目だけ ----
def test_subject_proficiency_is_own_org_only(setup):
    user = setup["user_a"]
    _attempt(user, setup["problem_a"], True)
    _attempt(user, setup["problems_b"][0], False)

    result = AdaptiveProblemSelector(user)._calculate_subject_proficiency(
        ProblemAttempt.objects.filter(user=user), SpacedRepetitionReview.objects.filter(user=user))

    assert set(result.keys()) == {setup["subject_a"].id}


# ---- TC-10: 適応的学習の API は他組織の科目を存在しない科目と同じ 404 で断り、他組織を返さない ----
def test_adaptive_api_rejects_other_org_subject_and_leaks_nothing(setup):
    client = _client(setup["user_a"])
    for subject_id in (setup["subject_b"].id, _missing_id(Subject)):
        selected = client.post(
            STUDY + "adaptive-learning/select_problems/", {"subject_id": subject_id}, format="json")
        assert selected.status_code == status.HTTP_404_NOT_FOUND
        assert selected.json() == {"error": "科目が見つかりません"}
        analysis = client.get(
            STUDY + f"adaptive-learning/proficiency_analysis/?subject_id={subject_id}")
        assert analysis.status_code == status.HTTP_404_NOT_FOUND
        assert analysis.json() == {"error": "科目が見つかりません"}

    _attempt(setup["user_a"], setup["problems_b"][0], False)
    no_subject = client.post(STUDY + "adaptive-learning/select_problems/", {}, format="json")
    # difficulty の型の不具合で今はエラー。ステータスは見ない（I452 で直っても同じ判定が通る）
    assert _no_other(no_subject)


# ---- TC-11: 間違いの分析の土台は自組織の問題の記録だけ ----
def test_mistake_error_records_are_own_org_only(setup):
    user = setup["user_a"]
    _attempt(user, setup["problem_a"], False)
    _attempt(user, setup["problems_b"][0], False)
    _review(_card(user, setup["problem_a"]), is_correct=False)
    _review(_card(user, setup["problems_b"][0]), is_correct=False)

    sr_errors, attempt_errors = MistakeAnalysisService(user)._error_records(*_window())

    assert {x.problem_id for x in sr_errors} == {setup["problem_a"].id}
    assert {x.problem_id for x in attempt_errors} == {setup["problem_a"].id}


# ---- TC-12: 学習記録の作成は他組織・存在しない・全体共有科目を同じ 400 で断る ----
def test_study_log_create_rejects_other_org_subject_like_missing(setup):
    client = _client(setup["user_a"])
    url = STUDY + "logs/"
    missing_id = _missing_id(Subject)

    other = client.post(url, {"subject": setup["subject_b"].id}, format="json")
    missing = client.post(url, {"subject": missing_id}, format="json")
    shared = client.post(url, {"subject": setup["subject_shared"].id}, format="json")

    assert other.status_code == status.HTTP_400_BAD_REQUEST
    assert missing.status_code == status.HTTP_400_BAD_REQUEST
    assert shared.status_code == status.HTTP_400_BAD_REQUEST
    assert _masked(other, setup["subject_b"].id) == _masked(missing, missing_id)
    assert _no_other(other)
    assert StudyLog.objects.filter(user=setup["user_a"]).count() == 0

    own = client.post(url, {"subject": setup["subject_a"].id}, format="json")
    assert own.status_code == status.HTTP_201_CREATED
    assert own.json()["subject"] == setup["subject_a"].id
    assert own.json()["subject_name"] == "科目I431A"

    none = client.post(url, {}, format="json")
    assert none.status_code == status.HTTP_201_CREATED
    assert none.json()["subject"] is None


# ---- TC-13: 既にある他組織の科目の学習記録は一覧・詳細に出ない／科目なしは出る ----
def test_existing_other_org_study_logs_are_hidden(setup):
    user = setup["user_a"]
    log_a = StudyLog.objects.create(user=user, subject=setup["subject_a"], is_active=False)
    log_b = StudyLog.objects.create(user=user, subject=setup["subject_b"], is_active=True)
    log_none = StudyLog.objects.create(user=user, subject=None, is_active=False)
    client = _client(user)

    listed = client.get(STUDY + "logs/")
    assert listed.status_code == status.HTTP_200_OK
    assert {log["id"] for log in _items(listed)} == {log_a.id, log_none.id}
    assert _no_other(listed)

    missing_id = _missing_id(StudyLog)
    other = client.get(STUDY + f"logs/{log_b.id}/")
    missing = client.get(STUDY + f"logs/{missing_id}/")
    assert other.status_code == status.HTTP_404_NOT_FOUND
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert _masked(other, log_b.id) == _masked(missing, missing_id)

    ended = client.post(STUDY + f"logs/{log_b.id}/end/", {}, format="json")
    assert ended.status_code == status.HTTP_404_NOT_FOUND
    log_b.refresh_from_db()
    assert log_b.is_active is True


# ---- TC-14: 自分の学習記録の科目を他組織の科目に変えられない ----
def test_study_log_update_rejects_other_org_subject(setup):
    log_a = StudyLog.objects.create(user=setup["user_a"], subject=setup["subject_a"])
    client = _client(setup["user_a"])
    url = STUDY + f"logs/{log_a.id}/"
    missing_id = _missing_id(Subject)

    other = client.patch(url, {"subject": setup["subject_b"].id}, format="json")
    missing = client.patch(url, {"subject": missing_id}, format="json")

    assert other.status_code == status.HTTP_400_BAD_REQUEST
    assert missing.status_code == status.HTTP_400_BAD_REQUEST
    assert _masked(other, setup["subject_b"].id) == _masked(missing, missing_id)
    log_a.refresh_from_db()
    assert log_a.subject_id == setup["subject_a"].id


# ---- TC-15: 統計の科目別・最近の記録・日次の科目に他組織の科目が出ない ----
def test_statistics_hide_other_org_subjects(setup):
    user = setup["user_a"]
    UserSubjectAccess.objects.create(user=user, subject=setup["subject_a"])
    UserSubjectAccess.objects.create(user=user, subject=setup["subject_b"])
    StudyLog.objects.create(
        user=user, subject=setup["subject_a"], problems_attempted=4, problems_correct=3)
    StudyLog.objects.create(
        user=user, subject=setup["subject_b"], problems_attempted=4, problems_correct=3)
    summary = DailyStudySummary.objects.create(user=user, date=timezone.now().date())
    summary.subjects_studied.add(setup["subject_a"], setup["subject_b"])
    client = _client(user)

    overview = client.get(STUDY + "statistics/overview/")
    by_subject = client.get(STUDY + "statistics/by_subject/")
    daily = client.get(STUDY + "statistics/daily_summary/")

    for response in (overview, by_subject, daily):
        assert response.status_code == status.HTTP_200_OK
        assert _no_other(response)
    assert [s["subject_id"] for s in by_subject.json()] == [setup["subject_a"].id]
    assert {log["subject"] for log in overview.json()["recent_activity"]} == {setup["subject_a"].id}
    assert overview.json()["best_subject"]["subject_id"] == setup["subject_a"].id
    assert daily.json()[0]["subjects_studied"] == ["科目I431A"]


# ---- TC-15b: 科目のプルダウンの API に登録時の他組織の科目が出ない ----
def test_user_subjects_api_hides_other_org_subjects(setup):
    UserSubjectAccess.objects.create(user=setup["user_a"], subject=setup["subject_a"])
    UserSubjectAccess.objects.create(user=setup["user_a"], subject=setup["subject_b"])
    UserSubjectAccess.objects.create(user=setup["user_noorg"], subject=setup["subject_a"])

    own = _client(setup["user_a"]).get("/api/user/subjects/")
    noorg = _client(setup["user_noorg"]).get("/api/user/subjects/")

    assert own.status_code == status.HTTP_200_OK
    assert own.json() == [{"id": setup["subject_a"].id, "name": "科目I431A"}]
    assert noorg.status_code == status.HTTP_200_OK
    assert noorg.json() == []


# ---- TC-16: 間違い分析の一覧・まとめ・提案の生成・弱点の更新に他組織の科目が出ない ----
def test_mistake_analysis_hides_and_does_not_create_other_org(setup):
    user = setup["user_a"]
    pattern_a = MistakePattern.objects.create(
        user=user, pattern_type="subject_difficulty", subject=setup["subject_a"],
        description="自組織のパターン", confidence_score=0.5)
    pattern_b = MistakePattern.objects.create(
        user=user, pattern_type="subject_difficulty", subject=setup["subject_b"],
        description="科目I431Bのパターン", confidence_score=0.5)
    # 科目が空のパターンは、提案の生成（_generate_pattern_based_suggestions が全種類の文言を
    # pattern.subject.name で先に組み立てる既存の不具合・I452）に当たらないよう、生成の対象の
    # しきい値（confidence_score >= 0.3）より下にする。一覧には出る
    MistakePattern.objects.create(
        user=user, pattern_type="time_pressure", subject=None,
        description="時間のパターン", confidence_score=0.1)
    LearningWeakness.objects.create(
        user=user, subject=setup["subject_a"], concept_name="自組織の概念", severity="high")
    LearningWeakness.objects.create(
        user=user, subject=setup["subject_b"], concept_name="科目I431Bの概念", severity="high")
    s_a = LearningSuggestion.objects.create(
        user=user, subject=setup["subject_a"], suggestion_type="concept_review",
        title="自組織の提案", description="自組織")
    LearningSuggestion.objects.create(
        user=user, subject=setup["subject_b"], suggestion_type="concept_review",
        title="科目I431Bの提案", description="他組織")
    s_none = LearningSuggestion.objects.create(
        user=user, subject=None, suggestion_type="study_method",
        title="一般の提案", description="一般")
    LearningSuggestion.objects.create(
        user=user, subject=None, mistake_pattern=pattern_b, suggestion_type="concept_review",
        title="パターンだけ他組織の提案", description="パターン経由")
    client = _client(user)

    patterns = client.get(STUDY + "mistake-analysis/patterns/")
    suggestions = client.get(STUDY + "mistake-analysis/suggestions/")
    weaknesses = client.get(STUDY + "mistake-analysis/weaknesses/")
    for response in (patterns, suggestions, weaknesses):
        assert response.status_code == status.HTTP_200_OK
        assert _no_other(response)
    assert {p["subject"] for p in patterns.json()} == {setup["subject_a"].id, None}
    assert {s["id"] for s in suggestions.json()} == {s_a.id, s_none.id}
    assert {w["subject"] for w in weaknesses.json()} == {setup["subject_a"].id}

    service = MistakeAnalysisService(user)
    summary = service.get_analysis_summary()
    assert {p.subject_id for p in summary["patterns"]} == {setup["subject_a"].id, None}
    assert {w.subject_id for w in summary["weaknesses"]} == {setup["subject_a"].id}
    assert {s.id for s in summary["suggestions"]} == {s_a.id, s_none.id}

    LearningSuggestion.objects.all().delete()
    service.generate_learning_suggestions()
    assert not LearningSuggestion.objects.filter(user=user, subject=setup["subject_b"]).exists()
    assert not LearningSuggestion.objects.filter(user=user, mistake_pattern=pattern_b).exists()
    assert LearningSuggestion.objects.filter(user=user, subject=setup["subject_a"]).exists()
    assert LearningSuggestion.objects.filter(user=user, mistake_pattern=pattern_a).exists()

    LearningWeakness.objects.all().delete()
    for _ in range(5):
        _attempt(user, setup["problem_a"], False)
        _attempt(user, setup["problems_b"][0], False)
    service.update_learning_weaknesses(*_window())
    weakness_subjects = set(
        LearningWeakness.objects.filter(user=user).values_list("subject_id", flat=True))
    assert weakness_subjects == {setup["subject_a"].id}


# ---- TC-17: ダッシュボードの概要に他組織の科目が出ない ----
def test_dashboard_overview_hides_other_org_subjects(setup):
    user = setup["user_a"]
    QuizSession.objects.create(user=user, subject=setup["subject_a"], is_active=False)
    QuizSession.objects.create(user=user, subject=setup["subject_b"], is_active=False)
    StudyLog.objects.create(user=user, subject=setup["subject_b"], is_active=True)
    UserSubjectAccess.objects.create(user=user, subject=setup["subject_a"])
    UserSubjectAccess.objects.create(user=user, subject=setup["subject_b"])
    StudyLog.objects.create(
        user=user, subject=setup["subject_a"], is_active=False,
        problems_attempted=2, problems_correct=1)

    response = _client(user).get(DASH + "overview/")

    assert response.status_code == status.HTTP_200_OK
    assert _no_other(response)
    assert {q["subject"] for q in response.json()["recent_quizzes"]} == {"科目I431A"}
    assert response.json()["active_session"] is None
    assert {p["subject_name"] for p in response.json()["subject_progress"]} == {"科目I431A"}


# ---- TC-18: ダッシュボードの分析の科目の内訳に他組織の科目が出ない ----
def test_dashboard_analytics_hides_other_org_subjects(setup):
    user = setup["user_a"]
    for subject in (setup["subject_a"], setup["subject_b"], None):
        StudyLog.objects.create(user=user, subject=subject, duration=60)

    response = _client(user).get(DASH + "analytics/")

    assert response.status_code == status.HTTP_200_OK
    assert _no_other(response)
    distribution = response.json()["subject_distribution"]
    assert {d["subject__name"] for d in distribution} == {"科目I431A", None}


# ---- TC-19: おすすめに他組織の科目が出ず、問題数は自組織の未削除の問題だけ ----
def test_dashboard_recommendations_are_own_org_only(setup):
    user = setup["user_a"]
    for subject in (setup["subject_a"], setup["subject_b"]):
        StudyLog.objects.create(
            user=user, subject=subject, problems_attempted=10, problems_correct=1)

    response = _client(user).get(DASH + "recommendations/")

    assert response.status_code == status.HTTP_200_OK
    assert _no_other(response)
    recommendations = response.json()["recommendations"]
    assert {r["subject_id"] for r in recommendations} == {str(setup["subject_a"].id)}
    assert recommendations[0]["recommended_problems"] == 1


# ---- TC-20: 習熟度の非同期処理は他組織の科目を存在しない科目と同じに扱う ----
def test_proficiency_task_treats_other_org_subject_like_missing(setup):
    user_id = setup["user_a"].id
    other = update_user_proficiency_task.apply(args=[user_id, setup["subject_b"].id]).result
    missing = update_user_proficiency_task.apply(args=[user_id, _missing_id(Subject)]).result

    assert other == missing == {"error": "Subject matching query does not exist."}


# ---- TC-21: 組織に属さない利用者は問題・科目を扱えず、科目なしの記録だけ読める ----
def test_user_without_organization_is_fail_closed(setup):
    user = setup["user_noorg"]
    client = _client(user)

    card = client.post(
        STUDY + "spaced-repetition/create_card/", {"problem_id": setup["problem_a"].id},
        format="json")
    assert card.status_code == status.HTTP_404_NOT_FOUND
    assert card.json() == {"error": "問題が見つかりません"}

    log = client.post(STUDY + "logs/", {"subject": setup["subject_a"].id}, format="json")
    assert log.status_code == status.HTTP_400_BAD_REQUEST

    log_none = StudyLog.objects.create(user=user, subject=None)
    StudyLog.objects.create(user=user, subject=setup["subject_a"])
    listed = client.get(STUDY + "logs/")
    assert [item["id"] for item in _items(listed)] == [log_none.id]


# ---- TC-22: 境界の判定の関数（tenant_scope）の単体 ----
def test_tenant_scope_functions(setup):
    from problems.services.tenant_scope import (
        available_problems, available_subjects, scope_to_user_org,
    )

    user_a, user_noorg = setup["user_a"], setup["user_noorg"]
    assert {s.id for s in available_subjects(user_a)} == {setup["subject_a"].id}
    assert {p.id for p in available_problems(user_a)} == {setup["problem_a"].id}
    assert {p.id for p in available_problems(user_a, setup["subject_a"])} == {setup["problem_a"].id}
    assert list(available_subjects(user_noorg)) == []
    assert list(available_problems(user_noorg)) == []

    log_a = StudyLog.objects.create(user=user_a, subject=setup["subject_a"])
    StudyLog.objects.create(user=user_a, subject=setup["subject_b"])
    log_none = StudyLog.objects.create(user=user_a, subject=None)
    logs = StudyLog.objects.all()
    with_null = scope_to_user_org(logs, user_a, subject_path="subject", allow_null=True)
    without_null = scope_to_user_org(logs, user_a, subject_path="subject")
    noorg = scope_to_user_org(logs, user_noorg, subject_path="subject", allow_null=True)
    assert {log.id for log in with_null} == {log_a.id, log_none.id}
    assert {log.id for log in without_null} == {log_a.id}
    assert {log.id for log in noorg} == {log_none.id}
    assert list(scope_to_user_org(logs, user_noorg, subject_path="subject")) == []
