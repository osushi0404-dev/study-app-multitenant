"""パスキー（WebAuthn）の業務の処理（I619）

- 検証は py_webauthn に任せ、自前で暗号を書かない
- challenge は DB の表に置き、使うときに行を消す
  （消費は検証の前に別にコミットし、失敗した試行の challenge も 2 度使わせない）
- 失敗の文は理由ごとに分けず、理由はログの reason= だけに残す（個人情報・鍵・challenge・印は出さない）
"""
import json
import logging
import os
import unicodedata
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import parse_authentication_credential_json
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .models import Organization, Passkey, User, WebAuthnChallenge
from .serializers import UserSerializer

logger = logging.getLogger(__name__)

Purpose = WebAuthnChallenge.Purpose

LOGIN_FAILED = 'パスキーでログインできませんでした'
VERIFY_FAILED = 'パスキーを確かめられませんでした。もう一度お試しください'
DUPLICATE = 'この端末のパスキーはすでに登録されています'
WRONG_PASSWORD = 'パスワードが正しくありません'  # nosec B105（利用者に出す文で、パスワードではない）
NO_PASSKEYS = '登録済みのパスキーがありません'
REAUTH_SALT = 'accounts.passkeys.reauth'
NAME_MAX_LENGTH = 64
DEFAULT_NAME = 'パスキー'
# 既定の名前を UA から作る（上から順に見る。iPhone・Android の UA は Mac OS X・Linux を含むので先に見る）
_OS_MARKERS = (('iPhone', 'iPhone'), ('iPad', 'iPad'), ('Android', 'Android'), ('Windows', 'Windows'),
               ('CrOS', 'ChromeOS'), ('Macintosh', 'Mac'), ('Linux', 'Linux'))
_BROWSER_MARKERS = (('Edg/', 'Edge'), ('EdgiOS', 'Edge'), ('OPR/', 'Opera'), ('Firefox/', 'Firefox'),
                    ('FxiOS', 'Firefox'), ('CriOS', 'Chrome'), ('Chrome/', 'Chrome'), ('Safari/', 'Safari'))
_TRANSPORTS = {transport.value for transport in AuthenticatorTransport}
# 利用者の入力（応答の JSON）が壊れているときに py_webauthn・base64 の解析が投げうる例外
_BAD_RESPONSE = (WebAuthnException, ValueError, TypeError, KeyError)


class PasskeyError(serializers.ValidationError):
    """利用者向けの決まった文で 400 を返す（core.exceptions の形になる）"""


# ------------------------------------------------------------------ challenge ----
def issue_challenge(*, purpose: str, user: User | None = None) -> WebAuthnChallenge:
    now = timezone.now()
    WebAuthnChallenge.objects.filter(expires_at__lte=now).delete()  # 期限切れの行を片付ける
    return WebAuthnChallenge.objects.create(
        purpose=purpose, user=user, challenge=os.urandom(64),
        expires_at=now + timedelta(seconds=settings.WEBAUTHN_CHALLENGE_TTL_SECONDS))


def consume_challenge(*, challenge_id: uuid.UUID, purpose: str, user: User | None) -> bytes:
    """challenge を消して返す。自分の atomic でコミットしてから返すので、呼び出し側の検証が失敗しても戻らない"""
    with transaction.atomic():
        row = (WebAuthnChallenge.objects.select_for_update()
               .filter(pk=challenge_id, purpose=purpose, user=user).first())
        if row is not None:
            WebAuthnChallenge.objects.filter(pk=row.pk).delete()
    if row is None or row.expires_at <= timezone.now():
        raise PasskeyError(VERIFY_FAILED)
    return bytes(row.challenge)


def _options_dict(options: Any) -> dict:
    return json.loads(options_to_json(options))


def _descriptors(user: User) -> list[PublicKeyCredentialDescriptor]:
    return [
        PublicKeyCredentialDescriptor(
            id=bytes(passkey.credential_id),
            transports=[AuthenticatorTransport(t) for t in passkey.transports if t in _TRANSPORTS] or None)
        for passkey in user.passkeys.only('credential_id', 'transports')
    ]


# ------------------------------------------------------------------- 登録 ----
def _ensure_below_limit(user: User) -> None:
    if Passkey.objects.filter(user=user).count() >= settings.PASSKEY_MAX_PER_USER:
        raise PasskeyError(f'登録できるパスキーは {settings.PASSKEY_MAX_PER_USER} 個までです')


