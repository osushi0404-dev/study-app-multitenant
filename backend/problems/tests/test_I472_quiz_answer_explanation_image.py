"""
I472: 解説画像がある問題へのクイズの回答で 500 にならず、保存されたのに 500 になる状態も無い。

- 古い形式の解説画像（explanation_image はファイル名）の URL は get_explanation_image_url() で作る
- 新しい形式の解説画像（MediaAsset）を応答の explanation_images に表示順で入れる
- 応答の組み立てに失敗したら、回答・回の集計・復習の予定を残さない

TC-01〜TC-05（docs/tests/open/I472_auto_test.md）に対応。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import (
    Choice, MediaAsset, Problem, ProblemMediaAsset, QuizAnswer, QuizSession, Subject,
)
from problems.serializers import (
    AnswerExplanationSerializer, ProblemDisplaySerializer, ProblemSerializer,
    QuizSessionSerializer,
)
from studylogs.models import SpacedRepetitionCard, SpacedRepetitionReview

User = get_user_model()

QUIZ_URL = "/api/quiz/"
EXPLANATION_DIR = "/media/org/org-i472-a/subjects/subj-i472/explanation"
RESPONSE_KEYS = {
    "is_correct", "explanation", "explanation_image", "explanation_images",
    "correct_choices", "session_complete", "session", "session_stats",
}
MEDIA_ASSET_KEYS = {
    "id", "url", "usage_kind", "original_filename", "mime_type", "file_size_bytes", "created_at",
}


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI472", slug="test-cat-i472")
    org = Organization.objects.create(
        name="組織I472A", slug="org-i472-a", type="school", category=cat, is_active=True)
    user = User.objects.create_user(
        email="a_i472@example.com", user_id="a_i472", password="pass",
        organization=org, role="user",
    )
    subject = Subject.objects.create(name="科目I472", slug="subj-i472", organization=org)
    problem = Problem.objects.create(
        subject=subject, organization=org, created_by=user,
        question="I472の問題", problem_type="single", difficulty=1,
        explanation="I472の解説",
    )
    correct = Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    return {"org": org, "user": user, "subject": subject, "problem": problem, "correct": correct}


def _link_asset(setup, usage_kind, position, name):
    asset = MediaAsset.objects.create(
        organization=setup["org"], subject=setup["subject"], usage_kind=usage_kind,
        storage_key=f"org/org-i472-a/subjects/subj-i472/{usage_kind}/{name}",
        original_filename=name, mime_type="image/png", file_size_bytes=100,
    )
    ProblemMediaAsset.objects.create(
        organization=setup["org"], problem=setup["problem"], asset=asset,
        usage_kind=usage_kind, position=position,
    )
    return asset


def _client(user, raise_request_exception=True):
    client = APIClient(raise_request_exception=raise_request_exception)
    client.force_authenticate(user=user)
    return client


def _start_session(client, subject):
    response = client.post(QUIZ_URL, {"subject": subject.id}, format="json")
    assert response.status_code == 201
    return response.json()["id"]


def _answer(client, session_id, setup):
    return client.post(
        f"{QUIZ_URL}{session_id}/submit_answer/",
        {"problem_id": setup["problem"].id, "selected_choice_ids": [setup["correct"].id]},
        format="json",
    )


# ---- TC-01: 古い形式の解説画像がある問題への回答は 200・URL は get_explanation_image_url() ----
def test_legacy_explanation_image_returns_200(setup):
    problem = setup["problem"]
    problem.explanation_image = "sample.png"
    problem.save()
    client = _client(setup["user"])
    session_id = _start_session(client, setup["subject"])

    response = _answer(client, session_id, setup)

    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is True
    assert body["explanation_image"] == f"{EXPLANATION_DIR}/sample.png"
    assert body["explanation_image"] == problem.get_explanation_image_url()
    assert body["explanation_images"] == []
    assert QuizAnswer.objects.filter(session_id=session_id).count() == 1
    assert QuizSession.objects.get(id=session_id).completed_problems == 1


# ---- TC-02: 新しい形式の解説画像が表示順で応答に入る（問題用は入らない） ----
def test_new_format_explanation_images(setup):
    problem = setup["problem"]
    problem.explanation_image = "legacy.png"
    problem.save()
    second = _link_asset(setup, "explanation", 2, "e2.png")
    first = _link_asset(setup, "explanation", 1, "e1.png")
    _link_asset(setup, "problem", 1, "q1.png")
    client = _client(setup["user"])
    session_id = _start_session(client, setup["subject"])

    response = _answer(client, session_id, setup)

    assert response.status_code == 200
    body = response.json()
    images = body["explanation_images"]
    assert [image["id"] for image in images] == [str(first.id), str(second.id)]
    assert all(set(image) == MEDIA_ASSET_KEYS for image in images)
    assert [image["url"] for image in images] == [
        f"/media/{first.storage_key}", f"/media/{second.storage_key}"]
    assert {image["usage_kind"] for image in images} == {"explanation"}
    assert body["explanation_image"] == f"{EXPLANATION_DIR}/legacy.png"


# ---- TC-03: 画像の無い問題・応答のキー ----
def test_response_keys_without_images(setup):
    client = _client(setup["user"])
    session_id = _start_session(client, setup["subject"])

    response = _answer(client, session_id, setup)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == RESPONSE_KEYS
    assert body["explanation_image"] is None
    assert body["explanation_images"] == []
    assert body["explanation"] == "I472の解説"
    assert body["correct_choices"] == [{"id": setup["correct"].id, "text": "正解"}]
    assert body["session"]["completed_problems"] == 1
    assert body["session_stats"]["completed"] == 1


def _raise(*args, **kwargs):
    raise RuntimeError("I472: 応答の組み立ての失敗の注入")


# ---- TC-04: 応答の組み立てに失敗したら、回答・集計・復習の予定を残さない ----
@pytest.mark.parametrize("target", [
    (Problem, "get_explanation_image_url"),          # 組み立ての最初の欄（解説）
    (QuizSessionSerializer, "to_representation"),    # 組み立ての最後の欄（回）
])
def test_build_failure_leaves_nothing(setup, monkeypatch, target):
    user, problem = setup["user"], setup["problem"]
    client = _client(user, raise_request_exception=False)
    session_id = _start_session(client, setup["subject"])

    with monkeypatch.context() as patch:
        patch.setattr(*target, _raise)
        response = _answer(client, session_id, setup)

    assert response.status_code == 500
    assert QuizAnswer.objects.filter(session_id=session_id).count() == 0
    session = QuizSession.objects.get(id=session_id)
    assert session.completed_problems == 0
    assert session.correct_answers == 0
    assert SpacedRepetitionCard.objects.filter(user=user, problem=problem).count() == 0
    assert SpacedRepetitionReview.objects.filter(user=user, problem=problem).count() == 0

    retry = _answer(client, session_id, setup)
    assert retry.status_code == 200


# ---- TC-05: 新しい形式の画像の応答は、どの serializer でも用途ごと・表示順 ----
def test_serializers_share_media_assets(setup):
    problem = setup["problem"]
    q2 = _link_asset(setup, "problem", 2, "q2.png")
    q1 = _link_asset(setup, "problem", 1, "q1.png")
    e1 = _link_asset(setup, "explanation", 1, "e1.png")

    for serializer in (ProblemDisplaySerializer(problem), ProblemSerializer(problem)):
        data = serializer.data
        assert [image["id"] for image in data["question_images"]] == [str(q1.id), str(q2.id)]
        assert [image["id"] for image in data["explanation_images"]] == [str(e1.id)]
    assert (AnswerExplanationSerializer(problem).data["explanation_images"]
            == ProblemDisplaySerializer(problem).data["explanation_images"])
