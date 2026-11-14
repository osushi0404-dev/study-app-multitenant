"""
I488: 学習統計（GET /api/dashboard/analytics/）をクイズの答えの記録（QuizAnswer）から出す。

- 数え方はダッシュボード（I473）と同じ（1 問 300 秒まで・日本時間・今日の復習の回も含める）
- 期間（今日を含む days 日）と区切り（31 日以下は日・180 日以下は週〔月曜始まり〕・それより上は月。端は期間で切る）
- 応答の形（契約）・科目の選択・不正な subject_id の 400・組織の境界・クエリ数

TC-01〜TC-12（docs/tests/open/I488_auto_test.md）に対応。
"""
import json
from datetime import date, datetime, timedelta
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
from dashboard.selectors import _granularity, build_analytics
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject

User = get_user_model()

ANALYTICS = "/api/dashboard/analytics/"
JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 11, 14, 8, 0, tzinfo=JST)  # 土曜
INVALID_SUBJECT_BODY = {
    "error": {
        "main_message": "科目の指定が正しくありません",
        "sub_message": "学習統計の科目の選択からやり直してください",
        "details": {},
    }
}
INVALID_DAYS_MAIN = "期間の指定が正しくありません"
# 1 回の表示のクエリ数（2026-11-14 に実測。日ごと・科目別・有無の 3 本、科目の指定があれば科目の確かめで +1）
QUERIES_WITHOUT_SUBJECT = 3
QUERIES_WITH_SUBJECT = 4


@pytest.fixture(autouse=True)
def _clear_caches():
    """Redis があるときに、利用者 ID が同じ別テストの cache を拾わない"""
    for alias in settings.CACHES:
        caches[alias].clear()
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


def _jst(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=JST)


def _problem(subject, user, question):
    problem = Problem.objects.create(
        subject=subject, organization=subject.organization, created_by=user,
        question=question, problem_type="single", difficulty=1, explanation="解説",
    )
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    return problem


def _answer(user, problem, *, correct, seconds=0, at=None):
    """1 問の答え（セッションは答えごとに作る。QuizAnswer は同じセッション・同じ問題で 1 件まで）"""
    session = QuizSession.objects.create(user=user, subject=problem.subject, is_active=False)
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
    cat = OrganizationCategory.objects.create(name="テストI488", slug="test-cat-i488")
    org_a = Organization.objects.create(
        name="組織I488A", slug="org-i488-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織I488B", slug="org-i488-b", type="school", category=cat, is_active=True)
    user_a = User.objects.create_user(
        email="a_i488@example.com", user_id="a_i488", password="pass",
        organization=org_a, role="user")
    user_a2 = User.objects.create_user(
        email="a2_i488@example.com", user_id="a2_i488", password="pass",
        organization=org_a, role="user")
    user_b = User.objects.create_user(
        email="b_i488@example.com", user_id="b_i488", password="pass",
        organization=org_b, role="user")
    user_noorg = User.objects.create_user(
        email="n_i488@example.com", user_id="n_i488", password="pass",
        organization=None, role="user")
    math = Subject.objects.create(name="数学", slug="i488-math", organization=org_a)
    english = Subject.objects.create(name="英語", slug="i488-english", organization=org_a)
    subject_b = Subject.objects.create(name="B科目", slug="i488-b", organization=org_b)
    shared = Subject.objects.create(name="共有科目I488", slug="i488-shared", organization=None)
    return {
        "org_a": org_a, "user_a": user_a, "user_a2": user_a2, "user_b": user_b,
        "user_noorg": user_noorg, "math": math, "english": english,
        "subject_b": subject_b, "shared": shared,
        "p_math": _problem(math, user_a, "数学の問題"),
        "p_english": _problem(english, user_a, "英語の問題"),
        "p_b": _problem(subject_b, user_b, "B科目の問題"),
    }


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _bucket(analytics, start):
    return next(b for b in analytics["trend"] if b["start_date"] == start)


def _counts(bucket):
    return {k: bucket[k] for k in ("study_seconds", "answered_count", "correct_count", "accuracy_rate")}


