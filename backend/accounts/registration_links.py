"""登録用リンクの業務の処理（I620）

- リンクの値は 256 ビットの乱数。DB には SHA-256 だけを置き、元の値は発行の戻り値で一度だけ返す
- 発行の時点で、前のリンクを失効にし、その利用者のパスキーと refresh トークンをすべて使えなくする
- 使えない理由（期限切れ・使用済み・失効・無効）は応答で見分けさせず、ログの reason= だけに残す
- ログには利用者・リンク・発行者の ID だけを出す（値・ハッシュ・ユーザー ID は出さない）
"""
import hashlib
import logging
import re
import secrets
import uuid
from datetime import timedelta
from typing import Literal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from . import passkeys
from .models import Organization, Passkey, RegistrationLink, User, WebAuthnChallenge
from .serializers import DUPLICATE_USER_ID

logger = logging.getLogger(__name__)

LINK_UNUSABLE = 'このリンクは使えません。管理者に新しいリンクを発行してもらってください'
CANNOT_TARGET_SELF = '自分あてには操作できません。ほかの管理者か運営に依頼してください'
INACTIVE_TARGET = '無効の利用者には発行できません'
STAFF_TARGET = '運営のアカウントには画面から発行できません'
INDIVIDUAL_TARGET = '個人利用の利用者には発行できません'
TOKEN_PATTERN = re.compile(r'[A-Za-z0-9_-]{43}')  # secrets.token_urlsafe(32) の形

Scope = Literal['org', 'staff']


def hash_token(token: str) -> str:
    """値は十分に長い乱数なので、遅いハッシュは要らない（OWASP の Forgot Password と同じ）"""
    return hashlib.sha256(token.encode()).hexdigest()


def link_url(token: str) -> str:
    return f'{settings.REGISTRATION_LINK_BASE_URL}{settings.REGISTRATION_LINK_PATH}#token={token}'


def ensure_target(*, actor: User, target: User, scope: Scope, for_issue: bool) -> None:
    """操作の相手にできるか。範囲の外（ほかの組織など）は呼ぶ前に get_queryset で 404 にしておく"""
    if target.pk == actor.pk:
        raise passkeys.PasskeyError(CANNOT_TARGET_SELF)
    if scope == 'staff':
        if target.is_staff or target.is_superuser:
            raise passkeys.PasskeyError(STAFF_TARGET)
        if target.organization is not None and target.organization.is_individual:
            raise passkeys.PasskeyError(INDIVIDUAL_TARGET)
    if for_issue and not target.is_active:
        raise passkeys.PasskeyError(INACTIVE_TARGET)


# ---------------------------------------------------------------- 発行・失効 ----
def revoke_sessions(*, user: User) -> int:
    """その利用者の期限内の refresh トークンをすべて失効の表に入れる（simplejwt の公式の表）"""
    tokens = (OutstandingToken.objects
              .filter(user=user, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True))
    created = BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in tokens], ignore_conflicts=True)
    return len(created)


def _close_open_links(*, user: User, now) -> int:
    return RegistrationLink.objects.filter(
        user=user, used_at__isnull=True, revoked_at__isnull=True).update(revoked_at=now)


def issue_link(*, target: User, issued_by: User | None) -> tuple[RegistrationLink, str]:
    """前のリンクの失効 → パスキーの削除 → refresh の失効 → 新しいリンク を 1 つのトランザクションで行う"""
    token = secrets.token_urlsafe(32)
    with transaction.atomic():
        # 同じ人への同時の発行を一列にする（開いたリンクが 2 つにならない。DB の部分一意制約でも止まる）
        User.objects.select_for_update().filter(pk=target.pk).first()
        now = timezone.now()
        _close_open_links(user=target, now=now)
        deleted, _ = Passkey.objects.filter(user=target).delete()
        revoked = revoke_sessions(user=target)
        link = RegistrationLink.objects.create(
            user=target, issued_by=issued_by, token_hash=hash_token(token),
            expires_at=now + timedelta(seconds=settings.REGISTRATION_LINK_TTL_SECONDS))
    logger.info('registration link issued user_id=%s link_id=%s issued_by=%s passkeys_deleted=%s '
                'sessions_revoked=%s', target.pk, link.pk, getattr(issued_by, 'pk', 'command'), deleted, revoked)
    return link, token


