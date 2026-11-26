"""
I619: パスキー（WebAuthn）の登録・一覧・名前の変更・削除と、パスキーでのログイン。

WebAuthn の応答はテスト用のソフトの認証器（webauthn_soft_authenticator.py）で作り、
本物の py_webauthn の検証を通す（検証は差し替えない）。

TC-01〜TC-13・TC-15（docs/tests/open/I619_auto_test.md）に対応。
"""
import logging
import time
import uuid
from base64 import urlsafe_b64encode

import pytest
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import caches
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory, Passkey, WebAuthnChallenge
from accounts.passkeys import default_passkey_name
from accounts.tests.webauthn_soft_authenticator import SoftAuthenticator

User = get_user_model()

TEST_PASSWORD = "I619TestPass123!"  # pragma: allowlist secret（テスト用ダミー値）
WRONG_INPUT = "wrong-password"  # pragma: allowlist secret（誤りのパスワードのテスト用ダミー値）
ORIGIN = "http://localhost:3000"
REAUTH_SALT = "accounts.passkeys.reauth"
WINDOWS_CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

BASE = "/api/auth/passkeys/"
LOGIN_OPTIONS = f"{BASE}login/options/"
LOGIN = f"{BASE}login/"
REAUTH_OPTIONS = f"{BASE}reauth/options/"
REAUTH = f"{BASE}reauth/"
REGISTER_OPTIONS = f"{BASE}register/options/"
REGISTER = f"{BASE}register/"

LOGIN_FAILED = "パスキーでログインできませんでした"
VERIFY_FAILED = "パスキーを確かめられませんでした。もう一度お試しください"
DUPLICATE = "この端末のパスキーはすでに登録されています"
LIMIT = "登録できるパスキーは 20 個までです"
WRONG_PASSWORD = "パスワードが正しくありません"
NO_PASSKEYS = "登録済みのパスキーがありません"

THROTTLE_TEST_CACHES = {
    alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"i619-{alias}"}
    for alias in ("default", "sessions", "problems", "analytics")
}


