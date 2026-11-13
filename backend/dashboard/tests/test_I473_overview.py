"""
I473: ダッシュボードの数字をクイズの答えの記録（QuizAnswer）から出す。

- 学習時間は time_taken の合計（1 問 300 秒まで）・日付は日本時間・今日の復習の回も含める
- 応答の形（契約）を固定し、科目の選択・不正な subject_id の 400・組織の境界・クエリ数を確かめる
- 引き継ぎ 3（科目のキャッシュの並び順・キーの組織）

TC-01〜TC-16（docs/tests/open/I473_auto_test.md）に対応。
"""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from core.subject_service import subject_service, user_subjects_cache_key
from dashboard.selectors import build_overview
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject, UserSubjectAccess
from studylogs.models import StudyLog

User = get_user_model()

OVERVIEW = "/api/dashboard/overview/"
JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 11, 13, 8, 0, tzinfo=JST)
INVALID_SUBJECT_BODY = {
    "error": {
        "main_message": "科目の指定が正しくありません",
        "sub_message": "ダッシュボードの科目の選択からやり直してください",
        "details": {},
    }
}


@pytest.fixture(autouse=True)
def _clear_caches():
    """Redis があるときに、利用者 ID が同じ別テストの cache を拾わない"""
    for alias in settings.CACHES:
        caches[alias].clear()
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


def _jst(month, day, hour=12, minute=0):
    return datetime(2026, month, day, hour, minute, tzinfo=JST)


def _problem(subject, user, question):
    problem = Problem.objects.create(
        subject=subject, organization=subject.organization, created_by=user,
        question=question, problem_type="single", difficulty=1, explanation="解説",
    )
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    return problem


def _answer(user, problem, *, correct, seconds=0, at=None, mode=QuizSession.MODE_NORMAL):
    """1 問の答え（セッションは答えごとに作る。QuizAnswer は同じセッション・同じ問題で 1 件まで）"""
    session = QuizSession.objects.create(
        user=user, subject=problem.subject, is_active=False, mode=mode)
    answer = QuizAnswer.objects.create(
        session=session, problem=problem, is_correct=correct, time_taken=seconds)
    if at is not None:
        QuizAnswer.objects.filter(pk=answer.pk).update(answered_at=at)
    return answer


def _answers(user, problem, total, correct, *, at=None, seconds=0):
    for i in range(total):
        _answer(user, problem, correct=i < correct, at=at, seconds=seconds)


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI473", slug="test-cat-i473")
    org_a = Organization.objects.create(
        name="組織I473A", slug="org-i473-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織I473B", slug="org-i473-b", type="school", category=cat, is_active=True)
    user_a = User.objects.create_user(
        email="a_i473@example.com", user_id="a_i473", password="pass",
        organization=org_a, role="user")
    user_a2 = User.objects.create_user(
        email="a2_i473@example.com", user_id="a2_i473", password="pass",
        organization=org_a, role="user")
    user_b = User.objects.create_user(
        email="b_i473@example.com", user_id="b_i473", password="pass",
        organization=org_b, role="user")
    user_noorg = User.objects.create_user(
        email="n_i473@example.com", user_id="n_i473", password="pass",
        organization=None, role="user")
    math = Subject.objects.create(name="数学", slug="i473-math", organization=org_a)
    english = Subject.objects.create(name="英語", slug="i473-english", organization=org_a)
    science = Subject.objects.create(name="理科", slug="i473-science", organization=org_a)
    subject_b = Subject.objects.create(name="B科目", slug="i473-b", organization=org_b)
    shared = Subject.objects.create(name="共有科目I473", slug="i473-shared", organization=None)
    for subject in (math, english, science):
        UserSubjectAccess.objects.create(user=user_a, subject=subject)
    return {
        "org_a": org_a, "user_a": user_a, "user_a2": user_a2, "user_b": user_b,
        "user_noorg": user_noorg,
        "math": math, "english": english, "science": science,
        "subject_b": subject_b, "shared": shared,
        "p_math": _problem(math, user_a, "数学の問題"),
        "p_english": _problem(english, user_a, "英語の問題"),
        "p_b": _problem(subject_b, user_b, "B科目の問題"),
    }


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _day(overview, date_text):
    return next(d for d in overview["last_7_days"] if d["date"] == date_text)


