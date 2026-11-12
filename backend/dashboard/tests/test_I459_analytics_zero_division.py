"""
I459: 学習統計（GET /api/dashboard/analytics/）が、解いた問題が 0 件の日があっても 500 にならない。

- 週ごとの正答率は「週の正解数の合計 ÷ 週の解いた問題数の合計 × 100」（週の合計が 0 問なら 0）
- days は 1〜365 の整数（省略時 30）。不正な値は 400
- おすすめ（recommendations）は 0 問の学習記録があっても 0 で割らない

TC-01〜TC-06（docs/tests/open/I459_auto_test.md）に対応。
"""
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import Subject
from studylogs.models import DailyStudySummary, StudyLog

User = get_user_model()

ANALYTICS = "/api/dashboard/analytics/"
RECOMMENDATIONS = "/api/dashboard/recommendations/"
INVALID_DAYS_BODY = {
    "error": {
        "main_message": "期間の指定が正しくありません",
        "sub_message": "日数は 1〜365 の整数で指定してください",
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


@pytest.fixture
def org(db):
    cat = OrganizationCategory.objects.create(name="テストI459", slug="test-cat-i459")
    return Organization.objects.create(
        name="組織I459", slug="org-i459", type="school", category=cat, is_active=True)


@pytest.fixture
def user(org):
    return User.objects.create_user(
        email="u_i459@example.com", user_id="u_i459", password="pass",
        organization=org, role="user",
    )


@pytest.fixture
def client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _today():
    return timezone.now().date()


def _summary(user, days_ago, attempted, correct, study_time=0):
    return DailyStudySummary.objects.create(
        user=user, date=_today() - timedelta(days=days_ago),
        total_problems_attempted=attempted, total_problems_correct=correct,
        total_study_time=study_time,
    )


def test_zero_problem_day_in_week(client, user):
    """TC-01: 0 問の日を含む週で 200・正答率は週の合計で割る"""
    _summary(user, 6, attempted=10, correct=8)
    _summary(user, 5, attempted=1, correct=0)
    _summary(user, 4, attempted=0, correct=0, study_time=600)

    response = client.get(ANALYTICS, {"days": 6})

    assert response.status_code == 200
    trends = response.json()["performance_trends"]
    assert len(trends) == 1
    assert trends[0]["week_start"] == (_today() - timedelta(days=6)).isoformat()
    assert trends[0]["avg_accuracy"] == 72.73
    zero_day = next(
        d for d in response.json()["daily_data"]
        if d["date"] == (_today() - timedelta(days=4)).isoformat())
    assert zero_day["problems_attempted"] == 0
    assert zero_day["accuracy"] == 0


def test_week_without_problems_is_zero(client, user):
    """TC-02: 0 問の日だけの週・まとめが無い週は 0"""
    _summary(user, 13, attempted=0, correct=0, study_time=600)

    response = client.get(ANALYTICS, {"days": 13})

    assert response.status_code == 200
    trends = response.json()["performance_trends"]
    assert len(trends) == 2
    assert [week["avg_accuracy"] for week in trends] == [0, 0]


@pytest.mark.parametrize("days", ["abc", "1.5", "0", "-1", "366"])
def test_invalid_days_returns_400(client, days):
    """TC-03: days が整数でない・1 未満・365 を超えると同じ 400"""
    response = client.get(ANALYTICS, {"days": days})

    assert response.status_code == 400
    assert response.json() == INVALID_DAYS_BODY


@pytest.mark.parametrize("query, expected_days", [
    ({}, 31),
    ({"days": ""}, 31),
    ({"days": "1"}, 2),
    ({"days": "365"}, 366),
])
def test_valid_days_returns_200(client, query, expected_days):
    """TC-04: 省略・空は 30 日、1 と 365 は通る（daily_data は両端を含む）"""
    response = client.get(ANALYTICS, query)

    assert response.status_code == 200
    assert len(response.json()["daily_data"]) == expected_days


def test_recommendations_with_zero_problem_log(client, user, org):
    """TC-05: 0 問の学習記録があっても、おすすめは 0 で割らない"""
    subject_zero = Subject.objects.create(name="科目I459ゼロ", slug="subj-i459-zero", organization=org)
    subject_low = Subject.objects.create(name="科目I459低", slug="subj-i459-low", organization=org)
    StudyLog.objects.create(
        user=user, subject=subject_zero, problems_attempted=0, problems_correct=0, duration=60)
    StudyLog.objects.create(
        user=user, subject=subject_low, problems_attempted=4, problems_correct=1, duration=60)

    response = client.get(RECOMMENDATIONS)

    assert response.status_code == 200
    # 正答率が低い科目の項目（未学習の科目の項目は current_accuracy が None）
    with_accuracy = [
        r for r in response.json()["recommendations"] if r["current_accuracy"] is not None]
    assert [(r["subject_id"], r["current_accuracy"]) for r in with_accuracy] == [
        (str(subject_low.id), 25.0)]


def test_analytics_requires_login(db):
    """TC-06: ログインしていなければ 401"""
    response = APIClient().get(ANALYTICS)

    assert response.status_code == 401