def b64url(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


# ---------------------------------------------------------------- 下準備 ----
@pytest.fixture(autouse=True)
def _settings(settings):
    settings.RATELIMIT_ENABLE = False  # パスワードのログイン（django-ratelimit）。DRF のスロットルは conftest が止める
    settings.WEBAUTHN_RP_ID = "localhost"
    settings.WEBAUTHN_ALLOWED_ORIGINS = [ORIGIN]


@pytest.fixture
def category(db):
    return OrganizationCategory.objects.create(name="I619", slug="cat-i619")


@pytest.fixture
def org_a(category):
    return Organization.objects.create(name="組織A_I619", slug="org-a-i619", category=category)


@pytest.fixture
def org_b(category):
    return Organization.objects.create(name="組織B_I619", slug="org-b-i619", category=category)


def _user(name, org, **extra):
    return User.objects.create_user(
        email=f"{name}_i619@example.com", user_id=name, password=TEST_PASSWORD,
        organization=org, **extra)


@pytest.fixture
def alice(org_a):
    return _user("alice", org_a)


@pytest.fixture
def carol(org_a):
    return _user("carol", org_a)


@pytest.fixture
def bob(org_b):
    return _user("bob", org_b)


@pytest.fixture
def staff(org_a):
    return _user("staff", org_a, is_staff=True, role="admin")


def client_for(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def reauth_token(user):
    response = client_for(user).post(REAUTH, {"password": TEST_PASSWORD}, format="json")
    assert response.status_code == status.HTTP_200_OK, response.content
    return response.json()["reauth_token"]


def signed_token(user, seconds_ago):
    return signing.dumps({"uid": str(user.id), "iat": int(time.time()) - seconds_ago},
                         salt=REAUTH_SALT)


def register_options(user, token):
    return client_for(user).post(REGISTER_OPTIONS, {}, format="json", HTTP_X_REAUTH_TOKEN=token)


def register(user, authenticator=None, *, token=None, user_agent=WINDOWS_CHROME_UA, **response_kw):
    """本人確認 → options → 登録。(認証器, 登録の応答) を返す"""
    authenticator = authenticator or SoftAuthenticator()
    token = token or reauth_token(user)
    options = register_options(user, token).json()
    credential = authenticator.registration_response(options["options"]["challenge"], **response_kw)
    response = client_for(user).post(
        REGISTER, {"challenge_id": options["challenge_id"], "credential": credential},
        format="json", HTTP_X_REAUTH_TOKEN=token, HTTP_USER_AGENT=user_agent)
    return authenticator, response


def registered(user, **kw):
    authenticator, response = register(user, **kw)
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return authenticator


def login_options():
    response = client_for().post(LOGIN_OPTIONS, {}, format="json")
    assert response.status_code == status.HTTP_200_OK, response.content
    return response.json()


def login(authenticator, user, *, options=None, **assertion_kw):
    options = options or login_options()
    assertion_kw.setdefault("user_handle", user.id.bytes)
    credential = authenticator.assertion_response(options["options"]["challenge"], **assertion_kw)
    return client_for().post(
        LOGIN, {"challenge_id": options["challenge_id"], "credential": credential}, format="json")


def sub_message(response):
    return response.json()["error"]["sub_message"]


def dummy_passkey(user, name="ダミー"):
    return Passkey.objects.create(
        user=user, credential_id=uuid.uuid4().bytes, public_key=b"\x00", name=name)


# ------------------------------------------------------- TC-01 登録の options ----
@pytest.mark.django_db
def test_tc01_register_options_requires_auth_and_recent_reauth(alice, carol):
    assert client_for().post(REGISTER_OPTIONS, {}, format="json").status_code == 401

    valid = reauth_token(alice)
    broken = valid[:-1] + ("A" if valid[-1] != "A" else "B")
    for token in (None, signed_token(alice, 301), reauth_token(carol), broken):
        kwargs = {"HTTP_X_REAUTH_TOKEN": token} if token else {}
        response = client_for(alice).post(REGISTER_OPTIONS, {}, format="json", **kwargs)
        assert response.status_code == status.HTTP_403_FORBIDDEN, token
        assert response.json()["error"]["main_message"] == "アクセスが拒否されました"

    assert register_options(alice, signed_token(alice, 299)).status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_tc01_register_options_body(alice):
    authenticator = registered(alice)
    response = register_options(alice, reauth_token(alice))

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    options = body["options"]
    assert options["rp"]["id"] == "localhost"
    assert options["authenticatorSelection"]["residentKey"] == "required"
    assert options["authenticatorSelection"]["userVerification"] == "required"
    assert options["attestation"] == "none"
    assert options["timeout"] == 300000
    assert options["user"]["id"] == b64url(alice.id.bytes)
    assert options["user"]["name"] == "alice"
    assert [c["id"] for c in options["excludeCredentials"]] == [b64url(authenticator.credential_id)]
    challenge = WebAuthnChallenge.objects.get(pk=uuid.UUID(body["challenge_id"]))
    assert challenge.purpose == WebAuthnChallenge.Purpose.REGISTER
    assert challenge.user_id == alice.id


# ------------------------------------------------------------- TC-02 登録 ----
@pytest.mark.django_db
def test_tc02_register_success(alice):
    authenticator, response = register(alice, SoftAuthenticator(sign_count=3))

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert set(body) == {"id", "name", "created_at", "last_used_at"}
    assert body["name"] == "Windows の Chrome"
    assert body["last_used_at"] is None
    passkey = Passkey.objects.get(user=alice)
    assert str(passkey.id) == body["id"]
    assert bytes(passkey.credential_id) == authenticator.credential_id
    assert passkey.sign_count == 3
    assert passkey.transports == ["internal"]
    assert not WebAuthnChallenge.objects.filter(purpose="register").exists()


@pytest.mark.django_db
def test_tc02_register_same_authenticator_twice(alice):
    authenticator = registered(alice)
    _, response = register(alice, authenticator)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert sub_message(response) == DUPLICATE
    assert Passkey.objects.filter(user=alice).count() == 1


def _register_with(user, token, challenge_id, credential):
    return client_for(user).post(
        REGISTER, {"challenge_id": challenge_id, "credential": credential},
        format="json", HTTP_X_REAUTH_TOKEN=token, HTTP_USER_AGENT=WINDOWS_CHROME_UA)


@pytest.mark.django_db
def test_tc02_register_rejects_bad_challenge_or_response(alice, carol):
    token = reauth_token(alice)
    authenticator = SoftAuthenticator()

    # (c) 同じ challenge で 2 回目
    options = register_options(alice, token).json()
    credential = authenticator.registration_response(options["options"]["challenge"])
    assert _register_with(alice, token, options["challenge_id"], credential).status_code == 201
    second = _register_with(alice, token, options["challenge_id"],
                            SoftAuthenticator().registration_response(options["options"]["challenge"]))
    assert second.status_code == 400 and sub_message(second) == VERIFY_FAILED

    # (d) 期限切れ
    options = register_options(alice, token).json()
    WebAuthnChallenge.objects.filter(pk=options["challenge_id"]).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1))
    expired = _register_with(alice, token, options["challenge_id"],
                             SoftAuthenticator().registration_response(options["options"]["challenge"]))
    assert expired.status_code == 400 and sub_message(expired) == VERIFY_FAILED

    # (e) carol の challenge
    carol_options = register_options(carol, reauth_token(carol)).json()
    other = _register_with(alice, token, carol_options["challenge_id"],
                           SoftAuthenticator().registration_response(carol_options["options"]["challenge"]))
    assert other.status_code == 400 and sub_message(other) == VERIFY_FAILED

    # (f) ログイン用の challenge
    login_opts = login_options()
    wrong_purpose = _register_with(alice, token, login_opts["challenge_id"],
                                   SoftAuthenticator().registration_response(login_opts["options"]["challenge"]))
    assert wrong_purpose.status_code == 400 and sub_message(wrong_purpose) == VERIFY_FAILED

    # (h) UV なし
    options = register_options(alice, token).json()
    no_uv = _register_with(alice, token, options["challenge_id"],
                           SoftAuthenticator().registration_response(options["options"]["challenge"], uv=False))
    assert no_uv.status_code == 400 and sub_message(no_uv) == VERIFY_FAILED

    # (g) 別の origin → (k) その challenge で正しい応答をもう一度
    options = register_options(alice, token).json()
    retry = SoftAuthenticator()
    evil = _register_with(alice, token, options["challenge_id"], retry.registration_response(
        options["options"]["challenge"], origin="http://evil.example:3000"))
    assert evil.status_code == 400 and sub_message(evil) == VERIFY_FAILED
    again = _register_with(alice, token, options["challenge_id"],
                           retry.registration_response(options["options"]["challenge"]))
    assert again.status_code == 400 and sub_message(again) == VERIFY_FAILED

    assert Passkey.objects.filter(user=alice).count() == 1