# ---- TC-01: 契約（キーと型） ----
def test_contract_keys_and_types(setup):
    user = setup["user_a"]
    _answers(user, setup["p_english"], 5, 1)

    response = _client(user).get(OVERVIEW)

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "has_data", "today", "streak", "totals", "last_7_days", "weak_subjects",
        "recommendations"}
    assert set(data["today"]) == {
        "study_seconds", "answered_count", "correct_count", "accuracy_rate"}
    assert set(data["streak"]) == {"current_days"}
    assert set(data["totals"]) == {"answered_count", "correct_count", "accuracy_rate"}
    assert all(
        set(day) == {"date", "study_seconds", "answered_count", "correct_count"}
        for day in data["last_7_days"])
    assert data["weak_subjects"] and all(
        set(w) == {"subject_id", "subject_name", "answered_count", "accuracy_rate"}
        for w in data["weak_subjects"])
    assert data["recommendations"] and all(
        set(r) == {"kind", "subject_id", "subject_name", "reason"}
        for r in data["recommendations"])
    assert isinstance(data["has_data"], bool)
    assert isinstance(data["weak_subjects"][0]["subject_id"], int)
    assert isinstance(data["recommendations"][0]["subject_id"], int)


# ---- TC-02: 期待値と 1 問 300 秒の上限 ----
def test_values_and_seconds_cap(setup):
    user, problem = setup["user_a"], setup["p_math"]
    _answer(user, problem, correct=True, seconds=10, at=_jst(11, 13, 7))
    _answer(user, problem, correct=True, seconds=20, at=_jst(11, 13, 7))
    _answer(user, problem, correct=False, seconds=400, at=_jst(11, 13, 7))
    _answer(user, problem, correct=True, seconds=30, at=_jst(11, 10))

    overview = build_overview(user, now=NOW)

    assert overview["has_data"] is True
    assert overview["today"] == {
        "study_seconds": 330, "answered_count": 3, "correct_count": 2, "accuracy_rate": 0.6667}
    assert overview["totals"] == {"answered_count": 4, "correct_count": 3, "accuracy_rate": 0.75}


# ---- TC-03: 日本時間の日付の境界 ----
def test_dates_are_japan_time(setup):
    user, problem = setup["user_a"], setup["p_math"]
    _answer(user, problem, correct=True, at=_jst(11, 12, 23, 30))
    _answer(user, problem, correct=True, at=_jst(11, 13, 0, 30))  # UTC では 11-12 15:30

    overview = build_overview(user, now=NOW)

    assert overview["today"]["answered_count"] == 1
    assert _day(overview, "2026-11-12")["answered_count"] == 1
    assert _day(overview, "2026-11-13")["answered_count"] == 1


# ---- TC-04: 連続日数 ----
@pytest.mark.parametrize("days, expected", [
    ((12, 11), 2),       # 今日はまだ・昨日まで続いている
    ((13, 12, 11), 3),
    ((13, 11), 1),       # 昨日が抜けている
    ((10,), 0),          # 昨日も今日も無い
    ((), 0),
])
def test_current_streak(setup, days, expected):
    user, problem = setup["user_a"], setup["p_math"]
    for day in days:
        _answer(user, problem, correct=True, at=_jst(11, day))

    assert build_overview(user, now=NOW)["streak"] == {"current_days": expected}


# ---- TC-05: 直近 7 日 ----
def test_last_7_days(setup):
    user, problem = setup["user_a"], setup["p_math"]
    _answer(user, problem, correct=True, seconds=60, at=_jst(11, 7))   # 範囲の最初の日
    _answer(user, problem, correct=True, seconds=60, at=_jst(11, 6))   # 範囲の外
    _answers(user, problem, 2, 2, at=_jst(11, 13, 7), seconds=30)

    days = build_overview(user, now=NOW)["last_7_days"]

    assert [d["date"] for d in days] == [f"2026-11-{n:02d}" for n in range(7, 14)]
    by_date = {d["date"]: d for d in days}
    assert by_date["2026-11-07"] == {
        "date": "2026-11-07", "study_seconds": 60, "answered_count": 1, "correct_count": 1}
    assert by_date["2026-11-13"]["answered_count"] == 2
    assert by_date["2026-11-13"]["study_seconds"] == 60
    assert all(
        d["answered_count"] == 0 and d["study_seconds"] == 0
        for d in days if d["date"] not in ("2026-11-07", "2026-11-13"))


