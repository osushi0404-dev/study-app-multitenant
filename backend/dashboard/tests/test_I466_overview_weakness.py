"""
I466: ダッシュボードの overview に難易度別の苦手（weak_difficulties）と急いだ間違い（rushed_mistakes）

TC-07〜TC-09（docs/tests/open/I466_auto_test.md）に対応。
"""
from unittest import mock

import pytest
from django.conf import settings
from django.core.cache import caches
from rest_framework.test import APIClient

from problems.tests.i466_data import (
    EASY, HARD, MEDIUM, NOW, answers, days_ago, make_problem, make_world,
)

OVERVIEW = "/api/dashboard/overview/"
TOP_KEYS = {
    "has_data", "today", "streak", "totals", "last_7_days", "weak_subjects",
    "recommendations", "weak_difficulties", "rushed_mistakes",
}


def _clear_all_caches():
    for alias in settings.CACHES:
        caches[alias].clear()


@pytest.fixture(autouse=True)
def _clear_caches():
    _clear_all_caches()
    yield
    _clear_all_caches()


@pytest.fixture
def world(db):
    w = make_world()
    user = w["user_a"]
    # TC-02 の難易度別のデータ（初級 83%・中級 40%・上級 30%）
    answers(user, make_problem(w["math"], user, "易", EASY), 6, 5, seconds=40, at=days_ago(1))
    answers(user, make_problem(w["math"], user, "中", MEDIUM), 5, 2, seconds=40, at=days_ago(1))
    hard = make_problem(w["english"], user, "難", HARD)
    answers(user, hard, 6, 3, seconds=40, at=days_ago(1))
    # 急いだ間違い（上級の不正解 4 問を 5 秒）: 21 問・間違い 1+3+3+4=11・平均の半分未満の間違い 4
    answers(user, hard, 4, 0, seconds=5, at=days_ago(1))
    return w


def _get(user, params=None):
    client = APIClient()
    client.force_authenticate(user=user)
    with mock.patch("dashboard.selectors.timezone.now", return_value=NOW):
        return client.get(OVERVIEW, params or {})


def test_contract_includes_weakness_keys(world):
    """TC-07"""
    response = _get(world["user_a"])
    assert response.status_code == 200
    data = response.json()
    assert set(data) == TOP_KEYS
    assert data["weak_difficulties"] == [
        {"difficulty": "hard", "answered_count": 10, "accuracy_rate": 0.3},
        {"difficulty": "medium", "answered_count": 5, "accuracy_rate": 0.4},
    ]
    assert set(data["rushed_mistakes"]) == {"mistake_count", "rushed_count", "rushed_rate"}
    assert data["rushed_mistakes"] == {"mistake_count": 11, "rushed_count": 4, "rushed_rate": 0.3636}

    assert APIClient().get(OVERVIEW).status_code == 401


def test_subject_selection_does_not_change_weakness(world):
    """TC-08"""
    all_subjects = _get(world["user_a"]).json()
    math_only = _get(world["user_a"], {"subject_id": world["math"].id}).json()
    assert math_only["weak_difficulties"] == all_subjects["weak_difficulties"]
    assert math_only["rushed_mistakes"] == all_subjects["rushed_mistakes"]


def test_no_weakness_for_user_without_answers(world):
    """TC-09"""
    data = _get(world["user_a2"]).json()
    assert data["weak_difficulties"] == []
    assert data["rushed_mistakes"] is None