def registration_options(*, user: User) -> tuple[WebAuthnChallenge, dict]:
    _ensure_below_limit(user)
    challenge = issue_challenge(purpose=Purpose.REGISTER, user=user)
    name = user.user_id or str(user.id)
    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=user.id.bytes,  # メールアドレスに頼らない
        user_name=name,
        user_display_name=name,
        challenge=bytes(challenge.challenge),
        timeout=settings.WEBAUTHN_CHALLENGE_TTL_SECONDS * 1000,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED),
        exclude_credentials=_descriptors(user),
    )
    return challenge, _options_dict(options)


def default_passkey_name(user_agent: str) -> str:
    os_name = next((label for marker, label in _OS_MARKERS if marker in user_agent), None)
    browser = next((label for marker, label in _BROWSER_MARKERS if marker in user_agent), None)
    if os_name is None or browser is None:
        return DEFAULT_NAME
    return f'{os_name} の {browser}'[:NAME_MAX_LENGTH]


def register_passkey(*, user: User, challenge_id: uuid.UUID, credential: dict, user_agent: str) -> Passkey:
    _ensure_below_limit(user)
    try:
        challenge = consume_challenge(challenge_id=challenge_id, purpose=Purpose.REGISTER, user=user)
    except PasskeyError:
        logger.warning('passkey register failed user_id=%s reason=%s', user.id, 'challenge')
        raise
    try:
        verified = verify_registration_response(
            credential=credential, expected_challenge=challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID, expected_origin=settings.WEBAUTHN_ALLOWED_ORIGINS,
            require_user_verification=True)
    except _BAD_RESPONSE:
        logger.warning('passkey register failed user_id=%s reason=%s', user.id, 'verify')
        raise PasskeyError(VERIFY_FAILED)
    transports = credential.get('response', {}).get('transports') or []
    try:
        with transaction.atomic():
            passkey = Passkey.objects.create(
                user=user, credential_id=verified.credential_id, public_key=verified.credential_public_key,
                sign_count=verified.sign_count,
                transports=[t for t in transports if isinstance(t, str) and t in _TRANSPORTS],
                name=default_passkey_name(user_agent))
    except IntegrityError:
        logger.warning('passkey register failed user_id=%s reason=%s', user.id, 'duplicate')
        raise PasskeyError(DUPLICATE)
    logger.info('passkey registered user_id=%s passkey_id=%s', user.id, passkey.id)
    return passkey


# --------------------------------------------------------- ログイン・本人確認 ----
def authentication_options(*, user: User | None = None) -> tuple[WebAuthnChallenge, dict]:
    """ログイン（user なし・利用者名を入れない形）と本人確認（user あり・本人のパスキーだけ）"""
    allow = None
    if user is not None:
        allow = _descriptors(user)
        if not allow:
            raise PasskeyError(NO_PASSKEYS)
    purpose = Purpose.LOGIN if user is None else Purpose.REAUTH
    challenge = issue_challenge(purpose=purpose, user=user)
    options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        challenge=bytes(challenge.challenge),
        timeout=settings.WEBAUTHN_CHALLENGE_TTL_SECONDS * 1000,
        allow_credentials=allow or [],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return challenge, _options_dict(options)


def _authentication_failed(purpose: str, user: User | None, reason: str) -> PasskeyError:
    if purpose == Purpose.LOGIN:
        logger.warning('passkey login failed reason=%s', reason)
        return PasskeyError(LOGIN_FAILED)
    logger.warning('passkey reauth failed user_id=%s method=passkey reason=%s', user.id, reason)
    return PasskeyError(VERIFY_FAILED)


def _is_active(account: User) -> bool:
    organization = account.organization
    return account.is_active and (organization is None or organization.is_active)


def authenticate_passkey(*, challenge_id: uuid.UUID, credential: dict, user: User | None = None) -> Passkey:
    """ログイン（user なし）と本人確認（user あり）の assertion を確かめる"""
    purpose = Purpose.LOGIN if user is None else Purpose.REAUTH
    try:
        challenge = consume_challenge(challenge_id=challenge_id, purpose=purpose, user=user)
    except PasskeyError:
        raise _authentication_failed(purpose, user, 'challenge')
    try:
        parsed = parse_authentication_credential_json(credential)
    except _BAD_RESPONSE:
        raise _authentication_failed(purpose, user, 'format')

    with transaction.atomic():
        passkey = (Passkey.objects.select_for_update(of=('self',)).select_related('user__organization')
                   .filter(credential_id=parsed.raw_id).first())
        if passkey is None:
            raise _authentication_failed(purpose, user, 'unknown_credential')
        if user is not None and passkey.user_id != user.id:
            raise _authentication_failed(purpose, user, 'owner')
        handle = parsed.response.user_handle
        if handle is not None and handle != passkey.user.id.bytes:
            raise _authentication_failed(purpose, user, 'user_handle')
        if not _is_active(passkey.user):
            raise _authentication_failed(purpose, user, 'inactive')
        try:
            verified = verify_authentication_response(
                credential=parsed, expected_challenge=challenge,
                expected_rp_id=settings.WEBAUTHN_RP_ID, expected_origin=settings.WEBAUTHN_ALLOWED_ORIGINS,
                credential_public_key=bytes(passkey.public_key),
                credential_current_sign_count=passkey.sign_count,  # 巻き戻り（両方 0 を除く）はここで拒まれる
                require_user_verification=True)
        except _BAD_RESPONSE:
            raise _authentication_failed(purpose, user, 'verify')

        passkey.sign_count = verified.new_sign_count
        fields = ['sign_count']
        if purpose == Purpose.LOGIN:
            passkey.last_used_at = timezone.now()
            fields.append('last_used_at')
        passkey.save(update_fields=fields)

    if purpose == Purpose.LOGIN:
        logger.info('passkey login ok user_id=%s passkey_id=%s', passkey.user_id, passkey.id)
    else:
        logger.info('passkey reauth ok user_id=%s method=passkey', passkey.user_id)
    return passkey