def revoke_link(*, target: User, revoked_by: User | None) -> bool:
    """開いているリンクを失効にする。無ければ何もしない（冪等）"""
    closed = _close_open_links(user=target, now=timezone.now())
    if closed:
        logger.info('registration link revoked user_id=%s revoked_by=%s', target.pk,
                    getattr(revoked_by, 'pk', 'command'))
    return bool(closed)


# ------------------------------------------------------------------- 使用 ----
def _unusable(reason: str, link: RegistrationLink | None = None) -> passkeys.PasskeyError:
    logger.warning('registration link unusable link_id=%s reason=%s', getattr(link, 'pk', None), reason)
    return passkeys.PasskeyError(LINK_UNUSABLE)


def _usable_link(token: str, *, lock: bool) -> RegistrationLink:
    if not TOKEN_PATTERN.fullmatch(token):
        raise _unusable('format')
    links = RegistrationLink.objects.select_related('user__organization')
    if lock:
        links = links.select_for_update(of=('self',))
    link = links.filter(token_hash=hash_token(token)).first()
    if link is None:
        raise _unusable('not_found')
    if link.used_at is not None:
        raise _unusable('used', link)
    if link.revoked_at is not None:
        raise _unusable('revoked', link)
    if link.expires_at <= timezone.now():
        raise _unusable('expired', link)
    organization = link.user.organization
    if not link.user.is_active or (organization is not None and not organization.is_active):
        raise _unusable('inactive', link)
    return link


def link_registration_options(*, token: str) -> tuple[WebAuthnChallenge, dict, User]:
    link = _usable_link(token, lock=False)
    challenge, options = passkeys.build_registration_options(
        user=link.user, purpose=WebAuthnChallenge.Purpose.LINK_REGISTER)
    return challenge, options, link.user


def complete_link_registration(*, token: str, challenge_id: uuid.UUID, credential: dict,
                               user_agent: str) -> dict:
    """リンクでパスキーを登録してログインさせる。使用の確定はリンクの行の鍵の中で行う（同時に使っても 1 回）"""
    user = _usable_link(token, lock=False).user
    challenge = passkeys.consume_challenge(
        challenge_id=challenge_id, purpose=WebAuthnChallenge.Purpose.LINK_REGISTER, user=user)
    with transaction.atomic():
        link = _usable_link(token, lock=True)
        if link.user_id != user.pk:  # 値のハッシュは一意なので起きないが、念のため
            raise _unusable('user_changed', link)
        passkey = passkeys.verify_and_create_passkey(
            user=user, challenge=challenge, credential=credential, user_agent=user_agent)
        link.used_at = timezone.now()
        link.save(update_fields=['used_at'])
    logger.info('registration link used user_id=%s link_id=%s passkey_id=%s', user.pk, link.pk, passkey.pk)
    return passkeys.complete_login(user=user)


# ------------------------------------------------------------ メンバーの作成 ----
def create_member(*, organization: Organization, user_id: str) -> User:
    """組織の一般の利用者を作る（パスワード無し）。存在の確認の後に同じ ID ができていたら重複の 400（I636 F4）

    セーブポイント（atomic）の中で作るので、一意の制約の違反で外側のトランザクションを壊さない。
    一意の制約は user_id だけ（email は None）なので、IntegrityError は ID の重複に限られる
    """
    try:
        with transaction.atomic():
            return User.objects.create_user(user_id=user_id, password=None, organization=organization, role='user')
    except IntegrityError:
        logger.info('member create duplicate organization_id=%s', organization.pk)
        raise serializers.ValidationError({'user_id': [DUPLICATE_USER_ID]})


# ------------------------------------------------------- 管理者によるパスキー ----
def delete_passkey_of(*, target: User, passkey_id: uuid.UUID, deleted_by: User) -> None:
    passkey = Passkey.objects.filter(user=target, pk=passkey_id).first()
    if passkey is None:
        raise Http404
    passkey.delete()
    logger.info('passkey deleted by admin user_id=%s passkey_id=%s deleted_by=%s',
                target.pk, passkey_id, deleted_by.pk)
