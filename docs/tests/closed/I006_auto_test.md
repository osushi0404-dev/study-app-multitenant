# 自動テスト仕様書: I006 企業・団体ごとの科目追加機能

## 基本情報
- **関連イシュー**: #006
- **関連計画書**: I006_plan
- **作成日**: 2026-03-24
- **テストファイル**: `backend/problems/tests/test_I006_subject_org_admin.py`

---

## テストファイル構成

```
backend/problems/tests/
└── test_I006_subject_org_admin.py   ← 新規作成
```

---

## 共通フィクスチャ

```python
import pytest
import os
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from problems.models import Subject
from accounts.models import Organization, OrganizationCategory

User = get_user_model()


@pytest.fixture
def category(db):
    return OrganizationCategory.objects.create(name="テスト", slug="test-cat")


@pytest.fixture
def setup_data(db, category):
    org = Organization.objects.create(
        name="テスト組織", slug="test-org", category=category
    )
    # 組織管理者
    admin_user = User.objects.create_user(
        email="admin@example.com",
        password="pass",
        username="orgadmin",
        organization=org,
        role='admin',
    )
    # 一般ユーザー
    normal_user = User.objects.create_user(
        email="user@example.com",
        password="pass",
        username="normaluser",
        organization=org,
        role='user',
    )
    # 既存科目
    existing = Subject.objects.create(
        name="既存科目", slug="existing", organization=org
    )
    return {
        "org": org,
        "admin": admin_user,
        "normal": normal_user,
        "existing": existing,
    }
```

---

## テストケース

### [TC-AUTO-001] POST /api/subjects/ — role='admin' で科目が作成される

```python
@pytest.mark.django_db
def test_create_subject_as_org_admin(setup_data):
    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "新科目"}, format="json")

    assert response.status_code == 201
    assert Subject.objects.filter(
        name="新科目", organization=setup_data["org"]
    ).exists()
```

---

### [TC-AUTO-002] POST /api/subjects/ — role='user' で 403

```python
@pytest.mark.django_db
def test_create_subject_forbidden_for_normal_user(setup_data):
    client = APIClient()
    client.force_authenticate(user=setup_data["normal"])

    response = client.post("/api/subjects/", {"name": "不正科目"}, format="json")

    assert response.status_code == 403
    assert not Subject.objects.filter(name="不正科目").exists()
```

---

### [TC-AUTO-003] POST /api/subjects/ — 未認証で 401

```python
@pytest.mark.django_db
def test_create_subject_unauthorized():
    client = APIClient()

    response = client.post("/api/subjects/", {"name": "不正科目"}, format="json")

    assert response.status_code == 401
```

---

### [TC-AUTO-004] POST /api/subjects/ — 英語名でスラッグが自動生成される

```python
@pytest.mark.django_db
def test_create_subject_slug_auto_generated_english(setup_data):
    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "AWS SAA"}, format="json")

    assert response.status_code == 201
    subject = Subject.objects.get(name="AWS SAA", organization=setup_data["org"])
    assert subject.slug == "aws-saa"
```

---

### [TC-AUTO-005] POST /api/subjects/ — 日本語名でスラッグが UUID 形式になる

```python
@pytest.mark.django_db
def test_create_subject_slug_auto_generated_japanese(setup_data):
    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "基礎数学"}, format="json")

    assert response.status_code == 201
    subject = Subject.objects.get(name="基礎数学", organization=setup_data["org"])
    assert subject.slug  # 空でないこと
    assert subject.slug.startswith("s-")  # UUID フォールバック
```

---

### [TC-AUTO-006] POST /api/subjects/ — スラッグ重複時に自動採番

```python
@pytest.mark.django_db
def test_create_subject_slug_collision_auto_numbered(setup_data):
    """同一組織内でスラッグが衝突する場合 -2 が付与される"""
    org = setup_data["org"]
    Subject.objects.create(name="テスト1", slug="test", organization=org)
    Subject.objects.create(name="テスト2", slug="test-2", organization=org)

    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])
    # name="test" の英語入力 → slug="test" → 重複 → "test-2" も重複 → "test-3"
    response = client.post("/api/subjects/", {"name": "test"}, format="json")

    assert response.status_code == 201
    subject = Subject.objects.get(name="test", organization=org)
    assert subject.slug == "test-3"
```

---

### [TC-AUTO-007] POST /api/subjects/ — 同名科目で 400（unique_together 違反）

```python
@pytest.mark.django_db
def test_create_subject_duplicate_name_returns_400(setup_data):
    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post(
        "/api/subjects/", {"name": "既存科目"}, format="json"
    )

    assert response.status_code == 400
```

