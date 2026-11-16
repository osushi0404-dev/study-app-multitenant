"""
I494: 利用者が学ぶ科目を選び直す API（PUT /api/user/subjects/・GET /api/user/subjects/available/）

- 自組織の科目だけを選べる。他組織・全体共有（組織なし）・存在しない番号は同じ 400 で断る
- 0 件は断る（最低 1 つ）。保存の後にキャッシュが古い一覧を返さない
- 書き換えは 1 つのトランザクション。サービスもシリアライザに依らず組織で絞る

TC-01〜TC-11（docs/tests/open/I494_auto_test.md）に対応。
"""
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from core.cache_service import cache_service
from core.subject_service import subject_service, user_subjects_cache_key
from problems.models import Subject, UserSubjectAccess
from problems.services.user_subject_service import replace_user_subjects

User = get_user_model()

URL = "/api/user/subjects/"
AVAILABLE_URL = "/api/user/subjects/available/"
MISSING_ID = 4949999
INVALID = "選択された科目の一部が無効です"
AT_LEAST_ONE = "科目を最低1つ選択してください"
# キャッシュを本当に通すため、どの置き場も LocMem にする（Redis が無い環境で素通りしない）
LOCMEM = {
    alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": f"i494-{alias}"}
    for alias in settings.CACHES
}


@pytest.fixture
def world(db):
    category = OrganizationCategory.objects.create(name="I494分類", slug="i494-cat")
    org_a = Organization.objects.create(name="I494組織A", slug="i494-org-a", category=category)
    org_b = Organization.objects.create(name="I494組織B", slug="i494-org-b", category=category)
    math = Subject.objects.create(name="数学", slug="i494-math", organization=org_a)
    english = Subject.objects.create(
        name="英語", slug="i494-english", organization=org_a, description="英文法")
    physics = Subject.objects.create(name="物理", slug="i494-physics", organization=org_a)
    b_math = Subject.objects.create(name="B数学", slug="i494-b-math", organization=org_b)
    shared = Subject.objects.create(name="共有科目", slug="i494-shared", organization=None)
    user_a = User.objects.create_user(
        email="user_a_i494@example.com", user_id="user_a_i494", password="pass",
        organization=org_a, role="user")
    user_none = User.objects.create_user(
        email="user_none_i494@example.com", user_id="user_none_i494", password="pass",
        organization=None, role="user")
    UserSubjectAccess.objects.create(user=user_a, subject=math)
    return {
        "org_a": org_a, "math": math, "english": english, "physics": physics,
        "b_math": b_math, "shared": shared, "user_a": user_a, "user_none": user_none,
    }