def complete_login(*, user: User) -> dict:
    """ログインを終える（最後のログインの日時を更新し、応答を作る）。パスワード・パスキーで同じ"""
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh), 'user': UserSerializer(user).data}


# ---------------------------------------------------------------- 本人確認 ----
def issue_reauth_token(*, user: User) -> str:
    return signing.dumps({'uid': str(user.id), 'iat': int(timezone.now().timestamp())}, salt=REAUTH_SALT)


def has_valid_reauth(*, user: User, token: str | None) -> bool:
    if not token or not getattr(user, 'is_authenticated', False):
        return False
    try:
        payload = signing.loads(token, salt=REAUTH_SALT)
    except signing.BadSignature:
        return False
    if not isinstance(payload, dict) or payload.get('uid') != str(user.id):
        return False
    issued_at = payload.get('iat')
    if not isinstance(issued_at, int):
        return False
    age = timezone.now().timestamp() - issued_at
    return 0 <= age <= settings.PASSKEY_REAUTH_MAX_AGE_SECONDS


def verify_password_for_reauth(*, user: User, password: str) -> None:
    """本人確認のパスワード。誤りはログインと同じく数え、5 回で 30 分ロックする（ロック中は正しくても拒む）"""
    with transaction.atomic():
        account = User.objects.select_for_update().get(pk=user.pk)
        if account.is_account_locked():
            logger.warning('passkey reauth failed user_id=%s method=password reason=%s', user.id, 'locked')
            until = timezone.localtime(account.account_locked_until).strftime('%Y/%m/%d %H:%M')
            raise PasskeyError(f'アカウントがロックされています。{until}まで待ってから再試行してください。')
        failed = not account.check_password(password)
        if failed:
            account.record_failed_login()  # ログインと同じ規則（User.LOCK_THRESHOLD・LOCK_MINUTES）
        elif account.failed_login_attempts:
            account.unlock_account()
    if failed:
        logger.warning('passkey reauth failed user_id=%s method=password reason=%s', user.id, 'password')
        raise PasskeyError(WRONG_PASSWORD)
    logger.info('passkey reauth ok user_id=%s method=password', user.id)


# -------------------------------------------------------------- 名前・削除 ----
def clean_passkey_name(value: str) -> str:
    """前後の空白を除き、制御文字（Cc）と書字方向などを変える文字（Cf）を拒む"""
    name = value.strip()
    if not name:
        raise serializers.ValidationError('名前を入力してください')
    if any(unicodedata.category(ch) in ('Cc', 'Cf') for ch in name):
        raise serializers.ValidationError('名前に使えない文字が含まれています')
    return name


def rename_passkey(*, passkey: Passkey, name: str) -> Passkey:
    passkey.name = name
    passkey.save(update_fields=['name'])
    logger.info('passkey renamed user_id=%s passkey_id=%s', passkey.user_id, passkey.id)
    return passkey


def delete_passkey(*, passkey: Passkey) -> None:
    user_id, passkey_id = passkey.user_id, passkey.id
    passkey.delete()
    logger.info('passkey deleted user_id=%s passkey_id=%s', user_id, passkey_id)


def delete_passkeys_of_inactive_user(*, user: User) -> None:
    if user.is_active:
        return
    count, _ = Passkey.objects.filter(user=user).delete()
    if count:
        logger.info('passkeys deleted on deactivation user_id=%s count=%s', user.id, count)


def delete_passkeys_of_inactive_organization(*, organization: Organization) -> None:
    if organization.is_active:
        return
    count, _ = Passkey.objects.filter(user__organization=organization).delete()
    if count:
        logger.info('passkeys deleted on deactivation organization_id=%s count=%s', organization.id, count)
