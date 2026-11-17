"""
I466: 使われない分析の API（間違い分析・適応的な問題選択）の経路を消した

TC-30（docs/tests/open/I466_auto_test.md）に対応。
"""
import pytest
from rest_framework.test import APIClient

from problems.tests.i466_data import make_world

REMOVED = [
    ("get", "/api/study/mistake-analysis/analyze/"),
    ("get", "/api/study/mistake-analysis/patterns/"),
    ("post", "/api/study/mistake-analysis/refresh_analysis/"),
    ("get", "/api/study/adaptive-learning/proficiency_analysis/"),
    ("post", "/api/study/adaptive-learning/select_problems/"),
    ("get", "/api/study/adaptive-learning/learning_path/"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("method,path", REMOVED)
def test_removed_routes_are_404(method, path):
    client = APIClient()
    client.force_authenticate(user=make_world()["user_a"])
    assert getattr(client, method)(path, {}, format="json").status_code == 404
