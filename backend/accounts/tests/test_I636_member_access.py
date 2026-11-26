"""
I636: メンバー管理を使える条件を 1 か所で判定し、画面（/api/auth/me/ の can_manage_members）と API で一致させる（F5）。
あわせて、確かめ用の初期データ（seed_e2e）の運営と本人ひとりの組織の管理者。
TC-05・TC-12（docs/tests/open/I636_auto_test.md）に対応。
"""
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory

User = get_user_model()

TEST_PASSWORD = "I636TestPass123!"  # pragma: allowlist secret（テスト用ダミー値）
MEMBERS = "/api/members/"
ME = "/api/auth/me/"

# 組織の種類 → 作るときの属性
ORG_KINDS = {
    "invitable": {},
    "inactive": {"is_active": False},
    "individual": {"is_individual": True},
    "shared_personal": {"type": Organization.TYPE_PERSONAL, "slug": Organization.SHARED_PERSONAL_SLUG},
    "personal_other_slug": {"type": Organization.TYPE_PERSONAL},
}


@pytest.fixture
def category(db):
    return OrganizationCategory.objects.create(name="I636", slug="cat-i636")


def make_org(category, kind):
    extra = ORG_KINDS[kind]
    fields = {"name": f"組織_{kind}", "slug": f"org-i636-{kind}", "category": category, **extra}
    return Organization.objects.create(**fields)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ------------------------------------------------- TC-05 判定と API の一致 ----
ACTORS = [
    # (ユーザー ID, 組織の種類〔None は組織なし〕, 属性, メンバー管理を使えるか)
    ("admin_invitable", "invitable", {"role": "admin"}, True),
    ("admin_inactive", "inactive", {"role": "admin"}, False),
    ("admin_individual", "individual", {"role": "admin"}, False),
    ("admin_shared", "shared_personal", {"role": "admin"}, False),
    ("admin_personal", "personal_other_slug", {"role": "admin"}, True),
    ("user_invitable", "invitable", {"role": "user"}, False),
    ("staff_admin", "invitable", {"role": "admin", "is_staff": True}, True),
    ("admin_no_org", None, {"role": "admin"}, False),
]


@pytest.mark.django_db
@pytest.mark.parametrize("user_id,kind,extra,expected", ACTORS)
def test_i636_can_manage_members_matches_api(category, user_id, kind, extra, expected):
    org = make_org(category, kind) if kind else None
    actor = User.objects.create_user(user_id=user_id, password=TEST_PASSWORD, organization=org, **extra)
    client = client_for(actor)
    me = client.get(ME)
    assert me.status_code == status.HTTP_200_OK
    assert me.json()["can_manage_members"] is expected
    response = client.get(MEMBERS)
    if expected:
        assert response.status_code == status.HTTP_200_OK
    else:
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"]["main_message"] == "アクセスが拒否されました"


@pytest.mark.django_db
def test_i636_user_serializer_has_no_individual_flag(category):
    actor = User.objects.create_user(
        user_id="plain", password=TEST_PASSWORD, organization=make_org(category, "invitable"))
    assert "organization_is_individual" not in client_for(actor).get(ME).json()



# ------------------------------------------------------ TC-12 初期データ ----
def _seed():
    call_command("seed_e2e", "--scenario", "tenant_isolation", "--password", TEST_PASSWORD, stdout=StringIO())


@pytest.mark.django_db
def test_i636_seed_e2e_creates_staff_and_solo(settings):
    settings.DEBUG = True
    _seed()
    _seed()  # 何度流しても同じ
    staff = User.objects.get(email="e2e_staff@example.com")
    assert (staff.user_id, staff.is_staff, staff.role) == ("e2e_staff", True, "user")
    assert staff.organization.slug == "e2e-org-staff"
    solo = User.objects.get(email="e2e_solo@example.com")
    assert (solo.user_id, solo.role) == ("e2e_solo", "admin")
    assert solo.organization.is_individual is True
    assert solo.can_manage_members is False
    assert Organization.objects.filter(slug="e2e-org-solo").count() == 1
    for user_id in ("e2e_user_a", "e2e_user_b", "e2e_user_c", "e2e_staff", "e2e_solo"):
        assert User.objects.filter(user_id=user_id).count() == 1


@pytest.mark.django_db
def test_i636_seed_e2e_refuses_without_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="seed_e2e は DEBUG が真の環境（開発・E2E）でだけ流せます"):
        _seed()
    assert User.objects.filter(email__startswith="e2e_").count() == 0