# ---- TC-06: 今日の復習の回も数える ----
def test_review_mode_is_counted(setup):
    user, problem = setup["user_a"], setup["p_math"]
    _answer(user, problem, correct=True, at=_jst(11, 13, 7), mode=QuizSession.MODE_REVIEW)
    _answer(user, problem, correct=False, at=_jst(11, 13, 7), mode=QuizSession.MODE_REVIEW)

    overview = build_overview(user, now=NOW)

    assert overview["today"]["answered_count"] == 2
    assert overview["today"]["correct_count"] == 1
    assert overview["totals"]["answered_count"] == 2


# ---- TC-07: データ無し ----
def test_no_data(setup):
    overview = build_overview(setup["user_a2"], now=NOW)

    assert overview["has_data"] is False
    assert overview["today"] == {
        "study_seconds": 0, "answered_count": 0, "correct_count": 0, "accuracy_rate": None}
    assert overview["totals"]["accuracy_rate"] is None
    assert overview["streak"] == {"current_days": 0}
    assert len(overview["last_7_days"]) == 7
    assert all(d["answered_count"] == 0 for d in overview["last_7_days"])
    assert overview["weak_subjects"] == []


# ---- TC-08: 科目の選択 ----
def test_subject_filter(setup):
    user = setup["user_a"]
    _answers(user, setup["p_math"], 2, 2)
    _answers(user, setup["p_english"], 6, 1)
    client = _client(user)

    filtered = client.get(OVERVIEW, {"subject_id": setup["math"].id}).json()
    unfiltered = client.get(OVERVIEW).json()

    assert filtered["today"]["answered_count"] == 2
    assert filtered["totals"]["accuracy_rate"] == 1.0
    assert filtered["last_7_days"][-1]["answered_count"] == 2
    assert filtered["streak"] == {"current_days": 1}
    assert unfiltered["totals"]["answered_count"] == 8
    assert filtered["weak_subjects"] == unfiltered["weak_subjects"]
    assert filtered["recommendations"] == unfiltered["recommendations"]
    assert [w["subject_name"] for w in filtered["weak_subjects"]] == ["英語"]


# ---- TC-09: 不正な subject_id は同じ 400 ----
def test_invalid_subject_id_returns_same_400(setup):
    client = _client(setup["user_a"])
    missing = Subject.objects.order_by("-id").first().id + 1000

    responses = [
        client.get(OVERVIEW, {"subject_id": value})
        for value in ("abc", setup["subject_b"].id, setup["shared"].id, missing)]

    assert [r.status_code for r in responses] == [400, 400, 400, 400]
    assert all(r.json() == INVALID_SUBJECT_BODY for r in responses)


# ---- TC-10: 間違いやすい分野の境界 ----
def test_weak_subjects_rule(setup):
    user, org = setup["user_a"], setup["org_a"]
    plan = {"P": (4, 0), "Q": (5, 3), "R": (10, 7), "S": (5, 0), "T": (6, 3), "U": (5, 1)}
    for name, (total, correct) in plan.items():
        subject = Subject.objects.create(name=name, slug=f"i473-{name}", organization=org)
        _answers(user, _problem(subject, user, f"{name}の問題"), total, correct)

    weak = build_overview(user)["weak_subjects"]

    assert [(w["subject_name"], w["accuracy_rate"]) for w in weak] == [
        ("S", 0.0), ("U", 0.2), ("T", 0.5)]
    assert [w["answered_count"] for w in weak] == [5, 5, 6]


# ---- TC-11: おすすめ（引き継ぎ 1 を含む） ----
def test_recommendations(setup):
    user = setup["user_a"]
    _answers(user, setup["p_english"], 5, 1)
    _answers(user, setup["p_math"], 5, 5, at=timezone.now() - timedelta(days=10))
    StudyLog.objects.create(user=user, subject=None)  # NOT IN に NULL が混ざっても消えない

    recommendations = build_overview(user)["recommendations"]

    assert recommendations == [
        {"kind": "weak_subject", "subject_id": setup["english"].id, "subject_name": "英語",
         "reason": "正答率が 20% です。復習しましょう"},
        {"kind": "unstudied_subject", "subject_id": setup["math"].id, "subject_name": "数学",
         "reason": "この 7 日間、解いていません"},
    ]


