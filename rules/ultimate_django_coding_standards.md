# Ultimate Django/Python バックエンドコーディング規約 v2.0

> **バイブコーディング（Vibe Coding）最適化版** - Cursor & Claude Code併用開発の理想的規約
>
> 本規約は実践的な開発効率と最高品質を両立する、理想的なコーディングスタンダードです。

---

## 📋 目次

1. [対象と前提](#1-対象と前提)
2. [プロジェクト構成](#2-プロジェクト構成)
3. [コード品質と命名規則](#3-コード品質と命名規則)
4. [モデル設計](#4-モデル設計)
5. [API設計（DRF）](#5-api設計drf)
6. [サービス/セレクタパターン](#6-サービスセレクタパターン)
7. [クエリ最適化](#7-クエリ最適化)
8. [認証・認可・セキュリティ](#8-認証認可セキュリティ)
9. [テスト戦略](#9-テスト戦略)
10. [非同期処理](#10-非同期処理)
11. [ロギング・監視](#11-ロギング監視)
12. [CI/CD・運用](#12-cicd運用)
13. [Cursor/Claude Code運用規約](#13-cursorclaude-code運用規約)
14. [ベストプラクティス集](#14-ベストプラクティス集)

---

## 1. 対象と前提

### 技術スタック（最新版）
```yaml
Python: 3.11+ (推奨: 3.12)
Django: 5.x
Django REST Framework: 3.15+
PostgreSQL: 14+ (UTF-8, UTC)
Redis: 7.0+
依存管理: uv > Poetry > pip-tools
型チェック: mypy + django-stubs
Lint/Format: Ruff (lint + format)
コンテナ: Docker + docker-compose
```

### 基本原則
- **12-factor app** 準拠
- **Clean Architecture** の実践
- **DRY** (Don't Repeat Yourself)
- **KISS** (Keep It Simple, Stupid)
- **YAGNI** (You Ain't Gonna Need It)
- **早期リターン** でネストを浅く

---

## 2. プロジェクト構成

### 理想的なディレクトリ構造
```
project_root/
├── .env.example           # 環境変数サンプル（機密情報なし）
├── pyproject.toml         # ruff/mypy/pytest設定統合
├── Makefile              # よく使うコマンド短縮
├── docker/
│   ├── app.Dockerfile
│   └── compose.yml
├── manage.py
└── src/
    ├── config/           # プロジェクト設定
    │   ├── __init__.py
    │   ├── asgi.py
    │   ├── wsgi.py
    │   ├── urls.py
    │   ├── schema.py    # OpenAPI生成（drf-spectacular）
    │   ├── logging.py   # 構造化ログ設定
    │   ├── middleware.py # request_id等
    │   └── settings/
    │       ├── base.py
    │       ├── dev.py
    │       ├── test.py
    │       └── prod.py
    ├── apps/            # ビジネスロジック
    │   ├── users/
    │   │   ├── models.py
    │   │   ├── admin.py
    │   │   ├── services.py    # 書き込み・業務ロジック
    │   │   ├── selectors.py   # 読み取り専用クエリ
    │   │   ├── validators.py  # カスタムバリデーター
    │   │   ├── managers.py    # カスタムマネージャー
    │   │   ├── signals.py     # シグナルハンドラー
    │   │   ├── tasks.py       # Celeryタスク
    │   │   ├── api/
    │   │   │   ├── serializers.py
    │   │   │   ├── views.py
    │   │   │   ├── permissions.py
    │   │   │   └── urls.py
    │   │   └── tests/
    │   │       ├── test_models.py
    │   │       ├── test_api.py
    │   │       ├── test_services.py
    │   │       └── factories.py
    │   └── ...
    └── common/          # 共通処理（最小限に）
        ├── exceptions.py
        ├── middleware.py
        └── utils.py
```

---

## 3. コード品質と命名規則

### 命名規則
```python
# クラス名: PascalCase
class UserProfile(models.Model):
    pass

# 関数・メソッド・変数: snake_case
def calculate_total_price():
    user_count = 10

# 定数: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# プライベート属性: アンダースコア始まり
_internal_cache = {}

# 真偽値: is_/has_/can_/should_プレフィックス
is_active = True
has_permission = False
can_edit = True
should_notify = False
```

### 静的解析設定（pyproject.toml）
```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "B", "UP", "N", "ARG", "RUF", "SIM", "PTH"]
ignore = ["E501"]  # line too long（100文字制限で十分）

[tool.ruff.lint.isort]
known-first-party = ["apps", "config", "common"]

[tool.mypy]
python_version = "3.11"
plugins = ["mypy_django_plugin.main", "mypy_drf_plugin.main"]
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.django-stubs]
django_settings_module = "config.settings.dev"
```

---

## 4. モデル設計

### ベストプラクティスモデル例
```python
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator

class Article(models.Model):
    """記事モデル - ベストプラクティス実装例"""

    # 主キーはUUID（可能ならv7）
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="記事の一意識別子"
    )

    # 基本フィールド
    title = models.CharField(
        max_length=200,
        db_index=True,  # 検索頻度が高い場合
        help_text="記事タイトル"
    )
    slug = models.SlugField(
        unique=True,
        max_length=255,
        help_text="URL用スラッグ"
    )

    # TextChoicesを使用
    class Status(models.TextChoices):
        DRAFT = 'draft', '下書き'
        PUBLISHED = 'published', '公開'
        ARCHIVED = 'archived', 'アーカイブ'

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )

    # 金額はDecimalField
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # 関連
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='articles',
        db_index=True
    )

    # 多対多は中間モデル検討
    tags = models.ManyToManyField(
        'Tag',
        through='ArticleTag',
        related_name='articles'
    )

    # メタデータ
    view_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, db_index=True)

    # タイムスタンプ
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'articles'
        ordering = ['-created_at']
        verbose_name = '記事'
        verbose_name_plural = '記事'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['author', '-published_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name='price_non_negative'
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        # スラッグ自動生成
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def clean(self):
        # モデルレベルバリデーション
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
```

### カスタムマネージャー
```python
class PublishedManager(models.Manager):
    """公開済み記事専用マネージャー"""

    def get_queryset(self):
        return super().get_queryset().filter(
            status=Article.Status.PUBLISHED,
            published_at__lte=timezone.now()
        )

    def with_stats(self):
        """統計情報付きクエリセット"""
        return self.get_queryset().annotate(
            comment_count=Count('comments'),
            avg_rating=Avg('ratings__score')
        )

class Article(models.Model):
    # デフォルトマネージャーとカスタムマネージャー
    objects = models.Manager()
    published = PublishedManager()
```

### マイグレーション

#### FK 追加 migration の dependencies ルール

FK（外部キー）を追加する migration を作成する際、参照先テーブルが
別の migration で **DELETE → CREATE 再作成** されている場合は、
その再作成 migration を `dependencies` に明示的に含めること。

Django の migration グラフは FK の参照先テーブルが「どの migration で作られたか」
を最初の `CreateModel` から追跡する。テーブルが一度 `DeleteModel` → `CreateModel`
で再作成されると、再作成 migration への依存を手動で追加しない限り、
Django は旧来の `CreateModel` migration（再作成前）を参照先と誤認識する。
これにより FK を追加した migration が再作成 migration より先に実行される可能性があり、
整合性エラーや `django.db.utils.ProgrammingError` を引き起こす。

**ルール**:
> FK を追加する migration を書く際は、参照先テーブルの migration 履歴を確認し、
> 後続の migration で `DeleteModel` → `CreateModel` が行われていれば、
> その migration 番号を `dependencies` に追加すること。

**具体例（I050 の事例）**:

`problems/0004` は `accounts.Organization` に FK を追加する。
`accounts/0010` では Organization テーブルを DELETE → CREATE で再作成している。
この場合、`problems/0004` の `dependencies` に `accounts/0010` を明示しなければ、
FK migration が再作成 migration より前に実行されうる。

```python
# ❌ 悪い例: 再作成 migration が dependencies に含まれていない
class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0009_organization_user_users_organiz_ca9165_idx_and_more'),
        ('problems', '0003_field_problem_field_usersubjectaccess_and_more'),
    ]

# ✅ 良い例: 再作成 migration を明示的に含める
class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0009_organization_user_users_organiz_ca9165_idx_and_more'),
        ('accounts', '0010_update_organization_structure'),  # explicit: ensure table recreated before FK
        ('problems', '0003_field_problem_field_usersubjectaccess_and_more'),
    ]
```

**チェック手順**:
1. `makemigrations` 後、生成された migration の `dependencies` を確認する
2. 参照先アプリの migration 履歴を `git log -- <app>/migrations/` で確認する
3. 参照先テーブルに `DeleteModel` + `CreateModel` のセットが存在する場合、
   その `CreateModel` を含む migration 番号を `dependencies` に追加する

---

## 5. API設計（DRF）

### ViewSetベストプラクティス
```python
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django_filters.rest_framework import DjangoFilterBackend

class ArticleViewSet(viewsets.ModelViewSet):
    """
    記事API - 完全なCRUD + カスタムアクション
    """
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['status', 'author', 'is_featured']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'view_count', 'price']
    ordering = ['-created_at']

    def get_queryset(self):
        """最適化されたクエリセット"""
        queryset = Article.objects.all()

        # 関連データを事前取得（N+1回避）
        queryset = queryset.select_related('author')
        queryset = queryset.prefetch_related(
            'tags',
            Prefetch(
                'comments',
                queryset=Comment.objects.select_related('author')
            )
        )

        # アノテーション
        queryset = queryset.annotate(
            comment_count=Count('comments'),
            is_popular=Case(
                When(view_count__gte=1000, then=True),
                default=False,
                output_field=BooleanField()
            )
        )

        # ユーザーによるフィルタリング
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(status=Article.Status.PUBLISHED) |
                Q(author=self.request.user)
            )

        return queryset

    def get_serializer_class(self):
        """アクションに応じたシリアライザー切り替え"""
        if self.action == 'list':
            return ArticleListSerializer
        if self.action == 'create':
            return ArticleCreateSerializer
        if self.action == 'stats':
            return ArticleStatsSerializer
        return self.serializer_class

    @extend_schema(
        summary="記事を公開",
        description="下書き記事を公開状態に変更",
        responses={200: ArticleSerializer}
    )
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """記事公開アクション"""
        article = self.get_object()

        if article.status != Article.Status.DRAFT:
            return Response(
                {'error': '下書き状態の記事のみ公開できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        article.status = Article.Status.PUBLISHED
        article.published_at = timezone.now()
        article.save(update_fields=['status', 'published_at', 'updated_at'])

        serializer = self.get_serializer(article)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """統計情報取得"""
        stats = {
            'total': self.get_queryset().count(),
            'published': self.get_queryset().filter(
                status=Article.Status.PUBLISHED
            ).count(),
            'avg_view_count': self.get_queryset().aggregate(
                avg=Avg('view_count')
            )['avg']
        }
        return Response(stats)

    def perform_create(self, serializer):
        """作成時の処理"""
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """更新時の処理"""
        # 更新履歴を記録
        instance = self.get_object()
        UpdateHistory.objects.create(
            content_object=instance,
            user=self.request.user,
            changes=self._get_changes(instance, serializer.validated_data)
        )
        serializer.save()
```

### 高度なシリアライザー
```python
class ArticleSerializer(serializers.ModelSerializer):
    """記事シリアライザー - 完全版"""

    # 追加フィールド
    author_name = serializers.CharField(source='author.display_name', read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    is_editable = serializers.SerializerMethodField()

    # ネストされたシリアライザー
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True,
        source='tags'
    )

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'content', 'status',
            'author', 'author_name', 'tags', 'tag_ids',
            'price', 'view_count', 'is_featured',
            'comment_count', 'is_editable',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = ['id', 'slug', 'view_count', 'created_at', 'updated_at']
        extra_kwargs = {
            'content': {'help_text': 'Markdown形式で記述'},
            'price': {'min_value': 0, 'max_value': 99999.99}
        }

    def get_is_editable(self, obj):
        """編集可能かどうかを判定"""
        request = self.context.get('request')
        if not request:
            return False
        return obj.author == request.user or request.user.is_staff

    def validate_title(self, value):
        """タイトルのバリデーション"""
        if len(value) < 5:
            raise serializers.ValidationError("タイトルは5文字以上必要です")

        # 重複チェック（更新時は自身を除外）
        qs = Article.objects.filter(title__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("このタイトルは既に使用されています")

        return value

    def validate(self, attrs):
        """クロスフィールドバリデーション"""
        if attrs.get('status') == Article.Status.PUBLISHED:
            if not attrs.get('content'):
                raise serializers.ValidationError({
                    'content': '公開する記事には本文が必要です'
                })
        return attrs

    def create(self, validated_data):
        """トランザクション内で作成"""
        tags = validated_data.pop('tags', [])

        with transaction.atomic():
            article = Article.objects.create(**validated_data)
            article.tags.set(tags)

            # 作成通知を送信（非同期）
            notify_article_created.delay(article.id)

        return article
```

---

## 6. サービス/セレクタパターン

### セレクタ（読み取り専用）
```python
# apps/articles/selectors.py
from typing import Optional, List, Dict, Any
from django.db.models import QuerySet, Q, Count, Avg
from .models import Article

class ArticleSelector:
    """記事の読み取り専用ロジック"""

    @staticmethod
    def get_published_articles() -> QuerySet[Article]:
        """公開済み記事を取得"""
        return Article.published.select_related('author').prefetch_related('tags')

    @staticmethod
    def search_articles(
        query: str,
        user: Optional['User'] = None
    ) -> QuerySet[Article]:
        """記事を検索"""
        queryset = Article.objects.all()

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct()

        if user and not user.is_staff:
            queryset = queryset.filter(
                Q(status=Article.Status.PUBLISHED) |
                Q(author=user)
            )

        return queryset.select_related('author')

    @staticmethod
    def get_article_stats(article_id: uuid.UUID) -> Dict[str, Any]:
        """記事の統計情報を取得"""
        article = Article.objects.filter(id=article_id).annotate(
            total_comments=Count('comments'),
            avg_rating=Avg('ratings__score'),
            unique_viewers=Count('views__user', distinct=True)
        ).first()

        if not article:
            return {}

        return {
            'view_count': article.view_count,
            'comment_count': article.total_comments,
            'avg_rating': article.avg_rating or 0,
            'unique_viewers': article.unique_viewers
        }
```

### サービス（書き込み・業務ロジック）
```python
# apps/articles/services.py
import logging
from typing import Optional, Dict, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Article, ArticleHistory
from .tasks import send_notification

logger = logging.getLogger(__name__)

class ArticleService:
    """記事の書き込み・業務ロジック"""

    @staticmethod
    @transaction.atomic
    def create_article(
        *,
        title: str,
        content: str,
        author: 'User',
        tags: Optional[List['Tag']] = None,
        **extra_fields
    ) -> Article:
        """記事を作成（冪等性考慮）"""

        # 重複チェック（冪等性のため）
        existing = Article.objects.filter(
            title=title,
            author=author
        ).first()

        if existing:
            logger.info(f"Article already exists: {existing.id}")
            return existing

        try:
            article = Article.objects.create(
                title=title,
                content=content,
                author=author,
                **extra_fields
            )

            if tags:
                article.tags.set(tags)

            # 履歴記録
            ArticleHistory.objects.create(
                article=article,
                action='created',
                user=author,
                data={'title': title}
            )

            # 非同期通知
            send_notification.delay(
                'article_created',
                article_id=str(article.id)
            )

            logger.info(f"Article created: {article.id}")
            return article

        except Exception as e:
            logger.error(f"Failed to create article: {e}", exc_info=True)
            raise ValidationError(f"記事の作成に失敗しました: {str(e)}")

    @staticmethod
    @transaction.atomic
    def publish_article(
        article: Article,
        user: 'User'
    ) -> Article:
        """記事を公開"""

        if article.status == Article.Status.PUBLISHED:
            return article  # 冪等性

        if article.status != Article.Status.DRAFT:
            raise ValidationError("下書き状態の記事のみ公開できます")

        if not article.content:
            raise ValidationError("本文が必要です")

        article.status = Article.Status.PUBLISHED
        article.published_at = timezone.now()
        article.save(update_fields=['status', 'published_at', 'updated_at'])

        # 履歴記録
        ArticleHistory.objects.create(
            article=article,
            action='published',
            user=user
        )

        # 公開通知（非同期）
        send_notification.delay(
            'article_published',
            article_id=str(article.id),
            author_id=str(article.author_id)
        )

        logger.info(f"Article published: {article.id}")
        return article

    @staticmethod
    def bulk_update_status(
        article_ids: List[uuid.UUID],
        new_status: str,
        user: 'User'
    ) -> int:
        """複数記事のステータスを一括更新"""

        with transaction.atomic():
            updated = Article.objects.filter(
                id__in=article_ids
            ).update(
                status=new_status,
                updated_at=timezone.now()
            )

            # 履歴を一括作成
            histories = [
                ArticleHistory(
                    article_id=article_id,
                    action='status_changed',
                    user=user,
                    data={'new_status': new_status}
                )
                for article_id in article_ids
            ]
            ArticleHistory.objects.bulk_create(histories)

            logger.info(f"Bulk updated {updated} articles to {new_status}")
            return updated
```

---

## 7. クエリ最適化

### N+1問題の回避
```python
# ❌ 悪い例
articles = Article.objects.all()
for article in articles:
    print(article.author.name)  # N+1クエリ
    print(article.comments.count())  # さらにN+1

# ✅ 良い例
articles = Article.objects.select_related('author').prefetch_related(
    Prefetch(
        'comments',
        queryset=Comment.objects.select_related('author')
    )
)

# さらに最適化
articles = Article.objects.annotate(
    comment_count=Count('comments')
).select_related('author')
```

### 高度なクエリ最適化
```python
from django.db.models import Prefetch, Count, Exists, OuterRef, Subquery

class OptimizedArticleViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # サブクエリで最新コメントを取得
        latest_comment = Comment.objects.filter(
            article=OuterRef('pk')
        ).order_by('-created_at')

        # Existsで効率的な存在チェック
        user_has_liked = Like.objects.filter(
            article=OuterRef('pk'),
            user=self.request.user if self.request.user.is_authenticated else None
        )

        queryset = Article.objects.annotate(
            # カウント
            comment_count=Count('comments'),
            like_count=Count('likes'),

            # 最新コメント情報
            latest_comment_date=Subquery(
                latest_comment.values('created_at')[:1]
            ),
            latest_comment_author=Subquery(
                latest_comment.values('author__name')[:1]
            ),

            # ユーザー固有情報
            user_has_liked=Exists(user_has_liked)
        )

        # 条件付きPrefetch
        queryset = queryset.prefetch_related(
            Prefetch(
                'comments',
                queryset=Comment.objects.filter(
                    is_approved=True
                ).select_related('author').order_by('-created_at')[:5],
                to_attr='recent_comments'
            )
        )

        return queryset
```

---

## 8. 認証・認可・セキュリティ

### カスタム認証
```python
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

class AuthService:
    """認証サービス"""

    @staticmethod
    def login(email: str, password: str) -> Dict[str, str]:
        """JWT認証"""
        user = authenticate(username=email, password=password)

        if not user:
            raise ValidationError("認証に失敗しました")

        if not user.is_active:
            raise ValidationError("アカウントが無効です")

        refresh = RefreshToken.for_user(user)

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': str(user.id),
            'email': user.email
        }

    @staticmethod
    def verify_2fa(user: 'User', code: str) -> bool:
        """2要素認証の検証"""
        # TOTP実装例
        from django_otp import match_token
        return match_token(user, code)
```

### カスタムパーミッション
```python
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """所有者のみ編集可能"""

    def has_object_permission(self, request, view, obj):
        # 読み取りは全員OK
        if request.method in permissions.SAFE_METHODS:
            return True

        # 書き込みは所有者のみ
        return obj.owner == request.user

class HasActiveSubscription(permissions.BasePermission):
    """有効なサブスクリプションが必要"""

    message = "有効なサブスクリプションが必要です"

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return hasattr(request.user, 'subscription') and \
               request.user.subscription.is_active
```

### セキュリティ設定
```python
# settings/base.py
import os
from datetime import timedelta

# セキュリティ基本設定
SECRET_KEY = os.environ['SECRET_KEY']  # 必須
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')

# セッション設定
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24  # 1日

# CSRF設定
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# セキュリティヘッダー
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'

# パスワード設定
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# JWT設定（REST Framework Simple JWT）
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# レート制限
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

---

## 9. テスト戦略

### pytest設定
```toml
# pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
testpaths = ["src/apps"]
python_files = ["test_*.py", "*_test.py"]
addopts = """
    -v
    --strict-markers
    --tb=short
    --maxfail=1
    --cov=src
    --cov-report=term-missing:skip-covered
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=85
"""
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### 完全なテスト例
```python
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, Mock
from freezegun import freeze_time

@pytest.fixture
def api_client():
    """APIクライアントフィクスチャ"""
    return APIClient()

@pytest.fixture
def user(db):
    """ユーザーフィクスチャ"""
    from apps.users.tests.factories import UserFactory
    return UserFactory()

@pytest.fixture
def authenticated_client(api_client, user):
    """認証済みクライアント"""
    api_client.force_authenticate(user=user)
    return api_client

@pytest.mark.django_db
class TestArticleAPI:
    """記事APIのテストスイート"""

    def test_list_articles(self, authenticated_client, article_factory):
        """記事一覧取得テスト"""
        # Arrange
        articles = article_factory.create_batch(3)

        # Act
        response = authenticated_client.get('/api/articles/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3
        assert len(response.data['results']) == 3

    @freeze_time("2024-01-01 12:00:00")
    def test_create_article(self, authenticated_client, user):
        """記事作成テスト（時刻固定）"""
        # Arrange
        data = {
            'title': 'テスト記事',
            'content': 'テスト内容',
            'status': 'draft'
        }

        # Act
        response = authenticated_client.post(
            '/api/articles/',
            data=data,
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'テスト記事'
        assert response.data['author'] == str(user.id)
        assert response.data['created_at'] == '2024-01-01T12:00:00Z'

    @patch('apps.articles.tasks.send_notification.delay')
    def test_publish_article(self, mock_task, authenticated_client, article):
        """記事公開テスト（タスクモック）"""
        # Arrange
        article.status = 'draft'
        article.save()

        # Act
        response = authenticated_client.post(
            f'/api/articles/{article.id}/publish/'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'published'

        # タスクが呼ばれたことを確認
        mock_task.assert_called_once_with(
            'article_published',
            article_id=str(article.id),
            author_id=str(article.author_id)
        )

    @pytest.mark.parametrize("status_code,error_message", [
        (400, "タイトルは必須です"),
        (401, "認証が必要です"),
        (403, "権限がありません"),
        (404, "記事が見つかりません"),
    ])
    def test_error_responses(
        self,
        api_client,
        status_code,
        error_message
    ):
        """エラーレスポンステスト（パラメータ化）"""
        # エラーケースごとのテスト実装
        pass

    @pytest.mark.slow
    @pytest.mark.integration
    def test_bulk_operations(self, authenticated_client, article_factory):
        """大量データ操作テスト"""
        # 1000件の記事を作成
        articles = article_factory.create_batch(1000)

        # パフォーマンス測定
        import time
        start = time.time()
        response = authenticated_client.get('/api/articles/')
        duration = time.time() - start

        assert response.status_code == status.HTTP_200_OK
        assert duration < 2.0  # 2秒以内
```

### ファクトリーパターン
```python
# apps/articles/tests/factories.py
import factory
from factory.django import DjangoModelFactory
from faker import Faker

fake = Faker('ja_JP')

class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'users.User'

    email = factory.LazyAttribute(lambda _: fake.email())
    display_name = factory.LazyAttribute(lambda _: fake.name())
    is_active = True

class ArticleFactory(DjangoModelFactory):
    class Meta:
        model = 'articles.Article'

    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=5))
    content = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=1000))
    author = factory.SubFactory(UserFactory)
    status = 'draft'

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)
```

---

## 10. 非同期処理

### Celeryタスク
```python
# apps/articles/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
import time

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    name='articles.generate_report',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True
)
def generate_report(self, report_id: str):
    """レポート生成タスク（冪等性・リトライ対応）"""

    # 重複実行防止（分散ロック）
    lock_key = f"task:generate_report:{report_id}"
    lock = cache.add(lock_key, "locked", timeout=3600)

    if not lock:
        logger.info(f"Task already running for report {report_id}")
        return

    try:
        from apps.reports.models import Report
        report = Report.objects.get(id=report_id)

        # 既に完了していれば何もしない（冪等性）
        if report.status == 'completed':
            logger.info(f"Report {report_id} already completed")
            return

        report.status = 'processing'
        report.save(update_fields=['status'])

        # 実際の処理
        logger.info(f"Generating report {report_id}")
        result = _generate_report_data(report)

        report.result = result
        report.status = 'completed'
        report.save(update_fields=['result', 'status'])

        logger.info(f"Report {report_id} completed successfully")

    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found")
        raise self.retry(countdown=60)

    except Exception as e:
        logger.error(f"Failed to generate report {report_id}: {e}")

        # 失敗時の処理
        try:
            report.status = 'failed'
            report.error_message = str(e)
            report.save(update_fields=['status', 'error_message'])
        except:
            pass

        raise self.retry(exc=e)

    finally:
        # ロック解除
        cache.delete(lock_key)

@shared_task
def cleanup_old_data():
    """定期的なデータクリーンアップ"""
    from datetime import timedelta
    from django.utils import timezone

    cutoff_date = timezone.now() - timedelta(days=90)

    # 古いログを削除
    deleted = LogEntry.objects.filter(
        created_at__lt=cutoff_date
    ).delete()

    logger.info(f"Deleted {deleted[0]} old log entries")
```

### Django非同期ビュー
```python
# Django 4.1+ async views
import asyncio
import aiohttp
from django.http import JsonResponse
from asgiref.sync import sync_to_async

async def async_article_view(request, article_id):
    """非同期ビューの実装例"""

    # 非同期でDBアクセス
    @sync_to_async
    def get_article():
        return Article.objects.select_related('author').get(id=article_id)

    # 外部APIの非同期呼び出し
    async def fetch_external_data(article):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'https://api.example.com/stats/{article.slug}'
            ) as response:
                return await response.json()

    # 並行処理
    article, external_data = await asyncio.gather(
        get_article(),
        fetch_external_data(article) if article else None
    )

    return JsonResponse({
        'article': {
            'id': str(article.id),
            'title': article.title,
            'author': article.author.display_name
        },
        'external_stats': external_data
    })
```

---

## 11. ロギング・監視

### 構造化ログ設定
```python
# config/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.dict_tracebacks,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/app/django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### ロギング実装例
```python
import structlog
from django.utils.decorators import method_decorator

logger = structlog.get_logger()

class LoggingMixin:
    """ビューセット用ロギングミックスイン"""

    def dispatch(self, request, *args, **kwargs):
        # リクエストIDを設定
        request.id = str(uuid.uuid4())

        # 構造化ログコンテキスト
        log = logger.bind(
            request_id=request.id,
            method=request.method,
            path=request.path,
            user_id=str(request.user.id) if request.user.is_authenticated else None
        )

        log.info("Request started")

        try:
            response = super().dispatch(request, *args, **kwargs)
            log.info(
                "Request completed",
                status_code=response.status_code
            )
            return response

        except Exception as e:
            log.error(
                "Request failed",
                error=str(e),
                exc_info=True
            )
            raise

class ArticleViewSet(LoggingMixin, viewsets.ModelViewSet):
    """ロギング付きビューセット"""
    pass
```

---

## 12. CI/CD・運用

### Makefile
```makefile
.PHONY: help fmt lint type test migrate run build deploy

help:  ## ヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

fmt:  ## コードフォーマット
	ruff format src/

lint:  ## Lintチェック
	ruff check src/ --fix

type:  ## 型チェック
	mypy src/

test:  ## テスト実行
	pytest src/ -v --cov=src --cov-report=html

test-fast:  ## 高速テスト（単体テストのみ）
	pytest src/ -v -m "not slow and not integration"

migrate:  ## マイグレーション実行
	python manage.py migrate

makemigrations:  ## マイグレーション作成
	python manage.py makemigrations

run:  ## 開発サーバー起動
	python manage.py runserver 0.0.0.0:8000

celery:  ## Celeryワーカー起動
	celery -A config worker -l info

shell:  ## Django shell起動
	python manage.py shell_plus --ipython

check:  ## デプロイ前チェック
	python manage.py check --deploy
	python manage.py makemigrations --check

clean:  ## クリーンアップ
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf htmlcov/ .coverage .pytest_cache/

build:  ## Dockerイメージビルド
	docker build -f docker/app.Dockerfile -t myapp:latest .

deploy:  ## デプロイ
	@echo "Deploying to production..."
	python manage.py migrate --noinput
	python manage.py collectstatic --noinput
	gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### GitHub Actions CI/CD
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt

      - name: Run formatters check
        run: ruff format --check src/

      - name: Run linters
        run: ruff check src/

      - name: Run type checking
        run: mypy src/

      - name: Check migrations
        run: python manage.py makemigrations --check

      - name: Run tests
        run: |
          pytest src/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=85

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

      - name: Security check
        run: |
          pip-audit
          python manage.py check --deploy

      - name: Build Docker image
        if: github.ref == 'refs/heads/main'
        run: |
          docker build -f docker/app.Dockerfile -t myapp:${{ github.sha }} .

      - name: Deploy to staging
        if: github.ref == 'refs/heads/develop'
        run: |
          echo "Deploy to staging environment"

      - name: Deploy to production
        if: github.ref == 'refs/heads/main'
        run: |
          echo "Deploy to production environment"
```

---

## 13. Cursor/Claude Code運用規約

### ガードレール設定
```yaml
# .cursorrules または .claude-code-rules
rules:
  - "本規約を厳守すること"
  - "既存のpublic API/DBスキーマを変更しない"
  - "不足情報はTODOとraise NotImplementedErrorで明示"
  - "差分は200行以内、それ以上は分割"
  - "migrationsは必ず生成し、説明を含める"
  - "テストカバレッジ85%以上を維持"
  - "型ヒントを必ず付ける"
  - "docstringは公開APIに必須"

forbidden:
  - "機密情報のハードコード"
  - "print()デバッグ（loggerを使用）"
  - "過剰な依存追加（1PR1〜2個まで）"
  - "ロングトランザクション"
  - "View内でのビジネスロジック実装"
  - "生SQLの直接実行"
  - "同期的な外部API呼び出し"

validation:
  pre_commit:
    - "ruff format"
    - "ruff check"
    - "mypy"
    - "pytest -x"

  post_generation:
    - "python manage.py check"
    - "python manage.py makemigrations --check"
```

### プロンプトテンプレート
```markdown
## コンテキスト
- プロジェクト: Django REST API
- 規約: Ultimate Django Coding Standards v2.0準拠
- 環境: Python 3.11, Django 5.x, PostgreSQL 14

## タスク
[具体的なタスクを記述]

## 制約
- サービス/セレクタパターンを使用
- N+1問題を回避
- 適切なログ出力
- テストを含める
- 型ヒント必須

## 期待する出力
- 実装コード
- テストコード
- マイグレーション（必要な場合）
- 更新が必要なドキュメント一覧
```

---

## 14. ベストプラクティス集

### ✅ 必ず守るべき原則

1. **早期リターン**: ネストを3段階以内に
2. **単一責任**: 1関数/クラス = 1責務
3. **依存性注入**: 密結合を避ける
4. **防御的プログラミング**: 異常系を考慮
5. **ログ出力**: 適切なレベルで記録
6. **冪等性**: 再実行可能な設計
7. **トランザクション境界**: サービス層で明確化
8. **タイムアウト設定**: 外部I/Oは必須

### ⚠️ アンチパターン

```python
# ❌ 悪い例
def bad_function(items=[]):  # 可変デフォルト引数
    try:
        # 全部キャッチ
        ...
    except:
        pass  # エラー握りつぶし

    # グローバル変数
    global counter
    counter += 1

    # 巨大な関数（100行以上）
    # ...

# ✅ 良い例
def good_function(items: Optional[List] = None):
    if items is None:
        items = []

    try:
        # 具体的な処理
        ...
    except SpecificException as e:
        logger.error(f"Failed to process: {e}")
        raise
```

### 📊 パフォーマンスチェックリスト

- [ ] select_related/prefetch_related使用
- [ ] 不要なクエリ削除
- [ ] インデックス設定
- [ ] キャッシュ活用
- [ ] ページネーション実装
- [ ] 非同期処理の検討
- [ ] bulk操作の使用

### 🔒 セキュリティチェックリスト

- [ ] 環境変数で機密情報管理
- [ ] SQLインジェクション対策
- [ ] XSS対策
- [ ] CSRF対策
- [ ] 適切な認証・認可
- [ ] レート制限
- [ ] ログに機密情報を含めない
- [ ] ファイルアップロード検証

---

## まとめ

本規約は、バイブコーディングにおける理想的なDjango開発を実現するための包括的ガイドラインです。実践的な例と最新のベストプラクティスを組み合わせ、高品質で保守性の高いコードベースを構築できます。

**重要**: 規約は定期的に見直し、プロジェクトの成長とチームのニーズに応じて更新してください。

---

*最終更新: 2024年*
*バージョン: 2.0*
*対象: Django 5.x + Python 3.11+*
