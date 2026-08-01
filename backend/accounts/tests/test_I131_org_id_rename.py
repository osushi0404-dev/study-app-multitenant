"""
I131: Organization PK 改名（organization_id → id・migration 0021）の改名漏れ修正の回帰テスト。

- accounts/views.py:230（validate-slug）の旧属性参照で有効 slug が常に 500、
  accounts/views.py:88 + accounts/serializers.py:91（登録 API）の旧参照で
  新規登録が全件 400 になっていた。
- 修正後は validate-slug が有効 slug で 200、登録 API が両ルート
  （/api/auth/register/・/api/auth/register/<slug>/）で 201 を返す。
  404/400 系は body 完全一致で既存挙動を固定する（別要因の 404/400 と区別）。

TC-AUTO-01/03/04/05/06/07（docs/tests/open/I131_auto_test.md）に対応。
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory, User
from problems.models import Subject, UserSubjectAccess


@pytest.fixture(autouse=True)
def _disable_django_ratelimit(settings):
    """登録ビューの @ratelimit(10/5m) は redis カウンタが実行間で共有され
    反復実行が flaky になるため、公式スイッチで無効化する（E2E CI と同方式）。"""
    settings.RATELIMIT_ENABLE = False


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI131", slug="test-cat-i131")
    # type のデフォルトは 'personal'。slug なし登録の既定組織検索（type='personal' の
    # 先頭）に誤って拾われないよう、personal 以外の組織には明示的に type を与える。
    org = Organization.objects.create(
        name="組織I131", slug="org-i131", type="school", category=cat, is_active=True)
    inactive = Organization.objects.create(
        name="非アクティブI131", slug="org-inactive-i131", type="school",
        category=cat, is_active=False)
    # --no-migrations のため personal 組織は存在しない。slug なし登録の既定組織
    # （_get_organization の type='personal' 検索）用に fixture で自作する。
    personal = Organization.objects.create(
        name="個人利用I131", slug="personal", type="personal", category=cat, is_active=True)
    subject = Subject.objects.create(name="科目I131", slug="subj-i131", organization=org)
    subject_p = Subject.objects.create(name="科目P_I131", slug="subj-p-i131", organization=personal)
    return {"org": org, "inactive": inactive, "personal": personal,
            "subject": subject, "subject_p": subject_p}


def _payload(user_id, subject_id):
    return {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "password": "I131TestPass123!",  # pragma: allowlist secret（テスト用ダミー値）
        "password_confirm": "I131TestPass123!",  # pragma: allowlist secret
        "subject_ids": [subject_id],
    }


# ---- TC-AUTO-01: validate-slug 有効 slug 200（本バグの再発防止） ----
@pytest.mark.django_db
def test_validate_slug_valid_returns_200(setup):
    client = APIClient()
    resp = client.get("/api/organizations/validate-slug/org-i131/")
    assert resp.status_code == status.HTTP_200_OK
    # body 完全一致 = キー集合固定（過剰露出なし）・organization_id は現行 PK 値
    assert resp.json() == {
        "valid": True,
        "organization_name": "組織I131",
        "organization_id": setup["org"].id,
    }


# ---- TC-AUTO-03: validate-slug 存在しない slug 404（既存挙動不変） ----
@pytest.mark.django_db
def test_validate_slug_unknown_returns_404(setup):
    client = APIClient()
    resp = client.get("/api/organizations/validate-slug/no-such-org-i131/")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    # body 完全一致 = ルート不在等の別要因 404 と区別
    assert resp.json() == {
        "valid": False,
        "message": '組織 "no-such-org-i131" は見つかりません',
    }


# ---- TC-AUTO-04: validate-slug 非アクティブ組織 404（既存挙動不変） ----
@pytest.mark.django_db
def test_validate_slug_inactive_returns_404(setup):
    client = APIClient()
    resp = client.get("/api/organizations/validate-slug/org-inactive-i131/")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert resp.json() == {
        "valid": False,
        "message": '組織 "org-inactive-i131" は見つかりません',
    }


# ---- TC-AUTO-05: 登録 API・組織 slug ルート 201（本バグの再発防止） ----
@pytest.mark.django_db
def test_register_with_org_slug_returns_201(setup):
    client = APIClient()
    resp = client.post(
        "/api/auth/register/org-i131/",
        _payload("i131_user_a", setup["subject"].id),
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json()["organization"] == "組織I131"
    # 縦貫通の確認: 指定組織への所属と科目アクセス権の作成まで固定する
    user = User.objects.get(user_id="i131_user_a")
    assert user.organization_id == setup["org"].id
    assert UserSubjectAccess.objects.filter(user=user, subject=setup["subject"]).count() == 1


# ---- TC-AUTO-06: 登録 API・slug なしルート 201（personal 既定・本バグの再発防止） ----
@pytest.mark.django_db
def test_register_without_slug_uses_personal(setup):
    client = APIClient()
    resp = client.post(
        "/api/auth/register/",
        _payload("i131_user_b", setup["subject_p"].id),
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    user = User.objects.get(user_id="i131_user_b")
    assert user.organization_id == setup["personal"].id


# ---- TC-AUTO-07: 登録 API・無効 slug 400（既存挙動不変） ----
@pytest.mark.django_db
def test_register_unknown_slug_returns_400(setup):
    client = APIClient()
    resp = client.post(
        "/api/auth/register/no-such-org-i131/",
        _payload("i131_user_c", setup["subject"].id),
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    # 組織不在分岐（views.py:79-84）の文言で AttributeError 経由の 400 と区別
    assert resp.json()["error"]["main_message"] == "組織の設定に失敗しました"
