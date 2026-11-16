"""
I539 AC13: 学ぶ科目の API（GET・PUT /api/user/subjects/）が科目ごとの問題数を返す

- ダッシュボードが、問題の無い科目でクイズを始めさせない（エラーの通知で戻さない）ための数
- 数えるのは今の組織の科目だけ（組織を移った後の古い登録の科目は入らない）
- キャッシュは科目の番号だけなので、問題を足した直後も古い数を返さない
- 選択肢の数で問題数が膨らまない

TC-24（docs/tests/open/I539_auto_test.md）に対応。
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import Choice, Problem, Subject, UserSubjectAccess

User = get_user_model()

URL = "/api/user/subjects/"
# キャッシュを本当に通すため、どの置き場も LocMem にする（Redis が無い環境で素通りしない）
LOCMEM = {
    alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": f"i539-{alias}"}
    for alias in settings.CACHES
}


def _add_problem(subject, user, n):
    problem = Problem.objects.create(
        subject=subject, organization=subject.organization, created_by=user,
        question=f"{subject.name}の問題{n}", explanation="解説")
    for order in range(4):
        Choice.objects.create(problem=problem, text=f"選択肢{order}", is_correct=order == 0, order=order)
    return problem


@pytest.fixture
def world(db):
    category = OrganizationCategory.objects.create(name="I539分類", slug="i539-pc-cat")
    org_a = Organization.objects.create(name="I539組織A", slug="i539-pc-org-a", category=category)
    org_b = Organization.objects.create(name="I539組織B", slug="i539-pc-org-b", category=category)
    user = User.objects.create_user(
        email="i539_pc@example.com", user_id="i539_pc", password="pass",  # pragma: allowlist secret
        organization=org_a, role="user")
    x = Subject.objects.create(name="X科目", slug="i539-pc-x", organization=org_a)
    y = Subject.objects.create(name="Y科目", slug="i539-pc-y", organization=org_a)
    z = Subject.objects.create(name="Z科目", slug="i539-pc-z", organization=org_b)
    for n in range(2):
        _add_problem(x, user, n)
    for n in range(3):
        _add_problem(z, user, n)
    for subject in (x, y, z):
        # Z は組織を移った後の古い登録の形（他組織の科目）
        UserSubjectAccess.objects.create(user=user, subject=subject)
    client = APIClient()
    client.force_authenticate(user=user)
    return {"user": user, "x": x, "y": y, "client": client}


@override_settings(CACHES=LOCMEM)
def test_user_subjects_include_problem_count(world):
    w = world
    expected = [
        {"id": w["x"].id, "name": "X科目", "problem_count": 2},
        {"id": w["y"].id, "name": "Y科目", "problem_count": 0},
    ]

    get_response = w["client"].get(URL)
    assert get_response.status_code == 200
    assert get_response.json() == expected

    put_response = w["client"].put(URL, {"subject_ids": [w["x"].id, w["y"].id]}, format="json")
    assert put_response.status_code == 200
    assert put_response.json() == expected

    # キャッシュが温まった後に問題を足しても、古い数を返さない
    _add_problem(w["x"], w["user"], 99)
    again = w["client"].get(URL).json()
    assert again[0] == {"id": w["x"].id, "name": "X科目", "problem_count": 3}
