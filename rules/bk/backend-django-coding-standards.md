# Django/Python バックエンドコーディング規約

## 1. 基本原則

### 1.1 コード品質の維持
- **可読性優先**: 複雑さよりも明確さを重視
- **DRY原則**: Don't Repeat Yourself - コードの重複を避ける
- **KISS原則**: Keep It Simple, Stupid - シンプルな実装を心がける
- **早期リターン**: ネストを深くせず、条件に合わない場合は早期にreturn

### 1.2 Python哲学
- **PEP 8準拠**: Pythonの公式スタイルガイドに従う
- **Pythonic**: Pythonらしいイディオムを使用
- **明示的 > 暗黙的**: 明示的なコードを書く

## 2. ファイル構成とプロジェクト構造

### 2.1 Djangoアプリ構造
```
app_name/
├── __init__.py
├── admin.py          # Django Admin設定
├── apps.py           # アプリケーション設定
├── models.py         # データモデル
├── views.py          # ビューロジック（APIの場合はviewsets）
├── serializers.py    # DRF シリアライザー
├── urls.py           # URLルーティング
├── permissions.py    # カスタムパーミッション
├── signals.py        # シグナルハンドラー
├── tasks.py          # Celeryタスク
├── managers.py       # カスタムマネージャー
├── validators.py     # カスタムバリデーター
├── utils.py          # ユーティリティ関数
├── constants.py      # 定数定義
├── exceptions.py     # カスタム例外
├── middleware.py     # カスタムミドルウェア
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_serializers.py
│   └── factories.py  # テストデータファクトリー
└── migrations/       # データベースマイグレーション
```

### 2.2 ファイル分割の基準
- 1ファイル500行を超えたら分割を検討
- 関連性の高い機能でグループ化
- 循環参照を避ける設計

## 3. 命名規則

### 3.1 基本ルール
```python
# クラス名: PascalCase
class UserProfile(models.Model):
    pass

# 関数・メソッド名: snake_case
def calculate_total_price():
    pass

# 変数名: snake_case
user_count = 10

# 定数: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# プライベート属性: アンダースコア始まり
_internal_cache = {}

# 保護属性: アンダースコア始まり
class MyClass:
    def __init__(self):
        self._protected_attr = None
```

### 3.2 Django特有の命名
```python
# Model名: 単数形
class User(models.Model):
    pass

# Manager名: objects または説明的な名前
class ArticleManager(models.Manager):
    pass

# ViewSet名: ModelNameViewSet
class UserViewSet(viewsets.ModelViewSet):
    pass

# Serializer名: ModelNameSerializer
class UserSerializer(serializers.ModelSerializer):
    pass

# URL名: app_name:view_name
app_name = 'accounts'
urlpatterns = [
    path('users/', UserListView.as_view(), name='user-list'),
]
```

## 4. モデル設計

### 4.1 フィールド定義
```python
class Article(models.Model):
    # 必須フィールドを先に定義
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    # オプションフィールド
    description = models.TextField(blank=True)

    # 外部キー
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='articles'
    )

    # 日時フィールドは最後に
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # カスタムロジック
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
```

### 4.2 カスタムマネージャー
```python
class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status='published')

class Article(models.Model):
    objects = models.Manager()  # デフォルトマネージャー
    published = PublishedManager()  # カスタムマネージャー
```

## 5. ビューとビューセット

### 5.1 Django REST Framework ViewSet
```python
class ArticleViewSet(viewsets.ModelViewSet):
    """
    記事のCRUD操作を提供するViewSet
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """クエリセットをカスタマイズ"""
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            return queryset
        return queryset.filter(is_public=True)

    def get_serializer_class(self):
        """アクションに応じてシリアライザーを切り替え"""
        if self.action == 'list':
            return ArticleListSerializer
        if self.action == 'create':
            return ArticleCreateSerializer
        return self.serializer_class

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """カスタムアクション: 記事を公開"""
        article = self.get_object()
        article.status = 'published'
        article.published_at = timezone.now()
        article.save()
        return Response({'status': 'published'})
```

### 5.2 APIView
```python
class LoginAPIView(APIView):
    """
    ユーザーログインエンドポイント
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email
        })
```

## 6. シリアライザー

### 6.1 ModelSerializer
```python
class UserSerializer(serializers.ModelSerializer):
    # 追加フィールド
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_full_name(self, obj):
        """フルネームを返す"""
        return f"{obj.first_name} {obj.last_name}".strip()

    def validate_email(self, value):
        """メールアドレスのカスタムバリデーション"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("このメールアドレスは既に使用されています")
        return value

    def create(self, validated_data):
        """ユーザー作成時のカスタムロジック"""
        user = User.objects.create_user(**validated_data)
        return user
```

