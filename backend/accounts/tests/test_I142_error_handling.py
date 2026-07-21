"""I142: accounts API のエラー応答設計（想定内は個別捕捉 / 想定外は顕在化）の回帰テスト。

- 広域 except Exception を撤去し、想定外例外（プログラム欠陥）は捕捉せず
  custom_exception_handler に委ねて「スタックトレース記録 + 統一 JSON 500」で顕在化させる。
- 想定内エラー（クライアント起因）は既存の 4xx 契約を body 完全一致で維持する。
- logout は refresh 欠落・不正形式を明示分岐で 400 とし、TokenError のみ捕捉する。

TC-AUTO-01〜10（docs/tests/open/I142_auto_test.md）に対応。
"""
import logging
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Organization, OrganizationCategory, User
from problems.models import Subject


@pytest.fixture(autouse=True)
def _disable_django_ratelimit(settings):
    """登録・logout の @ratelimit は redis カウンタが実行間で共有され反復実行が flaky に
    なるため、公式スイッチで無効化する（I131/I140 と同方式）。"""
    settings.RATELIMIT_ENABLE = False


class _RequestLogCapture(logging.Handler):
    """django.request は propagate=False（core/enhanced_logging.py:327-331）のため
    pytest の caplog では捕捉できない（計画時のスパイクで実証済み）。
    検証用ハンドラを直接装着して記録を取得する。"""

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def request_log():
    handler = _RequestLogCapture()
    logger = logging.getLogger('django.request')
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI142", slug="test-cat-i142")
    org = Organization.objects.create(
        name="組織I142", slug="org-i142", type="school", category=cat, is_active=True)
    subject = Subject.objects.create(name="科目I142", slug="subj-i142", organization=org)
    return {"cat": cat, "org": org, "subject": subject}


def _payload(user_id, subject_id):
    return {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "password": "I142TestPass123!",  # pragma: allowlist secret（テスト用ダミー値）
        "password_confirm": "I142TestPass123!",  # pragma: allowlist secret
        "subject_ids": [subject_id],
    }


# 想定外例外時に返る統一 JSON（DEBUG=False）
EXPECTED_500_BODY = {
    "error": {
        "main_message": "サーバーエラー",
        "sub_message": "しばらく時間をおいて再度お試しください",
        "details": {},
    }
}

LOGOUT_FAILURE_BODY = {"error": "ログアウトに失敗しました。"}


def _inject_orm_failure():
    """ORM 境界に想定外例外を注入する（本番コードに注入点を設けない）。"""
    return mock.patch.object(
        Organization.objects, 'filter', side_effect=RuntimeError('I142 injected'))


# ---- TC-AUTO-01: 想定外例外 → 統一 JSON 500（DEBUG=False） ----
@pytest.mark.django_db
def test_register_unexpected_exception_returns_json_500(setup, settings):
    settings.DEBUG = False
    client = APIClient()
    with _inject_orm_failure():
        resp = client.post(
            "/api/auth/register/org-i142/", _payload("i142_user_a", setup["subject"].id),
            format="json")
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert resp.json() == EXPECTED_500_BODY


# ---- TC-AUTO-02: 想定外例外のスタックトレースが django.request に記録される ----
@pytest.mark.django_db
def test_register_unexpected_exception_logs_stack_trace(setup, settings, request_log):
    settings.DEBUG = False
    client = APIClient()
    with _inject_orm_failure():
        client.post(
            "/api/auth/register/org-i142/", _payload("i142_user_b", setup["subject"].id),
            format="json")
    assert any(
        r.levelno == logging.ERROR and r.exc_info and r.exc_info[0] is RuntimeError
        for r in request_log.records)


# ---- TC-AUTO-03: DEBUG 時のみ例外詳細を露出 ----
@pytest.mark.django_db
def test_register_unexpected_exception_exposes_detail_in_debug(setup, settings):
    settings.DEBUG = True
    client = APIClient()
    with _inject_orm_failure():
        resp = client.post(
            "/api/auth/register/org-i142/", _payload("i142_user_c", setup["subject"].id),
            format="json")
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert resp.json()["error"]["sub_message"] == "RuntimeError: I142 injected"


# ---- TC-AUTO-04: validate-slug の想定外例外 → 統一 JSON 500 ----
@pytest.mark.django_db
def test_validate_slug_unexpected_exception_returns_json_500(setup, settings):
    settings.DEBUG = False
    client = APIClient()
    with _inject_orm_failure():
        resp = client.get("/api/organizations/validate-slug/org-i142/")
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # 旧: {"valid": false, "message": "エラーが発生しました"} に丸められないこと
    assert resp.json() == EXPECTED_500_BODY


# ---- TC-AUTO-05: 登録の不正なリクエスト形式は 400（500 でない） ----
@pytest.mark.django_db
def test_register_with_non_dict_body_returns_400(setup):
    client = APIClient()
    resp = client.post("/api/auth/register/org-i142/", [1, 2], format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {
        "error": {
            "main_message": "入力内容にエラーがあります",
            "sub_message": "不正なリクエスト形式です",
            "details": {},
        }
    }


# ---- TC-AUTO-06: logout 正常系＋トークン失効 ----
@pytest.mark.django_db
def test_logout_succeeds_and_blacklists_token(setup):
    user = User.objects.create_user(
        user_id="i142_logout", email="i142_logout@example.com",
        password="I142TestPass123!",  # pragma: allowlist secret（テスト用ダミー値）
        organization=setup["org"])
    refresh = str(RefreshToken.for_user(user))
    client = APIClient()

    first = client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
    assert first.status_code == status.HTTP_200_OK
    assert first.json() == {"message": "ログアウトしました。"}

    # 失効済みトークンの再利用は想定内エラー（400）
    second = client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
    assert second.status_code == status.HTTP_400_BAD_REQUEST
    assert second.json() == LOGOUT_FAILURE_BODY


# ---- TC-AUTO-07: logout の refresh 欠落は 400（既存契約維持） ----
@pytest.mark.django_db
def test_logout_without_refresh_returns_400():
    resp = APIClient().post("/api/auth/logout/", {}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == LOGOUT_FAILURE_BODY


# ---- TC-AUTO-08: logout の無効トークンは 400（既存契約維持） ----
@pytest.mark.django_db
def test_logout_with_invalid_token_returns_400():
    resp = APIClient().post(
        "/api/auth/logout/", {"refresh": "not-a-valid-token"}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == LOGOUT_FAILURE_BODY


# ---- TC-AUTO-09: logout の不正なリクエスト形式は 400（500 でない） ----
@pytest.mark.django_db
def test_logout_with_non_dict_body_returns_400():
    resp = APIClient().post("/api/auth/logout/", [], format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == LOGOUT_FAILURE_BODY


# ---- TC-AUTO-10: 登録の serializer 検証 400 の契約維持 ----
@pytest.mark.django_db
def test_register_validation_error_keeps_400_contract(setup):
    User.objects.create_user(
        user_id="i142_dup", email="i142_dup@example.com",
        password="I142TestPass123!",  # pragma: allowlist secret（テスト用ダミー値）
        organization=setup["org"])
    client = APIClient()
    resp = client.post(
        "/api/auth/register/org-i142/", _payload("i142_dup", setup["subject"].id),
        format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    body = resp.json()
    assert body["error"]["main_message"] == "入力内容にエラーがあります"
    assert "user_id" in body["error"]["details"]
