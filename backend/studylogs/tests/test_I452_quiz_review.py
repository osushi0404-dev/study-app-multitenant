"""
I452: クイズの回答から復習の予定（間隔反復のカード）を作り、今日の復習を始められるようにする

- 回答のたびのカードの更新（SM-2・正解 4／不正解 2・答えた日の 0 時＋間隔・同じ日の 2 回目は更新しない）
- 今日の復習の件数と次の日付（review_summary）・復習のクイズ（QuizSession.mode='review'）
- 組織の境界（他組織の問題・削除した問題・同じ組織の別の利用者・他組織の科目の指定）
- 間違い分析・適応的な問題選択・学習洞察の 500 の直し（難易度の型・科目が空のパターン）
- キャッシュのキーの組織・印付けの 3 経路の組織の絞り込み

TC-01〜TC-13（docs/tests/open/I452_auto_test.md）に対応。
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.difficulty import LABEL_BY_LEVEL
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject
from studylogs.models import (
    SpacedRepetitionCard,
    SpacedRepetitionReview,
)
from studylogs.services import SpacedRepetitionService

User = get_user_model()

JST = ZoneInfo("Asia/Tokyo")
QUIZ = "/api/quiz/"
SR = "/api/study/spaced-repetition/"


def at(month, day, hour=10, minute=0, second=0):
    return datetime(2026, month, day, hour, minute, second, tzinfo=JST)


def midnight(month, day):
    return datetime(2026, month, day, tzinfo=JST)


def start_of_today():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


@pytest.fixture(autouse=True)
def _clear_caches():
    for alias in settings.CACHES:
        caches[alias].clear()
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI452", slug="test-cat-i452")
    org_a = Organization.objects.create(
        name="組織I452A", slug="org-i452-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織I452B", slug="org-i452-b", type="school", category=cat, is_active=True)

    def user(name, org):
        return User.objects.create_user(
            email=f"{name}_i452@example.com", user_id=f"{name}_i452", password="pass",
            organization=org, role="user",
        )

    return {
        "org_a": org_a, "org_b": org_b,
        "user_a": user("a", org_a), "user_a2": user("a2", org_a),
        "user_b": user("b", org_b), "user_noorg": user("n", None),
        "s1": Subject.objects.create(name="科目I452-1", slug="subj-i452-1", organization=org_a),
        "s2": Subject.objects.create(name="科目I452-2", slug="subj-i452-2", organization=org_a),
        "s3": Subject.objects.create(name="科目I452-3", slug="subj-i452-3", organization=org_a),
        "sb": Subject.objects.create(name="科目I452-B", slug="subj-i452-b", organization=org_b),
    }


def make_problem(creator, subject, difficulty=1, is_deleted=False):
    problem = Problem.objects.create(
        subject=subject, organization=subject.organization, created_by=creator,
        question=f"問題{subject.slug}", problem_type="single", difficulty=difficulty,
        explanation="解説", is_deleted=is_deleted,
    )
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    return problem


def make_card(user, problem, next_review_date, is_active=True):
    return SpacedRepetitionCard.objects.create(
        user=user, problem=problem, next_review_date=next_review_date, is_active=is_active)


def make_review(user, problem, is_correct=True):
    card, _ = SpacedRepetitionCard.objects.get_or_create(
        user=user, problem=problem, defaults={"next_review_date": timezone.now()})
    return SpacedRepetitionReview.objects.create(
        card=card, user=user, problem=problem, quality_score=4 if is_correct else 2,
        response_time_seconds=10, is_correct=is_correct, previous_ease_factor=2.5,
        previous_interval=1, previous_repetition_count=0, new_ease_factor=2.5, new_interval=1,
        new_repetition_count=1, next_review_date=timezone.now(),
    )


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def choice_id(problem, correct):
    return problem.choices.get(is_correct=correct).id


def answer(client, session_id, problem, correct=True):
    return client.post(
        f"{QUIZ}{session_id}/submit_answer/",
        {"problem_id": problem.id, "selected_choice_ids": [choice_id(problem, correct)],
         "time_taken": 7},
        format="json",
    )


def card_of(user, problem):
    return SpacedRepetitionCard.objects.get(user=user, problem=problem)


# ---- TC-01: 間隔の決まり ----

def test_schedule_correct_sequence(setup):
    user = setup["user_a"]
    problem = make_problem(user, setup["s1"])
    service = SpacedRepetitionService(user)

    service.record_quiz_answer(problem, True, 10, now=at(11, 12))
    card = card_of(user, problem)
    assert (card.repetition_count, card.interval_days) == (1, 1)
    assert card.next_review_date == midnight(11, 13)
    assert card.ease_factor == pytest.approx(2.5)

    service.record_quiz_answer(problem, True, 10, now=at(11, 13))
    card.refresh_from_db()
    assert (card.repetition_count, card.interval_days) == (2, 6)
    assert card.next_review_date == midnight(11, 19)

    service.record_quiz_answer(problem, True, 10, now=at(11, 19))
    card.refresh_from_db()
    assert (card.repetition_count, card.interval_days) == (3, 15)
    assert card.next_review_date == midnight(12, 4)
    assert SpacedRepetitionReview.objects.filter(card=card).count() == 3


def test_schedule_incorrect_resets(setup):
    user = setup["user_a"]
    problem = make_problem(user, setup["s1"])
    service = SpacedRepetitionService(user)

    service.record_quiz_answer(problem, True, 10, now=at(11, 12))
    service.record_quiz_answer(problem, True, 10, now=at(11, 13))
    service.record_quiz_answer(problem, False, 10, now=at(11, 19))
    card = card_of(user, problem)
    assert (card.repetition_count, card.interval_days) == (0, 1)
    assert card.next_review_date == midnight(11, 20)
    assert card.ease_factor == pytest.approx(2.5 - 0.32)
    assert (card.total_reviews, card.correct_reviews) == (3, 2)

    # 初めての回答が不正解でも、翌日の 0 時
    other = make_problem(user, setup["s1"])
    service.record_quiz_answer(other, False, 10, now=at(11, 12))
    other_card = card_of(user, other)
    assert (other_card.repetition_count, other_card.interval_days) == (0, 1)
    assert other_card.next_review_date == midnight(11, 13)


def test_schedule_ease_factor_floor(setup):
    user = setup["user_a"]
    problem = make_problem(user, setup["s1"])
    service = SpacedRepetitionService(user)
    for day in range(12, 18):
        service.record_quiz_answer(problem, False, 10, now=at(11, day))
    assert card_of(user, problem).ease_factor == pytest.approx(1.3)


def test_schedule_day_boundary(setup):
    user = setup["user_a"]
    problem = make_problem(user, setup["s1"])
    service = SpacedRepetitionService(user)

    service.record_quiz_answer(problem, True, 10, now=at(11, 12, 23, 59))
    assert card_of(user, problem).next_review_date == midnight(11, 13)
    assert service.due_cards_queryset(now=at(11, 12, 23, 59, 30)).count() == 0
    assert service.due_cards_queryset(now=midnight(11, 13)).count() == 1

    # 0 時を過ぎた回答は別の日の回答として更新する
    service.record_quiz_answer(problem, True, 10, now=at(11, 13, 0, 0, 30))
    card = card_of(user, problem)
    assert (card.repetition_count, card.interval_days) == (2, 6)


# ---- TC-02: 同じ日の 2 回目 ----

def test_same_day_second_answer_service(setup):
    user = setup["user_a"]
    problem = make_problem(user, setup["s1"])
    service = SpacedRepetitionService(user)

    first = service.record_quiz_answer(problem, True, 10, now=at(11, 12, 9))
    before = card_of(user, problem)
    second = service.record_quiz_answer(problem, False, 10, now=at(11, 12, 21))
    after = card_of(user, problem)

    assert first is not None
    assert second is None
    for field in ("next_review_date", "repetition_count", "interval_days", "ease_factor",
                  "total_reviews", "correct_reviews"):
        assert getattr(after, field) == getattr(before, field)
    assert SpacedRepetitionReview.objects.filter(card=after).count() == 1


def test_same_day_second_answer_api(setup):
    user = setup["user_a"]
    problem = make_problem(user, setup["s1"])
    client = client_for(user)

    first = client.post(QUIZ, {"subject": setup["s1"].id}, format="json")
    assert answer(client, first.data["id"], problem, correct=True).status_code == 200
    before = card_of(user, problem)

    second = client.post(QUIZ, {"subject": setup["s1"].id}, format="json")
    assert answer(client, second.data["id"], problem, correct=False).status_code == 200
    after = card_of(user, problem)

    assert (after.next_review_date, after.repetition_count, after.total_reviews) == (
        before.next_review_date, before.repetition_count, before.total_reviews)
    assert SpacedRepetitionReview.objects.filter(card=after).count() == 1


# ---- TC-03: 回答の API からカードを作る ----

def test_submit_answer_updates_card(setup):
    user = setup["user_a"]
    right = make_problem(user, setup["s1"])
    wrong = make_problem(user, setup["s1"])
    client = client_for(user)
    session = client.post(QUIZ, {"subject": setup["s1"].id}, format="json")
    assert session.status_code == 201

    ok = answer(client, session.data["id"], right, correct=True)
    ng = answer(client, session.data["id"], wrong, correct=False)

    assert (ok.status_code, ok.data["is_correct"]) == (200, True)
    assert (ng.status_code, ng.data["is_correct"]) == (200, False)
    assert set(ok.data.keys()) == {
        "is_correct", "explanation", "explanation_images",  # I587: explanation_image を外した
        "correct_choices", "session_complete", "session", "session_stats"}
    tomorrow = start_of_today() + timedelta(days=1)
    right_card, wrong_card = card_of(user, right), card_of(user, wrong)
    assert (right_card.repetition_count, right_card.next_review_date) == (1, tomorrow)
    assert (wrong_card.repetition_count, wrong_card.next_review_date) == (0, tomorrow)


# ---- TC-04: 今日の復習の件数と次の日付 ----

@pytest.fixture
def review_data(setup):
    user = setup["user_a"]
    past = timezone.now() - timedelta(hours=1)
    today = start_of_today()
    s1_due = [make_problem(user, setup["s1"]) for _ in range(2)]
    s2_due = make_problem(user, setup["s2"])
    s1_future = make_problem(user, setup["s1"])
    s2_future = make_problem(user, setup["s2"])
    inactive = make_problem(user, setup["s1"])
    deleted = make_problem(user, setup["s1"], is_deleted=True)
    for problem in (*s1_due, s2_due):
        make_card(user, problem, past)
    make_card(user, s1_future, today + timedelta(days=3))
    make_card(user, s2_future, today + timedelta(days=10))
    make_card(user, inactive, past, is_active=False)
    make_card(user, deleted, past)
    return {"s1_due": s1_due, "s2_due": s2_due, "s1_future": s1_future}


def _date_after(days):
    return (timezone.localdate() + timedelta(days=days)).isoformat()


def test_review_summary_counts(setup, review_data):
    client = client_for(setup["user_a"])
    url = SR + "review_summary/"

    assert client.get(url).data == {"due_count": 3, "next_review_date": _date_after(3)}
    assert client.get(url, {"subject_id": setup["s1"].id}).data == {
        "due_count": 2, "next_review_date": _date_after(3)}
    assert client.get(url, {"subject_id": setup["s2"].id}).data == {
        "due_count": 1, "next_review_date": _date_after(10)}
    assert client.get(url, {"subject_id": setup["s3"].id}).data == {
        "due_count": 0, "next_review_date": None}


@pytest.mark.parametrize("bad", ["abc", "foreign", "missing"])
def test_review_summary_rejects_bad_subject(setup, review_data, bad):
    value = {"abc": "abc", "foreign": setup["sb"].id, "missing": 999999}[bad]
    response = client_for(setup["user_a"]).get(SR + "review_summary/", {"subject_id": value})
    assert response.status_code == 400
    assert response.data["error"]["main_message"] == "科目の指定が正しくありません"


def test_review_summary_requires_login(setup):
    assert APIClient().get(SR + "review_summary/").status_code == 401


# ---- TC-05: 復習のクイズ ----

def _run_review(client, session_id, correct_ids=()):
    served = []
    while True:
        response = client.get(f"{QUIZ}{session_id}/next_problem/")
        assert response.status_code == 200
        if response.data.get("review_complete"):
            return served, response.data
        assert response.data["is_review_mode"] is False
        assert response.data["difficulty"] == "easy"
        problem = Problem.objects.get(id=response.data["id"])
        assert problem.id not in served
        served.append(problem.id)
        assert answer(client, session_id, problem, correct=problem.id in correct_ids).status_code == 200


def test_review_session_by_subject(setup, review_data):
    client = client_for(setup["user_a"])
    started = client.post(QUIZ, {"subject": setup["s1"].id, "mode": "review"}, format="json")
    assert started.status_code == 201
    assert (started.data["mode"], started.data["total_problems"]) == ("review", 2)

    expected = {p.id for p in review_data["s1_due"]}
    served, done = _run_review(client, started.data["id"], correct_ids={min(expected)})
    assert set(served) == expected
    assert done == {"review_complete": True, "total_problems": 2,
                    "completed_problems": 2, "correct_answers": 1}


def test_review_session_all_subjects(setup, review_data):
    client = client_for(setup["user_a"])
    started = client.post(QUIZ, {"mode": "review"}, format="json")
    assert (started.status_code, started.data["total_problems"]) == (201, 3)

    served, done = _run_review(client, started.data["id"])
    assert set(served) == {p.id for p in review_data["s1_due"]} | {review_data["s2_due"].id}
    assert done["review_complete"] is True


def test_normal_session_keeps_serving(setup, review_data):
    client = client_for(setup["user_a"])
    started = client.post(QUIZ, {"subject": setup["s1"].id}, format="json")
    assert started.data["mode"] == "normal"
    session_id = started.data["id"]
    available = Problem.objects.filter(subject=setup["s1"], is_deleted=False).count()
    for _ in range(available):
        response = client.get(f"{QUIZ}{session_id}/next_problem/")
        problem = Problem.objects.get(id=response.data["id"])
        answer(client, session_id, problem)
    again = client.get(f"{QUIZ}{session_id}/next_problem/")
    assert again.status_code == 200
    assert again.data["is_review_mode"] is True
    assert "review_complete" not in again.data


# ---- TC-06: 中断 ----

def test_review_interrupted(setup, review_data):
    user = setup["user_a"]
    client = client_for(user)
    started = client.post(QUIZ, {"mode": "review"}, format="json")
    first = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
    answered = Problem.objects.get(id=first.data["id"])
    answer(client, started.data["id"], answered)
    assert client.post(f"{QUIZ}{started.data['id']}/end/").status_code == 200

    assert card_of(user, answered).next_review_date > timezone.now()
    assert client.get(SR + "review_summary/").data["due_count"] == 2


# ---- TC-07: 過去の回答 ----

def test_past_answers_do_not_create_cards(setup):
    user = setup["user_a"]
    problem = make_problem(user, setup["s1"])
    session = QuizSession.objects.create(user=user, subject=setup["s1"], is_active=False)
    QuizAnswer.objects.create(session=session, problem=problem, is_correct=False)

    assert not SpacedRepetitionCard.objects.filter(user=user).exists()
    assert client_for(user).get(SR + "review_summary/").data == {
        "due_count": 0, "next_review_date": None}


# ---- TC-08: 組織の境界 ----

def test_review_tenant_excludes_foreign_and_others(setup, review_data):
    user = setup["user_a"]
    past = timezone.now() - timedelta(hours=1)
    make_card(user, make_problem(setup["user_b"], setup["sb"]), past)  # 古いデータ
    make_card(setup["user_a2"], make_problem(user, setup["s1"]), past)

    client = client_for(user)
    assert client.get(SR + "review_summary/").data["due_count"] == 3
    started = client.post(QUIZ, {"mode": "review"}, format="json")
    assert started.data["total_problems"] == 3
    served, _ = _run_review(client, started.data["id"])
    assert set(served) == {p.id for p in review_data["s1_due"]} | {review_data["s2_due"].id}


def test_review_tenant_noorg_user(setup):
    user = setup["user_noorg"]
    client = client_for(user)
    assert client.get(SR + "review_summary/").data == {"due_count": 0, "next_review_date": None}
    started = client.post(QUIZ, {"mode": "review"}, format="json")
    assert (started.status_code, started.data["total_problems"]) == (201, 0)
    first = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
    assert first.data["review_complete"] is True


def test_review_tenant_idempotency_mode(setup):
    client = client_for(setup["user_a"])
    headers = {"HTTP_IDEMPOTENCY_KEY": "6f1c2b3a-1111-4222-8333-444455556666"}
    first = client.post(QUIZ, {"mode": "review"}, format="json", **headers)
    second = client.post(QUIZ, {}, format="json", **headers)
    assert (first.status_code, second.status_code) == (201, 422)


def test_review_tenant_rejects_foreign_subject_and_bad_mode(setup):
    client = client_for(setup["user_a"])
    before = QuizSession.objects.count()
    foreign = client.post(QUIZ, {"subject": setup["sb"].id, "mode": "review"}, format="json")
    bad_mode = client.post(QUIZ, {"mode": "other"}, format="json")
    assert (foreign.status_code, bad_mode.status_code) == (400, 400)
    assert QuizSession.objects.count() == before


# ---- TC-09: 難易度の対応 ----

def test_difficulty_mapping_matches_choices():
    assert set(LABEL_BY_LEVEL) == {level for level, _ in Problem.DIFFICULTY_CHOICES}


# ---- TC-10: 学習記録の API が 500 にならない ----

def test_learning_endpoints_ok(setup):
    user = setup["user_a"]
    for level in (1, 2, 3):
        problem = make_problem(user, setup["s1"], difficulty=level)
        make_review(user, problem, is_correct=level != 3)
    client = client_for(user)

    insights = client.get(SR + "learning_insights/")
    assert insights.status_code == 200
    assert insights.data == {"insights": [], "recommendations": [], "period_days": 7,
                             "analytics_data": []}
    assert client.post(SR + "update_analytics/", {}, format="json").status_code == 200
    assert client.get(SR + "learning_insights/").status_code == 200
    # 間違い分析・適応的な問題選択の経路は I466 で消した（studylogs/tests/test_I466_removed_routes.py）


# ---- TC-12: キャッシュのキーの組織 ----

def test_cache_key_has_org(setup):
    user = setup["user_a"]
    problem = make_problem(user, setup["s1"])
    make_card(user, problem, timezone.now() - timedelta(hours=1))
    make_review(user, problem)

    assert len(SpacedRepetitionService(user).get_due_cards()) == 1

    user.organization = setup["org_b"]
    user.save()
    assert SpacedRepetitionService(user).get_due_cards() == []
    # 習熟度のキャッシュ（AdaptiveProblemSelector）は I466 で消した
