import secrets
import uuid
from datetime import timedelta

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.http import Http404
from rest_framework import mixins, status, generics, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from core.throttling import AppAnonRateThrottle, AppScopedRateThrottle

from django.db.models import Count, OuterRef, Subquery

from . import passkeys, registration_links
from .models import (
    User, EmailVerification, PasswordResetToken, UserSettings, StudyStreak, Organization, Passkey,
    RegistrationLink,
)
from .permissions import HasRecentReauth, IsOrgMemberManager
from .services import get_personal_category
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    AdminUserSerializer,
    PasskeySerializer,
    PasskeyReauthSerializer,
    ReauthTokenSerializer,
    LoginResponseSerializer,
    MemberCreateSerializer,
    MemberSerializer,
    RegistrationLinkCompleteSerializer,
    RegistrationLinkIssuedSerializer,
    RegistrationLinkOptionsSerializer,
    RegistrationLinkTokenSerializer,
    WebAuthnCredentialSerializer,
    WebAuthnOptionsSerializer,
    UserSettingsSerializer,
    StudyStreakSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer,
    ChangePasswordSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = UserLoginSerializer

    @method_decorator(ratelimit(key='ip', rate='5/5m', method='POST'))
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # 最後のログインの日時の更新と応答は、パスキーのログインと同じ処理（I619）
        return Response(passkeys.complete_login(user=user))


# ------------------------------------------------------------ パスキー（I619） ----
def _options_response(challenge, options):
    return Response(WebAuthnOptionsSerializer({'challenge_id': challenge.id, 'options': options}).data)


@extend_schema(tags=['passkeys'])
class PasskeyLoginOptionsView(generics.GenericAPIView):
    """パスキーでのログインの options。ログインの前に呼ぶので AllowAny"""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AppScopedRateThrottle]
    throttle_scope = 'passkey_login_options'
    serializer_class = WebAuthnOptionsSerializer

    @extend_schema(request=None, responses={200: WebAuthnOptionsSerializer})
    def post(self, request):
        return _options_response(*passkeys.authentication_options())