@pytest.mark.django_db
def test_tc02_register_limit(alice):
    token = reauth_token(alice)
    for i in range(19):
        dummy_passkey(alice, f"ダミー{i}")
    options = register_options(alice, token).json()
    dummy_passkey(alice, "20 個目")

    over = _register_with(alice, token, options["challenge_id"],
                          SoftAuthenticator().registration_response(options["options"]["challenge"]))
    assert over.status_code == 400 and sub_message(over) == LIMIT
    limited = register_options(alice, token)
    assert limited.status_code == 400 and sub_message(limited) == LIMIT
    assert Passkey.objects.filter(user=alice).count() == 20


@pytest.mark.django_db
def test_tc02_register_requires_reauth(alice):
    options = register_options(alice, reauth_token(alice)).json()
    response = client_for(alice).post(
        REGISTER, {"challenge_id": options["challenge_id"],
                   "credential": SoftAuthenticator().registration_response(options["options"]["challenge"])},
        format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Passkey.objects.exists()


# ------------------------------------------------------------- TC-03 一覧 ----
@pytest.mark.django_db
def test_tc03_list(alice, carol, bob):
    assert client_for().get(BASE).status_code == 401
    assert client_for(alice).get(BASE).json() == {"count": 0, "next": None, "previous": None, "results": []}

    first = dummy_passkey(alice, "一つ目")
    second = dummy_passkey(alice, "二つ目")
    dummy_passkey(carol, "carol の鍵")
    dummy_passkey(bob, "bob の鍵")

    body = client_for(alice).get(BASE).json()
    assert body["count"] == 2
    assert [r["id"] for r in body["results"]] == [str(first.id), str(second.id)]
    assert all(set(r) == {"id", "name", "created_at", "last_used_at"} for r in body["results"])


# ----------------------------------------------------------- TC-04 名前の変更 ----
@pytest.mark.django_db
def test_tc04_rename(alice, carol, bob):
    own = dummy_passkey(alice, "元の名前")
    url = f"{BASE}{own.id}/"
    client = client_for(alice)

    ok = client.patch(url, {"name": "  会社の PC  "}, format="json")
    assert ok.status_code == 200 and ok.json()["name"] == "会社の PC"
    own.refresh_from_db()
    assert own.name == "会社の PC"

    for bad in ("   ", "あ" * 65, "abc‮gpj.exe", "a\u0007b"):
        response = client.patch(url, {"name": bad}, format="json")
        assert response.status_code == 400, bad
        assert "name" in response.json()["error"]["details"]
    own.refresh_from_db()
    assert own.name == "会社の PC"
    assert client.patch(url, {"name": "あ" * 64}, format="json").status_code == 200

    for other in (dummy_passkey(carol, "carol"), dummy_passkey(bob, "bob")):
        response = client.patch(f"{BASE}{other.id}/", {"name": "乗っ取り"}, format="json")
        assert response.status_code == 404
        assert response.json()["error"]["main_message"] == "リソースが見つかりません"
        other.refresh_from_db()
        assert other.name != "乗っ取り"
    assert client.patch(f"{BASE}{uuid.uuid4()}/", {"name": "x"}, format="json").status_code == 404
    assert client_for().patch(url, {"name": "x"}, format="json").status_code == 401
    assert client.put(url, {"name": "x"}, format="json").status_code == 405

    # F1: 名前の無い PATCH は入力の誤り（500 にしない）
    empty = client.patch(url, {}, format="json")
    assert empty.status_code == 400
    assert "name" in empty.json()["error"]["details"]


# ---------------------------------------------------------------- TC-05 削除 ----
@pytest.mark.django_db
def test_tc05_delete(alice, carol, bob):
    own = dummy_passkey(alice)
    url = f"{BASE}{own.id}/"

    assert client_for(alice).delete(url).status_code == 403
    assert client_for(alice).delete(url, HTTP_X_REAUTH_TOKEN=signed_token(alice, 301)).status_code == 403
    assert client_for().delete(url).status_code == 401
    assert Passkey.objects.filter(pk=own.pk).exists()

    token = reauth_token(alice)
    for other in (dummy_passkey(carol), dummy_passkey(bob)):
        response = client_for(alice).delete(f"{BASE}{other.id}/", HTTP_X_REAUTH_TOKEN=token)
        assert response.status_code == 404
        assert Passkey.objects.filter(pk=other.pk).exists()

    assert client_for(alice).delete(url, HTTP_X_REAUTH_TOKEN=token).status_code == 204
    assert not Passkey.objects.filter(user=alice).exists()


# ------------------------------------------------------------- TC-06 本人確認 ----
@pytest.mark.django_db
def test_tc06_reauth_with_password(alice):
    client = client_for(alice)
    ok = client.post(REAUTH, {"password": TEST_PASSWORD}, format="json")
    assert ok.status_code == 200
    assert set(ok.json()) == {"reauth_token", "expires_in"} and ok.json()["expires_in"] == 300

    wrong = client.post(REAUTH, {"password": WRONG_INPUT}, format="json")
    assert wrong.status_code == 400 and sub_message(wrong) == WRONG_PASSWORD
    assert client.post(REAUTH, {}, format="json").status_code == 400
    assert client.post(REAUTH, {"password": TEST_PASSWORD, "challenge_id": str(uuid.uuid4()),
                                "credential": {"id": "x"}}, format="json").status_code == 400
    assert client_for().post(REAUTH, {"password": TEST_PASSWORD}, format="json").status_code == 401
    assert register_options(alice, ok.json()["reauth_token"]).status_code == 200


@pytest.mark.django_db
def test_tc06_reauth_with_passkey(alice, carol):
    no_keys = client_for(alice).post(REAUTH_OPTIONS, {}, format="json")
    assert no_keys.status_code == 400 and sub_message(no_keys) == NO_PASSKEYS

    authenticator = registered(alice)
    carol_authenticator = registered(carol)
    options = client_for(alice).post(REAUTH_OPTIONS, {}, format="json").json()
    assert [c["id"] for c in options["options"]["allowCredentials"]] == [b64url(authenticator.credential_id)]

    # (h) alice の challenge で carol のパスキー
    foreign = client_for(alice).post(REAUTH, {
        "challenge_id": options["challenge_id"],
        "credential": carol_authenticator.assertion_response(
            options["options"]["challenge"], user_handle=carol.id.bytes)}, format="json")
    assert foreign.status_code == 400 and sub_message(foreign) == VERIFY_FAILED

    options = client_for(alice).post(REAUTH_OPTIONS, {}, format="json").json()
    ok = client_for(alice).post(REAUTH, {
        "challenge_id": options["challenge_id"],
        "credential": authenticator.assertion_response(
            options["options"]["challenge"], user_handle=alice.id.bytes)}, format="json")
    assert ok.status_code == 200 and ok.json()["expires_in"] == 300
    passkey = Passkey.objects.get(user=alice)
    assert passkey.sign_count == authenticator.sign_count
    assert passkey.last_used_at is None


@pytest.mark.django_db
def test_tc06_reauth_password_lockout(alice):
    authenticator = registered(alice)
    client = client_for(alice)
    for attempt in range(1, 6):
        response = client.post(REAUTH, {"password": WRONG_INPUT}, format="json")
        assert response.status_code == 400 and sub_message(response) == WRONG_PASSWORD, attempt
    alice.refresh_from_db()
    assert alice.account_locked_until is not None
    assert alice.account_locked_until > timezone.now() + timezone.timedelta(minutes=29)

    locked = client.post(REAUTH, {"password": TEST_PASSWORD}, format="json")
    assert locked.status_code == 400
    assert sub_message(locked).startswith("アカウントがロックされています")
    assert "reauth_token" not in locked.json()

    options = client.post(REAUTH_OPTIONS, {}, format="json").json()
    by_passkey = client.post(REAUTH, {
        "challenge_id": options["challenge_id"],
        "credential": authenticator.assertion_response(
            options["options"]["challenge"], user_handle=alice.id.bytes)}, format="json")
    assert by_passkey.status_code == 200


@pytest.mark.django_db
def test_tc06_lock_expiry_restarts_count(alice):
    """F2: ロックの期限が切れたら数え直す（期限後の 1 回の誤りで再ロックしない）。

    本人確認とパスワードのログインで同じ
    """
    client = client_for(alice)
    expired = timezone.now() - timezone.timedelta(seconds=1)

    User.objects.filter(pk=alice.pk).update(failed_login_attempts=5, account_locked_until=expired)
    assert client.post(REAUTH, {"password": WRONG_INPUT}, format="json").status_code == 400
    alice.refresh_from_db()
    assert alice.failed_login_attempts == 1
    assert alice.account_locked_until is None

    User.objects.filter(pk=alice.pk).update(failed_login_attempts=5, account_locked_until=expired)
    client_for().post("/api/auth/login/", {"email": "alice", "password": WRONG_INPUT}, format="json")
    alice.refresh_from_db()
    assert alice.failed_login_attempts == 1
    assert alice.account_locked_until is None
    assert client.post(REAUTH, {"password": TEST_PASSWORD}, format="json").status_code == 200


@pytest.mark.django_db
def test_tc06_reauth_success_resets_failures(alice):
    client = client_for(alice)
    for _ in range(2):
        client.post(REAUTH, {"password": WRONG_INPUT}, format="json")
    assert client.post(REAUTH, {"password": TEST_PASSWORD}, format="json").status_code == 200
    alice.refresh_from_db()
    assert alice.failed_login_attempts == 0


# --------------------------------------------------------- TC-07 ログイン ----
@pytest.mark.django_db
def test_tc07_login(alice):
    authenticator = registered(alice, authenticator=SoftAuthenticator(sign_count=1))
    options = login_options()
    assert options["options"]["allowCredentials"] == []
    assert options["options"]["userVerification"] == "required"
    assert options["options"]["rpId"] == "localhost"
    challenge = WebAuthnChallenge.objects.get(pk=options["challenge_id"])
    assert challenge.purpose == WebAuthnChallenge.Purpose.LOGIN and challenge.user_id is None

    response = login(authenticator, alice, options=options)

    assert response.status_code == 200, response.content
    body = response.json()
    assert set(body) == {"access", "refresh", "user"}
    assert body["user"]["id"] == str(alice.id)
    assert body["user"]["user_id"] == "alice"
    passkey = Passkey.objects.get(user=alice)
    alice.refresh_from_db()
    assert passkey.sign_count == 2
    assert timezone.now() - passkey.last_used_at < timezone.timedelta(minutes=1)
    assert timezone.now() - alice.last_login < timezone.timedelta(minutes=1)
    assert not WebAuthnChallenge.objects.filter(pk=options["challenge_id"]).exists()

    me = APIClient()
    me.credentials(HTTP_AUTHORIZATION=f"Bearer {body['access']}")
    assert me.get("/api/auth/me/").json()["user_id"] == "alice"


# ----------------------------------------------------- TC-08 ログインの拒否 ----
def assert_login_rejected(response):
    assert response.status_code == 400, response.content
    assert sub_message(response) == LOGIN_FAILED
    assert "access" not in response.json()


@pytest.mark.django_db
def test_tc08_challenge_rules(alice):
    authenticator = registered(alice)
    options = login_options()
    assert login(authenticator, alice, options=options).status_code == 200
    assert_login_rejected(login(authenticator, alice, options=options))  # (a)

    options = login_options()  # (b)
    WebAuthnChallenge.objects.filter(pk=options["challenge_id"]).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1))
    assert_login_rejected(login(authenticator, alice, options=options))

    register_opts = register_options(alice, reauth_token(alice)).json()  # (c)
    assert_login_rejected(login(authenticator, alice, options=register_opts))


