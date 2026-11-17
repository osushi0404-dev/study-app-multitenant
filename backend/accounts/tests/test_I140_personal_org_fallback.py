"""
I140: 登録 API の personal 組織自動作成フォールバック廃止の回帰テスト。

- I140 当時: slug なし登録で共有の personal 組織が不在なら、自動作成せず 400
  「組織の設定に失敗しました」に載せ、error ログで環境異常を残す。
- I539 から: slug なし登録は本人ひとりの組織を作る。作るのに要る「個人利用」カテゴリ
  （slug='personal'・migration 0017）が不在なら、同じく自動作成せず 400 に載せ、
  組織も利用者も作らず、error ログを残す（I140 の考え方を引き継ぐ）。

TC-AUTO-01/02/03/04（docs/tests/open/I140_auto_test.md）・TC-17（docs/tests/open/I539_auto_test.md）に対応。
"""
import logging

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory, User
from problems.models import Subject


@pytest.fixture(autouse=True)
def _disable_django_ratelimit(settings):
    """登録ビューの @ratelimit(10/5m) は redis カウンタが実行間で共有され
    反復実行が flaky になるため、公式スイッチで無効化する（I131 と同方式）。"""
    settings.RATELIMIT_ENABLE = False


@pytest.fixture
def setup(db):
    """「個人利用」カテゴリ（slug='personal'）も personal 組織も作らない（--no-migrations の素の DB）。
    ペイロードを有効値にするための school 組織・科目のみ用意する。"""
    cat = OrganizationCategory.objects.create(name="テストI140", slug="test-cat-i140")
    org = Organization.objects.create(
        name="組織I140", slug="org-i140", type="school", category=cat, is_active=True)
    subject = Subject.objects.create(name="科目I140", slug="subj-i140", organization=org)
    return {"cat": cat, "org": org, "subject": subject}


def _payload(user_id, subject_id=None):
    # I539 から slug なし登録は科目を送らない（本人ひとりの組織には科目がまだ無い）
    return {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "password": "I140TestPass123!",  # pragma: allowlist secret（テスト用ダミー値）
        "password_confirm": "I140TestPass123!",  # pragma: allowlist secret
    }


# views.py:78-84 の既存分岐の body（完全一致 = 広域 except 経由の 400 と区別）
EXPECTED_400_BODY = {
    "error": {
        "main_message": "組織の設定に失敗しました",
        "sub_message": "無効な組織URLまたはシステムエラー",
    }
}


# ---- TC-AUTO-01: personal 不在・slug なし登録 400（本バグの再発防止） ----
@pytest.mark.django_db
def test_register_without_personal_org_returns_400(setup):
    client = APIClient()
    resp = client.post(
        "/api/auth/register/", _payload("i140_user_a", setup["subject"].id),
        format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == EXPECTED_400_BODY


# ---- TC-AUTO-02: 組織・利用者が新規作成されない（自動作成廃止の固定） ----
@pytest.mark.django_db
def test_register_without_personal_org_creates_no_organization(setup):
    client = APIClient()
    count_before = Organization.objects.count()
    client.post(
        "/api/auth/register/", _payload("i140_user_b", setup["subject"].id),
        format="json")
    assert Organization.objects.count() == count_before
    assert not Organization.objects.filter(slug="personal").exists()
    assert not OrganizationCategory.objects.filter(slug="personal").exists()
    assert not User.objects.filter(user_id="i140_user_b").exists()


# ---- TC-AUTO-03: error ログで環境異常が可観測 ----
@pytest.mark.django_db
def test_register_without_personal_org_logs_error(setup, caplog):
    client = APIClient()
    with caplog.at_level(logging.ERROR, logger="django"):
        client.post(
            "/api/auth/register/", _payload("i140_user_c", setup["subject"].id),
            format="json")
    assert any(
        r.levelno == logging.ERROR and "Personal organization category" in r.getMessage()
        for r in caplog.records)


# ---- TC-AUTO-04: 共有の personal 組織（非アクティブ）があってもカテゴリが無ければ同挙動 ----
@pytest.mark.django_db
def test_register_with_only_inactive_personal_org_returns_400(setup):
    Organization.objects.create(
        name="個人利用I140", slug="personal", type="personal",
        category=setup["cat"], is_active=False)
    client = APIClient()
    count_before = Organization.objects.count()
    resp = client.post(
        "/api/auth/register/", _payload("i140_user_d", setup["subject"].id),
        format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == EXPECTED_400_BODY
    # 非アクティブ personal を active 化・複製していないこと
    assert Organization.objects.count() == count_before
    assert not Organization.objects.filter(slug="personal", is_active=True).exists()
