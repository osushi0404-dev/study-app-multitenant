"""
I437: ログに個人情報（メールアドレス・氏名・ログイン ID）と秘密（パスワード・リフレッシュトークン）を
残さない回帰テスト。

TC-01〜TC-08（docs/tests/open/I437_auto_test.md）に対応。
`django.request` は propagate=False で caplog に届かないので、対象の logger に記録を集めるハンドラーを付けて確かめる。
"""
import json
import logging
from contextlib import contextmanager

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import EmailVerification, Organization, OrganizationCategory, User
from accounts.views import UserRegistrationView
from core.enhanced_logging import DetailedFormatter, ErrorContextMiddleware
from core.middleware import RequestLoggingMiddleware
from core.monitoring import ErrorTracker, UserActivityMonitor
from core.subject_service import SubjectService
from problems.models import Subject

EMAIL = "u_i437@example.com"
FIRST_NAME = "太郎I437"
LAST_NAME = "山田I437"
# django は propagate=True で root に届くので付けない（同じ記録が 2 回入らないように）
TARGET_LOGGERS = ("", "django.request")


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def text(self):
        """集めた記録の本文と、本番と同じ整形（DetailedFormatter）をつないだ文字"""
        formatter = DetailedFormatter()
        return "\n".join(
            f"{r.getMessage()}\n{formatter.format(r)}" for r in self.records)


@contextmanager
def capture_logs(names=TARGET_LOGGERS):
    handler = _ListHandler()
    loggers = [logging.getLogger(n) for n in names]
    saved = [(lg, lg.level) for lg in loggers]
    for lg in loggers:
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        for lg, level in saved:
            lg.removeHandler(handler)
            lg.setLevel(level)


@pytest.fixture
def org(db):
    cat = OrganizationCategory.objects.create(name="テストI437", slug="test-cat-i437")
    return Organization.objects.create(
        name="組織I437", slug="org-i437", type="school", category=cat, is_active=True)


@pytest.fixture
def subject(org):
    return Subject.objects.create(name="科目I437", slug="subj-i437", organization=org)


@pytest.fixture
def user(org):
    return User.objects.create_user(
        email=EMAIL, user_id="u_i437", password=None, organization=org, role="user",
        first_name=FIRST_NAME, last_name=LAST_NAME)


# ---- TC-01 ----
@pytest.mark.django_db
def test_error_tracker_has_no_email(user):
    with capture_logs() as logs:
        data = ErrorTracker.log_error(ValueError("boom"), context={"path": "/api/x/"}, user=user)
        anonymous = ErrorTracker.log_error(ValueError("boom"), user=None)
    assert "user_email" not in data
    assert data["user_id"] == str(user.id)
    assert "user_email" not in anonymous
    assert anonymous["user_id"] is None
    assert EMAIL not in logs.text()


# ---- TC-02 ----
@pytest.mark.django_db
def test_user_activity_has_no_email(user):
    with capture_logs() as logs:
        UserActivityMonitor.log_user_activity(user, "view_problems", {"path": "/api/problems/"})
    lines = [r.getMessage() for r in logs.records if r.getMessage().startswith("User Activity: ")]
    assert lines
    activity = json.loads(lines[0][len("User Activity: "):])
    assert "user_email" not in activity
    assert activity["user_id"] == str(user.id)
    assert EMAIL not in logs.text()


# ---- TC-03 ----
@pytest.mark.django_db
def test_request_logging_uses_user_id(user):
    middleware = RequestLoggingMiddleware(lambda request: HttpResponse())
    factory = RequestFactory()
    with capture_logs() as logs:
        request = factory.get("/api/problems/")
        request.user = user
        middleware.process_request(request)
        anonymous_request = factory.get("/api/problems/")
        anonymous_request.user = AnonymousUser()
        middleware.process_request(anonymous_request)
    starts = [r.getMessage() for r in logs.records if r.getMessage().startswith("[START]")]
    assert starts[0].endswith(f"User: {user.id}")
    assert starts[-1].endswith("User: anonymous")
    assert EMAIL not in logs.text()