@pytest.mark.django_db
def test_tc08_sign_count(alice):
    authenticator = registered(alice)
    Passkey.objects.filter(user=alice).update(sign_count=5)
    failed = login_options()
    assert_login_rejected(login(authenticator, alice, options=failed, sign_count=5))  # (d)
    assert Passkey.objects.get(user=alice).sign_count == 5
    # (m) 失敗した試行の challenge は消えている
    assert not WebAuthnChallenge.objects.filter(pk=failed["challenge_id"]).exists()
    assert_login_rejected(login(authenticator, alice, options=failed, sign_count=6))
    assert login(authenticator, alice, sign_count=6).status_code == 200


@pytest.mark.django_db
def test_tc08_zero_sign_count_is_accepted(alice):
    authenticator = registered(alice, authenticator=SoftAuthenticator(sign_count=0))
    assert Passkey.objects.get(user=alice).sign_count == 0
    assert login(authenticator, alice, sign_count=0).status_code == 200  # (e)


@pytest.mark.django_db
def test_tc08_identity_and_response_checks(alice, carol):
    authenticator = registered(alice)
    assert_login_rejected(login(SoftAuthenticator(), alice))  # (f)
    assert_login_rejected(login(authenticator, alice, user_handle=carol.id.bytes))  # (i)
    assert_login_rejected(login(authenticator, alice, origin="http://evil.example:3000"))  # (j)
    assert_login_rejected(login(authenticator, alice, uv=False))  # (k)
    assert Passkey.objects.get(user=alice).last_used_at is None


