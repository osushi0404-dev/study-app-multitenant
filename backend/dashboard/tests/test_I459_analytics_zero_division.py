"""
I459: 学習統計（GET /api/dashboard/analytics/）の days の入力の確かめ。

- days は 1〜365 の整数（省略時 30）。不正な値は 400
（おすすめの TC-05 は I473 で経路を消したので削除。週の正答率の TC-01・02 は I488 で集計元を
 クイズの答えに替えたので削除。0 件で割らないことは test_I488_analytics.py〔答えの無い区切りは null〕が見る）

TC-03・TC-04・TC-06（docs/tests/open/I459_auto_test.md）に対応。TC-04 は I488 の新しい形で確かめる。
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory

User = get_user_model()

ANALYTICS = "/api/dashboard/analytics/"
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


@pytest.mark.parametrize("days", ["abc", "1.5", "0", "-1", "366"])
def test_invalid_days_returns_400(client, days):
    """TC-03: days が整数でない・1 未満・365 を超えると同じ 400"""
    response = client.get(ANALYTICS, {"days": days})

    assert response.status_code == 400
    assert response.json() == INVALID_DAYS_BODY


@pytest.mark.parametrize("query, expected_days, granularity, trend_len", [
    ({}, 30, "day", 30),
    ({"days": ""}, 30, "day", 30),
    ({"days": "1"}, 1, "day", 1),
    ({"days": "365"}, 365, "month", None),  # 月の区切りの数は今日の日付で 13 か 12
])
def test_valid_days_returns_200(client, query, expected_days, granularity, trend_len):
    """TC-04: 省略・空は 30 日、1 と 365 は通る（期間は今日を含む days 日・I488）"""
    response = client.get(ANALYTICS, query)

    assert response.status_code == 200
    period = response.json()["period"]
    assert (period["days"], period["granularity"]) == (expected_days, granularity)
    if trend_len is not None:
        assert len(response.json()["trend"]) == trend_len


def test_analytics_requires_login(db):
    """TC-06: ログインしていなければ 401"""
    response = APIClient().get(ANALYTICS)

    assert response.status_code == 401
