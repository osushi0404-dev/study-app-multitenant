import secrets
from datetime import timedelta

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from rest_framework import status, generics, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from core.throttling import AppAnonRateThrottle
from core.exceptions import EnvironmentMisconfiguredError

from .models import User, EmailVerification, PasswordResetToken, UserSettings, StudyStreak, Organization
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    AdminUserSerializer,
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

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


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

        # 想定内: リクエスト形式が不正（クライアント起因）
        if not isinstance(request.data, dict):
            return Response({
                'error': {
                    'main_message': '入力内容にエラーがあります',
                    'sub_message': '不正なリクエスト形式です',
                    'details': {}
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # 想定内: slug 指定で組織が見つからない（クライアント起因）
        # slug なしで personal 組織が不在の場合は _get_organization が 500 を raise する
        organization = self._get_organization(organization_slug)
        if not organization:
            return Response({
                'error': {
                    'main_message': '組織の設定に失敗しました',
                    'sub_message': '無効な組織URLまたはシステムエラー'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # リクエストデータに組織IDを追加
        mutable_data = request.data.copy()
        mutable_data['organization_id'] = organization.id

        logger.info(f"Registration attempt with data: {mutable_data}")

        with transaction.atomic():
            serializer = self.get_serializer(data=mutable_data)
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
            logger.info(f"User created successfully: {user.email} with organization_id: {user.organization_id}")

            # Send email verification
            try:
                self.send_verification_email(user)
                logger.info("Email verification sent")
            except Exception as email_error:
                # 意図的な狭域設計: メール送信の失敗では登録自体を失敗させない（I142 規約の許容ケース）
                logger.error(f"Email sending failed: {str(email_error)}", exc_info=True)

            return Response({
                'message': '登録完了。メール認証を行ってください。',
                'user_id': str(user.id),
                'organization': organization.name
            }, status=status.HTTP_201_CREATED)
        # 想定外例外は捕捉せず伝播させる（custom_exception_handler がログ+500 に変換する）

    def _get_organization(self, slug=None):
        """組織を取得する（slug 指定時は該当組織・未指定時は既定の personal 組織）"""
        import logging
        logger = logging.getLogger('django')

        if slug:
            # slugから組織を検索
            organization = Organization.objects.filter(
                slug=slug,
                is_active=True
            ).first()
            if organization:
                logger.info(f"Found organization by slug: {organization.name}")
            else:
                logger.warning(f"No organization found for slug: {slug}")
            return organization
        else:
            # デフォルト：personal組織を取得
            personal = Organization.objects.filter(
                type='personal',
                is_active=True
            ).first()

            if not personal:
                # personal 組織は migration 0014/0017/0018 で常に存在する前提。
                # 不在は環境異常（サーバー起因）のため、クライアント起因の 400 ではなく
                # 500 で顕在化させる（I142）
                logger.error(
                    "Personal organization (type='personal', is_active=True) not found. "
                    "Environment is misconfigured; slug-less registration rejected."
                )
                raise EnvironmentMisconfiguredError()

            logger.info(f"Using personal organization: {personal.name}")
            return personal

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
            print(f"Email verification token for {user.email}: {token}")
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

        organization = Organization.objects.filter(
            slug=slug,
            is_active=True
        ).first()

        if organization:
            logger.info(f"Valid organization found: {organization.name}")
            return Response({
                'valid': True,
                'organization_name': organization.name,
                'organization_id': organization.id
            })

        logger.warning(f"No active organization found for slug: {slug}")
        return Response({
            'valid': False,
            'message': f'組織 "{slug}" は見つかりません'
        }, status=status.HTTP_404_NOT_FOUND)
        # 想定外例外は捕捉せず伝播させる（custom_exception_handler がログ+500 に変換する）


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
    # 想定内: refresh 欠落・不正なリクエスト形式（クライアント起因）
    refresh_token = request.data.get('refresh') if isinstance(request.data, dict) else None
    if not refresh_token:
        return Response(
            {'error': 'ログアウトに失敗しました。'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        RefreshToken(refresh_token).blacklist()
    except TokenError:
        # 想定内: 無効・失効・ブラックリスト済みのトークン（クライアント起因）
        return Response(
            {'error': 'ログアウトに失敗しました。'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({'message': 'ログアウトしました。'})
    # 想定外例外は捕捉せず伝播させる（custom_exception_handler がログ+500 に変換する）


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    管理者用ユーザー管理API
    """
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]

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
