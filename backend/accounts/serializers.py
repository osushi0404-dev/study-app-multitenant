from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import RegexValidator
from django.db import transaction
from .models import Passkey, User, UserSettings, StudyStreak
from .services import create_personal_organization


class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    user_id = serializers.CharField(
        required=True,
        min_length=3,
        max_length=30,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_]+$',
                message='ユーザーIDは半角英数字とアンダースコアのみ使用できます',
                code='invalid_user_id'
            )
        ]
    )
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    # 学ぶ科目。組織に科目があるときだけ 1 つ以上が必須（validate で見る・I539）
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list,
    )

    class Meta:
        model = User
        fields = (
            'email', 'user_id', 'password', 'password_confirm',
            'first_name', 'last_name', 'subject_ids'
        )

    def _registration_target(self):
        """登録先（招待先の組織、または個人用の組織を作るときの「個人利用」カテゴリ）

        組織は入力から受け取らず、ビューが context で渡す（I539）。ちょうど片方が無ければ
        設定の誤りとして止める（渡し忘れで黙って個人用の組織を作らない）
        """
        organization = self.context.get('organization')
        personal_category = self.context.get('personal_category')
        if (organization is None) == (personal_category is None):
            raise ImproperlyConfigured(
                'UserRegistrationSerializer には context の organization か personal_category の'
                'ちょうど片方が要ります')
        return organization, personal_category

    def validate(self, attrs):
        organization, _ = self._registration_target()

        # パスワード確認
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'パスワードが一致しません'
            })

        subject_ids = attrs.get('subject_ids', [])
        if organization is None:
            # 個人用の組織はまだ無く科目も無い。番号は他組織・存在しないの区別なく同じ応答で断る（I446）
            if subject_ids:
                raise serializers.ValidationError({
                    'subject_ids': '選択された科目の一部が無効です'
                })
            return attrs

        from problems.models import Subject
        org_subjects = Subject.objects.filter(organization=organization)
        if not subject_ids:
            if org_subjects.exists():
                raise serializers.ValidationError({
                    'subject_ids': '科目を最低1つ選択してください'
                })
            return attrs

        # 科目が組織に属することを確認
        if org_subjects.filter(id__in=subject_ids).count() != len(subject_ids):
            raise serializers.ValidationError({
                'subject_ids': '選択された科目の一部が無効です'
            })

        return attrs

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'このメールアドレスは既に使用されています'
            )
        return value

    def validate_user_id(self, value):
        if User.objects.filter(user_id=value).exists():
            raise serializers.ValidationError(
                'このユーザーIDは既に使用されています'
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        subject_ids = validated_data.pop('subject_ids', [])
        validated_data.pop('password_confirm')

        organization, personal_category = self._registration_target()
        if organization is None:
            # 本人ひとりの組織を、利用者と同じトランザクションで作り、その人を管理者にする（I539）
            organization = create_personal_organization(
                user_id=validated_data['user_id'], category=personal_category)
            role = 'admin'
        else:
            role = 'user'

        user = User.objects.create_user(**validated_data, organization=organization, role=role)

        # 科目アクセス権限を設定
        if subject_ids:
            from problems.models import UserSubjectAccess
            UserSubjectAccess.objects.bulk_create([
                UserSubjectAccess(user=user, subject_id=subject_id)
                for subject_id in subject_ids
            ])

        # 既存の関連オブジェクト作成
        UserSettings.objects.get_or_create(user=user)
        StudyStreak.objects.get_or_create(user=user)

        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.CharField()  # ユーザーIDまたはメールアドレス
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email_or_user_id = attrs.get('email')  # フィールド名はemailだが、実際はユーザーIDまたはメールアドレス
        password = attrs.get('password')

        if email_or_user_id and password:
            try:
                # メールアドレス形式かどうかチェック
                if '@' in email_or_user_id:
                    user = User.objects.get(email=email_or_user_id)
                else:
                    user = User.objects.get(user_id=email_or_user_id)

                # Check if account is locked
                if user.is_account_locked():
                    raise serializers.ValidationError(
                        f"アカウントがロックされています。{user.account_locked_until}まで待ってから再試行してください。"
                    )

                # Authenticate user
                user = authenticate(
                    request=self.context.get('request'),
                    username=email_or_user_id,
                    password=password,
                )

                if not user:
                    # Handle failed login attempt - get the user again to update failed attempts
                    if '@' in email_or_user_id:
                        failed_user = User.objects.get(email=email_or_user_id)
                    else:
                        failed_user = User.objects.get(user_id=email_or_user_id)

                    # Lock account after LOCK_THRESHOLD failed attempts（パスキーの本人確認と同じ規則・I619）
                    failed_user.record_failed_login()
                    raise serializers.ValidationError("ユーザーIDまたはパスワードが正しくありません。")

                if not user.is_active:
                    raise serializers.ValidationError("このアカウントは無効化されています。")

                # Reset failed login attempts on successful login
                if user.failed_login_attempts > 0:
                    user.unlock_account()

                attrs['user'] = user
                return attrs

            except User.DoesNotExist:
                raise serializers.ValidationError("ユーザーIDまたはパスワードが正しくありません。")

        raise serializers.ValidationError("ユーザーIDとパスワードを入力してください。")


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.name', read_only=True, default=None
    )
    # メンバー管理を使えるか（画面がメニューと入口を出し分ける。API の権限と同じ判定・I636）
    can_manage_members = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'user_id', 'role',
            'is_email_verified', 'is_staff', 'is_superuser',
            'last_login', 'created_at',
            'organization_name', 'can_manage_members',
        )
        read_only_fields = (
            'id', 'user_id', 'role', 'is_staff', 'is_superuser',
            'last_login', 'created_at', 'organization_name', 'can_manage_members',
        )


