from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from django.db import transaction
from .models import User, UserSettings, StudyStreak, Organization


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
    organization_id = serializers.IntegerField(write_only=True, required=True)

    # 新規追加フィールド
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True,
        min_length=1,
        error_messages={
            'required': '科目を最低1つ選択してください',
            'min_length': '科目を最低1つ選択してください',
        }
    )

    class Meta:
        model = User
        fields = (
            'email', 'user_id', 'password', 'password_confirm',
            'first_name', 'last_name', 'organization_id', 'subject_ids'
        )

    def validate(self, attrs):
        # パスワード確認
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'パスワードが一致しません'
            })

        # 科目が組織に属することを確認
        organization_id = attrs.get('organization_id')
        subject_ids = attrs.get('subject_ids', [])

        from problems.models import Subject
        valid_subjects = Subject.objects.filter(
            organization_id=organization_id,
            id__in=subject_ids
        )

        if valid_subjects.count() != len(subject_ids):
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

    def validate_organization_id(self, value):
        """組織IDの検証"""
        if not Organization.objects.filter(
            organization_id=value,
            is_active=True
        ).exists():
            raise serializers.ValidationError('無効な組織IDです')
        return value

    @transaction.atomic
    def create(self, validated_data):
        subject_ids = validated_data.pop('subject_ids')
        organization_id = validated_data.pop('organization_id')
        validated_data.pop('password_confirm')

        # ユーザー作成
        user = User.objects.create_user(**validated_data)

        # 組織を設定
        user.organization_id = organization_id
        user.save(update_fields=['organization_id'])

        # 科目アクセス権限を設定
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

                    failed_user.failed_login_attempts += 1

                    # Lock account after 5 failed attempts for 30 minutes
                    if failed_user.failed_login_attempts >= 5:
                        failed_user.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)

                    failed_user.save(update_fields=['failed_login_attempts', 'account_locked_until'])
                    raise serializers.ValidationError("ユーザーIDまたはパスワードが正しくありません。")

                if not user.is_active:
                    raise serializers.ValidationError("このアカウントは無効化されています。")

                # Reset failed login attempts on successful login
                if user.failed_login_attempts > 0:
                    user.failed_login_attempts = 0
                    user.account_locked_until = None
                    user.save(update_fields=['failed_login_attempts', 'account_locked_until'])

                attrs['user'] = user
                return attrs

            except User.DoesNotExist:
                raise serializers.ValidationError("ユーザーIDまたはパスワードが正しくありません。")

        raise serializers.ValidationError("ユーザーIDとパスワードを入力してください。")


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.name', read_only=True, default=None
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'user_id', 'role',
            'is_email_verified', 'is_staff', 'is_superuser',
            'last_login', 'created_at',
            'organization_name',
        )
        read_only_fields = (
            'id', 'user_id', 'role', 'is_staff', 'is_superuser',
            'last_login', 'created_at', 'organization_name',
        )


class AdminUserSerializer(serializers.ModelSerializer):
    """管理者用の詳細なユーザーシリアライザー"""
    is_admin = serializers.BooleanField(source='is_staff', required=False)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'user_id', 'first_name', 'last_name',
            'role', 'is_active', 'is_admin', 'is_superuser',
            'is_email_verified', 'last_login', 'created_at', 'updated_at',
            'failed_login_attempts', 'account_locked_until'
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