def _client(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def _selected(user):
    return set(UserSubjectAccess.objects.filter(user=user).values_list("subject_id", flat=True))


def _put(user, subject_ids=None, body=None):
    payload = {"subject_ids": subject_ids} if body is None else body
    return _client(user).put(URL, payload, format="json")


def _cached(key):
    return cache_service.get_subjects_cache(key) is not None


# ---- TC-01: 足して保存できる ----
def test_add_subject(world):
    w = world
    response = _put(w["user_a"], [w["math"].id, w["english"].id])

    assert response.status_code == 200
    # 名前の順（DB の並び。「数学」が「英語」より前）
    assert response.json() == [
        {"id": w["math"].id, "name": "数学"}, {"id": w["english"].id, "name": "英語"}]
    assert _selected(w["user_a"]) == {w["math"].id, w["english"].id}
    assert UserSubjectAccess.objects.get(
        user=w["user_a"], subject=w["english"]).granted_by == w["user_a"]


# ---- TC-02: 外して保存できる ----
def test_remove_subject(world):
    w = world
    UserSubjectAccess.objects.create(user=w["user_a"], subject=w["english"])

    response = _put(w["user_a"], [w["english"].id])

    assert response.status_code == 200
    assert response.json() == [{"id": w["english"].id, "name": "英語"}]
    assert _selected(w["user_a"]) == {w["english"].id}


# ---- TC-03: 他組織・全体共有・存在しない番号は同じ 400 で断る ----
def test_foreign_shared_missing_rejected_alike(world):
    w = world
    bodies = []
    for other in (w["b_math"].id, w["shared"].id, MISSING_ID):
        response = _put(w["user_a"], [w["math"].id, other])
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["sub_message"] == INVALID
        assert body["error"]["details"] == {"subject_ids": [INVALID]}
        bodies.append(body)
        assert _selected(w["user_a"]) == {w["math"].id}
    assert bodies[0] == bodies[1] == bodies[2]


# ---- TC-04: 0 件・キーなし・上限超えは断る ----
def test_empty_missing_and_too_many_rejected(world):
    w = world
    for body in ({"subject_ids": []}, {}):
        response = _put(w["user_a"], body=body)
        assert response.status_code == 400
        assert response.json()["error"]["details"]["subject_ids"] == [AT_LEAST_ONE]
    too_many = _put(w["user_a"], list(range(1, 202)))
    assert too_many.status_code == 400
    assert too_many.json()["error"]["details"]["subject_ids"] == ["選べる科目の数を超えています"]
    assert _selected(w["user_a"]) == {w["math"].id}


# ---- TC-05: 保存の後にキャッシュが古い一覧を返さない ----
@override_settings(CACHES=LOCMEM)
def test_cache_cleared_after_save(world, django_capture_on_commit_callbacks):
    w = world
    user, org = w["user_a"], w["org_a"]
    caches["default"].clear()
    keys = [user_subjects_cache_key(user.id, org.id, flag) for flag in (False, True)]

    assert _client(user).get(URL).json() == [{"id": w["math"].id, "name": "数学"}]
    list(subject_service.get_user_selected_subjects(user, annotate_count=True))
    # 正の対照: 保存の前に両方のキーに値が入っている（キャッシュを本当に通っている）
    assert all(_cached(k) for k in keys)

    # 足すだけ（bulk_create は post_save を送らないので、シグナルだけではキャッシュが残る）
    with django_capture_on_commit_callbacks(execute=True):
        assert _put(user, [w["math"].id, w["physics"].id]).status_code == 200

    assert not any(_cached(k) for k in keys)
    assert _client(user).get(URL).json() == [
        {"id": w["math"].id, "name": "数学"}, {"id": w["physics"].id, "name": "物理"}]


# ---- TC-06: 重複は 1 つにまとめる ----
def test_duplicates_collapsed(world):
    w = world
    response = _put(w["user_a"], [w["english"].id, w["english"].id])

    assert response.status_code == 200
    assert response.json() == [{"id": w["english"].id, "name": "英語"}]
    assert _selected(w["user_a"]) == {w["english"].id}


# ---- TC-07: 未認証は 401 ----
def test_unauthenticated(world):
    assert _client().put(URL, {"subject_ids": [world["math"].id]}, format="json").status_code == 401
    assert _client().get(AVAILABLE_URL).status_code == 401


# ---- TC-08: 組織の科目を全件・名前の順で返す ----
def test_available_lists_own_org_only(world):
    w = world
    for i in range(22):
        Subject.objects.create(name=f"追加{i:02d}", slug=f"i494-extra-{i}", organization=w["org_a"])

    response = _client(w["user_a"]).get(AVAILABLE_URL)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 25
    assert all(set(item) == {"id", "name", "description"} for item in body)
    expected = list(Subject.objects.filter(organization=w["org_a"]).order_by("name")
                    .values_list("id", flat=True))
    assert [item["id"] for item in body] == expected
    assert {w["b_math"].id, w["shared"].id}.isdisjoint(item["id"] for item in body)
    assert next(item for item in body if item["id"] == w["english"].id)["description"] == "英文法"


# ---- TC-09: 組織の無い利用者は全体共有の科目も選べず、一覧も空 ----
def test_user_without_org(world):
    w = world
    user = w["user_none"]
    for subject in (w["math"], w["shared"]):
        response = _put(user, [subject.id])
        assert response.status_code == 400
        assert response.json()["error"]["sub_message"] == INVALID
    replace_user_subjects(user=user, subject_ids=[w["shared"].id])
    assert _selected(user) == set()

    response = _client(user).get(AVAILABLE_URL)
    assert response.status_code == 200
    assert response.json() == []


# ---- TC-10: 同じ内容の保存は行に触らない ----
def test_same_selection_keeps_rows(world):
    w = world
    before = UserSubjectAccess.objects.get(user=w["user_a"], subject=w["math"])

    for _ in range(2):
        response = _put(w["user_a"], [w["math"].id])
        assert response.status_code == 200
        assert response.json() == [{"id": w["math"].id, "name": "数学"}]

    after = UserSubjectAccess.objects.get(user=w["user_a"], subject=w["math"])
    assert (after.pk, after.granted_at) == (before.pk, before.granted_at)


# ---- TC-10b: サービスは呼び出し元に依らず組織の外を書かない ----
def test_service_filters_by_org(world):
    w = world
    replace_user_subjects(
        user=w["user_a"], subject_ids=[w["english"].id, w["b_math"].id, w["shared"].id])

    assert _selected(w["user_a"]) == {w["english"].id}


# ---- TC-11: 途中で失敗したら元のまま ----
def test_rollback_on_failure(world):
    w = world
    with mock.patch.object(UserSubjectAccess.objects, "bulk_create", side_effect=RuntimeError):
        with pytest.raises(RuntimeError):
            replace_user_subjects(user=w["user_a"], subject_ids=[w["english"].id])

    assert _selected(w["user_a"]) == {w["math"].id}
