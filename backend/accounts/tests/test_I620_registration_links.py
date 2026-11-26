"""
I620: 組織の管理者（と運営）が発行する、パスキーを登録するための 1 回だけの登録用リンク。

WebAuthn の応答は I619 のソフトの認証器で作り、py_webauthn の検証は差し替えない。
TC-01〜TC-12（docs/tests/open/I620_auto_test.md）に対応。
"""
import hashlib
import logging
import re
import threading
import uuid
from datetime import datetime, timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import connection, connections
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts import passkeys
from accounts.models import Organization, OrganizationCategory, Passkey, RegistrationLink, WebAuthnChallenge
from accounts.tests.webauthn_soft_authenticator import SoftAuthenticator

User = get_user_model()

TEST_PASSWORD = "I620TestPass123!"  # pragma: allowlist secret（テスト用ダミー値）
ORIGIN = "http://localhost:3000"

MEMBERS = "/api/members/"
ADMIN_USERS = "/api/admin/users/"
LINK_OPTIONS = "/api/auth/registration-links/options/"
LINK_COMPLETE = "/api/auth/registration-links/complete/"
LOGIN_OPTIONS = "/api/auth/passkeys/login/options/"
LOGIN = "/api/auth/passkeys/login/"
REFRESH = "/api/auth/refresh/"

LINK_UNUSABLE = "このリンクは使えません。管理者に新しいリンクを発行してもらってください"
CANNOT_TARGET_SELF = "自分あてには操作できません。ほかの管理者か運営に依頼してください"
INACTIVE_TARGET = "無効の利用者には発行できません"
STAFF_TARGET = "運営のアカウントには画面から発行できません"
INDIVIDUAL_TARGET = "個人利用の利用者には発行できません"

VERIFY_FAILED = "パスキーを確かめられませんでした。もう一度お試しください"
DUPLICATE = "この端末のパスキーはすでに登録されています"
URL_PATTERN = re.compile(r"^http://localhost:3000/passkey-setup#token=([A-Za-z0-9_-]{43})$")


# ---------------------------------------------------------------- 下準備 ----
@pytest.fixture(autouse=True)
def _settings(settings):
    settings.RATELIMIT_ENABLE = False
    settings.WEBAUTHN_RP_ID = "localhost"
    settings.WEBAUTHN_ALLOWED_ORIGINS = [ORIGIN]
    settings.REGISTRATION_LINK_BASE_URL = ORIGIN


@pytest.fixture
def category(db):
    return OrganizationCategory.objects.create(name="I620", slug="cat-i620")


@pytest.fixture
def org_a(category):
    return Organization.objects.create(name="組織A_I620", slug="org-a-i620", category=category)


@pytest.fixture
def org_b(category):
    return Organization.objects.create(name="組織B_I620", slug="org-b-i620", category=category)


@pytest.fixture
def solo_org(category):
    return Organization.objects.create(
        name="soloさんの学習", slug="p-i620solo", category=category, is_individual=True)


def _user(name, org, **extra):
    return User.objects.create_user(user_id=name, password=TEST_PASSWORD, organization=org, **extra)


@pytest.fixture
def people(org_a, org_b, solo_org):
    return {
        "admin_a": _user("admin_a", org_a, role="admin"),
        "admin_a2": _user("admin_a2", org_a, role="admin"),
        "alice": _user("alice", org_a),
        "ghost": _user("ghost", org_a, is_active=False),
        "admin_b": _user("admin_b", org_b, role="admin"),
        "bob": _user("bob", org_b),
        "solo": _user("solo", solo_org, role="admin"),
        "staff": _user("staff", org_a, is_staff=True, role="admin"),
        "root": _user("root", org_b, is_staff=True, is_superuser=True, role="admin"),
    }


