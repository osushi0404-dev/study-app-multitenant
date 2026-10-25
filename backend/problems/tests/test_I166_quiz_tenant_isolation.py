"""
I166: クイズの全経路（開始・出題・回答・再挑戦）で組織の境界を守る。

- 開始で受け付ける科目はユーザーの組織の科目だけ（他組織は存在しない ID と同じ 400）
- 科目なしのセッションの問題数・出題は自組織の問題だけ
- 回答は自組織かつセッションの科目の問題だけ（外れたら存在しない問題と同じ 404・保存しない）
- 他組織の科目を持つセッションが既にあっても、他組織の問題は出ない・答えられない（多層防御）
- 組織に属さないユーザー・context の無いシリアライザは何も受け付けない（fail-closed）

TC-01〜TC-12（docs/tests/open/I166_auto_test.md）に対応。
"""
import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject
from problems.serializers import QuizSessionSerializer

User = get_user_model()

QUIZ_URL = "/api/quiz/"
BODY_404_PROBLEM = {"error": "Problem not found"}
BODY_404_NO_PROBLEMS = {"error": "No problems available in this subject"}


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
    cat = OrganizationCategory.objects.create(name="テストI166", slug="test-cat-i166")
    org_a = Organization.objects.create(
        name="組織I166A", slug="org-i166-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織I166B", slug="org-i166-b", type="school", category=cat, is_active=True)
    user_a = User.objects.create_user(
        email="a_i166@example.com", user_id="a_i166", password="pass",
        organization=org_a, role="user",
    )
    user_b = User.objects.create_user(
        email="b_i166@example.com", user_id="b_i166", password="pass",
        organization=org_b, role="user",
    )
    subject_a1 = Subject.objects.create(name="科目I166A1", slug="subj-i166-a1", organization=org_a)
    subject_a2 = Subject.objects.create(name="科目I166A2", slug="subj-i166-a2", organization=org_a)
    subject_b = Subject.objects.create(name="科目I166B", slug="subj-i166-b", organization=org_b)
    # 組織 A: subject_a1 に未削除 1 件＋削除済み 1 件、subject_a2 に 1 件（自組織の未削除は計 2 件）
    problem_a1 = _problem(subject_a1, user_a, "A1")
    _problem(subject_a1, user_a, "A1削除済み", is_deleted=True)
    problem_a2 = _problem(subject_a2, user_a, "A2")
    # 組織 B: 3 件（自組織より多くし、出題の判定を乱数に頼らない）
    problems_b = [_problem(subject_b, user_b, f"B{i}") for i in range(1, 4)]
    # 全体共有科目（organization が空・クイズでは使わない）に 1 件
    subject_shared = Subject.objects.create(
        name="共有科目I166", slug="subj-i166-shared", organization=None)
    problem_shared = _problem(subject_shared, user_a, "共有1")
    return {
        "user_a": user_a, "user_b": user_b,
        "subject_a1": subject_a1, "subject_a2": subject_a2, "subject_b": subject_b,
        "subject_shared": subject_shared,
        "problem_a1": problem_a1, "problem_a2": problem_a2,
        "problems_b": problems_b, "problem_shared": problem_shared,
    }


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _missing_subject_id():
    return Subject.objects.order_by("-id").first().id + 1000


def _missing_problem_id():
    return Problem.objects.order_by("-id").first().id + 1000


def _correct_choice_id(problem):
    return problem.choices.get(is_correct=True).id


def _start(client, payload):
    return client.post(QUIZ_URL, payload, format="json")


def _answer(client, session_id, problem):
    return client.post(
        f"{QUIZ_URL}{session_id}/submit_answer/",
        {"problem_id": problem.id, "selected_choice_ids": [_correct_choice_id(problem)]},
        format="json",
    )


def _masked(response, pk):
    """応答本文の ID 部分を伏せた文字列（他組織と存在しない ID の応答を比べるため）"""
    return json.dumps(response.json(), ensure_ascii=False).replace(str(pk), "<pk>")


# ---- TC-01: 他組織の科目での開始は「存在しない科目」と同じ 400・セッションを作らない ----
def test_start_with_other_org_subject_is_rejected_like_missing(setup):
    client = _client(setup["user_a"])
    other_id = setup["subject_b"].id
    missing_id = _missing_subject_id()

    other = _start(client, {"subject": other_id})
    missing = _start(client, {"subject": missing_id})

    assert other.status_code == status.HTTP_400_BAD_REQUEST
    assert missing.status_code == status.HTTP_400_BAD_REQUEST
    assert QuizSession.objects.filter(user=setup["user_a"]).count() == 0
    assert _masked(other, other_id) == _masked(missing, missing_id)
    assert list(other.json()["error"]["details"].keys()) == ["subject"]

    # 全体共有科目（organization が空）も組織に属するユーザーは指定できない
    shared = _start(client, {"subject": setup["subject_shared"].id})
    assert shared.status_code == status.HTTP_400_BAD_REQUEST
    assert QuizSession.objects.filter(user=setup["user_a"]).count() == 0


