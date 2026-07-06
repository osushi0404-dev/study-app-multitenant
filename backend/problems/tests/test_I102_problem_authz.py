"""
I102: 問題管理（ProblemViewSet）を組織管理者（role=='admin'）限定にする認可回帰テスト。

- 非admin（role='user'）は参照含む全経路で 403
- 未認証は 401（IsAuthenticated が IsOrgAdmin より前に遮断）
- admin（role='admin'）は参照・CRUD・カスタムアクションで 403 にならない

TC-AUTO-01/02/02b/03/03b（docs/tests/open/I102_auto_test.md）に対応。
"""
import json
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from problems.models import Subject, Problem, Choice
from accounts.models import Organization, OrganizationCategory

User = get_user_model()

DUMMY_ASSET_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def category(db):
    return OrganizationCategory.objects.create(name="テストI102", slug="test-cat-i102")


@pytest.fixture
def setup(db, category):
    org = Organization.objects.create(name="組織A_I102", slug="org-a-i102", category=category)
    admin = User.objects.create_user(
        email="admin_i102@example.com", user_id="admin_i102", password="pass",
        organization=org, role="admin",
    )
    normal = User.objects.create_user(
        email="user_i102@example.com", user_id="user_i102", password="pass",
        organization=org, role="user",
    )
    subject = Subject.objects.create(name="科目A_I102", slug="subject-a-i102", organization=org)
    problem = Problem.objects.create(
        subject=subject, organization=org, created_by=admin, question="問題1",
        problem_type="single", difficulty=1, explanation="解説",
    )
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    return {"org": org, "admin": admin, "normal": normal, "subject": subject, "problem": problem}


def _valid_payload(subject_id):
    """multipart 作成/更新用の有効なペイロード（choices は JSON 文字列リスト）。"""
    return {
        "subject": subject_id,
        "question_text": "新規問題",
        "problem_type": "single_choice",
        "difficulty": "easy",
        "explanation": "解説",
        "choices": [
            json.dumps({"text": "A", "is_correct": True}),
            json.dumps({"text": "B", "is_correct": False}),
        ],
    }


# ---- TC-AUTO-01: 非admin は参照系（list/retrieve）で 403 ----
@pytest.mark.django_db
def test_non_admin_cannot_read(setup):
    client = APIClient()
    client.force_authenticate(user=setup["normal"])
    pid = setup["problem"].id
    assert client.get("/api/problems/").status_code == 403
    assert client.get(f"/api/problems/{pid}/").status_code == 403


# ---- TC-AUTO-02: 非admin は更新系・AI生成・画像で 403 ----
@pytest.mark.django_db
def test_non_admin_cannot_mutate(setup, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup["normal"])
    pid = setup["problem"].id
    sid = setup["subject"].id
    assert client.post("/api/problems/", _valid_payload(sid), format="multipart").status_code == 403
    assert client.put(f"/api/problems/{pid}/", _valid_payload(sid), format="multipart").status_code == 403
    assert client.patch(f"/api/problems/{pid}/", {"explanation": "x"}, format="multipart").status_code == 403
    assert client.delete(f"/api/problems/{pid}/").status_code == 403
    assert client.post("/api/problems/generate_ai/", {}, format="json").status_code == 403
    assert client.post("/api/problems/generate_adaptive/", {}, format="json").status_code == 403
    assert client.post(f"/api/problems/{pid}/images/upload/", {}, format="multipart").status_code == 403
    assert client.delete(
        f"/api/problems/{pid}/images/delete/{DUMMY_ASSET_ID}/"
    ).status_code == 403
    # 認可で弾かれるため副作用が起きていないこと
    assert not Problem.objects.filter(question="新規問題").exists()


# ---- TC-AUTO-02b: 未認証（匿名）は 401 ----
@pytest.mark.django_db
def test_anonymous_gets_401(setup):
    client = APIClient()
    assert client.get("/api/problems/").status_code == 401


# ---- TC-AUTO-03: admin は参照・CRUD を従来どおり実行できる ----
@pytest.mark.django_db
def test_admin_can_read_and_crud(setup, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup["admin"])
    pid = setup["problem"].id
    sid = setup["subject"].id
    assert client.get("/api/problems/").status_code == 200
    assert client.get(f"/api/problems/{pid}/").status_code == 200
    create = client.post("/api/problems/", _valid_payload(sid), format="multipart")
    assert create.status_code == 201, create.content
    assert Problem.objects.filter(question="新規問題", is_deleted=False).exists()
    put = client.put(f"/api/problems/{pid}/", _valid_payload(sid), format="multipart")
    assert put.status_code == 200, put.content
    delete = client.delete(f"/api/problems/{pid}/")
    # ProblemViewSet は destroy() を override せず DRF 既定＝204（perform_destroy が論理削除）
    assert delete.status_code == 204


# ---- TC-AUTO-03b: admin はカスタムアクション（AI生成・画像）で 403 にならない ----
@pytest.mark.django_db
def test_admin_custom_actions_not_forbidden(setup, tmp_path, settings):
    """admin が全アクションで IsOrgAdmin を通過することを固定（AC2 の全アクションを明示）。
    AI生成/画像は入力不足で 400 になるが、重要なのは 403 でないこと（認可通過）。"""
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup["admin"])
    pid = setup["problem"].id
    assert client.post("/api/problems/generate_ai/", {}, format="json").status_code != 403
    assert client.post("/api/problems/generate_adaptive/", {}, format="json").status_code != 403
    assert client.post(f"/api/problems/{pid}/images/upload/", {}, format="multipart").status_code != 403
