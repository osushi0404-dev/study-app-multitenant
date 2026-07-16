"""
I078: is_correct の露出分離テスト（答え漏洩リグレッション防止）。

- 管理経路（ProblemViewSet・I102 で admin 限定）: is_correct を返す（読み書き両可）
- 出題経路（next_problem・ProblemDisplaySerializer）: 返さない
- 結果経路（QuizAnswerDetailSerializer の problem / selected_choices）: 返さない
- AI 生成応答が直接使う ProblemSerializer / ChoiceSerializer（単体）: 返さない

TC-AUTO-01〜07（docs/tests/open/I078_auto_test.md）に対応。
"""
import json
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from problems.models import Subject, Problem, Choice, QuizSession, QuizAnswer
from problems.serializers import ProblemSerializer, ChoiceSerializer
from accounts.models import Organization, OrganizationCategory

User = get_user_model()


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="I078", slug="cat-i078")
    org = Organization.objects.create(name="org_I078", slug="org-i078", category=cat)
    admin = User.objects.create_user(
        email="admin_i078@example.com", user_id="admin_i078", password="pass",
        organization=org, role="admin",
    )
    normal = User.objects.create_user(
        email="user_i078@example.com", user_id="user_i078", password="pass",
        organization=org, role="user",
    )
    subject = Subject.objects.create(name="科目I078", slug="subj-i078", organization=org)
    problem = Problem.objects.create(
        subject=subject, organization=org, created_by=admin, question="問題I078",
        problem_type="single", difficulty=1, explanation="解説",
    )
    correct = Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    wrong = Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    # 出題・結果経路用（TC-AUTO-05/06）: normal ユーザーのセッションと回答。
    # 回答済み1問のみでも next_problem は復習モードのフォールバック
    # （quiz_service.py）により決定論的に 200 で同問題を返す。
    session = QuizSession.objects.create(user=normal, subject=subject, is_active=True)
    answer = QuizAnswer.objects.create(session=session, problem=problem, time_taken=0)
    answer.selected_choices.set([correct])
    return {
        "org": org, "admin": admin, "normal": normal, "subject": subject,
        "problem": problem, "correct": correct, "wrong": wrong,
        "session": session, "answer": answer,
    }


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _valid_payload(subject_id, question="新規問題I078"):
    """multipart 作成/更新用の有効なペイロード（choices は JSON 文字列リスト）。"""
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


# ---- TC-AUTO-01: 管理 list で is_correct 露出 ----
@pytest.mark.django_db
def test_admin_list_exposes_is_correct(setup):
    client = _client(setup["admin"])
    res = client.get("/api/problems/")
    assert res.status_code == 200
    data = res.json()
    target = next((p for p in data if p["id"] == setup["problem"].id), None)
    assert target is not None
    assert len(target["choices"]) == 2
    assert all("is_correct" in c for c in target["choices"])
    by_text = {c["text"]: c["is_correct"] for c in target["choices"]}
    assert by_text["正解"] is True
    assert by_text["不正解"] is False


# ---- TC-AUTO-02: 管理 retrieve で is_correct 露出 ----
@pytest.mark.django_db
def test_admin_retrieve_exposes_is_correct(setup):
    client = _client(setup["admin"])
    res = client.get(f"/api/problems/{setup['problem'].id}/")
    assert res.status_code == 200
    choices = res.json()["choices"]
    assert len(choices) == 2
    assert all("is_correct" in c for c in choices)
    by_text = {c["text"]: c["is_correct"] for c in choices}
    assert by_text["正解"] is True
    assert by_text["不正解"] is False


# ---- TC-AUTO-03: create の読み書き両可 ----
@pytest.mark.django_db
def test_admin_create_returns_and_saves_is_correct(setup, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = _client(setup["admin"])
    res = client.post("/api/problems/", _valid_payload(setup["subject"].id))
    assert res.status_code == 201
    body = res.json()
    assert all("is_correct" in c for c in body["choices"])
    by_text = {c["text"]: c["is_correct"] for c in body["choices"]}
    assert by_text["A"] is True
    assert by_text["B"] is False
    # DB 保存も従来どおり
    assert Choice.objects.get(problem_id=body["id"], text="A").is_correct is True
    assert Choice.objects.get(problem_id=body["id"], text="B").is_correct is False


# ---- TC-AUTO-04: 正解保持（テキストのみ編集・FE の編集保存と同型） ----
@pytest.mark.django_db
def test_admin_update_preserves_is_correct(setup, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client = _client(setup["admin"])
    pid = setup["problem"].id
    payload = _valid_payload(setup["subject"].id, question="編集後の問題I078")
    # FE と同型: 取得値どおりの choices（is_correct 付き）を再送
    payload["choices"] = [
        json.dumps({"text": "正解", "is_correct": True}),
        json.dumps({"text": "不正解", "is_correct": False}),
    ]
    res = client.put(f"/api/problems/{pid}/", payload)
    assert res.status_code == 200
    body = res.json()
    assert all("is_correct" in c for c in body["choices"])
    # 正解の取り違えが起きていない
    assert Choice.objects.filter(problem_id=pid, text="正解", is_correct=True).exists()
    assert not Choice.objects.filter(problem_id=pid, text="不正解", is_correct=True).exists()
    assert Choice.objects.filter(problem_id=pid, is_correct=True).count() == 1


# ---- TC-AUTO-05: 出題経路の非露出（回帰） ----
@pytest.mark.django_db
def test_next_problem_does_not_expose_is_correct(setup):
    client = _client(setup["normal"])
    res = client.get(f"/api/quiz/{setup['session'].id}/next_problem/")
    assert res.status_code == 200
    choices = res.json()["choices"]
    assert len(choices) > 0  # 空リストでの見せかけ合格を防ぐ
    assert all("is_correct" not in c for c in choices)


# ---- TC-AUTO-06: 結果経路の非露出（回帰） ----
@pytest.mark.django_db
def test_session_detail_does_not_expose_is_correct(setup):
    client = _client(setup["normal"])
    res = client.get(f"/api/quiz/{setup['session'].id}/")
    assert res.status_code == 200
    answers = res.json()["answers"]
    assert len(answers) > 0  # 空リストでの見せかけ合格を防ぐ
    for answer in answers:
        problem_choices = answer["problem"]["choices"]
        assert len(problem_choices) > 0
        assert all("is_correct" not in c for c in problem_choices)
        assert len(answer["selected_choices"]) > 0
        assert all("is_correct" not in c for c in answer["selected_choices"])


# ---- TC-AUTO-07: AI 応答が使う ProblemSerializer の非露出（単体・回帰） ----
@pytest.mark.django_db
def test_problem_serializer_does_not_expose_is_correct(setup):
    # generate_ai / generate_adaptive の応答は ProblemSerializer を直接使用する
    # （views.py）。ここで非露出を固定することで AI 応答経路を構造的に担保する。
    data = ProblemSerializer(setup["problem"]).data
    assert len(data["choices"]) == 2
    assert all("is_correct" not in c for c in data["choices"])
    assert "is_correct" not in ChoiceSerializer(setup["correct"]).data