# ---------------------------------------------------------------- メンバー管理（I620） ----
class MemberSerializer(serializers.ModelSerializer):
    """組織の管理者が見るメンバーの行。数と期限は get_queryset の注釈から読む"""
    passkey_count = serializers.IntegerField(read_only=True)
    registration_link_expires_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_self = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'user_id', 'role', 'is_active', 'last_login', 'created_at',
                  'passkey_count', 'registration_link_expires_at', 'is_self')
        read_only_fields = fields

    def get_is_self(self, obj) -> bool:
        request = self.context.get('request')
        return request is not None and obj.pk == request.user.pk


DUPLICATE_USER_ID = 'このユーザーIDは既に使用されています'


class MemberCreateSerializer(serializers.Serializer):
    """メンバーの作成はユーザー ID だけ（役割・組織・有効は受け取らない）"""
    # エラー文はすべて日本語にそろえる（DRF の既定の英語を出さない・I636 F6）
    user_id = serializers.CharField(
        min_length=3, max_length=30,
        error_messages={'required': 'ユーザーIDを入力してください',
                        'null': 'ユーザーIDを入力してください',
                        'blank': 'ユーザーIDを入力してください',
                        'invalid': 'ユーザーIDは文字で入力してください',
                        'min_length': 'ユーザーIDは3文字以上で入力してください',
                        'max_length': 'ユーザーIDは30文字以内で入力してください'},
        validators=[RegexValidator(regex=r'^[a-zA-Z0-9_]+$',
                                   message='ユーザーIDは半角英数字とアンダースコアのみ使用できます',
                                   code='invalid_user_id')])

    def validate_user_id(self, value):
        if User.objects.filter(user_id=value).exists():
            raise serializers.ValidationError(DUPLICATE_USER_ID)
        return value


class RegistrationLinkIssuedSerializer(serializers.Serializer):
    url = serializers.CharField()
    expires_at = serializers.DateTimeField()


class RegistrationLinkTokenSerializer(serializers.Serializer):
    """リンクの値。形の確かめはサービスが行い、使えないリンクと同じ文にそろえる（理由を見分けさせない）"""
    token = serializers.CharField(allow_blank=True, trim_whitespace=False)


class RegistrationLinkOptionsSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    options = serializers.DictField()
    user_id = serializers.CharField()


class RegistrationLinkCompleteSerializer(RegistrationLinkTokenSerializer):
    challenge_id = serializers.UUIDField()
    credential = serializers.DictField()


class AdminUserSerializer(serializers.ModelSerializer):
    """管理者用の詳細なユーザーシリアライザー"""
    is_admin = serializers.BooleanField(source='is_staff', required=False)
    # 本人ひとりの組織か（運営の画面が登録用リンクの欄を出し分ける・I620）
    organization_is_individual = serializers.BooleanField(
        source='organization.is_individual', read_only=True, default=False)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'user_id', 'first_name', 'last_name',
            'role', 'is_active', 'is_admin', 'is_superuser',
            'is_email_verified', 'last_login', 'created_at', 'updated_at',
            'failed_login_attempts', 'account_locked_until', 'organization_is_individual',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_login')


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = (
            'daily_study_goal_minutes',
            'study_reminders_enabled',
            'reminder_time',
            'theme_preference',
            'notification_settings',
        )

    def validate_daily_study_goal_minutes(self, value):
        if value < 5 or value > 480:  # 5 minutes to 8 hours
            raise serializers.ValidationError("学習目標時間は5分から480分の間で設定してください。")
        return value


class StudyStreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyStreak
        fields = ('current_streak', 'longest_streak', 'last_study_date')
        read_only_fields = ('current_streak', 'longest_streak', 'last_study_date')


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("このメールアドレスのユーザーは存在しません。")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class PasskeySerializer(serializers.ModelSerializer):
    """パスキーの一覧・名前の変更（I619）。鍵・認証器の ID・署名回数は出さない"""
    name = serializers.CharField(max_length=64, trim_whitespace=True)

    class Meta:
        model = Passkey
        fields = ('id', 'name', 'created_at', 'last_used_at')
        read_only_fields = ('id', 'created_at', 'last_used_at')

    def validate_name(self, value):
        from .passkeys import clean_passkey_name  # passkeys が serializers を読むので、ここで読む
        return clean_passkey_name(value)

    def validate(self, attrs):
        # 書ける項目は名前だけ。PATCH（partial）で名前が無い本文は入力の誤り（I619 F1）
        if 'name' not in attrs:
            raise serializers.ValidationError({'name': '名前を入力してください'})
        return attrs


class WebAuthnOptionsSerializer(serializers.Serializer):
    """WebAuthn の options と、検証のときに送り返す challenge の番号（I619）"""
    challenge_id = serializers.UUIDField()
    options = serializers.DictField()


class WebAuthnCredentialSerializer(serializers.Serializer):
    """ブラウザの PublicKeyCredential.toJSON() の結果（中身の検証は py_webauthn に任せる・I619）"""
    challenge_id = serializers.UUIDField()
    credential = serializers.DictField()


class PasskeyReauthSerializer(serializers.Serializer):
    """本人確認: パスワードか、パスキー（challenge_id と credential）のちょうど片方（I619）"""
    password = serializers.CharField(required=False, write_only=True, trim_whitespace=False)
    challenge_id = serializers.UUIDField(required=False)
    credential = serializers.DictField(required=False)

    def validate(self, attrs):
        present = attrs.keys() & {'password', 'challenge_id', 'credential'}
        if present not in ({'password'}, {'challenge_id', 'credential'}):
            raise serializers.ValidationError('パスワードか、パスキーのどちらか一方で確かめてください')
        return attrs


class ReauthTokenSerializer(serializers.Serializer):
    reauth_token = serializers.CharField()
    expires_in = serializers.IntegerField()


class LoginResponseSerializer(serializers.Serializer):
    """ログインの応答（パスワード・パスキーで同じ形・I619）"""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("現在のパスワードが正しくありません。")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("新しいパスワードが一致しません。")
        return attrs