---

### [TC-AUTO-008] GET /api/subjects/ — role='user' でも科目一覧取得可能

```python
@pytest.mark.django_db
def test_list_subjects_accessible_for_normal_user(setup_data):
    """list アクションは role に関係なく全認証ユーザーが使用可能"""
    client = APIClient()
    client.force_authenticate(user=setup_data["normal"])

    response = client.get("/api/subjects/")

    assert response.status_code == 200
```

---

### [TC-AUTO-009] POST /api/subjects/ — 科目作成時にメディアフォルダが作成される

```python
@pytest.mark.django_db
def test_media_folders_created_on_subject_create(setup_data, tmp_path, settings):
    """perform_create 内で problem/ と explanation/ フォルダが作成される"""
    settings.MEDIA_ROOT = str(tmp_path)

    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "Folder Test"}, format="json")

    assert response.status_code == 201
    org_slug = setup_data["org"].slug
    subject = Subject.objects.get(name="Folder Test", organization=setup_data["org"])

    problem_dir = tmp_path / "org" / org_slug / "subjects" / subject.slug / "problem"
    explanation_dir = tmp_path / "org" / org_slug / "subjects" / subject.slug / "explanation"

    assert problem_dir.exists(), "problem/ ディレクトリが作成されていない"
    assert explanation_dir.exists(), "explanation/ ディレクトリが作成されていない"
```

---

### [TC-AUTO-010] POST /api/subjects/ — フォルダ作成失敗時に科目がロールバックされる

```python
@pytest.mark.django_db
def test_subject_rolled_back_when_folder_creation_fails(setup_data, tmp_path, settings, monkeypatch):
    """os.makedirs が失敗した場合、transaction.atomic() により Subject も DB にコミットされない"""
    settings.MEDIA_ROOT = str(tmp_path)

    import os
    original_makedirs = os.makedirs

    def broken_makedirs(path, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "makedirs", broken_makedirs)

    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "ロールバックテスト"}, format="json")

    assert response.status_code == 500
    assert not Subject.objects.filter(name="ロールバックテスト").exists()
```

---

### [TC-AUTO-011] UserSerializer — organization_name が含まれる

```python
@pytest.mark.django_db
def test_user_serializer_includes_organization_name(setup_data):
    from accounts.serializers import UserSerializer

    serializer = UserSerializer(setup_data["admin"])
    data = serializer.data

    assert "organization_name" in data
    assert data["organization_name"] == "テスト組織"
```

---

### [TC-AUTO-012] UserSerializer — organization なしユーザーは None

```python
@pytest.mark.django_db
def test_user_serializer_organization_name_none_when_no_org(db, category):
    org = Organization.objects.create(
        name="仮組織", slug="temp", category=category
    )
    user_no_org = User.objects.create_user(
        email="noorg@example.com",
        password="pass",
        username="noorguser",
        organization=None,
        role='admin',
    )
    from accounts.serializers import UserSerializer

    serializer = UserSerializer(user_no_org)
    assert serializer.data["organization_name"] is None
```

---

## テスト実行コマンド

```bash
# I006 のテストのみ実行
docker-compose exec --user root backend python -m pytest problems/tests/test_I006_subject_org_admin.py -v

# 全テスト
docker-compose exec --user root backend python -m pytest -v
```

## テスト結果（2026-03-25）

| TC | テスト名 | 結果 |
|----|----------|------|
| TC-AUTO-001 | role='admin' で科目作成 | ✅ PASS |
| TC-AUTO-002 | role='user' で 403 | ✅ PASS |
| TC-AUTO-003 | 未認証で 401 | ✅ PASS |
| TC-AUTO-004 | 英語名スラッグ自動生成 | ✅ PASS |
| TC-AUTO-005 | 日本語名スラッグ UUID フォールバック | ✅ PASS |
| TC-AUTO-006 | スラッグ重複時に自動採番 | ✅ PASS |
| TC-AUTO-007 | 同名科目で 400 | ✅ PASS |
| TC-AUTO-008 | role='user' でも一覧取得可能 | ✅ PASS |
| TC-AUTO-009 | 科目作成時にフォルダ自動作成 | ✅ PASS |
| TC-AUTO-010 | フォルダ失敗時に科目ロールバック | ✅ PASS |
| TC-AUTO-011 | UserSerializer に organization_name 含まれる | ✅ PASS |
| TC-AUTO-012 | org なしユーザーは organization_name が None | ✅ PASS |