def test_recommendations_limit(setup):
    """TC-11b: weak が 3 科目・unstudied が 2 科目なら、weak の 3 件だけ"""
    user, org = setup["user_a"], setup["org_a"]
    for name in ("W1", "W2", "W3"):
        subject = Subject.objects.create(name=name, slug=f"i473-{name}", organization=org)
        _answers(user, _problem(subject, user, f"{name}の問題"), 5, 0)
    # 数学・英語は選んでいて問題があり、この 7 日間に答えが無い（unstudied の候補）

    recommendations = build_overview(user)["recommendations"]

    assert len(recommendations) == 3
    assert {r["kind"] for r in recommendations} == {"weak_subject"}


# ---- TC-12: クエリ数がデータの量に依らない ----
def _count_queries(client):
    for alias in settings.CACHES:
        caches[alias].clear()
    with CaptureQueriesContext(connection) as context:
        response = client.get(OVERVIEW)
    assert response.status_code == 200
    return len(context.captured_queries)


def test_query_count_is_constant(setup):
    user, org = setup["user_a"], setup["org_a"]
    client = _client(user)
    _answer(user, setup["p_math"], correct=True)
    small = _count_queries(client)

    now = timezone.now()
    for i, name in enumerate(("Q1", "Q2", "Q3")):
        subject = Subject.objects.create(name=name, slug=f"i473-{name}", organization=org)
        UserSubjectAccess.objects.create(user=user, subject=subject)
        problem = _problem(subject, user, f"{name}の問題")
        for day in range(20):
            _answer(user, problem, correct=(day + i) % 3 == 0, seconds=40,
                    at=now - timedelta(days=day))
    large = _count_queries(client)

    assert small == large
    assert large == 9  # 実装後に数えた本数（I473）。増やすなら理由を計画書に書く


# ---- TC-13: 認可と組織の境界 ----
def test_requires_login(db):
    assert APIClient().get(OVERVIEW).status_code == 401


def test_only_own_answers_in_own_org(setup):
    user_a = setup["user_a"]
    _answer(user_a, setup["p_math"], correct=True)
    _answer(setup["user_a2"], setup["p_math"], correct=True)
    _answer(setup["user_b"], setup["p_b"], correct=True)
    _answers(user_a, setup["p_b"], 5, 0)  # 不具合で残った他組織の問題への答えの想定

    response = _client(user_a).get(OVERVIEW)

    data = response.json()
    assert data["totals"]["answered_count"] == 1
    assert "B科目" not in json.dumps(data, ensure_ascii=False)
    ids = {w["subject_id"] for w in data["weak_subjects"]}
    ids |= {r["subject_id"] for r in data["recommendations"]}
    assert setup["subject_b"].id not in ids


def test_user_without_organization(setup):
    user = setup["user_noorg"]
    _answer(user, setup["p_math"], correct=True)

    response = _client(user).get(OVERVIEW)

    assert response.status_code == 200
    data = response.json()
    assert data["has_data"] is False
    assert data["totals"]["answered_count"] == 0
    assert data["weak_subjects"] == []
    assert data["recommendations"] == []


# ---- TC-14: おすすめの経路は消した ----
def test_recommendations_route_removed(setup):
    assert _client(setup["user_a"]).get("/api/dashboard/recommendations/").status_code == 404


# ---- TC-16: 引き継ぎ 3（科目のキャッシュ） ----
def test_selected_subjects_cache_order_and_key(setup):
    user, org = setup["user_a"], setup["org_a"]
    # 名前の順と作った順がずれる科目を足す（あ は 数学・英語・理科 より前）
    late = Subject.objects.create(name="あ科目", slug="i473-late", organization=org)
    UserSubjectAccess.objects.create(user=user, subject=late)
    for alias in settings.CACHES:
        caches[alias].clear()

    from_db = list(subject_service.get_user_selected_subjects(user).values_list("id", flat=True))
    from_cache = list(
        subject_service.get_user_selected_subjects(user).values_list("id", flat=True))
    expected = list(Subject.objects.filter(
        organization=org, user_access__user=user).order_by("name").values_list("id", flat=True))

    assert from_db == from_cache == expected

    extra = Subject.objects.create(name="追加科目", slug="i473-extra", organization=org)
    UserSubjectAccess.objects.create(user=user, subject=extra)
    assert extra.id in set(
        subject_service.get_user_selected_subjects(user).values_list("id", flat=True))

    assert user_subjects_cache_key(1, 7, False) == "user_subjects_1_org_7_count_False"