# ---- TC-01: 契約（キーと型） ----
def test_contract_keys_and_types(setup):
    user = setup["user_a"]
    _answers(user, setup["p_english"], 3, 1, seconds=20)

    response = _client(user).get(ANALYTICS)

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"has_data", "period", "totals", "trend", "subject_breakdown"}
    assert set(data["period"]) == {"days", "start_date", "end_date", "granularity"}
    assert set(data["totals"]) == {
        "study_seconds", "answered_count", "correct_count", "accuracy_rate", "studied_days"}
    assert set(data["trend"][0]) == {
        "start_date", "end_date", "study_seconds", "answered_count", "correct_count",
        "accuracy_rate"}
    assert set(data["subject_breakdown"][0]) == {
        "subject_id", "subject_name", "study_seconds", "answered_count", "correct_count",
        "accuracy_rate"}
    assert isinstance(data["has_data"], bool)
    assert isinstance(data["subject_breakdown"][0]["subject_id"], int)
    for old_key in ("daily_data", "subject_distribution", "performance_trends", "mistake_patterns"):
        assert old_key not in data


# ---- TC-02: 期待値と 300 秒の上限 ----
def test_expected_values_and_cap(setup):
    user, p_math = setup["user_a"], setup["p_math"]
    _answer(user, p_math, correct=True, seconds=10, at=_jst(2026, 11, 14, 7))
    _answer(user, p_math, correct=True, seconds=20, at=_jst(2026, 11, 14, 7))
    _answer(user, p_math, correct=False, seconds=400, at=_jst(2026, 11, 14, 7))
    _answer(user, setup["p_english"], correct=True, seconds=30, at=_jst(2026, 11, 10))
    _answer(user, p_math, correct=True, seconds=50, at=_jst(2026, 10, 15))  # 範囲の外（1 日前）

    data = build_analytics(user, 30, now=NOW)

    assert data["period"] == {
        "days": 30, "start_date": date(2026, 10, 16), "end_date": date(2026, 11, 14),
        "granularity": "day"}
    assert data["totals"] == {
        "study_seconds": 360, "answered_count": 4, "correct_count": 3,
        "accuracy_rate": 0.75, "studied_days": 2}
    assert len(data["trend"]) == 30
    first = data["trend"][0]
    assert first["start_date"] == first["end_date"] == date(2026, 10, 16)
    starts = [b["start_date"] for b in data["trend"]]
    assert starts == sorted(starts)
    assert _counts(_bucket(data, date(2026, 11, 14))) == {
        "study_seconds": 330, "answered_count": 3, "correct_count": 2, "accuracy_rate": 0.6667}
    assert _counts(_bucket(data, date(2026, 10, 16))) == {
        "study_seconds": 0, "answered_count": 0, "correct_count": 0, "accuracy_rate": None}
    assert data["has_data"] is True


# ---- TC-03: 区切りの境目（週は月曜始まり・月は暦の月・端は期間で切る） ----
def test_week_buckets(setup):
    user, p = setup["user_a"], setup["p_math"]
    _answer(user, p, correct=True, at=_jst(2026, 11, 8))   # 日曜
    _answer(user, p, correct=True, at=_jst(2026, 11, 9))   # 月曜
    _answer(user, p, correct=True, at=_jst(2026, 11, 9))
    _answer(user, p, correct=True, at=_jst(2026, 8, 17))   # 期間の最初の日（月曜）
    _answer(user, p, correct=True, at=_jst(2026, 8, 16))   # 範囲の外

    data = build_analytics(user, 90, now=NOW)

    assert data["period"]["granularity"] == "week"
    assert len(data["trend"]) == 13
    first = data["trend"][0]
    assert (first["start_date"], first["end_date"]) == (date(2026, 8, 17), date(2026, 8, 23))
    assert first["answered_count"] == 1
    week = _bucket(data, date(2026, 11, 2))
    assert (week["end_date"], week["answered_count"]) == (date(2026, 11, 8), 1)
    last = data["trend"][-1]
    assert (last["start_date"], last["end_date"]) == (date(2026, 11, 9), date(2026, 11, 14))
    assert last["answered_count"] == 2
    assert data["totals"]["answered_count"] == 4


