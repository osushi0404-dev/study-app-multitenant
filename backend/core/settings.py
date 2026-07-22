"""
Django settings for core project.
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # logout での refresh トークン失効に必要（I142）
    'corsheaders',
    'django_extensions',
    'django_filters',
    'guardian',
]

LOCAL_APPS = [
    'accounts',
    'problems',
    'studylogs',
    'dashboard',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.RequestLoggingMiddleware',  # リクエストログ出力
    'core.enhanced_logging.ErrorContextMiddleware',  # エラー詳細情報収集
    'core.middleware.MonitoringMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_ratelimit.middleware.RatelimitMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'learning_app'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Frontend URL
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Django REST Framework
# スロットル設定（DEFAULT_THROTTLE_CLASSES/RATES・NUM_PROXIES）は下方の Rate Limiting セクション参照（I127）
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    # I142: token_blacklist 有効化前は blacklist 機能が存在せず、この設定は
    # simplejwt 内部で無視されていた（＝ローテート済み refresh も期限まで有効）。
    # フロントエンドがローテート後の新 refresh を保存していないため、True のままだと
    # 2 回目の更新で強制ログアウトになる。FE の更新処理を是正するまで明示的に False とする。
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# カスタムヘッダーを許可
# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUserIdBackend',  # Custom backend for email or user_id login
    'django.contrib.auth.backends.ModelBackend',  # Default Django backend
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'cache-control',  # フロントエンドのキャッシュ制御用
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-user-actions',  # カスタムヘッダーを追加
]

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'learning_app',
        'VERSION': 1,
        'TIMEOUT': 300,  # 5分のデフォルトタイムアウト
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'learning_app_sessions',
        'TIMEOUT': 1800,  # 30分
    },
    'problems': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'learning_app_problems',
        'TIMEOUT': 3600,  # 1時間
    },
    'analytics': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'learning_app_analytics',
        'TIMEOUT': 1800,  # 30分
    }
}

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'apikey')
EMAIL_HOST_PASSWORD = os.getenv('SENDGRID_API_KEY', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@learningapp.com')

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Rate Limiting
# デフォルト True（本番・開発環境）。E2E CI では RATELIMIT_ENABLE=false を設定して無効化する（12-Factor App）。
# このスイッチは django-ratelimit（accounts の認証系）と DRF スロットル（API 全体・I127）の両方に効く。
RATELIMIT_ENABLE = os.environ.get('RATELIMIT_ENABLE', 'True').lower() != 'false'
RATELIMIT_USE_CACHE = 'default'

# DRF スロットル（I127: API 全体の基本レート制限。使用キャッシュは default=Redis・
# IGNORE_EXCEPTIONS=True のため Redis 断時はフェイルオープン=可用性優先）
# クラスリストは無条件の定数とし、有効スイッチ・レート値は core/throttling.py の
# アプリ専用クラスがリクエスト時にライブ評価する（import 時スナップショット回避・計画 発見4）。
API_THROTTLE_ENABLED = RATELIMIT_ENABLE  # DRF スロットル有効スイッチ（リクエスト時にライブ参照される）
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'core.throttling.AppAnonRateThrottle',
    'core.throttling.AppUserRateThrottle',
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '60/min',   # 未認証: IP ごと（登録画面の科目取得等は数 req/min で余裕）
    'user': '300/min',  # 認証済み: ユーザーごと（1 問/秒のクイズ回答=60 req/min でも 300/min に余裕で抵触しない）
}
# 本番は nginx 1 段（X-Forwarded-For 付与・nginx/default.conf）。XFF が無い直アクセスは
# REMOTE_ADDR に自動フォールバックするため開発環境でもこの値のままでよい。
REST_FRAMEWORK['NUM_PROXIES'] = 1

# Logging
# 拡張ログ設定をインポート
from .enhanced_logging import ENHANCED_LOGGING_CONFIG  # noqa: E402

# ログ設定を拡張版に置き換え
LOGGING = ENHANCED_LOGGING_CONFIG

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 1800  # 30分
SESSION_SAVE_EVERY_REQUEST = True

# Application specific settings
STUDY_SESSION_TIMEOUT_MINUTES = 30
MAX_QUIZ_QUESTIONS_PER_SESSION = 50
SPACED_REPETITION_INTERVALS = [1, 3, 7, 14, 30, 90]  # days

# Cache settings
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'learning_app'

# Cache timeouts for different data types
CACHE_TIMEOUTS = {
    'user_profile': 1800,        # 30分
    'problem_list': 3600,        # 1時間
    'subject_list': 7200,        # 2時間
    'analytics_daily': 1800,     # 30分
    'analytics_weekly': 3600,    # 1時間
    'spaced_repetition': 300,    # 5分
    'mistake_patterns': 1800,    # 30分
    'learning_suggestions': 900,  # 15分
}
