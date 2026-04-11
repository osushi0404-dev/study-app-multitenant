# バックエンド開発コーディング規約（Python / Django）

本ドキュメントは **Cursor** と **Claude Code** を併用した Web アプリ開発におけるバックエンド（Python/Django）の実装規約です。フロントエンド規約と併用し、個人/チーム開発の双方に適用します。

---

## 0. 対象と前提
- Python **3.11+**（可能なら 3.12）
- Django **5.x** / Django REST Framework（以下 DRF）**3.15+**
- DB：**PostgreSQL 14+**（UTF-8, UTC）
- 依存管理：**uv / pip-tools / Poetry のいずれか**（プロジェクトで固定）
- 型：**mypy + django-stubs**、Lint/Format：**Ruff（lint+format）**
- コンテナ：Docker / docker-compose（本番は `--no-dev` 依存のみ）
- 環境変数管理：**12-factor** 徹底（後述）

> 注：Cursor/Claude による自動生成は **本規約を上書きしない**。ガードレールは末尾の運用規約に準拠。

---

## 1. プロジェクト構成（例）
```text
project_root/
  pyproject.toml         # ruff/mypy/pytest 設定（可能な限り統合）
  .env.example           # 環境変数サンプル（機密は含めない）
  docker/
    app.Dockerfile
    compose.yml
  Makefile               # よく使うコマンドの短縮（後述）
  manage.py
  src/
    config/              # 設定・URL・WSGI/ASGI
      __init__.py
      asgi.py
      wsgi.py
      urls.py
      settings/
        __init__.py
        base.py
        dev.py
        test.py
        prod.py
      schema.py          # OpenAPI 生成（drf-spectacular 等）
      logging.py         # ロギング設定
      middleware.py      # request_id 等
    apps/
      users/
        __init__.py
        models.py
        admin.py
        services.py      # ドメイン/ユースケース
        selectors.py     # 読み取り系（QuerySet/集計）
        api/
          serializers.py
          views.py       # ViewSet/Router
          urls.py
        tasks.py         # Celery/RQ 等
        tests/
          test_models.py
          test_api.py
      ...                # 他アプリ
```
- **分離**：
  - 読み取りは `selectors.py`、書き込み/業務は `services.py`。
  - API レイヤは `apps/<app>/api/` に集約。
  - アプリまたぎの共通処理は `src/common/` を作り小さく保つ。

---

## 2. 依存関係とバージョン
- **固定**：本番リリースごとに lock/constraints を更新・固定。
- **原則**：メジャーアップグレードは検証ブランチで。
- **禁止**：目的不明の依存追加。1 PR で 1～2 個まで。

---

## 3. 設定管理（settings）
- `config/settings/base.py` に共通、`dev.py/test.py/prod.py` で上書き。
- 機密・環境依存値は **環境変数** からのみ取得。
- 推奨：`django-environ` または `pydantic-settings`。
- `USE_TZ = True`、**内部は UTC** 運用。表示はクライアントでローカライズ。
- `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` は必須。
- 静的/メディア：開発は `STATICFILES_DIRS`、本番は S3 + CDN（後述）。

---

## 4. 型/静的解析・コード規約
- **Ruff**：`ruff check` + `ruff format` を CI で強制。
- **mypy**：`django-stubs` を導入。`QuerySet[Model]` 型、`TypedDict`/`Protocol` を活用。
- **Docstring**：公開 API/サービス層は Google 形式で記述。
- **命名**：
  - モジュール/関数/変数：`snake_case`
  - クラス：`PascalCase`
  - 定数：`UPPER_SNAKE_CASE`
  - 真偽：`is_`/`has_`/`can_`/`should_`

---

## 5. モデル設計
- **主キーは UUID**（`UUIDField`、可能なら v7）。外部公開 ID と整合。
- **必ず `__str__`** を定義。`Meta` に `db_table`/`ordering`/`indexes`/`constraints` を整理。
- **choices** は `TextChoices/IntegerChoices` を使用。
- 金額/率は `DecimalField`（`max_digits`, `decimal_places` 明示）。
- `null=True` は **DB 上の意味を持つ**ため慎重に。空文字と混同しない。
- 多対多は **中間モデル（through）** を検討し監査項目（作成者/日時）を持たせる。

**例**
```py
# src/apps/users/models.py
import uuid
from django.db import models

class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        indexes = [models.Index(fields=["email"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.display_name} <{self.email}>"
```

---

## 6. マイグレーション指針
- 1 PR = 1 機能単位で**小さく**。命名は `app; change summary`。
- 既存テーブルの重い変更は **段階的**（列追加→バックフィル→NOT NULL 付与）。
- 大規模バックフィルは **データ移行 `RunPython`** を分割し **バッチ処理**。
- PostgreSQL のインデックスは **CONCURRENTLY** を優先（`AddIndexConcurrently`）。
- **禁止**：長時間ロックを伴う一括変更、業務時間帯の危険な `ALTER`。
- 定期的に **squashmigrations**。