def test_month_buckets(setup):
    user, p = setup["user_a"], setup["p_math"]
    _answer(user, p, correct=True, at=_jst(2025, 11, 15))  # 期間の最初の日
    _answer(user, p, correct=True, at=_jst(2025, 11, 14))  # 範囲の外
    _answer(user, p, correct=True, at=_jst(2026, 10, 31))
    _answer(user, p, correct=True, at=_jst(2026, 11, 1))
    _answer(user, p, correct=True, at=_jst(2026, 11, 1))

    data = build_analytics(user, 365, now=NOW)

    assert data["period"]["granularity"] == "month"
    assert len(data["trend"]) == 13
    first, last = data["trend"][0], data["trend"][-1]
    assert (first["start_date"], first["end_date"]) == (date(2025, 11, 15), date(2025, 11, 30))
    assert first["answered_count"] == 1
    october = _bucket(data, date(2026, 10, 1))
    assert (october["end_date"], october["answered_count"]) == (date(2026, 10, 31), 1)
    assert (last["start_date"], last["end_date"]) == (date(2026, 11, 1), date(2026, 11, 14))
    assert last["answered_count"] == 2
    assert data["totals"]["answered_count"] == 4


# ---- TC-04: 日本時間の日付の境界 ----
def test_dates_are_japan_time(setup):
    user, p = setup["user_a"], setup["p_math"]
    _answer(user, p, correct=True, at=_jst(2026, 11, 13, 23, 30))
    _answer(user, p, correct=True, at=_jst(2026, 11, 14, 0, 30))  # UTC では 11-13 15:30

    data = build_analytics(user, 7, now=NOW)

    assert data["period"]["granularity"] == "day"
    assert [b["start_date"] for b in data["trend"]] == [date(2026, 11, d) for d in range(8, 15)]
    assert _bucket(data, date(2026, 11, 13))["answered_count"] == 1
    assert _bucket(data, date(2026, 11, 14))["answered_count"] == 1
    assert data["totals"]["studied_days"] == 2


# ---- TC-05: days ごとの区切り ----
@pytest.mark.parametrize("days, expected", [
    (1, "day"), (7, "day"), (30, "day"), (31, "day"), (32, "week"), (90, "week"),
    (180, "week"), (181, "month"), (365, "month"),
])
def test_granularity_by_days(days, expected):
    assert _granularity(days) == expected


# ---- TC-06: 科目の選択 ----
def test_subject_filter(setup):
    user = setup["user_a"]
    _answers(user, setup["p_math"], 2, 2, seconds=10)
    _answers(user, setup["p_english"], 4, 1, seconds=10)
    client = _client(user)

    data = client.get(ANALYTICS, {"subject_id": setup["math"].id}).json()
    all_data = client.get(ANALYTICS).json()

    assert data["totals"]["answered_count"] == 2
    assert data["totals"]["accuracy_rate"] == 1.0
    assert sum(b["answered_count"] for b in data["trend"]) == 2
    assert data["subject_breakdown"] == all_data["subject_breakdown"]
    assert {s["subject_name"] for s in data["subject_breakdown"]} == {"数学", "英語"}


# ---- TC-07: 不正な入力は同じ 400 ----
def test_invalid_subject_returns_same_400(setup):
    client = _client(setup["user_a"])
    missing = Subject.objects.order_by("-id").first().id + 1000
    for value in ("abc", setup["subject_b"].id, setup["shared"].id, missing):
        response = client.get(ANALYTICS, {"subject_id": value})
        assert response.status_code == 400, value
        assert response.json() == INVALID_SUBJECT_BODY, value

    response = _client(setup["user_noorg"]).get(ANALYTICS, {"subject_id": setup["math"].id})
    assert response.status_code == 400
    assert response.json() == INVALID_SUBJECT_BODY

    response = client.get(ANALYTICS, {"days": "abc", "subject_id": "abc"})
    assert response.status_code == 400
    assert response.json()["error"]["main_message"] == INVALID_DAYS_MAIN


# ---- TC-08: 認可と境界 ----
def test_requires_login(db):
    assert APIClient().get(ANALYTICS).status_code == 401


def test_only_own_answers_in_own_org(setup):
    user = setup["user_a"]
    _answer(user, setup["p_math"], correct=True)
    _answer(setup["user_a2"], setup["p_math"], correct=True)
    _answer(setup["user_b"], setup["p_b"], correct=True)
    _answers(user, setup["p_b"], 3, 0, seconds=30)  # 不具合で残った他組織の問題への答えの想定

    response = _client(user).get(ANALYTICS)

    assert response.status_code == 200
    data = response.json()
    assert data["totals"]["answered_count"] == 1
    assert "B科目" not in json.dumps(data, ensure_ascii=False)
    assert setup["subject_b"].id not in {s["subject_id"] for s in data["subject_breakdown"]}


