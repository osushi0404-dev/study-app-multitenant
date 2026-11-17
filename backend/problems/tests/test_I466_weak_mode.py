"""
I466: クイズのモード weak（苦手を優先）

- 並び: 最後が不正解 → 苦手な難易度 → それ以外（未回答が先・最後の答えの古い順）
- 回の進み方は通常と同じ（同じ回で答えた問題は続けて出ない・全部答えたら既出から）
- 本人の解答が 5 問未満の科目は、いつもの順と is_weak_fallback
- 開始の検証・クエリ数（F4）・組織の境界

TC-10〜TC-15・TC-17・TC-18（docs/tests/open/I466_auto_test.md）に対応。
"""
import uuid

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from problems.models import Problem, QuizSession, Subject
from problems.services.quiz_service import QuizService
from problems.services.tenant_scope import available_problems
from problems.services.weakness import order_weak_first
from problems.tests.i466_data import EASY, HARD, MEDIUM, answer, days_ago, make_problem, make_world

QUIZ = "/api/quiz/"


def _ago(days):
    """実際の今から days 日前（API で答える分は実際の今の時刻になるため、それより前に置く）"""
    return days_ago(days, now=timezone.now())


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def submit(client, session_id, problem, correct=True):
    return client.post(
        f"{QUIZ}{session_id}/submit_answer/",
        {"problem_id": problem.id,
         "selected_choice_ids": [problem.choices.get(is_correct=correct).id],
         "time_taken": 7},
        format="json",
    )


@pytest.fixture
def world(db):
    """TC-10 の準備（テスト文書のとおり）"""
    w = make_world()
    user, math, english = w["user_a"], w["math"], w["english"]
    p = {name: make_problem(math, user, name, HARD if name in ("p3", "p7") else EASY)
         for name in ("p1", "p2", "p3", "p4", "p5", "p6", "p7")}
    for i in range(5):
        answer(user, make_problem(english, user, f"e{i + 1}", HARD), correct=i == 0, at=_ago(5))
    for name, correct, days in (
        ("p5", True, 20), ("p5", True, 18), ("p6", True, 15), ("p3", False, 10),
        ("p1", True, 9), ("p2", False, 8), ("p1", False, 3), ("p6", True, 2), ("p2", True, 1),
    ):
        answer(user, p[name], correct=correct, at=_ago(days))
    w["p"] = p
    return w


def _expected(world):
    return [world["p"][name] for name in ("p3", "p1", "p7", "p4", "p5", "p6", "p2")]


def test_order_weak_first(world):
    """TC-10"""
    user, math = world["user_a"], world["math"]
    ordered, fallback = order_weak_first(available_problems(user, math), user, math)
    assert fallback is False
    assert list(ordered) == _expected(world)


def _start(client, subject, mode="weak", key=None):
    headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
    return client.post(QUIZ, {"subject": subject.id, "mode": mode}, format="json", **headers)


def test_weak_session_progresses_in_order(world):
    """TC-11"""
    client = client_for(world["user_a"])
    started = _start(client, world["math"])
    assert started.status_code == 201
    assert started.data["mode"] == "weak"
    assert started.data["total_problems"] == 7

    first = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
    assert first.status_code == 200
    assert first.data["id"] == world["p"]["p3"].id
    assert first.data["is_weak_fallback"] is False
    assert first.data["is_review_mode"] is False

    assert submit(client, started.data["id"], world["p"]["p3"]).status_code == 200
    second = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
    assert second.data["id"] == world["p"]["p1"].id


def test_fallback_when_few_answers(world):
    """TC-12: 科目の本人の答えが 4 件なら判定できない・5 件なら判定する"""
    user = world["user_a"]
    client = client_for(user)
    subject = Subject.objects.create(
        name="理科", slug="i466-science", organization=world["org_a"])
    problems = [make_problem(subject, user, f"s{i}") for i in range(3)]
    for i in range(4):
        answer(user, problems[i % 3], correct=False, at=_ago(1))

    started = _start(client, subject)
    first = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
    assert first.data["is_weak_fallback"] is True
    assert first.data["id"] in {p.id for p in problems}

    answer(user, problems[0], correct=False, at=_ago(1))
    again = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
    assert again.data["is_weak_fallback"] is False


