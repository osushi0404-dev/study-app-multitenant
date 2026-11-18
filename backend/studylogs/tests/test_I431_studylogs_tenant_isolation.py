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
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject, UserSubjectAccess
from studylogs.models import SpacedRepetitionCard, SpacedRepetitionReview
from studylogs.services import SpacedRepetitionService

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


# ---- TC-15b: 科目のプルダウンの API に登録時の他組織の科目が出ない ----
def test_user_subjects_api_hides_other_org_subjects(setup):
    UserSubjectAccess.objects.create(user=setup["user_a"], subject=setup["subject_a"])
    UserSubjectAccess.objects.create(user=setup["user_a"], subject=setup["subject_b"])
    UserSubjectAccess.objects.create(user=setup["user_noorg"], subject=setup["subject_a"])

    own = _client(setup["user_a"]).get("/api/user/subjects/")
    noorg = _client(setup["user_noorg"]).get("/api/user/subjects/")

    assert own.status_code == status.HTTP_200_OK
    # problem_count は組織 A の科目の出題できる問題数（fixture の 2 問のうち削除済みの 1 問は数えない・I539）
    assert own.json() == [{"id": setup["subject_a"].id, "name": "科目I431A", "problem_count": 1}]
    assert noorg.status_code == status.HTTP_200_OK
    assert noorg.json() == []


def _quiz_answers(user, problem, total, correct):
    """クイズの答えを total 件（うち正解 correct 件）。セッションは答えごとに作る（I473）"""
    for i in range(total):
        session = QuizSession.objects.create(user=user, subject=problem.subject, is_active=False)
        QuizAnswer.objects.create(session=session, problem=problem, is_correct=i < correct)


# ---- TC-17: ダッシュボードの概要に他組織の科目が出ない（I473 でクイズの答えから数える形に書き直し） ----
def test_dashboard_overview_hides_other_org_subjects(setup):
    user = setup["user_a"]
    UserSubjectAccess.objects.create(user=user, subject=setup["subject_a"])
    UserSubjectAccess.objects.create(user=user, subject=setup["subject_b"])
    _quiz_answers(user, setup["problem_a"], 5, 1)
    _quiz_answers(user, setup["problems_b"][0], 5, 0)  # 不具合で残った他組織の問題への答えの想定

    response = _client(user).get(DASH + "overview/")

    assert response.status_code == status.HTTP_200_OK
    assert _no_other(response)
    data = response.json()
    assert data["totals"]["answered_count"] == 5
    assert {w["subject_name"] for w in data["weak_subjects"]} == {"科目I431A"}
    assert {r["subject_id"] for r in data["recommendations"]} == {setup["subject_a"].id}


# ---- TC-18: 学習統計の科目の内訳に他組織の科目が出ない（I488 でクイズの答えから数える形に書き直し） ----
def test_dashboard_analytics_hides_other_org_subjects(setup):
    user = setup["user_a"]
    _quiz_answers(user, setup["problem_a"], 3, 1)
    _quiz_answers(user, setup["problems_b"][0], 3, 0)  # 不具合で残った他組織の問題への答えの想定

    response = _client(user).get(DASH + "analytics/")

    assert response.status_code == status.HTTP_200_OK
    assert _no_other(response)
    data = response.json()
    assert {s["subject_name"] for s in data["subject_breakdown"]} == {"科目I431A"}
    assert data["totals"]["answered_count"] == 3


# ---- TC-19: おすすめに他組織の科目が出ない（I473 で overview の recommendations に移した） ----
def test_dashboard_recommendations_are_own_org_only(setup):
    user = setup["user_a"]
    for subject in (setup["subject_a"], setup["subject_b"]):
        UserSubjectAccess.objects.create(user=user, subject=subject)

    response = _client(user).get(DASH + "overview/")

    assert response.status_code == status.HTTP_200_OK
    assert _no_other(response)
    recommendations = response.json()["recommendations"]
    assert [(r["kind"], r["subject_id"]) for r in recommendations] == [
        ("unstudied_subject", setup["subject_a"].id)]


# ---- TC-21: 組織に属さない利用者は問題を扱えない（学習記録の API は I492 で消した） ----
def test_user_without_organization_is_fail_closed(setup):
    user = setup["user_noorg"]
    client = _client(user)

    card = client.post(
        STUDY + "spaced-repetition/create_card/", {"problem_id": setup["problem_a"].id},
        format="json")
    assert card.status_code == status.HTTP_404_NOT_FOUND
    assert card.json() == {"error": "問題が見つかりません"}


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

    # 科目が NULL になりうる記録（I492 で StudyLog から QuizSession に替えた。進行中は 1 人 1 つなので終了済み）
    log_a = QuizSession.objects.create(user=user_a, subject=setup["subject_a"], is_active=False)
    QuizSession.objects.create(user=user_a, subject=setup["subject_b"], is_active=False)
    log_none = QuizSession.objects.create(user=user_a, subject=None, is_active=False)
    logs = QuizSession.objects.filter(user=user_a)
    with_null = scope_to_user_org(logs, user_a, subject_path="subject", allow_null=True)
    without_null = scope_to_user_org(logs, user_a, subject_path="subject")
    noorg = scope_to_user_org(logs, user_noorg, subject_path="subject", allow_null=True)
    assert {log.id for log in with_null} == {log_a.id, log_none.id}
    assert {log.id for log in without_null} == {log_a.id}
    assert {log.id for log in noorg} == {log_none.id}
    assert list(scope_to_user_org(logs, user_noorg, subject_path="subject")) == []