### 6.2 ネストされたシリアライザー
```python
class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'content', 'author', 'created_at']

class ArticleDetailSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author', 'comments']
```

## 7. URLルーティング

### 7.1 URLパターン定義
```python
# app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'articles'

router = DefaultRouter()
router.register('articles', views.ArticleViewSet)

urlpatterns = [
    # ViewSetのルーティング
    path('', include(router.urls)),

    # 個別のビュー
    path('search/', views.SearchView.as_view(), name='search'),
    path('stats/', views.StatsView.as_view(), name='stats'),
]
```

### 7.2 プロジェクトURL
```python
# project/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('auth/', include('authentication.urls')),
        path('articles/', include('articles.urls')),
        path('users/', include('users.urls')),
    ])),
    path('api-auth/', include('rest_framework.urls')),
]
```

## 8. エラーハンドリング

### 8.1 カスタム例外
```python
# exceptions.py
class BusinessLogicError(Exception):
    """ビジネスロジックエラーの基底クラス"""
    default_message = "ビジネスロジックエラーが発生しました"

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)

class InsufficientBalanceError(BusinessLogicError):
    default_message = "残高が不足しています"

class InvalidTransitionError(BusinessLogicError):
    default_message = "無効な状態遷移です"
```

### 8.2 例外ハンドラー
```python
# views.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            'error': True,
            'message': str(exc),
            'status_code': response.status_code,
            'details': response.data
        }
        response.data = custom_response_data

    return response
```

### 8.3 ビューでのエラーハンドリング
```python
class PaymentView(APIView):
    def post(self, request):
        try:
            # ビジネスロジック
            payment_service = PaymentService()
            result = payment_service.process_payment(request.data)
            return Response(result)

        except InsufficientBalanceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Payment processing failed: {e}", exc_info=True)
            return Response(
                {'error': 'Payment processing failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

## 9. データベースクエリ最適化

### 9.1 select_related と prefetch_related
```python
# 悪い例
articles = Article.objects.all()
for article in articles:
    print(article.author.name)  # N+1問題

# 良い例
articles = Article.objects.select_related('author').all()
for article in articles:
    print(article.author.name)

# ManyToManyまたは逆参照の場合
articles = Article.objects.prefetch_related('tags', 'comments').all()
```

### 9.2 クエリ最適化のベストプラクティス
```python
class ArticleViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = Article.objects.all()

        # 関連データを事前に取得
        queryset = queryset.select_related('author', 'category')
        queryset = queryset.prefetch_related('tags', 'comments__author')

        # 必要なフィールドのみ取得
        if self.action == 'list':
            queryset = queryset.only('id', 'title', 'slug', 'created_at')

        # アノテーション
        queryset = queryset.annotate(
            comment_count=Count('comments'),
            is_popular=Case(
                When(view_count__gte=1000, then=True),
                default=False,
                output_field=BooleanField()
            )
        )

        return queryset
```

## 10. テスト

### 10.1 テストクラス構造
```python
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Article
from .factories import UserFactory, ArticleFactory

class ArticleModelTest(TestCase):
    """モデルのテスト"""

    def setUp(self):
        self.user = UserFactory()
        self.article = ArticleFactory(author=self.user)

    def test_string_representation(self):
        """文字列表現のテスト"""
        self.assertEqual(str(self.article), self.article.title)

    def test_slug_generation(self):
        """スラッグ自動生成のテスト"""
        article = Article.objects.create(
            title="Test Article",
            author=self.user
        )
        self.assertEqual(article.slug, "test-article")

