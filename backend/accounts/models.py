import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import MinLengthValidator, RegexValidator


class OrganizationCategory(models.Model):
    name = models.CharField(max_length=50, verbose_name='カテゴリー名')
    slug = models.SlugField(max_length=50, unique=True, verbose_name='URL識別子')
    description = models.TextField(blank=True, verbose_name='説明')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organization_categories'
        ordering = ['display_order', 'name']
        verbose_name = '組織カテゴリー'
        verbose_name_plural = '組織カテゴリー'

    def __str__(self):
        return self.name


class Organization(models.Model):
    TYPE_CHOICES = [
        ('school', 'School'),
        ('corporate', 'Corporate'),
        ('personal', 'Personal'),
    ]

    id = models.AutoField(primary_key=True)  # organization_idから変更
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=100, verbose_name='組織名')
    slug = models.SlugField(
        max_length=50,
        unique=False,  # 重複可能に変更
        verbose_name='URL識別子',
        help_text='URL用の識別子（半角英数字とハイフンのみ）'
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='personal',
        verbose_name='組織タイプ'
    )
    is_active = models.BooleanField(default=True, verbose_name='有効')
    category = models.ForeignKey(
        'OrganizationCategory',
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='カテゴリー'
    )

    class Meta:
        verbose_name = '組織'
        verbose_name_plural = '組織'
        db_table = 'organizations'
        indexes = [
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email=None, user_id=None, password=None, **extra_fields):
        if not user_id:
            raise ValueError('The User ID field must be set')
        if email:
            email = self.normalize_email(email)
        user = self.model(email=email, user_id=user_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, user_id=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, user_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, null=True, blank=True)
    user_id = models.CharField(
        max_length=30,
        unique=True,
        null=True,  # Temporarily allow null for migration
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_]+$',
                message='ユーザーIDは半角英数字とアンダースコアのみ使用できます',
                code='invalid_user_id'
            ),
            MinLengthValidator(3, 'ユーザーIDは3文字以上で入力してください')
        ],
        help_text='半角英数字とアンダースコアのみ使用可能'
    )
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
        verbose_name='所属組織'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['last_login']),
        ]

    def __str__(self):
        return self.email

    def is_account_locked(self):
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False

    def unlock_account(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])


class EmailVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_verifications'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_reset_tokens'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()


class UserSettings(models.Model):
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    daily_study_goal_minutes = models.IntegerField(default=30)
    study_reminders_enabled = models.BooleanField(default=True)
    reminder_time = models.TimeField(default='19:00:00')
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    notification_settings = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_settings'

    def __str__(self):
        return f"{self.user.email} Settings"


class StudyStreak(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='study_streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'study_streaks'

    def __str__(self):
        return f"{self.user.email} - {self.current_streak} days"

    def update_streak(self, study_date=None):
        if study_date is None:
            study_date = timezone.now().date()

        if self.last_study_date is None:
            # First study session
            self.current_streak = 1
            self.longest_streak = 1
        elif study_date == self.last_study_date:
            # Same day, no change
            return
        elif study_date == self.last_study_date + timezone.timedelta(days=1):
            # Consecutive day
            self.current_streak += 1
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
        else:
            # Streak broken
            self.current_streak = 1

        self.last_study_date = study_date
        self.save()