def test_user_without_org_sees_nothing(setup):
    user = setup["user_noorg"]
    _answer(user, setup["p_math"], correct=True)

    response = _client(user).get(ANALYTICS)

    assert response.status_code == 200
    data = response.json()
    assert data["has_data"] is False
    assert data["totals"]["answered_count"] == 0
    assert data["subject_breakdown"] == []


# ---- TC-09: データ無し ----
def test_no_data(setup):
    data = _client(setup["user_a2"]).get(ANALYTICS, {"days": 7}).json()

    assert data["has_data"] is False
    assert data["totals"] == {
        "study_seconds": 0, "answered_count": 0, "correct_count": 0,
        "accuracy_rate": None, "studied_days": 0}
    assert len(data["trend"]) == 7
    empty = {"study_seconds": 0, "answered_count": 0, "correct_count": 0, "accuracy_rate": None}
    assert all(_counts(b) == empty for b in data["trend"])
    assert data["subject_breakdown"] == []


# ---- TC-10: 期間に答えが無い（全期間ではある） ----
def test_no_answers_in_period(setup):
    user = setup["user_a"]
    _answer(user, setup["p_math"], correct=True, at=timezone.now() - timedelta(days=40))

    data = _client(user).get(ANALYTICS, {"days": 30}).json()

    assert data["has_data"] is True
    assert data["totals"]["answered_count"] == 0
    assert data["subject_breakdown"] == []


# ---- TC-11: 科目別の並びと値 ----
def test_subject_breakdown_order(setup):
    user, org_a = setup["user_a"], setup["org_a"]
    science = Subject.objects.create(name="理科", slug="i488-science", organization=org_a)
    chemistry = Subject.objects.create(name="化学", slug="i488-chemistry", organization=org_a)
    at = _jst(2026, 11, 10)
    for correct in (True, True, False):
        _answer(user, setup["p_math"], correct=correct, seconds=100, at=at)
    _answers(user, setup["p_english"], 2, 0, seconds=400, at=at)
    _answer(user, _problem(science, user, "理科の問題"), correct=True, seconds=100, at=at)
    _answer(user, _problem(chemistry, user, "化学の問題"), correct=False, seconds=100, at=at)

    breakdown = build_analytics(user, 30, now=NOW)["subject_breakdown"]

    assert [s["subject_name"] for s in breakdown] == ["英語", "数学", "化学", "理科"]
    english, math = breakdown[0], breakdown[1]
    assert (english["study_seconds"], english["answered_count"], english["accuracy_rate"]) == (
        600, 2, 0.0)
    assert (math["study_seconds"], math["answered_count"], math["accuracy_rate"]) == (
        300, 3, 0.6667)


# ---- TC-12: クエリ数が期間・データの量に依らない ----
def _count_queries(client, params):
    for alias in settings.CACHES:
        caches[alias].clear()
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(ANALYTICS, params)
    assert response.status_code == 200
    return len(ctx.captured_queries)


def test_query_count_is_constant(setup):
    small, large = setup["user_a"], setup["user_a2"]
    _answer(small, setup["p_math"], correct=True)
    social = Subject.objects.create(name="社会", slug="i488-social", organization=setup["org_a"])
    problems = [setup["p_math"], setup["p_english"], _problem(social, large, "社会の問題")]
    for i in range(120):
        _answer(large, problems[i % 3], correct=i % 2 == 0, seconds=60,
                at=timezone.now() - timedelta(days=i * 200 // 120))

    for subject, limit in ((None, QUERIES_WITHOUT_SUBJECT), (setup["math"], QUERIES_WITH_SUBJECT)):
        counts = []
        for user in (small, large):
            client = _client(user)
            for days in (7, 365):
                params = {"days": days}
                if subject is not None:
                    params["subject_id"] = subject.id
                counts.append(_count_queries(client, params))
        assert len(set(counts)) == 1, counts
        assert counts[0] <= limit, counts