@pytest.mark.django_db
def test_tc08_inactive_user_or_org_by_update(alice, org_a):
    authenticator = registered(alice)
    User.objects.filter(pk=alice.pk).update(is_active=False)  # (g) シグナルを通らない
    assert_login_rejected(login(authenticator, alice))
    User.objects.filter(pk=alice.pk).update(is_active=True)
    Organization.objects.filter(pk=org_a.pk).update(is_active=False)  # (h)
    assert_login_rejected(login(authenticator, alice))


@pytest.mark.django_db
def test_tc08_password_lock_does_not_block_passkey(alice):
    authenticator = registered(alice)
    User.objects.filter(pk=alice.pk).update(
        account_locked_until=timezone.now() + timezone.timedelta(minutes=30))
    assert login(authenticator, alice).status_code == 200  # (l)


# ------------------------------------------------------ TC-09 無効化での削除 ----
@pytest.mark.django_db
def test_tc09_deactivation_deletes_passkeys(alice, carol, bob, staff, org_a, org_b):
    for user, count in ((alice, 2), (carol, 1), (bob, 1)):
        for i in range(count):
            dummy_passkey(user, f"{user.user_id}{i}")
    admin = client_for(staff)

    assert admin.post(f"/api/admin/users/{alice.pk}/toggle_active/").status_code == 200  # (a)
    assert not Passkey.objects.filter(user=alice).exists()
    assert Passkey.objects.filter(user__in=[carol, bob]).count() == 2

    assert admin.patch(f"/api/admin/users/{carol.pk}/", {"is_active": False}, format="json").status_code == 200
    assert not Passkey.objects.filter(user=carol).exists()  # (b)

    bob.is_active = False  # (c)
    bob.save()
    assert not Passkey.objects.filter(user=bob).exists()

    assert admin.post(f"/api/admin/users/{alice.pk}/toggle_active/").json()["is_active"] is True
    assert not Passkey.objects.filter(user=alice).exists()  # (d)

    dave = _user("dave", org_a)  # (e)
    erin = _user("erin", org_b)
    dummy_passkey(dave)
    dummy_passkey(erin)
    org_a.is_active = False
    org_a.save()
    assert not Passkey.objects.filter(user__organization=org_a).exists()
    assert Passkey.objects.filter(user=erin).count() == 1


