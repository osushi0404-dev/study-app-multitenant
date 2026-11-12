"""
I103: 問題作成の越境 subject 書き込み防止の回帰テスト。

問題を作成する全3経路（perform_create / generate_ai / generate_adaptive）で、
他組織 subject への作成を、存在しない科目と同じ応答で拒否することを固定する
（I446 で 403 から変更: 作成は 400・AI 経路は 404。他組織に科目があることを知らせない）。

- 越境（org A admin × org B subject）→ 存在しない科目と同じ 400／404・Problem 未作成
- 自組織 → 従来どおり成功（create=201 / AI 経路は非403＝org 検証通過）

TC-AUTO-01〜05（docs/tests/open/I103_auto_test.md）に対応。
"""
import json
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from problems.models import Subject, Problem
from accounts.models import Organization, OrganizationCategory

User = get_user_model()

BODY_404_SUBJECT = {"error": "指定された科目が見つかりません"}


def _missing_subject_id():
    return Subject.objects.order_by("-id").first().id + 1000


def _masked(resp, pk):
    """応答本文の科目 ID を伏せた文字列（他組織と存在しない科目の応答を比べるため）"""
    return json.dumps(resp.json(), ensure_ascii=False).replace(str(pk), "<pk>")


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="I103", slug="cat-i103")
    org_a = Organization.objects.create(name="orgA_I103", slug="org-a-i103", category=cat)
    org_b = Organization.objects.create(name="orgB_I103", slug="org-b-i103", category=cat)
    admin_a = User.objects.create_user(
        email="admin_a_i103@example.com", user_id="admin_a_i103", password="pass",
        organization=org_a, role="admin",
    )
    subject_a = Subject.objects.create(name="subjA", slug="subj-a-i103", organization=org_a)
    subject_b = Subject.objects.create(name="subjB", slug="subj-b-i103", organization=org_b)
    return {"org_a": org_a, "org_b": org_b, "admin_a": admin_a,
            "subject_a": subject_a, "subject_b": subject_b}


def _valid_payload(subject_id, question="越境問題I103"):
    """multipart 作成用の有効なペイロード（choices は JSON 文字列リスト）。"""
    return {
        "subject": subject_id,
        "question_text": question,
        "problem_type": "single_choice",
        "difficulty": "easy",
        "explanation": "解説",
        "choices": [
            json.dumps({"text": "A", "is_correct": True}),
            json.dumps({"text": "B", "is_correct": False}),
        ],
    }


# ---- TC-AUTO-01: 越境 create=存在しない科目と同じ 400・Problem 未作成 ----
@pytest.mark.django_db
def test_cross_org_create_rejected(setup, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup["admin_a"])
    other_id = setup["subject_b"].id
    missing_id = _missing_subject_id()
    resp = client.post("/api/problems/", _valid_payload(other_id), format="multipart")
    missing = client.post("/api/problems/", _valid_payload(missing_id), format="multipart")
    assert resp.status_code == 400, resp.content
    assert missing.status_code == 400, missing.content
    assert _masked(resp, other_id) == _masked(missing, missing_id)
    assert not Problem.objects.filter(question="越境問題I103").exists()


# ---- TC-AUTO-02a: 越境 generate_ai=404（save_to_db 既定=True）・未作成 ----
# 注: ProblemViewSet は parser_classes=[MultiPartParser, FormParser]（JSON 非対応）。
#     json で送ると org チェック到達前に 415 になるため multipart で送る。
@pytest.mark.django_db
def test_cross_org_generate_ai_rejected(setup):
    client = APIClient()
    client.force_authenticate(user=setup["admin_a"])
    resp = client.post(
        "/api/problems/generate_ai/", {"subject_id": setup["subject_b"].id}, format="multipart"
    )
    assert resp.status_code == 404, resp.content
    assert resp.json() == BODY_404_SUBJECT
    assert Problem.objects.filter(subject=setup["subject_b"]).count() == 0


# ---- TC-AUTO-02b: 越境 generate_ai=404（save_to_db=False でも一律） ----
@pytest.mark.django_db
def test_cross_org_generate_ai_rejected_no_save(setup):
    client = APIClient()
    client.force_authenticate(user=setup["admin_a"])
    resp = client.post(
        "/api/problems/generate_ai/",
        {"subject_id": setup["subject_b"].id, "save_to_db": False},
        format="multipart",
    )
    assert resp.status_code == 404, resp.content
    assert resp.json() == BODY_404_SUBJECT


# ---- TC-AUTO-03: 越境 generate_adaptive=404・未作成 ----
@pytest.mark.django_db
def test_cross_org_generate_adaptive_rejected(setup):
    client = APIClient()
    client.force_authenticate(user=setup["admin_a"])
    resp = client.post(
        "/api/problems/generate_adaptive/",
        {"subject_id": setup["subject_b"].id},
        format="multipart",
    )
    assert resp.status_code == 404, resp.content
    assert resp.json() == BODY_404_SUBJECT
    assert Problem.objects.filter(subject=setup["subject_b"]).count() == 0


# ---- TC-AUTO-04: 自組織 create=201（正常系不変） ----
@pytest.mark.django_db
def test_same_org_create_succeeds(setup, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    client.force_authenticate(user=setup["admin_a"])
    resp = client.post(
        "/api/problems/",
        _valid_payload(setup["subject_a"].id, question="自組織問題I103"),
        format="multipart",
    )
    assert resp.status_code == 201, resp.content
    assert Problem.objects.filter(question="自組織問題I103", is_deleted=False).exists()


# ---- TC-AUTO-05: 自組織 AI 経路は非403（認可・org 検証通過） ----
@pytest.mark.django_db
def test_same_org_ai_paths_not_forbidden(setup):
    """自組織 subject では org 検証を通過し生成処理へ進む（AI 未設定で 400/500 になり得るが 403 でないことが要点）。"""
    client = APIClient()
    client.force_authenticate(user=setup["admin_a"])
    ai = client.post(
        "/api/problems/generate_ai/", {"subject_id": setup["subject_a"].id}, format="multipart"
    )
    adaptive = client.post(
        "/api/problems/generate_adaptive/", {"subject_id": setup["subject_a"].id}, format="multipart"
    )
    assert ai.status_code != 403, ai.content
    assert adaptive.status_code != 403, adaptive.content
