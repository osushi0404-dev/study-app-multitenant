"""
I140: 登録 API の personal 組織自動作成フォールバック廃止の回帰テスト。

- slug なし登録で personal 組織（type='personal'・is_active=True）が不在の場合、
  従来は Organization.objects.create()（category 未指定）が IntegrityError となり
  広域 except で 400「エラーが発生しました」に丸められていた（潜在バグ）。
- 修正後は自動作成せず None を返し、既存 400 分岐「組織の設定に失敗しました」
  （views.py:78-84）に載る。組織は新規作成されず、error ログで環境異常が残る。

TC-AUTO-01/02/03/04（docs/tests/open/I140_auto_test.md）に対応。
"""
import logging

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import Subject


@pytest.fixture(autouse=True)
def _disable_django_ratelimit(settings):
    """登録ビューの @ratelimit(10/5m) は redis カウンタが実行間で共有され
    反復実行が flaky になるため、公式スイッチで無効化する（I131 と同方式）。"""
    settings.RATELIMIT_ENABLE = False


@pytest.fixture
def setup(db):
    """personal 組織を作らない（--no-migrations の素の DB = personal 不在状態）。
    ペイロードを有効値にするための school 組織・科目のみ用意する。"""
    cat = OrganizationCategory.objects.create(name="テストI140", slug="test-cat-i140")
    org = Organization.objects.create(
        name="組織I140", slug="org-i140", type="school", category=cat, is_active=True)
    subject = Subject.objects.create(name="科目I140", slug="subj-i140", organization=org)
    return {"cat": cat, "org": org, "subject": subject}


def _payload(user_id, subject_id):
    return {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "password": "I140TestPass123!",  # pragma: allowlist secret（テスト用ダミー値）
        "password_confirm": "I140TestPass123!",  # pragma: allowlist secret
        "subject_ids": [subject_id],
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


# ---- TC-AUTO-02: 組織が新規作成されない（自動作成廃止の固定） ----
@pytest.mark.django_db
def test_register_without_personal_org_creates_no_organization(setup):
    client = APIClient()
    count_before = Organization.objects.count()
    client.post(
        "/api/auth/register/", _payload("i140_user_b", setup["subject"].id),
        format="json")
    assert Organization.objects.count() == count_before
    assert not Organization.objects.filter(slug="personal").exists()


# ---- TC-AUTO-03: error ログで環境異常が可観測 ----
@pytest.mark.django_db
def test_register_without_personal_org_logs_error(setup, caplog):
    client = APIClient()
    with caplog.at_level(logging.ERROR, logger="django"):
        client.post(
            "/api/auth/register/", _payload("i140_user_c", setup["subject"].id),
            format="json")
    assert any(
        r.levelno == logging.ERROR and "Personal organization" in r.getMessage()
        for r in caplog.records)


# ---- TC-AUTO-04: personal が非アクティブのみ存在しても同挙動 ----
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
