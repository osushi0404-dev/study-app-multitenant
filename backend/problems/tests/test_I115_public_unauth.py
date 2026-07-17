"""
I115: SubjectViewSet.public の未認証 401 バグ修正の回帰テスト。

- get_permissions() の override が @action(permission_classes=[AllowAny]) を無効化し、
  未認証の GET /api/subjects/public/ が 401 になっていた（登録画面の科目取得が壊れる）。
- 修正後は両ルート（/api/subjects/public/・/api/organizations/subjects/public/）で
  未認証 200 を返す。テナントスコープ・露出フィールド・レガシー slug 変換も固定する。

TC-AUTO-01/03/05（docs/tests/open/I115_auto_test.md）に対応。
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from problems.models import Subject
from accounts.models import Organization, OrganizationCategory

BOTH_ROUTES = ["/api/subjects/public/", "/api/organizations/subjects/public/"]


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI115", slug="test-cat-i115")
    org_a = Organization.objects.create(name="組織A_I115", slug="org-a-i115", category=cat)
    org_b = Organization.objects.create(name="組織B_I115", slug="org-b-i115", category=cat)
    sub_a1 = Subject.objects.create(name="科目A1_I115", slug="subj-a1-i115", organization=org_a)
    sub_a2 = Subject.objects.create(name="科目A2_I115", slug="subj-a2-i115", organization=org_a)
    sub_b1 = Subject.objects.create(name="科目B1_I115", slug="subj-b1-i115", organization=org_b)
    return {"org_a": org_a, "org_b": org_b,
            "sub_a1": sub_a1, "sub_a2": sub_a2, "sub_b1": sub_b1}


# ---- TC-AUTO-01: 未認証 200 + テナントスコープ + 露出フィールド（両ルート） ----
@pytest.mark.django_db
@pytest.mark.parametrize("route", BOTH_ROUTES)
def test_public_unauth_200_tenant_scoped(setup, route):
    client = APIClient()
    resp = client.get(f"{route}?slug=org-a-i115")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # テナントスコープ: org_b の科目（科目B1_I115）が混入しない
    assert {s["name"] for s in data} == {"科目A1_I115", "科目A2_I115"}
    # 露出フィールドは id/name/description の3つに固定（過剰露出なし）
    for subject in data:
        assert set(subject.keys()) == {"id", "name", "description"}


# ---- TC-AUTO-03: 存在しない slug は空リスト 200（両ルート・既存挙動不変） ----
@pytest.mark.django_db
@pytest.mark.parametrize("route", BOTH_ROUTES)
def test_public_unknown_slug_empty_200(setup, route):
    client = APIClient()
    resp = client.get(f"{route}?slug=no-such-org-i115")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


# ---- TC-AUTO-05: レガシー slug 変換（未指定/'register'→'personal'）の既存挙動不変 ----
@pytest.mark.django_db
@pytest.mark.parametrize("route", BOTH_ROUTES)
@pytest.mark.parametrize("query", ["", "?slug=register"])
def test_public_legacy_slug_resolves_personal(setup, route, query):
    # 両者とも 'personal' に解決される。personal 組織はマイグレーション 0014 で作成され
    # 科目を持たないため空リスト（組織が無い環境でも同じく空リスト）で決定論的。
    client = APIClient()
    resp = client.get(f"{route}{query}")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []
