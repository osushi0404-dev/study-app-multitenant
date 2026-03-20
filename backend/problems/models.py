import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class SubjectGroup(models.Model):
    name = models.CharField(max_length=50, verbose_name='グループ名')
    slug = models.SlugField(max_length=50, unique=True, verbose_name='URL識別子')
    description = models.TextField(blank=True, verbose_name='説明')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'problems_subject_group'
        ordering = ['display_order', 'name']
        verbose_name = '科目グループ'
        verbose_name_plural = '科目グループ'

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100)  # unique=Trueを削除（Meta.unique_togetherで管理）
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subjects',
        verbose_name='所属組織',
        help_text='null=全体共有科目、値あり=グループ専用科目'
    )
    group = models.ForeignKey(
        'SubjectGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subjects',
        verbose_name='科目グループ'
    )

    # 画像ディレクトリ管理フィールド（イシュー#028対応）
    image_directory = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='画像ディレクトリ',
        help_text='科目の画像ベースディレクトリ（例: problems/aws-clf）。空の場合は科目名から自動生成。'
    )

    # ストレージパス用スラッグ（イシュー#029対応）
    slug = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        verbose_name='科目スラッグ',
        help_text='科目のスラッグ（ストレージパス用、例: aws-saa）'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['name', 'organization']]

    def __str__(self):
        return self.name

    def get_image_base_directory(self):
        """科目の画像ベースディレクトリを取得（設定値またはデフォルト）"""
        if self.image_directory:
            return self.image_directory.rstrip('/')
        # デフォルト: 科目名をスラッグ化（科目別ディレクトリ構造）
        subject_slug = self.name.lower().replace(' ', '-')
        return f'problems/{subject_slug}'

    def get_question_image_directory(self):
        """問題画像のディレクトリを取得（新形式対応）"""
        # イシュー#029: 新形式のディレクトリ構造に対応
        # org/{org.slug}/subjects/{subject.slug}/problem
        if hasattr(self, 'organization') and self.organization:
            return f'org/{self.organization.slug}/subjects/{self.slug}/problem'
        # フォールバック（旧形式）
        return f'{self.get_image_base_directory()}/questions'

    def get_explanation_image_directory(self):
        """解説画像のディレクトリを取得（新形式対応）"""
        # イシュー#029: 新形式のディレクトリ構造に対応
        # org/{org.slug}/subjects/{subject.slug}/explanation
        if hasattr(self, 'organization') and self.organization:
            return f'org/{self.organization.slug}/subjects/{self.slug}/explanation'
        # フォールバック（旧形式）
        return f'{self.get_image_base_directory()}/explanations'


class Problem(models.Model):
    DIFFICULTY_CHOICES = [
        (1, '初級'),
        (2, '中級'),
        (3, '上級'),
    ]

    PROBLEM_TYPE_CHOICES = [
        ('single', '単一選択'),
        ('multiple', '複数選択'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='problems')
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        null=True,  # 一時的にnull許容（データ移行後にnull=Falseに変更）
        blank=True,
        related_name='problems',
        help_text='SubjectのOrganizationと一致する必要がある（データ移行中）'
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_problems')
    question = models.TextField()
    problem_type = models.CharField(max_length=10, choices=PROBLEM_TYPE_CHOICES, default='single')
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=1)
    explanation = models.TextField(blank=False)
    question_image = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='問題画像ファイル名',
        help_text='[非推奨] 旧形式。MediaAsset使用を推奨'
    )
    explanation_image = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='解説画像ファイル名',
        help_text='[非推奨] 旧形式。MediaAsset使用を推奨'
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text='論理削除フラグ'
    )
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['id', 'organization']),  # 複合FK用
        ]

    def get_media_assets(self, usage_kind=None):
        """新方式: 紐づいた画像を取得"""
        qs = self.media_links.select_related('asset')
        if usage_kind:
            qs = qs.filter(usage_kind=usage_kind)
        return qs.order_by('usage_kind', 'position')

    def get_question_image_url(self):
        """問題画像の完全なURLを生成"""
        if not self.question_image:
            return None
        directory = self.subject.get_question_image_directory()
        return f'/media/{directory}/{self.question_image}'

    def get_explanation_image_url(self):
        """解説画像の完全なURLを生成"""
        if not self.explanation_image:
            return None
        directory = self.subject.get_explanation_image_directory()
        return f'/media/{directory}/{self.explanation_image}'

    def __str__(self):
        return f"{self.subject.name}: {self.question[:50]}..."


class Choice(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='choices')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.problem.question[:30]}... - {self.text[:30]}..."


class QuizSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    total_problems = models.IntegerField(default=0)
    completed_problems = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.started_at}"


class QuizAnswer(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='answers')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    selected_choices = models.ManyToManyField(Choice, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    time_taken = models.IntegerField(default=0, help_text="Time taken in seconds")

    class Meta:
        ordering = ['answered_at']
        unique_together = ['session', 'problem']

    def __str__(self):
        return f"{self.session.user.username} - {self.problem.question[:30]}..."


class Field(models.Model):
    """分野モデル（科目の下位分類）"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='fields')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subject', 'name']
        unique_together = [['subject', 'name']]

    def __str__(self):
        return f"{self.subject.name} - {self.name}"


class UserSubjectAccess(models.Model):
    """ユーザーと科目のアクセス権限管理"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subject_access')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='user_access')
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_subject_access'
    )

    class Meta:
        ordering = ['user', 'subject']
        unique_together = [['user', 'subject']]

    def __str__(self):
        return f"{self.user.user_id} - {self.subject.name}"


class UserFieldAccess(models.Model):
    """ユーザーと分野のアクセス権限管理"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='field_access')
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='user_access')
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_field_access'
    )

    class Meta:
        ordering = ['user', 'field']
        unique_together = [['user', 'field']]

    def __str__(self):
        return f"{self.user.user_id} - {self.field.name}"


class MediaAsset(models.Model):
    """画像ファイルのメタデータ管理"""

    class UsageKind(models.TextChoices):
        PROBLEM = 'problem', '問題用'
        EXPLANATION = 'explanation', '解説用'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='画像アセットの一意識別子'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 組織・科目への紐づけ（両方必須・データ移行中は一時的にnull許容）
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        null=True,  # 一時的にnull許容（データ移行後にnull=Falseに変更）
        blank=True,
        related_name='media_assets',
        help_text='画像を所有する組織（データ移行中）'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        null=True,  # 一時的にnull許容（データ移行後にnull=Falseに変更）
        blank=True,
        related_name='media_assets',
        help_text='画像が紐づく科目（データ移行中）'
    )

    # 画像メタデータ
    usage_kind = models.CharField(
        max_length=20,
        choices=UsageKind.choices,
        default=UsageKind.PROBLEM,
        help_text='画像の用途（問題用/解説用）'
    )
    storage_key = models.TextField(
        help_text='物理ストレージのキー（例: org/1/subjects/uuid/problem/uuid.png）'
    )
    original_filename = models.TextField(
        null=True,
        blank=True,
        help_text='アップロード時の元ファイル名'
    )
    mime_type = models.TextField(
        null=True,
        blank=True,
        help_text='MIMEタイプ（例: image/png）'
    )
    file_size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='ファイルサイズ（バイト）'
    )
    checksum_sha256 = models.TextField(
        null=True,
        blank=True,
        help_text='SHA256ハッシュ値（整合性検証用）'
    )
    version = models.IntegerField(
        default=1,
        help_text='バージョン番号（楽観ロック用）'
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text='論理削除フラグ'
    )

    class Meta:
        db_table = 'media_assets'
        ordering = ['created_at']
        verbose_name = '画像アセット'
        verbose_name_plural = '画像アセット'
        unique_together = [['organization', 'storage_key']]
        indexes = [
            models.Index(fields=['id', 'organization']),  # 複合FK用
            models.Index(fields=['organization', 'is_deleted']),
            models.Index(fields=['subject']),
            models.Index(fields=['usage_kind']),
        ]

    def __str__(self):
        return f'{self.original_filename or self.storage_key} ({self.get_usage_kind_display()})'

    def get_url(self):
        """画像URLを取得（将来的には署名付きURLに変更可能）"""
        return f'/media/{self.storage_key}'


class ProblemMediaAsset(models.Model):
    """問題と画像の紐づけ・表示順管理（中間テーブル）"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='紐づけレコードの一意識別子'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        null=True,  # 一時的にnull許容（データ移行後にnull=Falseに変更）
        blank=True,
        help_text='組織（マルチテナント分離用・データ移行中）'
    )
    problem = models.ForeignKey(
        'Problem',
        on_delete=models.CASCADE,
        related_name='media_links',
        help_text='紐づく問題'
    )
    asset = models.ForeignKey(
        'MediaAsset',
        on_delete=models.RESTRICT,  # 画像削除を制限
        related_name='problem_links',
        help_text='紐づく画像アセット'
    )
    usage_kind = models.CharField(
        max_length=20,
        choices=MediaAsset.UsageKind.choices,
        help_text='画像の用途（問題用/解説用）'
    )
    position = models.IntegerField(
        help_text='表示順（1始まり）'
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text='論理削除フラグ'
    )

    class Meta:
        db_table = 'problem_media_assets'
        ordering = ['problem', 'usage_kind', 'position']
        verbose_name = '問題画像紐づけ'
        verbose_name_plural = '問題画像紐づけ'
        unique_together = [
            ['problem', 'asset', 'usage_kind'],  # 同じ画像を重複紐づけ防止
            ['problem', 'usage_kind', 'position'],  # 順序一意性
        ]
        indexes = [
            models.Index(fields=['problem', 'usage_kind', 'position']),
            models.Index(fields=['asset']),
            models.Index(fields=['organization']),
        ]

    def __str__(self):
        return f'{self.problem.id} - {self.asset.original_filename} ({self.position})'