# ------------------------------------------------- TC-10 パスワードのログイン ----
@pytest.mark.django_db
def test_tc10_password_login_shape_matches_passkey_login(alice):
    authenticator = registered(alice)
    passkey_body = login(authenticator, alice).json()
    response = client_for().post("/api/auth/login/", {"email": "alice", "password": TEST_PASSWORD},
                                 format="json")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access", "refresh", "user"}
    assert set(body["user"]) == set(passkey_body["user"])
    alice.refresh_from_db()
    assert timezone.now() - alice.last_login < timezone.timedelta(minutes=1)


# ------------------------------------------------------------ TC-11 回数の制限 ----
@pytest.mark.django_db
def test_tc11_throttles():
    with override_settings(API_THROTTLE_ENABLED=True, CACHES=THROTTLE_TEST_CACHES):
        caches["default"].clear()
        client = APIClient()
        for i in range(20):
            assert client.post(LOGIN_OPTIONS, {}, format="json").status_code == 200, i
        assert client.post(LOGIN_OPTIONS, {}, format="json").status_code == 429
        for i in range(10):
            assert client.post(LOGIN, {}, format="json").status_code == 400, i
        assert client.post(LOGIN, {}, format="json").status_code == 429


# ------------------------------------------------------------ TC-12 既定の名前 ----
@pytest.mark.parametrize("user_agent,expected", [
    (WINDOWS_CHROME_UA, "Windows の Chrome"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0", "Windows の Edge"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
     "Version/18.0 Safari/605.1.15", "Mac の Safari"),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
     "Version/18.0 Mobile/15E148 Safari/604.1", "iPhone の Safari"),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
     "CriOS/140.0.0.0 Mobile/15E148 Safari/604.1", "iPhone の Chrome"),
    ("Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/140.0.0.0 Mobile Safari/537.36", "Android の Chrome"),
    ("Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0", "Linux の Firefox"),
    ("", "パスキー"),
    ("curl/8.0", "パスキー"),
])
def test_tc12_default_name(user_agent, expected):
    assert default_passkey_name(user_agent) == expected