---

## 7. ORM/クエリ規約
- N+1 回避：`select_related`, `prefetch_related` を徹底。関連名に応じて最短で。
- 集計は `annotate`/`Subquery`/`Exists` を優先。必要なら **生 SQL は関数に隔離**。
- 大量挿入/更新は `bulk_create`/`bulk_update`。ただし `auto_now` 等に注意。
- 1 リクエストのクエリ数は **上限** を定め、DebugToolbar/Silk で監視。
- トランザクション：`atomic()` を **サービス層** で張り、整合境界を明確化。

---

## 8. サービス/セレクタ層（推奨パターン）
- **selectors.py**：読み取り専用（複合検索・ページング・集計）。副作用なし。
- **services.py**：書き込み・業務ロジック。**idempotent** を意識し再試行に耐える。
- API からは **サービス/セレクタを呼ぶだけ**。View でロジックを書かない。

---

## 9. API（DRF）規約
- **ViewSet + Router** を既定。アクションは `list/retrieve/create/update/partial_update/destroy` に準拠。
- **Serializer** で入出力を厳格化（`read_only_fields` と `validators`）。
- **Filter/Sort**：`django-filter` と `ordering` を使用。入力はホワイトリスト化。
- **Pagination**：LimitOffset か PageNumber を統一。
- **エラー形式**：Problem Details（`application/problem+json`）を推奨。最低限、`code`/`message`/`detail`。
- **OpenAPI**：`drf-spectacular` で自動生成し `/schema/` に配置。フロントは openapi-typescript 等で型生成。

**例**
```py
# src/apps/users/api/serializers.py
from rest_framework import serializers
from ..models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "display_name", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
```
```py
# src/apps/users/api/views.py
from rest_framework import viewsets, permissions
from .serializers import UserSerializer
from ..models import User

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
```
```py
# src/apps/users/api/urls.py
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
urlpatterns = router.urls
```

---

## 10. 認証/認可
- SPA 同一オリジン：**セッション + CSRF** を推奨。`SESSION_COOKIE_SECURE`, `HTTPONLY`, `SAMESITE=Lax|Strict`。
- クロスドメイン/API 専用：`django-rest-framework-simplejwt` 等を利用。**短寿命アクセストークン + リフレッシュ**。
- 権限：`IsAuthenticated` を既定、機能は **Object-level Permission** を検討。
- レート制限：DRF Throttling を設定（`AnonRate`, `UserRate`）。

---

## 11. シリアライゼーション/日付・時刻
- **ISO-8601 / UTC** で入出力。`DateTimeField` は `timezone.is_aware` を担保。
- 数値/金額の丸めは **サービス層** で統一。

---

## 12. バリデーション
- モデルレベル：`validators` / `clean()` / DB 制約。
- シリアライザレベル：`validate_*` / `validate`。エラーメッセージは i18n キーへ寄せる。

---

## 13. ロギング/監視
- **構造化 JSON ログ**。`logging.py` にハンドラ/フォーマタ集約。
- 1 リクエスト = 1 `request_id`（ミドルウェアで付与）。全ログに含める。
- **レベル**：`INFO`（業務イベント）、`WARNING`（想定内異常）、`ERROR`（失敗）、`DEBUG`（開発時）
- 例外は `logging.exception` + APM（Sentry など）へ転送。

**設定例**
```py
# src/config/logging.py（抜粋）
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"}
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
```

---

## 14. セキュリティ
- `SECRET_KEY`/DB 認証情報は **環境変数** のみ。リポジトリへ含めない。
- `manage.py check --deploy` を CI に組み込み。
- Cookie：`Secure`/`HttpOnly`/`SameSite` を適用。
- CSP：`django-csp` 推奨。CORS は **最小許可**。
- パスワード：**Argon2** を既定。
- ファイルアップロード：拡張子/Content-Type 検証、サイズ上限、ウイルススキャン（必要に応じ ClamAV 等）。

---

## 15. パフォーマンス/キャッシュ
- キャッシュ：`django-redis` を使用。キーは `app:resource:<ver>:<id>`。
- 失効戦略を決める（Write-through / Cache-aside）。
- 重い処理は非同期へ（次章）。
- ページネーションの既定上限を設定。無制限の取得禁止。

---

## 16. 非同期処理（Celery 等）
- ブローカー：Redis/RabbitMQ。**acks_late**、**重複排除キー**、**指数バックオフ** を設定。
- タスクは **冪等** に。外部 I/O はタイムアウト必須。
- ログには `task_id`/`request_id` を含める。

**例**
```py
# src/apps/users/tasks.py
from celery import shared_task

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=2, retry_kwargs={"max_retries": 5})
def send_welcome_email(self, user_id: str) -> None:
    ...
```

---

## 17. ストレージ（静的/メディア）
- 本番：S3 互換 + CDN（例：CloudFront）。`django-storages` を使用。
- メディアの公開可否は **署名付き URL** で制御。