class ArticleAPITest(APITestCase):
    """APIエンドポイントのテスト"""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_list_articles(self):
        """記事一覧取得のテスト"""
        ArticleFactory.create_batch(3)

        response = self.client.get('/api/articles/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_create_article(self):
        """記事作成のテスト"""
        data = {
            'title': 'New Article',
            'content': 'Article content'
        }

        response = self.client.post('/api/articles/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Article.objects.count(), 1)
```

### 10.2 ファクトリーパターン
```python
# factories.py
import factory
from factory.django import DjangoModelFactory
from .models import User, Article

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

class ArticleFactory(DjangoModelFactory):
    class Meta:
        model = Article

    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text')
    author = factory.SubFactory(UserFactory)
```

## 11. セキュリティ

### 11.1 認証・認可
```python
from rest_framework.permissions import BasePermission

class IsOwnerOrReadOnly(BasePermission):
    """
    オブジェクトの所有者のみ編集可能
    """
    def has_object_permission(self, request, view, obj):
        # 読み取り権限は全員に許可
        if request.method in permissions.SAFE_METHODS:
            return True

        # 書き込み権限は所有者のみ
        return obj.owner == request.user

class HasSubscription(BasePermission):
    """
    有効なサブスクリプションを持つユーザーのみ
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            hasattr(request.user, 'subscription') and
            request.user.subscription.is_active
        )
```

### 11.2 入力検証
```python
class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        min_length=8,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_password(self, value):
        """パスワードの強度チェック"""
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError(
                "パスワードには少なくとも1つの数字を含めてください"
            )
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError(
                "パスワードには少なくとも1つの大文字を含めてください"
            )
        return value
```

## 12. パフォーマンス

### 12.1 キャッシング
```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    @method_decorator(cache_page(60 * 15))  # 15分キャッシュ
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        # 手動キャッシング
        cache_key = f'article_{kwargs["pk"]}'
        article = cache.get(cache_key)

        if article is None:
            article = self.get_object()
            cache.set(cache_key, article, 60 * 60)  # 1時間キャッシュ

        serializer = self.get_serializer(article)
        return Response(serializer.data)
```

### 12.2 ページネーション
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# カスタムページネーション
class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        })
```

## 13. ロギング

### 13.1 ロギング設定
```python
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    def process_payment(self, payment_data):
        logger.info(f"Processing payment for user {payment_data['user_id']}")

        try:
            # 処理ロジック
            result = self._execute_payment(payment_data)
            logger.info(f"Payment successful: {result['transaction_id']}")
            return result

        except PaymentGatewayError as e:
            logger.error(
                f"Payment gateway error for user {payment_data['user_id']}: {e}",
                exc_info=True,
                extra={'payment_data': payment_data}
            )
            raise

        except Exception as e:
            logger.critical(
                f"Unexpected error in payment processing: {e}",
                exc_info=True
            )
            raise
```

### 13.2 構造化ログ
```python
import structlog

logger = structlog.get_logger()

class ArticleService:
    def create_article(self, data, user):
        log = logger.bind(
            user_id=user.id,
            action='create_article'
        )

        log.info("Starting article creation")

        try:
            article = Article.objects.create(**data)
            log.info(
                "Article created successfully",
                article_id=article.id,
                title=article.title
            )
            return article

        except Exception as e:
            log.error(
                "Article creation failed",
                error=str(e),
                data=data
            )
            raise
```

## 14. 非同期処理

### 14.1 Celeryタスク
```python
# tasks.py
from celery import shared_task
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60}
)
def send_email_task(self, subject, message, recipient_list):
    """
    メール送信タスク
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email='noreply@example.com',
            recipient_list=recipient_list,
            fail_silently=False
        )
        logger.info(f"Email sent successfully to {recipient_list}")

    except Exception as exc:
        logger.error(f"Email sending failed: {exc}")
        raise self.retry(exc=exc)

@shared_task
def generate_report(report_id):
    """
    レポート生成タスク
    """
    from .models import Report

    report = Report.objects.get(id=report_id)
    report.status = 'processing'
    report.save()

    try:
        # レポート生成ロジック
        data = collect_report_data(report)
        file_path = create_report_file(data)

        report.file_path = file_path
        report.status = 'completed'
        report.save()

    except Exception as e:
        report.status = 'failed'
        report.error_message = str(e)
        report.save()
        raise
```

### 14.2 非同期ビュー（Django 3.1+）
```python
import asyncio
from django.http import JsonResponse
from asgiref.sync import sync_to_async

async def async_view(request):
    """
    非同期ビューの例
    """
    # 非同期でデータベースクエリ
    @sync_to_async
    def get_articles():
        return list(Article.objects.all()[:10])

    # 複数の非同期処理を並行実行
    articles, user_count = await asyncio.gather(
        get_articles(),
        sync_to_async(User.objects.count)()
    )

    return JsonResponse({
        'articles': [{'id': a.id, 'title': a.title} for a in articles],
        'user_count': user_count
    })
```

## 15. 環境設定

### 15.1 設定ファイルの分割
```python
# settings/base.py
"""
共通設定
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ...
]

# settings/development.py
"""
開発環境設定
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dev_db',
        'USER': 'dev_user',
        'PASSWORD': 'dev_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# settings/production.py
"""
本番環境設定
"""
from .base import *

DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

### 15.2 環境変数の管理
```python
# .env.example
SECRET_KEY=your-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

## 16. ドキュメンテーション

### 16.1 docstring規約
```python
def calculate_discount(price: float, discount_percent: float) -> float:
    """
    割引価格を計算する

    Args:
        price: 元の価格
        discount_percent: 割引率（0-100）

    Returns:
        割引後の価格

    Raises:
        ValueError: 価格が負の値または割引率が範囲外の場合

    Example:
        >>> calculate_discount(1000, 20)
        800.0
    """
    if price < 0:
        raise ValueError("価格は0以上である必要があります")
    if not 0 <= discount_percent <= 100:
        raise ValueError("割引率は0-100の範囲である必要があります")

    return price * (1 - discount_percent / 100)

class PaymentProcessor:
    """
    決済処理を行うクラス

    Attributes:
        gateway: 決済ゲートウェイのインスタンス
        logger: ロガーインスタンス

    Example:
        >>> processor = PaymentProcessor(gateway=StripeGateway())
        >>> result = processor.process(amount=1000, currency='JPY')
    """

    def process(self, amount: float, currency: str) -> dict:
        """
        決済を処理する

        Args:
            amount: 決済金額
            currency: 通貨コード（ISO 4217）

        Returns:
            dict: 決済結果を含む辞書
                - transaction_id: トランザクションID
                - status: 決済ステータス
                - timestamp: 処理日時

        Raises:
            PaymentError: 決済処理に失敗した場合
        """
        pass
```

### 16.2 API ドキュメント
```python
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class ArticleViewSet(viewsets.ModelViewSet):
    @swagger_auto_schema(
        operation_description="記事一覧を取得",
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="検索キーワード",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: ArticleSerializer(many=True),
            401: "認証が必要です",
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
```

## 17. コードレビューチェックリスト

### 17.1 必須確認項目
- [ ] PEP 8準拠
- [ ] 適切なエラーハンドリング
- [ ] N+1問題の回避
- [ ] セキュリティ脆弱性のチェック
- [ ] テストの実装
- [ ] ドキュメントの更新

### 17.2 パフォーマンス確認
- [ ] 不要なデータベースクエリの削除
- [ ] 適切なインデックスの設定
- [ ] キャッシュの活用
- [ ] ページネーションの実装

### 17.3 保守性確認
- [ ] コードの重複排除
- [ ] 適切な抽象化
- [ ] 明確な命名
- [ ] 将来の拡張性考慮

## 18. デプロイメント

### 18.1 本番環境チェックリスト
```python
# チェック項目
DEBUG = False
SECRET_KEY が環境変数から取得
ALLOWED_HOSTS の設定
静的ファイルの配信設定
データベースのマイグレーション
Celeryワーカーの起動
ロギング設定の確認
エラー通知の設定
```

### 18.2 デプロイメントスクリプト例
```bash
#!/bin/bash
# deploy.sh

# 環境変数の読み込み
source .env.production

# 依存関係のインストール
pip install -r requirements.txt

# 静的ファイルの収集
python manage.py collectstatic --noinput

# マイグレーション
python manage.py migrate --noinput

# サーバー再起動
supervisorctl restart all
```

## 19. トラブルシューティング

### 19.1 デバッグツール
```python
# Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Django Extensions
INSTALLED_APPS += ['django_extensions']

# シェルプラス
# python manage.py shell_plus --ipython
```

### 19.2 一般的な問題と解決策
```python
# 循環インポート回避
# 悪い例
from app_a.models import ModelA  # app_b/models.py内
from app_b.models import ModelB  # app_a/models.py内

# 良い例 - 遅延インポート
def get_model_a():
    from app_a.models import ModelA
    return ModelA

# メモリリーク対策
# 悪い例
cache = []  # グローバル変数にデータを蓄積

# 良い例
from django.core.cache import cache
cache.set('key', value, timeout=3600)
```

## 20. ベストプラクティスまとめ

### 20.1 必ず守るべき原則
1. **早期リターン**: ネストを深くしない
2. **単一責任**: 1つの関数/クラスは1つの責務
3. **依存性注入**: 密結合を避ける
4. **防御的プログラミング**: 想定外の入力に対処
5. **ログ出力**: 適切なレベルでログを記録

### 20.2 推奨事項
1. **型ヒント使用**: Python 3.5+
2. **Enumの活用**: マジックナンバー回避
3. **データクラス使用**: Python 3.7+
4. **Context Manager活用**: リソース管理
5. **ジェネレータ使用**: メモリ効率的な処理

### 20.3 アンチパターン
1. **catch-all except**: 具体的な例外を捕捉
2. **可変デフォルト引数**: `def func(items=[])`は避ける
3. **グローバル変数**: 設定以外では使用しない
4. **巨大な関数**: 50行を超えたら分割検討
5. **コメントアウトされたコード**: 削除またはVCS活用

---

この規約は定期的に見直し、プロジェクトの成長とチームのニーズに応じて更新することを推奨します。