def test_second_round_keeps_weak_order(world):
    """TC-13"""
    client = client_for(world["user_a"])
    started = _start(client, world["math"])
    for problem in _expected(world):
        shown = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
        assert shown.data["id"] == problem.id
        submit(client, started.data["id"], problem, correct=problem != world["p"]["p3"])

    again = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
    assert again.data["is_review_mode"] is True
    assert again.data["id"] == world["p"]["p3"].id


def test_start_validation(world):
    """TC-14"""
    client = client_for(world["user_a"])
    assert _start(client, world["math"], mode="bogus").status_code == 400

    key = str(uuid.uuid4())
    assert _start(client, world["math"], mode="normal", key=key).status_code == 201
    reused = _start(client, world["math"], mode="weak", key=key)
    assert reused.status_code == 422
    assert reused.data["error"]["main_message"] == "Idempotency-Key が別の内容で使用されています"

    weak = _start(client, world["subject_b"], mode="weak")
    normal = _start(client, world["subject_b"], mode="normal")
    assert weak.status_code == normal.status_code
    assert weak.data == normal.data


def _weak_session_with(world, count, slug):
    user = world["user_a"]
    subject = Subject.objects.create(
        name=f"科目{count}", slug=slug, organization=world["org_a"])
    problems = [make_problem(subject, user, f"{slug}-{i}", HARD if i % 2 else EASY)
                for i in range(count)]
    for i in range(10):
        answer(user, problems[i % count], correct=i % 3 == 0, at=_ago(10 - i))
    return QuizSession.objects.create(
        user=user, subject=subject, mode=QuizSession.MODE_WEAK, total_problems=count,
        is_active=False)  # 2 つの回を並べるため（有効な回は 1 人 1 つ）


def test_query_count_does_not_grow_with_candidates(world):
    """TC-15（F4）"""
    small = _weak_session_with(world, 3, "i466-small")
    large = _weak_session_with(world, 40, "i466-large")
    counts = []
    for session in (small, large):
        with CaptureQueriesContext(connection) as ctx:
            QuizService.get_next_problem(session)
        counts.append(len(ctx.captured_queries))
    assert counts[0] == counts[1]


def test_other_org_and_other_people_do_not_change_order(world):
    """TC-17"""
    user, math = world["user_a"], world["math"]
    # ① B科目 の問題への user_a の答え（不具合で残った想定）。中級は B の問題への答えだけで正答率 0% になる
    #    ので、数えてしまうと未回答の中級 p8 が段 1 に上がる ② 同じ組織の別人の p4 への不正解
    p8 = make_problem(math, user, "p8", MEDIUM)
    b_problem = make_problem(world["subject_b"], world["user_b"], "b1", MEDIUM)
    for _ in range(5):
        answer(user, b_problem, correct=False, at=_ago(1))
    answer(world["user_a2"], world["p"]["p4"], correct=False, at=_ago(1))
    ordered, _ = order_weak_first(available_problems(user, math), user, math)
    p = world["p"]
    assert list(ordered) == [p["p3"], p["p1"], p["p7"], p["p4"], p8, p["p5"], p["p6"], p["p2"]]

    # ③ 科目なしの weak の回で、未回答の問題を出し切るまで
    client = client_for(user)
    started = client.post(QUIZ, {"mode": "weak"}, format="json")
    assert started.status_code == 201
    seen = set()
    for _ in range(started.data["total_problems"]):
        shown = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
        assert shown.data["is_review_mode"] is False
        seen.add(shown.data["id"])
        problem = Problem.objects.get(id=shown.data["id"])
        submit(client, started.data["id"], problem)
    assert b_problem.id not in seen
    assert {p.organization_id for p in Problem.objects.filter(id__in=seen)} \
        == {world["org_a"].id}


def test_normal_session_reports_no_fallback(world):
    """TC-18"""
    client = client_for(world["user_a"])
    started = _start(client, world["math"], mode="normal")
    shown = client.get(f"{QUIZ}{started.data['id']}/next_problem/")
    assert shown.data["is_weak_fallback"] is False