---

## 18. テスト戦略
- **pytest + pytest-django**。テストは `src/apps/<app>/tests/` に配置。
- ファクトリ：`model_bakery` または `factory_boy`。
- カバレッジ閾値：**Lines ≥ 85% / Branches ≥ 75%**（コアは 90%）。
- マーク：`@pytest.mark.django_db`（transactional/readonly を使い分け）。
- 外部 I/O はモック（`responses`/`respx`）。時刻は `freezegun`。

**例**
```py
# src/apps/users/tests/test_api.py
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_list_users():
    client = APIClient()
    client.force_authenticate(user=...)  # fixture 推奨
    res = client.get("/api/users/")
    assert res.status_code == 200
    assert "results" in res.data
```

---

## 19. CI/CD
- PR 必須ジョブ：`ruff check` → `ruff format --check` → `mypy` → `pytest --maxfail=1` → `manage.py check --deploy` → `python manage.py makemigrations --check` → `pip-audit`。
- 成果物：OpenAPI JSON を出力し、フロントが型生成できるようアーティファクト化。
- Docker イメージは **non-root** 実行、`distroless` など軽量ベースを推奨。

---

## 20. 運用（Runbook 抜粋）
- ロールアウト：DB 変更は **先行デプロイ（migrate）→ アプリ** の順。
- ログ監視：エラー率・P95/P99 をダッシュボード化。
- 機密ローテーション：四半期ごとに Secret 更新（自動化可）。

---

## 21. Makefile（抜粋）
```makefile
.PHONY: fmt lint type test run migrate makemig
fmt:        ## Ruff で整形
	ruff format
lint:       ## Ruff で lint
	ruff check --fix
type:       ## 型チェック
	mypy src
migrate:
	python manage.py migrate
makemig:
	python manage.py makemigrations
run:
	python manage.py runserver 0.0.0.0:8000
```

---

## 22. 設定スニペット
**pyproject.toml（抜粋）**
```toml
[tool.ruff]
line-length = 100
select = ["E","F","I","B","UP","N","ARG","RUF"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["apps","config"]

[tool.mypy]
python_version = "3.11"
plugins = ["mypy_django_plugin.main"]
strict = true
mypy_path = ["src"]

[tool.django-stubs]
django_settings_module = "config.settings.dev"

[tool.pytest.ini_options]
testpaths = ["src/apps"]
addopts = "-q --disable-warnings --maxfail=1 --cov=src --cov-report=term-missing"
```

**settings/base.py（抜粋）**
```py
import os
from .logging import LOGGING

DEBUG = False
TIME_ZONE = "UTC"
USE_TZ = True
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",") if os.getenv("ALLOWED_HOSTS") else []
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if os.getenv("CSRF_TRUSTED_ORIGINS") else []

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
LOGGING = LOGGING
```

---

## 23. Cursor / Claude Code 運用規約（バックエンド）
### 23.1 ガードレール（必須）
- 「**本規約（構成/命名/型/テスト/セキュリティ）を厳守**」
- 「**既存の public API/DB スキーマを変更しない**（やむを得ない場合は提案+移行計画）」
- 「**不足情報は TODO と `raise NotImplementedError` で明示**」
- 「**差分はパッチ形式**。200 行超は分割」
- 「**migrations は必ず生成し、説明を書く**」

### 23.2 出力・検証
- 生成後に `ruff format` / `ruff check` / `mypy` / `pytest` を実行。
- OpenAPI 変更は **意図を PR に要約** し、フロント自動生成に影響が出る点を記載。

### 23.3 禁止事項
- 機密のハードコード、過剰な依存追加、ロングトランザクション、View 内ロジック肥大化。

---

## 24. 付録：最小 API サンプル（モデル→API→テスト）
**モデル**
```py
# src/apps/notes/models.py
import uuid
from django.db import models

class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notes"
        indexes = [models.Index(fields=["owner", "created_at"])]
```

**シリアライザ/ビュー**
```py
# src/apps/notes/api/serializers.py
from rest_framework import serializers
from ..models import Note

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ("id", "title", "body", "owner", "created_at", "updated_at")
        read_only_fields = ("id", "owner", "created_at", "updated_at")
```
```py
# src/apps/notes/api/views.py
from rest_framework import viewsets, permissions
from .serializers import NoteSerializer
from ..models import Note

class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Note.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
```

**テスト**
```py
# src/apps/notes/tests/test_api.py
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_notes_crud(user_factory):
    client = APIClient()
    user = user_factory()
    client.force_authenticate(user)

    # Create
    res = client.post("/api/notes/", {"title": "t", "body": "b"}, format="json")
    assert res.status_code == 201

    # List
    res = client.get("/api/notes/")
    assert res.status_code == 200
    assert len(res.data["results"]) == 1
```

---

以上。必要に応じてプロジェクト特性（S3 バケット名、CSP ポリシー、JWT 寿命、レート制限値など）を別紙の運用定義に落とし込みます。