@extend_schema(tags=['passkeys'])
class PasskeyLoginView(generics.GenericAPIView):
    """パスキーでのログイン。ログインの前に呼ぶので AllowAny"""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AppScopedRateThrottle]
    throttle_scope = 'passkey_login'
    serializer_class = WebAuthnCredentialSerializer

    @extend_schema(request=WebAuthnCredentialSerializer, responses={200: LoginResponseSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        passkey = passkeys.authenticate_passkey(
            challenge_id=serializer.validated_data['challenge_id'],
            credential=serializer.validated_data['credential'])
        return Response(passkeys.complete_login(user=passkey.user))


@extend_schema(tags=['passkeys'])
class PasskeyReauthOptionsView(generics.GenericAPIView):
    """本人確認をパスキーで行うときの options（本人のパスキーだけを許す）"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WebAuthnOptionsSerializer

    @extend_schema(request=None, responses={200: WebAuthnOptionsSerializer})
    def post(self, request):
        return _options_response(*passkeys.authentication_options(user=request.user))


@extend_schema(tags=['passkeys'])
class PasskeyReauthView(generics.GenericAPIView):
    """本人確認（パスワードかパスキー）。通れば 5 分有効の印を返す"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AppScopedRateThrottle]
    throttle_scope = 'passkey_reauth'
    serializer_class = PasskeyReauthSerializer

    @extend_schema(request=PasskeyReauthSerializer, responses={200: ReauthTokenSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if 'password' in data:
            passkeys.verify_password_for_reauth(user=request.user, password=data['password'])
        else:
            passkeys.authenticate_passkey(
                challenge_id=data['challenge_id'], credential=data['credential'], user=request.user)
        return Response(ReauthTokenSerializer({
            'reauth_token': passkeys.issue_reauth_token(user=request.user),
            'expires_in': settings.PASSKEY_REAUTH_MAX_AGE_SECONDS,
        }).data)


@extend_schema(tags=['passkeys'])
class PasskeyViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    """本人のパスキーの一覧・名前の変更・削除・登録（他人・別の組織の物は 404）"""
    serializer_class = PasskeySerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_value_regex = '[0-9a-f-]{36}'  # UUID の形だけ（login などが詳細の <pk> に当たらない）

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # OpenAPI を作るとき（利用者がいない）
            return Passkey.objects.none()
        return Passkey.objects.filter(user=self.request.user)

    def get_permissions(self):
        if self.action in ('destroy', 'register_options', 'register'):
            return [permissions.IsAuthenticated(), HasRecentReauth()]
        return [permissions.IsAuthenticated()]

    def perform_update(self, serializer):
        passkeys.rename_passkey(passkey=serializer.instance, name=serializer.validated_data['name'])

    def perform_destroy(self, instance):
        passkeys.delete_passkey(passkey=instance)

    @extend_schema(request=None, responses={200: WebAuthnOptionsSerializer})
    @action(detail=False, methods=['post'], url_path='register/options')
    def register_options(self, request):
        return _options_response(*passkeys.registration_options(user=request.user))

    @extend_schema(request=WebAuthnCredentialSerializer, responses={201: PasskeySerializer})
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = WebAuthnCredentialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        passkey = passkeys.register_passkey(
            user=request.user, challenge_id=serializer.validated_data['challenge_id'],
            credential=serializer.validated_data['credential'],
            user_agent=request.headers.get('User-Agent', ''))
        return Response(PasskeySerializer(passkey).data, status=status.HTTP_201_CREATED)


# ------------------------------------------------------------ 登録用リンク（I620） ----
@extend_schema(tags=['registration-links'])
class RegistrationLinkOptionsView(generics.GenericAPIView):
    """登録用リンクを開いたときの options。ログインの前に開くので AllowAny（本人はリンクの値で決める）"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # 発行で失効した古いトークンが付いていても 401 にしない（本人はリンクの値で決める）
    throttle_classes = [AppScopedRateThrottle]
    throttle_scope = 'registration_link_options'
    serializer_class = RegistrationLinkTokenSerializer

    @extend_schema(request=RegistrationLinkTokenSerializer, responses={200: RegistrationLinkOptionsSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        challenge, options, user = registration_links.link_registration_options(
            token=serializer.validated_data['token'])
        return Response(RegistrationLinkOptionsSerializer(
            {'challenge_id': challenge.id, 'options': options, 'user_id': user.user_id}).data)


@extend_schema(tags=['registration-links'])
class RegistrationLinkCompleteView(generics.GenericAPIView):
    """登録用リンクでパスキーを登録し、ログインした状態にする。AllowAny（同上）"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # 同上
    throttle_classes = [AppScopedRateThrottle]
    throttle_scope = 'registration_link'
    serializer_class = RegistrationLinkCompleteSerializer

    @extend_schema(request=RegistrationLinkCompleteSerializer, responses={200: LoginResponseSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(registration_links.complete_link_registration(
            token=data['token'], challenge_id=data['challenge_id'], credential=data['credential'],
            user_agent=request.headers.get('User-Agent', '')))


class MemberCredentialActionsMixin:
    """1 人分のパスキーの一覧・削除と、登録用リンクの発行・失効（メンバー管理と運営で共通・I620）

    相手は get_object()（＝ get_queryset で絞った範囲）から取るので、範囲の外は 404 になる。
    credential_scope が 'staff' のときは、運営のアカウントと本人ひとりの組織の利用者を 400 で拒む。
    """
    credential_scope = 'org'
    credential_write_actions = ('delete_member_passkey', 'registration_link')

    def get_permissions(self):
        """書き込みの action だけ、各 ViewSet の permission_classes に直前の本人確認を足す"""
        perms = super().get_permissions()
        return perms + [HasRecentReauth()] if self.action in self.credential_write_actions else perms

    def _credential_target(self, *, for_issue=False):
        target = self.get_object()
        registration_links.ensure_target(
            actor=self.request.user, target=target, scope=self.credential_scope, for_issue=for_issue)
        return target

    @extend_schema(request=None, responses={200: PasskeySerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='passkeys', filter_backends=[])
    def member_passkeys(self, request, pk=None):
        # 組織の管理者は自分のパスキーの一覧も見てよい（相手の確かめは運営の範囲だけ）
        target = self._credential_target() if self.credential_scope == 'staff' else self.get_object()
        queryset = Passkey.objects.filter(user=target)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(PasskeySerializer(page, many=True).data)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=['delete'], url_path=r'passkeys/(?P<passkey_id>[0-9a-f-]{36})')
    def delete_member_passkey(self, request, pk=None, passkey_id=None):
        target = self._credential_target()
        try:  # URL の正規表現は UUID の形までは保証しない（`-` が 36 個など）。形の誤りは 404（I636 M1）
            passkey_uuid = uuid.UUID(passkey_id)
        except ValueError:
            raise Http404
        registration_links.delete_passkey_of(target=target, passkey_id=passkey_uuid, deleted_by=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(methods=['POST'], request=None, responses={201: RegistrationLinkIssuedSerializer})
    @extend_schema(methods=['DELETE'], request=None, responses={204: None})
    @action(detail=True, methods=['post', 'delete'], url_path='registration-link')
    def registration_link(self, request, pk=None):
        if request.method == 'DELETE':
            target = self._credential_target()
            registration_links.revoke_link(target=target, revoked_by=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        target = self._credential_target(for_issue=True)
        link, token = registration_links.issue_link(target=target, issued_by=request.user)
        return Response(RegistrationLinkIssuedSerializer(
            {'url': registration_links.link_url(token), 'expires_at': link.expires_at}).data,
            status=status.HTTP_201_CREATED)


@extend_schema(tags=['members'])
class MemberViewSet(MemberCredentialActionsMixin, mixins.ListModelMixin, mixins.CreateModelMixin,
                    viewsets.GenericViewSet):
    """組織の管理者のメンバー管理（I620）。自分の組織の利用者だけ（運営のアカウントは出さない）"""
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMemberManager]
    lookup_value_regex = '[0-9a-f-]{36}'
    filter_backends = []  # 並びはユーザー ID 順に固定（検索・並べ替えのクエリは受けない）

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # OpenAPI を作るとき（利用者がいない）
            return User.objects.none()
        open_link = RegistrationLink.objects.filter(
            user=OuterRef('pk'), used_at__isnull=True, revoked_at__isnull=True,
            expires_at__gt=timezone.now()).values('expires_at')[:1]
        return (User.objects
                .filter(organization_id=self.request.user.organization_id, is_staff=False, is_superuser=False)
                .annotate(passkey_count=Count('passkeys'),
                          registration_link_expires_at=Subquery(open_link))
                .order_by('user_id'))

    @extend_schema(request=MemberCreateSerializer, responses={201: MemberSerializer})
    def create(self, request, *args, **kwargs):
        serializer = MemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = registration_links.create_member(
            organization=request.user.organization, user_id=serializer.validated_data['user_id'])
        # 作ったばかりの人はパスキー 0 個・開いたリンク無し（集計の問い合わせを流し直さない）
        user.passkey_count = 0
        user.registration_link_expires_at = None
        return Response(MemberSerializer(user, context=self.get_serializer_context()).data,
                        status=status.HTTP_201_CREATED)


@method_decorator(ratelimit(key='ip', rate='10/5m', method='POST'), name='post')
class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger('django')

        # URLからorganization_slugを取得
        organization_slug = kwargs.get('organization_slug')
        logger.info(f"Registration attempt with slug: {organization_slug}")

        try:
            # 登録先を決める。招待（slug あり）は招待で引き当ててよい組織、slug なしは
            # 本人ひとりの組織をシリアライザが作る（組織は入力から受け取らない・I539）
            if organization_slug:
                organization = self._get_organization(organization_slug)
                if not organization:
                    return self._org_setup_failed()
                target = {'organization': organization}
                logger.info(f"Registration attempt for organization_id: {organization.id}")
            else:
                personal_category = get_personal_category()
                if not personal_category:
                    # 「個人利用」カテゴリは migration 0017 で常にある前提。不在は環境の異常なので
                    # 自動作成せず、組織も利用者も作らずに断る（I140 の考え方を引き継ぐ）
                    logger.error(
                        "Personal organization category (slug='personal') not found. "
                        "Environment is misconfigured; slug-less registration rejected."
                    )
                    return self._org_setup_failed()
                target = {'personal_category': personal_category}
                logger.info("Registration attempt for a new personal organization")

            with transaction.atomic():
                serializer = self.get_serializer(
                    data=request.data, context={**self.get_serializer_context(), **target})
                if not serializer.is_valid():
                    logger.error(f"Validation failed: {serializer.errors}")
                    return Response({
                        'error': {
                            'main_message': '入力内容にエラーがあります',
                            'sub_message': next(iter(serializer.errors.values()))[0] if serializer.errors else None,
                            'details': serializer.errors
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)

                logger.info("Validation passed, creating user...")
                user = serializer.save()
                logger.info(
                    f"User created successfully: user_id={user.id} with organization_id: {user.organization_id}")

                # Send email verification
                try:
                    self.send_verification_email(user)
                    logger.info("Email verification sent")
                except Exception as email_error:
                    logger.error(f"Email sending failed: {str(email_error)}", exc_info=True)
                    # Continue with registration even if email fails

                return Response({
                    'message': '登録完了。メール認証を行ってください。',
                    'user_id': str(user.id),
                    'organization': user.organization.name
                }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return Response({
                'error': {
                    'main_message': 'エラーが発生しました',
                    'sub_message': str(e) if settings.DEBUG else None,
                    'details': {}
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _org_setup_failed():
        return Response({
            'error': {
                'main_message': '組織の設定に失敗しました',
                'sub_message': '無効な組織URLまたはシステムエラー'
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    def _get_organization(self, slug):
        """招待の slug から登録先の組織を引く（本人ひとりの組織・共有の personal 組織は引かない・I539）"""
        import logging
        logger = logging.getLogger('django')

        organization = Organization.objects.invitable().filter(slug=slug).first()
        if organization:
            logger.info(f"Found organization by slug: {organization.name}")
        else:
            logger.warning(f"No organization found for slug: {slug}")
        return organization

    def send_verification_email(self, user):
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)

        EmailVerification.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

        # For development, skip email sending
        if settings.DEBUG:
            print(f"Email verification token for user_id={user.id}: {token}")
            return

        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        subject = "学習アプリ - メール認証"
        message = f"""
        こんにちは、

        学習アプリにご登録いただき、ありがとうございます。

        以下のリンクをクリックしてメール認証を完了してください：
        {verification_url}

        このリンクは24時間有効です。

        学習アプリチーム
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )


class OrganizationSlugValidationView(APIView):
    """組織slugの妥当性を検証するエンドポイント"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        """指定されたslugの組織が存在するか確認"""
        import logging
        logger = logging.getLogger('django')

        logger.info(f"Organization slug validation request: {slug}")

        try:
            # 招待で引き当ててよい組織だけ（本人ひとりの組織は「見つからない」と同じ・I539）
            organization = Organization.objects.invitable().filter(slug=slug).first()

            if organization:
                logger.info(f"Valid organization found: {organization.name}")
                return Response({
                    'valid': True,
                    'organization_name': organization.name,
                    'organization_id': organization.id
                })
            else:
                logger.warning(f"No active organization found for slug: {slug}")
                return Response({
                    'valid': False,
                    'message': f'組織 "{slug}" は見つかりません'
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error validating organization slug: {str(e)}", exc_info=True)
            return Response({
                'valid': False,
                'message': 'エラーが発生しました'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='10/5m', method='POST'))
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']

        try:
            verification = EmailVerification.objects.get(token=token)

            if not verification.is_valid():
                return Response({
                    'error': '認証トークンが無効または期限切れです。'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Mark as verified
            verification.is_used = True
            verification.save()

            verification.user.is_email_verified = True
            verification.user.save(update_fields=['is_email_verified'])

            return Response({
                'message': 'メール認証が完了しました。'
            })

        except EmailVerification.DoesNotExist:
            return Response({
                'error': '無効な認証トークンです。'
            }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='3/15m', method='POST'), name='post')
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        # Generate reset token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=1)

        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

        # Send reset email
        reset_url = f"{settings.FRONTEND_URL}/password-reset-confirm?token={token}"

        subject = "学習アプリ - パスワードリセット"
        message = f"""
        こんにちは、

        パスワードリセットのリクエストを受け付けました。

        以下のリンクをクリックして新しいパスワードを設定してください：
        {reset_url}

        このリンクは1時間有効です。

        もしこのリクエストに心当たりがない場合は、このメールを無視してください。

        学習アプリチーム
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        return Response({
            'message': 'パスワードリセット用のメールを送信しました。'
        })


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/5m', method='POST'))
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            reset_token = PasswordResetToken.objects.get(token=token)

            if not reset_token.is_valid():
                return Response({
                    'error': 'リセットトークンが無効または期限切れです。'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Reset password
            user = reset_token.user
            user.set_password(new_password)
            user.save()

            # Mark token as used
            reset_token.is_used = True
            reset_token.save()

            return Response({
                'message': 'パスワードがリセットされました。'
            })

        except PasswordResetToken.DoesNotExist:
            return Response({
                'error': '無効なリセットトークンです。'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        settings, created = UserSettings.objects.get_or_create(user=self.request.user)
        return settings


class StudyStreakView(generics.RetrieveAPIView):
    serializer_class = StudyStreakSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        streak, created = StudyStreak.objects.get_or_create(user=self.request.user)
        return streak


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='5/5m', method='POST'))
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data['new_password']

        user.set_password(new_password)
        user.save()

        return Response({
            'message': 'パスワードが変更されました。'
        })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@ratelimit(key='ip', rate='5/5m', method='POST')
def logout_view(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'ログアウトしました。'})
    except Exception:
        return Response(
            {'error': 'ログアウトに失敗しました。'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class AdminUserViewSet(MemberCredentialActionsMixin, viewsets.ModelViewSet):
    """
    管理者用ユーザー管理API
    """
    queryset = User.objects.select_related('organization')  # organization_is_individual（I620）で N+1 にしない
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    credential_scope = 'staff'  # 登録用リンク・パスキー（I620）: 運営・本人ひとりの組織の人は 400

    def create(self, request, *args, **kwargs):
        """管理者による新規ユーザー作成"""
        data = request.data.copy()

        # パスワードが提供されていない場合はランダムパスワードを生成
        if 'password' not in data:
            data['password'] = secrets.token_urlsafe(16)

        # 管理者フラグの設定を許可
        is_admin = data.get('is_admin', False)
        is_superuser = data.get('is_superuser', False)

        # ユーザーを作成
        serializer = UserRegistrationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # 管理者権限を設定
        if is_admin:
            user.is_staff = True
        if is_superuser:
            user.is_superuser = True
        user.save()

        return Response(
            AdminUserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """管理者によるユーザー情報更新"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()

        # パスワードの更新
        if 'password' in data:
            instance.set_password(data.pop('password'))

        # 管理者権限の更新
        if 'is_admin' in data:
            instance.is_staff = data.pop('is_admin')
        if 'is_superuser' in data:
            instance.is_superuser = data.pop('is_superuser')

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        instance.save()

        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """管理者によるパスワードリセット"""
        user = self.get_object()
        new_password = secrets.token_urlsafe(16)
        user.set_password(new_password)
        user.save()

        return Response({
            'message': 'パスワードをリセットしました',
            'temporary_password': new_password
        })

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """ユーザーのアクティブ状態を切り替え"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()

        return Response({
            'message': f'ユーザーを{"有効化" if user.is_active else "無効化"}しました',
            'is_active': user.is_active
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """ユーザー統計情報を取得"""
        from datetime import timedelta

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        admin_users = User.objects.filter(is_staff=True).count()
        verified_users = User.objects.filter(is_email_verified=True).count()

        # 過去30日間のログイン数
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_logins = User.objects.filter(
            last_login__gte=thirty_days_ago
        ).count()

        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'verified_users': verified_users,
            'recent_logins': recent_logins
        })


class FieldValidationView(generics.GenericAPIView):
    """フィールド単位のバリデーション（既存のバリデーションロジックを再利用）"""
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer
    throttle_classes = [AppAnonRateThrottle]

    def post(self, request, *args, **kwargs):
        field_name = request.data.get('field')
        field_value = request.data.get('value')

        if not field_name or field_value is None:
            return Response({
                'valid': False,
                'message': 'フィールド名と値が必要です'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 既存のSerializerのバリデーションメソッドを活用
        serializer = self.get_serializer()

        try:
            # フィールド固有のバリデーションメソッドを呼び出し
            if field_name == 'email' and hasattr(serializer, 'validate_email'):
                serializer.validate_email(field_value)
            elif field_name == 'user_id' and hasattr(serializer, 'validate_user_id'):
                serializer.validate_user_id(field_value)
            elif field_name == 'password':
                # パスワードの強度チェック
                validate_password(field_value)
            else:
                return Response({
                    'valid': False,
                    'message': f'未対応のフィールド: {field_name}'
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({'valid': True, 'message': None})

        except serializers.ValidationError as e:
            message = str(e.detail[0]) if isinstance(e.detail, list) else str(e.detail)
            return Response({'valid': False, 'message': message})
        except ValidationError as e:
            return Response({'valid': False, 'message': e.messages[0] if e.messages else 'バリデーションエラー'})