# --------------------------------------------------------------- TC-13 ログ ----
@pytest.mark.django_db
def test_tc13_audit_logs_without_secrets(alice, carol, staff, org_a, caplog):
    caplog.set_level(logging.INFO)
    authenticator = registered(alice)
    passkey = Passkey.objects.get(user=alice)
    client_for(alice).patch(f"{BASE}{passkey.id}/", {"name": "会社の PC"}, format="json")
    _, failed = register(alice, origin="http://evil.example:3000")
    assert failed.status_code == 400
    client_for(alice).post(REAUTH, {"password": WRONG_INPUT}, format="json")
    token = reauth_token(alice)
    options = login_options()
    assert login(authenticator, alice, options=options).status_code == 200
    assert_login_rejected(login(authenticator, alice, options=options))
    second = registered(carol)
    client_for(carol).delete(f"{BASE}{Passkey.objects.get(user=carol).id}/",
                             HTTP_X_REAUTH_TOKEN=reauth_token(carol))
    registered(carol, authenticator=second)
    client_for(staff).post(f"/api/admin/users/{carol.pk}/toggle_active/")
    dummy_passkey(_user("dave", org_a))
    org_a.is_active = False
    org_a.save()

    text = "\n".join(record.getMessage() for record in caplog.records)
    for phrase in ("passkey registered", "passkey register failed", "passkey renamed",
                   "passkey deleted", "passkey reauth ok", "passkey reauth failed",
                   "passkey login ok", "passkey login failed", "passkeys deleted on deactivation"):
        assert phrase in text, phrase
    assert f"organization_id={org_a.id}" in text
    assert "reason=" in text
    for secret in ("alice_i619@example.com", token, options["options"]["challenge"],
                   "会社の PC", b64url(bytes(passkey.public_key))):
        assert secret not in text


# ------------------------------------------------------ TC-15 システムチェック ----
@pytest.mark.parametrize("debug,origins,rp_id,expected", [
    (True, ["http://localhost:3000"], "localhost", []),
    (False, ["https://app.example.com"], "app.example.com", []),
    (False, ["https://app.example.com"], "example.com", []),
    (False, [], "app.example.com", ["accounts.E001"]),
    (False, ["http://app.example.com"], "app.example.com", ["accounts.E002"]),
    (False, ["https://app.example.com"], "evil.com", ["accounts.E003"]),
    (False, ["https://app.example.com"], "ample.com", ["accounts.E003"]),
])
def test_tc15_system_check(debug, origins, rp_id, expected):
    from accounts.checks import check_webauthn_settings

    with override_settings(DEBUG=debug, WEBAUTHN_ALLOWED_ORIGINS=origins, WEBAUTHN_RP_ID=rp_id):
        assert [error.id for error in check_webauthn_settings(None)] == expected