def client_for(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def reauth(user):
    return {"HTTP_X_REAUTH_TOKEN": passkeys.issue_reauth_token(user=user)}


def sub_message(response):
    return response.json()["error"]["sub_message"]


def dummy_passkey(user, name="ダミー"):
    return Passkey.objects.create(user=user, credential_id=uuid.uuid4().bytes, public_key=b"\x00", name=name)


def link_path(base, target):
    return f"{base}{target.id}/registration-link/"


def issue(actor, target, base=MEMBERS, *, with_reauth=True):
    kw = reauth(actor) if with_reauth else {}
    return client_for(actor).post(link_path(base, target), {}, format="json", **kw)


def issued_token(actor, target, base=MEMBERS):
    response = issue(actor, target, base)
    assert response.status_code == status.HTTP_201_CREATED, response.content
    match = URL_PATTERN.match(response.json()["url"])
    assert match, response.json()["url"]
    return match.group(1)


def link_options(token):
    return client_for().post(LINK_OPTIONS, {"token": token}, format="json")


def complete(token, authenticator=None, *, options=None):
    authenticator = authenticator or SoftAuthenticator()
    options = options or link_options(token).json()
    credential = authenticator.registration_response(options["options"]["challenge"])
    response = client_for().post(
        LINK_COMPLETE, {"token": token, "challenge_id": options["challenge_id"], "credential": credential},
        format="json")
    return authenticator, response


def passkey_login(authenticator, user):
    options = client_for().post(LOGIN_OPTIONS, {}, format="json").json()
    credential = authenticator.assertion_response(options["options"]["challenge"], user_handle=user.id.bytes)
    return client_for().post(LOGIN, {"challenge_id": options["challenge_id"], "credential": credential},
                             format="json")


# ------------------------------------------------------------- TC-01 一覧 ----
@pytest.mark.django_db
def test_tc01_list_requires_org_admin(people):
    assert client_for().get(MEMBERS).status_code == status.HTTP_401_UNAUTHORIZED
    assert client_for(people["alice"]).get(MEMBERS).status_code == status.HTTP_403_FORBIDDEN
    # 403 の文は共通のエラー処理（core.exceptions）が決まった文にそろえる
    assert client_for(people["solo"]).get(MEMBERS).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_tc01_list_scoped_to_own_org(people):
    dummy_passkey(people["alice"])
    dummy_passkey(people["alice"], "2 個目")
    issue(people["admin_a"], people["admin_a2"])
    response = client_for(people["admin_a"]).get(MEMBERS)
    assert response.status_code == status.HTTP_200_OK
    results = response.json()["results"]
    rows = {row["user_id"]: row for row in results}
    assert [row["user_id"] for row in results] == ["admin_a", "admin_a2", "alice", "ghost"]
    assert rows["alice"]["passkey_count"] == 2
    assert rows["alice"]["registration_link_expires_at"] is None
    assert rows["admin_a2"]["registration_link_expires_at"] is not None
    assert rows["admin_a"]["is_self"] is True and rows["alice"]["is_self"] is False
    assert rows["ghost"]["is_active"] is False
    assert set(rows["alice"]) == {"id", "user_id", "role", "is_active", "last_login", "created_at",
                                  "passkey_count", "registration_link_expires_at", "is_self"}


@pytest.mark.django_db
def test_tc01_list_expired_link_is_not_shown(people):
    issue(people["admin_a"], people["alice"])
    RegistrationLink.objects.filter(user=people["alice"]).update(expires_at=timezone.now() - timedelta(seconds=1))
    rows = {row["user_id"]: row for row in client_for(people["admin_a"]).get(MEMBERS).json()["results"]}
    assert rows["alice"]["registration_link_expires_at"] is None


@pytest.mark.django_db
def test_tc01_list_query_count_does_not_grow(people, org_a):
    admin = people["admin_a"]
    with CaptureQueriesContext(connection) as few:
        client_for(admin).get(MEMBERS)
    for i in range(5):
        dummy_passkey(_user(f"extra{i}", org_a))
    with CaptureQueriesContext(connection) as many:
        response = client_for(admin).get(MEMBERS)
    assert response.json()["count"] == 9
    assert len(many) == len(few)


# ------------------------------------------------------------- TC-02 作成 ----
@pytest.mark.django_db
def test_tc02_create_member(people, org_a):
    response = client_for(people["admin_a"]).post(MEMBERS, {"user_id": "new_member"}, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.content
    body = response.json()
    assert body["user_id"] == "new_member" and body["role"] == "user" and body["is_active"] is True
    user = User.objects.get(user_id="new_member")
    assert user.organization == org_a
    assert not user.has_usable_password()
    assert user.email is None


@pytest.mark.django_db
def test_tc02_create_member_ignores_extra_fields(people):
    response = client_for(people["admin_a"]).post(
        MEMBERS, {"user_id": "x_member", "role": "admin", "is_active": False, "is_staff": True,
                  "organization": str(people["bob"].organization_id)}, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(user_id="x_member")
    assert (user.role, user.is_active, user.is_staff) == ("user", True, False)
    assert user.organization_id == people["admin_a"].organization_id


@pytest.mark.django_db
@pytest.mark.parametrize("user_id", ["ab", "bad-id", "alice", ""])
def test_tc02_create_member_invalid(people, user_id):
    response = client_for(people["admin_a"]).post(MEMBERS, {"user_id": user_id}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "user_id" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_tc02_create_member_forbidden_and_no_detail_route(people):
    assert client_for(people["solo"]).post(MEMBERS, {"user_id": "y_y"}, format="json").status_code == 403
    detail = f"{MEMBERS}{people['alice'].id}/"
    for method in ("get", "patch", "put", "delete"):
        assert getattr(client_for(people["admin_a"]), method)(detail).status_code == status.HTTP_404_NOT_FOUND


# ------------------------------------------------------------- TC-03 発行 ----
@pytest.mark.django_db
def test_tc03_issue_requires_reauth(people):
    response = issue(people["admin_a"], people["alice"], with_reauth=False)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_tc03_issue_link(people):
    alice = people["alice"]
    dummy_passkey(alice)
    first_refresh = str(RefreshToken.for_user(alice))
    rotated = client_for().post(REFRESH, {"refresh": str(RefreshToken.for_user(alice))}, format="json")
    assert rotated.status_code == status.HTTP_200_OK, rotated.content
    rotated_refresh = rotated.json()["refresh"]

    before = timezone.now()
    response = issue(people["admin_a"], alice)
    assert response.status_code == status.HTTP_201_CREATED, response.content
    body = response.json()
    token = URL_PATTERN.match(body["url"]).group(1)
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert abs((expires_at - before).total_seconds() - 3600) < 5

    assert Passkey.objects.filter(user=alice).count() == 0
    for refresh in (first_refresh, rotated_refresh):
        assert client_for().post(REFRESH, {"refresh": refresh}, format="json").status_code == 401

    link = RegistrationLink.objects.get(user=alice)
    assert link.token_hash == hashlib.sha256(token.encode()).hexdigest()
    for field in RegistrationLink._meta.concrete_fields:
        assert token not in str(getattr(link, field.attname))
    assert link.issued_by == people["admin_a"]


@pytest.mark.django_db
def test_tc03_issue_again_revokes_previous(people):
    first = issued_token(people["admin_a"], people["alice"])
    second = issued_token(people["admin_a"], people["alice"])
    assert first != second
    links = RegistrationLink.objects.filter(user=people["alice"])
    assert links.count() == 2
    assert links.filter(used_at__isnull=True, revoked_at__isnull=True).count() == 1
    assert link_options(first).status_code == status.HTTP_400_BAD_REQUEST
    assert link_options(second).status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_tc03_issue_targets(people):
    admin = people["admin_a"]
    assert issue(admin, people["bob"]).status_code == status.HTTP_404_NOT_FOUND
    assert issue(admin, people["staff"]).status_code == status.HTTP_404_NOT_FOUND
    response = issue(admin, admin)
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == CANNOT_TARGET_SELF
    response = issue(admin, people["ghost"])
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == INACTIVE_TARGET
    assert issue(admin, people["admin_a2"]).status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_tc03_old_passkey_cannot_login_after_issue(people):
    alice = people["alice"]
    authenticator, response = complete(issued_token(people["admin_a"], alice))
    assert response.status_code == status.HTTP_200_OK
    assert passkey_login(authenticator, alice).status_code == status.HTTP_200_OK
    issued_token(people["admin_a"], alice)
    assert passkey_login(authenticator, alice).status_code == status.HTTP_400_BAD_REQUEST


# ------------------------------------------------------- TC-04 失効・失効の表 ----
@pytest.mark.django_db
def test_tc04_revoke(people):
    admin, alice = people["admin_a"], people["alice"]
    token = issued_token(admin, alice)
    path = link_path(MEMBERS, alice)
    assert client_for(admin).delete(path).status_code == status.HTTP_403_FORBIDDEN
    assert client_for(admin).delete(path, **reauth(admin)).status_code == status.HTTP_204_NO_CONTENT
    assert client_for(admin).delete(path, **reauth(admin)).status_code == status.HTTP_204_NO_CONTENT
    response = link_options(token)
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == LINK_UNUSABLE


@pytest.mark.django_db
def test_tc04_blacklist_app_works(people):
    alice = people["alice"]
    refresh = RefreshToken.for_user(alice)
    response = client_for(alice).post("/api/auth/logout/", {"refresh": str(refresh)}, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert client_for().post(REFRESH, {"refresh": str(refresh)}, format="json").status_code == 401


# ------------------------------------------------------- TC-05 リンクの options ----
@pytest.mark.django_db
def test_tc05_options_ok(people):
    token = issued_token(people["admin_a"], people["alice"])
    response = link_options(token)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["user_id"] == "alice"
    selection = body["options"]["authenticatorSelection"]
    assert selection["residentKey"] == "required" and selection["userVerification"] == "required"
    assert body["options"]["excludeCredentials"] == []
    assert WebAuthnChallenge.objects.get(pk=body["challenge_id"]).purpose == "link_register"


def _make_unusable(kind, people, token):
    link = RegistrationLink.objects.get(token_hash=hashlib.sha256(token.encode()).hexdigest())
    now = timezone.now()
    if kind == "expired":
        RegistrationLink.objects.filter(pk=link.pk).update(expires_at=now - timedelta(seconds=1))
    elif kind == "used":
        RegistrationLink.objects.filter(pk=link.pk).update(used_at=now)
    elif kind == "revoked":
        RegistrationLink.objects.filter(pk=link.pk).update(revoked_at=now)
    elif kind == "inactive_user":
        User.objects.filter(pk=link.user_id).update(is_active=False)
    elif kind == "inactive_org":
        Organization.objects.filter(pk=people["alice"].organization_id).update(is_active=False)


@pytest.mark.django_db
@pytest.mark.parametrize("kind,reason", [
    ("expired", "expired"), ("used", "used"), ("revoked", "revoked"),
    ("inactive_user", "inactive"), ("inactive_org", "inactive"),
])
def test_tc05_options_unusable(people, kind, reason, caplog):
    token = issued_token(people["admin_a"], people["alice"])
    _make_unusable(kind, people, token)
    with caplog.at_level(logging.WARNING, logger="accounts.registration_links"):
        response = link_options(token)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert sub_message(response) == LINK_UNUSABLE
    assert f"reason={reason}" in caplog.text


@pytest.mark.django_db
@pytest.mark.parametrize("token", ["short", "A" * 43, "!" * 43, ""])
def test_tc05_options_bad_token(people, token):
    response = link_options(token)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert sub_message(response) == LINK_UNUSABLE


# ------------------------------------------------------ TC-06 リンクの complete ----
@pytest.mark.django_db
def test_tc06_complete_logs_in(people):
    alice = people["alice"]
    token = issued_token(people["admin_a"], alice)
    second_options = link_options(token).json()  # 2 回目の complete のために先に取っておく
    authenticator, response = complete(token)
    assert response.status_code == status.HTTP_200_OK, response.content
    body = response.json()
    assert set(body) == {"access", "refresh", "user"}
    assert body["user"]["user_id"] == "alice"
    assert Passkey.objects.filter(user=alice).count() == 1
    assert RegistrationLink.objects.get(user=alice).used_at is not None
    assert passkey_login(authenticator, alice).status_code == status.HTTP_200_OK
    _, again = complete(token, options=second_options)
    assert again.status_code == status.HTTP_400_BAD_REQUEST and sub_message(again) == LINK_UNUSABLE
    response = link_options(token)
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == LINK_UNUSABLE


@pytest.mark.django_db
def test_tc06_complete_rejects_other_challenges(people):
    alice, admin_a2 = people["alice"], people["admin_a2"]
    token = issued_token(people["admin_a"], alice)
    # I619 のログイン済みの登録の challenge（用途 register）
    register_challenge, register_options = passkeys.registration_options(user=alice)
    _, response = complete(token, options={"challenge_id": str(register_challenge.id),
                                           "options": register_options})
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == VERIFY_FAILED
    # 別の利用者のリンクの challenge
    other_options = link_options(issued_token(people["admin_a"], admin_a2)).json()
    _, response = complete(token, options=other_options)
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == VERIFY_FAILED
    assert RegistrationLink.objects.get(user=alice).used_at is None


@pytest.mark.django_db
def test_tc06_duplicate_keeps_link_unused(people):
    alice, admin_a2 = people["alice"], people["admin_a2"]
    authenticator, response = complete(issued_token(people["admin_a"], alice))
    assert response.status_code == status.HTTP_200_OK
    token = issued_token(people["admin_a"], admin_a2)
    # alice のパスキーは残っているので、同じ認証器の鍵は重複になる
    _, response = complete(token, authenticator)
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == DUPLICATE
    assert RegistrationLink.objects.get(user=admin_a2).used_at is None


@pytest.mark.django_db
def test_tc06_reactivated_user(people):
    ghost = people["ghost"]
    ghost.is_active = True
    ghost.save()
    _, response = complete(issued_token(people["admin_a"], ghost))
    assert response.status_code == status.HTTP_200_OK


# ------------------------------------------------------------ TC-07 同時使用 ----
@pytest.mark.django_db(transaction=True)
def test_tc07_concurrent_complete_only_once(people):
    token = issued_token(people["admin_a"], people["alice"])
    prepared = []
    for _ in range(2):
        options = link_options(token).json()
        prepared.append((options, SoftAuthenticator().registration_response(options["options"]["challenge"])))
    barrier = threading.Barrier(2)
    results = []

    def run(options, credential):
        try:
            barrier.wait()
            response = client_for().post(
                LINK_COMPLETE, {"token": token, "challenge_id": options["challenge_id"],
                                "credential": credential}, format="json")
            results.append(response.status_code)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=run, args=item) for item in prepared]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [200, 400]
    assert Passkey.objects.filter(user=people["alice"]).count() == 1
    assert RegistrationLink.objects.filter(user=people["alice"], used_at__isnull=False).count() == 1


# ---------------------------------------------- TC-08 管理者によるパスキーの扱い ----
@pytest.mark.django_db
def test_tc08_member_passkeys(people):
    admin, alice, bob = people["admin_a"], people["alice"], people["bob"]
    passkey = dummy_passkey(alice, "会社の PC")
    bob_passkey = dummy_passkey(bob)
    response = client_for(admin).get(f"{MEMBERS}{alice.id}/passkeys/")
    assert response.status_code == status.HTTP_200_OK
    assert set(response.json()["results"][0]) == {"id", "name", "created_at", "last_used_at"}
    path = f"{MEMBERS}{alice.id}/passkeys/{passkey.id}/"
    assert client_for(admin).delete(path).status_code == status.HTTP_403_FORBIDDEN
    assert client_for(admin).delete(path, **reauth(admin)).status_code == status.HTTP_204_NO_CONTENT
    assert not Passkey.objects.filter(pk=passkey.pk).exists()

    assert client_for(admin).get(f"{MEMBERS}{bob.id}/passkeys/").status_code == status.HTTP_404_NOT_FOUND
    response = client_for(admin).delete(f"{MEMBERS}{alice.id}/passkeys/{bob_passkey.id}/", **reauth(admin))
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Passkey.objects.filter(pk=bob_passkey.pk).exists()
    own = dummy_passkey(admin)
    response = client_for(admin).delete(f"{MEMBERS}{admin.id}/passkeys/{own.id}/", **reauth(admin))
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == CANNOT_TARGET_SELF
    assert client_for(people["solo"]).get(f"{MEMBERS}{alice.id}/passkeys/").status_code == 403


# -------------------------------------------------------------- TC-09 運営 ----
@pytest.mark.django_db
def test_tc09_staff_api(people):
    staff = people["staff"]
    for target in (people["alice"], people["bob"]):
        assert issue(staff, target, ADMIN_USERS, with_reauth=False).status_code == 403
        assert issue(staff, target, ADMIN_USERS).status_code == status.HTTP_201_CREATED
        path = link_path(ADMIN_USERS, target)
        assert client_for(staff).delete(path, **reauth(staff)).status_code == status.HTTP_204_NO_CONTENT
        passkey = dummy_passkey(target)
        response = client_for(staff).get(f"{ADMIN_USERS}{target.id}/passkeys/")
        assert response.status_code == status.HTTP_200_OK and response.json()["count"] == 1
        passkey_path = f"{ADMIN_USERS}{target.id}/passkeys/{passkey.id}/"
        assert client_for(staff).delete(passkey_path).status_code == status.HTTP_403_FORBIDDEN
        assert client_for(staff).delete(passkey_path, **reauth(staff)).status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_tc09_staff_targets(people):
    staff = people["staff"]
    cases = [(people["root"], STAFF_TARGET), (staff, CANNOT_TARGET_SELF),
             (people["solo"], INDIVIDUAL_TARGET), (people["ghost"], INACTIVE_TARGET)]
    for target, message in cases:
        response = issue(staff, target, ADMIN_USERS)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, target.user_id
        assert sub_message(response) == message
    response = client_for(staff).get(f"{ADMIN_USERS}{people['solo'].id}/passkeys/")
    assert response.status_code == status.HTTP_400_BAD_REQUEST and sub_message(response) == INDIVIDUAL_TARGET


@pytest.mark.django_db
def test_tc09_non_staff_forbidden(people):
    for actor in (people["admin_a"], people["alice"]):
        assert issue(actor, people["alice"], ADMIN_USERS).status_code == status.HTTP_403_FORBIDDEN
        assert client_for(actor).get(f"{ADMIN_USERS}{people['alice'].id}/passkeys/").status_code == 403


# ------------------------------------------------------------- TC-10 コマンド ----
@pytest.mark.django_db
def test_tc10_command(people):
    staff = people["staff"]
    dummy_passkey(staff)
    out = StringIO()
    call_command("issue_registration_link", "staff", stdout=out)
    assert re.search(r"http://localhost:3000/passkey-setup#token=[A-Za-z0-9_-]{43}", out.getvalue())
    assert Passkey.objects.filter(user=staff).count() == 0
    link = RegistrationLink.objects.get(user=staff)
    assert link.issued_by is None and link.used_at is None and link.revoked_at is None
    with pytest.raises(CommandError, match="利用者が見つかりません"):
        call_command("issue_registration_link", "nobody", stdout=StringIO())
    with pytest.raises(CommandError, match=INACTIVE_TARGET):
        call_command("issue_registration_link", "ghost", stdout=StringIO())


# -------------------------------------------------------------- TC-11 ログ ----
@pytest.mark.django_db
def test_tc11_logs_have_no_secrets(people, caplog):
    admin, alice = people["admin_a"], people["alice"]
    passkey = dummy_passkey(alice)
    with caplog.at_level(logging.INFO):
        client_for(admin).delete(f"{MEMBERS}{alice.id}/passkeys/{passkey.id}/", **reauth(admin))
        first = issued_token(admin, alice)
        client_for(admin).delete(link_path(MEMBERS, alice), **reauth(admin))
        link_options(first)
        token = issued_token(admin, alice)
        complete(token)
    text = caplog.text
    for expected in ("registration link issued", "registration link revoked", "registration link used",
                     "passkey deleted by admin"):
        assert expected in text, expected
    for secret in (first, token, hashlib.sha256(token.encode()).hexdigest(), "alice"):
        assert secret not in text


# ------------------------------------------------- TC-12 organization_is_individual ----
@pytest.mark.django_db
def test_tc12_user_serializer_has_individual_flag(people):
    assert client_for(people["solo"]).get("/api/auth/me/").json()["organization_is_individual"] is True
    assert client_for(people["alice"]).get("/api/auth/me/").json()["organization_is_individual"] is False
    orphan = User.objects.create_user(user_id="orphan", password=TEST_PASSWORD)
    assert client_for(orphan).get("/api/auth/me/").json()["organization_is_individual"] is False


# ------------------------------------------------- TC-13 リンクの土台の確かめ ----
@pytest.mark.parametrize("base,expected", [
    ("https://app.example.com", []),
    ("https://other.example.com", ["accounts.E004"]),
])
def test_tc13_system_check_link_base(settings, base, expected):
    from accounts.checks import check_webauthn_settings

    settings.DEBUG = False
    settings.WEBAUTHN_ALLOWED_ORIGINS = ["https://app.example.com"]
    settings.WEBAUTHN_RP_ID = "app.example.com"
    settings.REGISTRATION_LINK_BASE_URL = base
    assert [error.id for error in check_webauthn_settings(None)] == expected


def test_tc13_empty_origins_do_not_break_settings_loading():
    """パスキーの origin の一覧が空でも、設定の読み込みで落ちない（F3。空は E001 が報告する）"""
    import os
    import subprocess  # nosec B404（テストで manage.py を別のプロセスで動かす）
    import sys
    from pathlib import Path

    env = {**os.environ, "WEBAUTHN_ALLOWED_ORIGINS": "", "DJANGO_SETTINGS_MODULE": "core.settings"}
    env.pop("REGISTRATION_LINK_BASE_URL", None)
    code = ("import django; django.setup(); from django.conf import settings; "
            "print(repr(settings.WEBAUTHN_ALLOWED_ORIGINS), settings.REGISTRATION_LINK_BASE_URL)")
    result = subprocess.run(  # nosec B603（固定の引数だけ）
        [sys.executable, "-c", code], env=env, cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("[] ")


# ---------------------------------------- TC-05 失効した古いトークンが付いていても ----
@pytest.mark.django_db
def test_tc05_stale_token_is_ignored(people):
    """発行で失効した本人のトークンがブラウザに残っていても、リンクの API は 401 にしない"""
    alice = people["alice"]
    token = issued_token(people["admin_a"], alice)
    stale = APIClient()
    stale.credentials(HTTP_AUTHORIZATION="Bearer not-a-valid-token")
    response = stale.post(LINK_OPTIONS, {"token": token}, format="json")
    assert response.status_code == status.HTTP_200_OK
