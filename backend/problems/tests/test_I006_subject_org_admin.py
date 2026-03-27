import pytest
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
    admin_user = User.objects.create_user(
        email="admin@example.com",
        user_id="orgadmin",
        password="pass",
        organization=org,
        role='admin',
    )
    normal_user = User.objects.create_user(
        email="user@example.com",
        user_id="normaluser",
        password="pass",
        organization=org,
        role='user',
    )
    existing = Subject.objects.create(
        name="既存科目", slug="existing", organization=org
    )
    return {
        "org": org,
        "admin": admin_user,
        "normal": normal_user,
        "existing": existing,
    }


# TC-AUTO-001
@pytest.mark.django_db
def test_create_subject_as_org_admin(setup_data, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "新科目"}, format="json")

    assert response.status_code == 201
    assert Subject.objects.filter(
        name="新科目", organization=setup_data["org"]
    ).exists()


# TC-AUTO-002
@pytest.mark.django_db
def test_create_subject_forbidden_for_normal_user(setup_data):
    client = APIClient()
    client.force_authenticate(user=setup_data["normal"])

    response = client.post("/api/subjects/", {"name": "不正科目"}, format="json")

    assert response.status_code == 403
    assert not Subject.objects.filter(name="不正科目").exists()


# TC-AUTO-003
@pytest.mark.django_db
def test_create_subject_unauthorized():
    client = APIClient()

    response = client.post("/api/subjects/", {"name": "不正科目"}, format="json")

    assert response.status_code == 401


# TC-AUTO-004
@pytest.mark.django_db
def test_create_subject_slug_auto_generated_english(setup_data, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "AWS SAA"}, format="json")

    assert response.status_code == 201
    subject = Subject.objects.get(name="AWS SAA", organization=setup_data["org"])
    assert subject.slug == "aws-saa"


# TC-AUTO-005
@pytest.mark.django_db
def test_create_subject_slug_auto_generated_japanese(setup_data, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "基礎数学"}, format="json")

    assert response.status_code == 201
    subject = Subject.objects.get(name="基礎数学", organization=setup_data["org"])
    assert subject.slug
    assert subject.slug.startswith("s-")


# TC-AUTO-006
@pytest.mark.django_db
def test_create_subject_slug_collision_auto_numbered(setup_data, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    org = setup_data["org"]
    Subject.objects.create(name="テスト1", slug="test", organization=org)
    Subject.objects.create(name="テスト2", slug="test-2", organization=org)

    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])
    response = client.post("/api/subjects/", {"name": "test"}, format="json")

    assert response.status_code == 201
    subject = Subject.objects.get(name="test", organization=org)
    assert subject.slug == "test-3"


# TC-AUTO-007
@pytest.mark.django_db
def test_create_subject_duplicate_name_returns_400(setup_data, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "既存科目"}, format="json")

    assert response.status_code == 400


# TC-AUTO-008
@pytest.mark.django_db
def test_list_subjects_accessible_for_normal_user(setup_data):
    client = APIClient()
    client.force_authenticate(user=setup_data["normal"])

    response = client.get("/api/subjects/")

    assert response.status_code == 200


# TC-AUTO-009
@pytest.mark.django_db
def test_media_folders_created_on_subject_create(setup_data, tmp_path, settings):
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


# TC-AUTO-010
@pytest.mark.django_db
def test_subject_rolled_back_when_folder_creation_fails(setup_data, tmp_path, settings, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)

    def broken_makedirs(path, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("os.makedirs", broken_makedirs)

    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=setup_data["admin"])

    response = client.post("/api/subjects/", {"name": "ロールバックテスト"}, format="json")

    assert response.status_code == 500
    assert not Subject.objects.filter(name="ロールバックテスト").exists()


# TC-AUTO-011
@pytest.mark.django_db
def test_user_serializer_includes_organization_name(setup_data):
    from accounts.serializers import UserSerializer

    serializer = UserSerializer(setup_data["admin"])
    data = serializer.data

    assert "organization_name" in data
    assert data["organization_name"] == "テスト組織"


# TC-AUTO-012
@pytest.mark.django_db
def test_user_serializer_organization_name_none_when_no_org(db):
    user_no_org = User.objects.create_user(
        email="noorg@example.com",
        user_id="noorguser",
        password="pass",
        organization=None,
        role='admin',
    )
    from accounts.serializers import UserSerializer

    serializer = UserSerializer(user_no_org)
    assert serializer.data["organization_name"] is None
