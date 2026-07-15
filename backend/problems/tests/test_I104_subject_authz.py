"""
I104: 科目管理（SubjectViewSet）の更新系を組織管理者（role=='admin'）限定にする認可回帰テスト。

- 非admin（role='user'）は更新系（create/update/partial_update/destroy）で 403
- 非admin も参照系（list/retrieve）は 200（I102 との差異＝参照は全ユーザー維持）
- 未認証は 401（IsAuthenticated が IsOrgAdmin より前に遮断）
- admin（role='admin'）は create=201 / update=200 / destroy=204

TC-AUTO-01〜05（docs/tests/open/I104_auto_test.md）に対応。
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from problems.models import Subject
from accounts.models import Organization, OrganizationCategory

User = get_user_model()


@pytest.fixture
def category(db):
    return OrganizationCategory.objects.create(name="テストI104", slug="test-cat-i104")


@pytest.fixture
def setup(db, category):
    org = Organization.objects.create(name="組織A_I104", slug="org-a-i104", category=category)
    admin = User.objects.create_user(
        email="admin_i104@example.com", user_id="admin_i104", password="pass",
        organization=org, role="admin",
    )
    normal = User.objects.create_user(
        email="user_i104@example.com", user_id="user_i104", password="pass",
        organization=org, role="user",
    )
    subject = Subject.objects.create(name="科目A_I104", slug="subject-a-i104", organization=org)
    return {"org": org, "admin": admin, "normal": normal, "subject": subject}


# ---- TC-AUTO-01: 非admin は更新系（PUT/PATCH/DELETE）で 403・DB 未改変 ----
@pytest.mark.django_db
def test_non_admin_cannot_mutate(setup):
    client = APIClient()
    client.force_authenticate(user=setup["normal"])
    sid = setup["subject"].id
    assert client.put(f"/api/subjects/{sid}/", {"name": "改名"}, format="json").status_code == 403
    assert client.patch(f"/api/subjects/{sid}/", {"name": "改名2"}, format="json").status_code == 403
    assert client.delete(f"/api/subjects/{sid}/").status_code == 403
    # 副作用が起きていないこと（name 不変・レコード残存）
    subject = Subject.objects.get(id=sid)
    assert subject.name == "科目A_I104"
    assert Subject.objects.filter(id=sid).exists()


# ---- TC-AUTO-02: 非admin は参照系（list/retrieve）で 200 ----
@pytest.mark.django_db
def test_non_admin_can_read(setup):
    client = APIClient()
    client.force_authenticate(user=setup["normal"])
    sid = setup["subject"].id
    assert client.get("/api/subjects/").status_code == 200
    assert client.get(f"/api/subjects/{sid}/").status_code == 200


# ---- TC-AUTO-03: admin は create/update/destroy を従来どおり実行できる ----
@pytest.mark.django_db
def test_admin_can_crud(setup, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup["admin"])

    create = client.post("/api/subjects/", {"name": "新科目I104"}, format="json")
    assert create.status_code == 201, create.content
    new_id = create.data["id"]
    assert Subject.objects.filter(name="新科目I104", organization=setup["org"]).exists()

    put = client.put(f"/api/subjects/{new_id}/", {"name": "更新後"}, format="json")
    assert put.status_code == 200, put.content
    assert Subject.objects.get(id=new_id).name == "更新後"

    delete = client.delete(f"/api/subjects/{new_id}/")
    # SubjectViewSet.perform_destroy は instance.delete()（物理削除）→ DRF 既定 204
    assert delete.status_code == 204
    assert not Subject.objects.filter(id=new_id).exists()


# ---- TC-AUTO-04: 未認証は 401 ----
@pytest.mark.django_db
def test_anonymous_gets_401(setup):
    client = APIClient()
    assert client.get("/api/subjects/").status_code == 401


# ---- TC-AUTO-05: 非admin の create は 403・未生成 ----
@pytest.mark.django_db
def test_non_admin_cannot_create(setup):
    client = APIClient()
    client.force_authenticate(user=setup["normal"])
    resp = client.post("/api/subjects/", {"name": "不正科目I104"}, format="json")
    assert resp.status_code == 403
    assert not Subject.objects.filter(name="不正科目I104").exists()