# ---- TC-04 ----
@pytest.mark.django_db
def test_registration_logs_have_no_email_or_password(org, subject, settings):
    settings.RATELIMIT_ENABLE = False
    password = "I437TestPass123!"  # pragma: allowlist secret（テスト用ダミー値）
    payload = {
        "user_id": "i437_new",
        "email": "i437_new@example.com",
        "password": password,
        "password_confirm": password,
        "subject_ids": [subject.id],
    }
    with capture_logs() as logs:
        resp = APIClient().post(f"/api/auth/register/{org.slug}/", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    created = User.objects.get(user_id="i437_new")
    text = logs.text()
    assert "i437_new@example.com" not in text
    assert password not in text
    assert f"Registration attempt for organization_id: {org.id}" in text
    assert f"User created successfully: user_id={created.id}" in text


# ---- TC-05 ----
@pytest.mark.django_db
def test_subject_service_logs_user_id(org):
    noorg = User.objects.create_user(
        email="u_i437_noorg@example.com", user_id="u_i437_noorg", password=None,
        organization=None, role="user")
    with capture_logs() as logs:
        SubjectService.get_user_subjects(noorg)
        SubjectService.get_subject_by_id(1, noorg)
        SubjectService.get_user_subjects(None)
    messages = [r.getMessage() for r in logs.records if "has no organization_id" in r.getMessage()]
    assert messages.count(f"User {noorg.id} has no organization_id") == 2
    assert "User None has no organization_id" in messages
    assert "u_i437_noorg@example.com" not in logs.text()


def _raise_with_email(request):
    user_email = request.user.email  # noqa: F841 その場の変数にメールアドレスを置く
    raise RuntimeError("boom")


def _exception_records(user):
    middleware = ErrorContextMiddleware(_raise_with_email)
    request = RequestFactory().get("/api/x/")
    request.user = user
    with capture_logs(("django.request",)) as logs:
        with pytest.raises(RuntimeError):
            middleware(request)
    assert len(logs.records) == 1
    formatted = json.loads(DetailedFormatter().format(logs.records[0]))
    frames = formatted.get("error_context", {}).get("stack_frames", [])
    return logs, frames


# ---- TC-06 ----
@pytest.mark.django_db
def test_exception_log_has_no_locals_when_not_debug(user, settings):
    settings.DEBUG = False
    logs, frames = _exception_records(user)
    assert logs.records[0].include_locals is False
    assert frames
    assert all("locals" not in f for f in frames)
    assert all({"file", "line", "function"} <= f.keys() for f in frames)
    assert EMAIL not in logs.text()


@pytest.mark.django_db
def test_exception_log_marks_locals_when_debug(user, settings):
    # 変数そのものは今の書く側（DetailedFormatter）の不具合で書かれないので、
    # 印が付くことだけを確かめる（plan_I437.md 計画変更記録）
    settings.DEBUG = True
    logs, _ = _exception_records(user)
    assert logs.records[0].include_locals is True


def _error_body(data, user):
    middleware = ErrorContextMiddleware(lambda request: HttpResponse(status=400))
    request = RequestFactory().post("/api/auth/login/", data=data)
    request.user = user
    with capture_logs(("django.request",)) as logs:
        middleware(request)
    bodies = [r.request["body"] for r in logs.records if "body" in getattr(r, "request", {})]
    assert len(bodies) == 1
    return logs, bodies[0]


# ---- TC-07 ----
@pytest.mark.django_db
def test_error_body_redacts_personal_fields(user):
    data = {
        "email": EMAIL, "first_name": FIRST_NAME, "last_name": LAST_NAME,
        "user_id": "u_i437", "refresh": "refresh-i437", "password": "pw-i437",  # pragma: allowlist secret
        "subject_ids": "7",
    }
    logs, body = _error_body(data, user)
    for field in ("email", "first_name", "last_name", "user_id", "refresh", "password"):
        assert body[field] == "[REDACTED]", field
    assert body["subject_ids"] == ["7"]
    text = logs.text()
    for value in (EMAIL, FIRST_NAME, LAST_NAME, "refresh-i437"):
        assert value not in text


@pytest.mark.django_db
def test_error_body_redacts_secret_name_variants(user):
    # パスワード変更 API（confirm_password）・入力欄の確かめの API（field/value）の欄の名前（fix-loop F1）
    data = {
        "current_password": "cur-i437", "new_password": "new-i437",  # pragma: allowlist secret
        "confirm_password": "new-i437", "refresh_token": "refresh-i437",  # pragma: allowlist secret
        "field": "email", "value": EMAIL,
    }
    logs, body = _error_body(data, user)
    for field in ("current_password", "new_password", "confirm_password", "refresh_token", "value"):
        assert body[field] == "[REDACTED]", field
    assert body["field"] == ["email"]
    text = logs.text()
    for value in ("cur-i437", "new-i437", "refresh-i437", EMAIL):
        assert value not in text


@pytest.mark.django_db
def test_error_body_adds_no_missing_fields(user):
    _, body = _error_body({"password": "pw-i437"}, user)  # pragma: allowlist secret
    assert body == {"password": "[REDACTED]"}


# ---- TC-08 ----
@pytest.mark.django_db
def test_debug_print_has_no_email(user, settings, capsys):
    settings.DEBUG = True
    UserRegistrationView().send_verification_email(user)
    out = capsys.readouterr().out
    assert EMAIL not in out
    assert f"user_id={user.id}" in out
    assert EmailVerification.objects.filter(user=user).count() == 1