# ---- TC-02: 自組織の科目での開始は従来どおり ----
def test_start_with_own_subject_succeeds(setup):
    response = _start(_client(setup["user_a"]), {"subject": setup["subject_a1"].id})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["subject"] == setup["subject_a1"].id
    assert response.data["total_problems"] == 1


# ---- TC-03: 科目なしの開始の問題数は自組織の未削除の問題数 ----
@pytest.mark.parametrize("payload", [{}, {"subject": None}])
def test_start_without_subject_counts_own_org_problems_only(setup, payload):
    response = _start(_client(setup["user_a"]), payload)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["subject"] is None
    assert response.data["total_problems"] == 2


# ---- TC-04: 科目なしのセッションでは他組織の問題が出ない ----
def test_next_problem_without_subject_serves_own_org_only(setup):
    client = _client(setup["user_a"])
    session_id = _start(client, {}).data["id"]
    for problem in (setup["problem_a1"], setup["problem_a2"]):
        assert _answer(client, session_id, problem).status_code == status.HTTP_200_OK

    own_ids = {setup["problem_a1"].id, setup["problem_a2"].id}
    for _ in range(3):
        response = client.get(f"{QUIZ_URL}{session_id}/next_problem/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] in own_ids
        assert response.data["is_review_mode"] is True
        assert response.data["total_problems_in_subject"] == 2


# ---- TC-05: 他組織の問題への回答は「存在しない問題」と同じ 404・保存しない ----
def test_answer_other_org_problem_is_rejected_like_missing(setup):
    client = _client(setup["user_a"])
    session_id = _start(client, {}).data["id"]

    other = _answer(client, session_id, setup["problems_b"][0])
    missing = client.post(
        f"{QUIZ_URL}{session_id}/submit_answer/",
        {"problem_id": _missing_problem_id(), "selected_choice_ids": []},
        format="json",
    )

    assert other.status_code == status.HTTP_404_NOT_FOUND
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert other.json() == BODY_404_PROBLEM
    assert missing.json() == BODY_404_PROBLEM
    assert QuizAnswer.objects.filter(session_id=session_id).count() == 0
    session = QuizSession.objects.get(pk=session_id)
    assert session.completed_problems == 0
    assert session.correct_answers == 0


# ---- TC-06: セッションの科目と違う問題への回答は 404（同じ組織でも） ----
def test_answer_problem_outside_session_subject_is_rejected(setup):
    client = _client(setup["user_a"])
    session_id = _start(client, {"subject": setup["subject_a1"].id}).data["id"]

    same_org = _answer(client, session_id, setup["problem_a2"])
    other_org = _answer(client, session_id, setup["problems_b"][0])

    assert same_org.status_code == status.HTTP_404_NOT_FOUND
    assert other_org.status_code == status.HTTP_404_NOT_FOUND
    assert same_org.json() == BODY_404_PROBLEM
    assert other_org.json() == BODY_404_PROBLEM
    assert QuizAnswer.objects.filter(session_id=session_id).count() == 0


# ---- TC-07: 自組織・セッションの科目の問題への回答は従来どおり ----
def test_answer_own_problem_succeeds(setup):
    client = _client(setup["user_a"])
    session_id = _start(client, {"subject": setup["subject_a1"].id}).data["id"]

    served = client.get(f"{QUIZ_URL}{session_id}/next_problem/")
    assert served.status_code == status.HTTP_200_OK
    assert served.data["id"] == setup["problem_a1"].id

    response = _answer(client, session_id, setup["problem_a1"])
    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_correct"] is True
    assert response.data["explanation"] == "A1の解説"
    assert response.data["correct_choices"] == [
        {"id": _correct_choice_id(setup["problem_a1"]), "text": "正解"}]
    assert response.data["session"]["completed_problems"] == 1


# ---- TC-08: 終えたセッションの科目での開始し直し（もう一度挑戦）にも同じ検査 ----
def test_restart_with_ended_session_subject_is_checked(setup):
    user = setup["user_a"]
    client = _client(user)
    first = _start(client, {"subject": setup["subject_a1"].id}).data
    assert client.post(f"{QUIZ_URL}{first['id']}/end/").status_code == status.HTTP_200_OK

    again = _start(client, {"subject": first["subject"]})
    assert again.status_code == status.HTTP_201_CREATED
    assert again.data["subject"] == setup["subject_a1"].id

    foreign = QuizSession.objects.create(user=user, subject=setup["subject_b"], is_active=False)
    rejected = _start(client, {"subject": foreign.subject_id})
    assert rejected.status_code == status.HTTP_400_BAD_REQUEST
    assert QuizSession.objects.filter(user=user).count() == 3


# ---- TC-09: 他組織の科目を持つセッションが既にあっても漏れない（多層防御） ----
def test_existing_foreign_subject_session_does_not_leak(setup):
    user = setup["user_a"]
    client = _client(user)
    session = QuizSession.objects.create(user=user, subject=setup["subject_b"], is_active=True)

    served = client.get(f"{QUIZ_URL}{session.id}/next_problem/")
    assert served.status_code == status.HTTP_404_NOT_FOUND
    assert served.json() == BODY_404_NO_PROBLEMS

    answered = _answer(client, session.id, setup["problems_b"][0])
    assert answered.status_code == status.HTTP_404_NOT_FOUND
    assert answered.json() == BODY_404_PROBLEM
    assert QuizAnswer.objects.filter(session=session).count() == 0


# ---- TC-12: 他組織の問題への過去の回答があっても、復習モードで他組織の問題は出ない（多層防御） ----
# 復習モードは回答済みの問題から選び直す。回答済みに他組織の問題が混ざっていても、
# 出題対象（自組織・科目）の中からしか選ばないことを、復習モードの 2 つの分岐それぞれで確かめる。
# 選び方は乱数のため、他組織の問題を候補の多数にして 20 回出題する（絞り込みが外れると見逃す確率は 1e-8 未満）。
@pytest.mark.parametrize("extra_own", [0, 4], ids=["fallback-branch", "exclude-recent-branch"])
def test_review_mode_ignores_foreign_answers(setup, extra_own):
    user = setup["user_a"]
    client = _client(user)
    session_id = _start(client, {}).data["id"]
    session = QuizSession.objects.get(pk=session_id)

    # 他組織の問題への回答（I166 より前のデータを想定）を古い日時で直接入れる
    for problem in setup["problems_b"]:
        QuizAnswer.objects.create(session=session, problem=problem)
    QuizAnswer.objects.filter(session=session).update(
        answered_at=timezone.now() - timedelta(days=1))

    # 自組織の問題にすべて回答して復習モードにする。extra_own=4 では自組織の回答を 6 件にし、
    # 「最近の 5 問を除外する」分岐（他組織の 3 件と自組織の 1 件が候補）を通す。
    # extra_own=0 では回答が 5 件以下になり、除外した後の候補が空になって後段の分岐を通す。
    own = [setup["problem_a1"], setup["problem_a2"]]
    own += [_problem(setup["subject_a2"], user, f"A追加{i}") for i in range(extra_own)]
    for problem in own:
        assert _answer(client, session_id, problem).status_code == status.HTTP_200_OK

    own_ids = {problem.id for problem in own}
    for _ in range(20):
        response = client.get(f"{QUIZ_URL}{session_id}/next_problem/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_review_mode"] is True
        assert response.data["id"] in own_ids


# ---- TC-10: 組織に属さないユーザーは何も使えない（fail-closed） ----
def test_user_without_organization_can_use_nothing(setup):
    user = User.objects.create_user(
        email="noorg_i166@example.com", user_id="noorg_i166", password="pass",
        organization=None, role="user",
    )
    client = _client(user)

    started = _start(client, {})
    assert started.status_code == status.HTTP_201_CREATED
    assert started.data["total_problems"] == 0
    served = client.get(f"{QUIZ_URL}{started.data['id']}/next_problem/")
    assert served.status_code == status.HTTP_404_NOT_FOUND
    assert served.json() == BODY_404_NO_PROBLEMS

    own = _start(client, {"subject": setup["subject_a1"].id})
    assert own.status_code == status.HTTP_400_BAD_REQUEST
    shared = _start(client, {"subject": setup["subject_shared"].id})
    assert shared.status_code == status.HTTP_400_BAD_REQUEST


# ---- TC-11: context の無いシリアライザは科目を受け付けない・出力は従来どおり ----
def test_serializer_without_context_accepts_no_subject(setup):
    serializer = QuizSessionSerializer(data={"subject": setup["subject_a1"].id})
    assert serializer.is_valid() is False
    assert "subject" in serializer.errors

    session = QuizSession.objects.create(user=setup["user_a"], subject=setup["subject_a1"])
    data = QuizSessionSerializer(session).data
    assert data["subject"] == setup["subject_a1"].id
    assert data["subject_name"] == "科目I166A1"
