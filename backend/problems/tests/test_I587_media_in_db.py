"""
I587: 問題・解説の画像の中身を DB に保存し、組織の境界を確かめる API（GET /api/media/<id>/）から返す。

TC-01・TC-02・TC-04〜TC-11・TC-19・TC-23（docs/tests/open/I587_auto_test.md）に対応。
"""
import builtins
import hashlib
import importlib
import io
import json
import os
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import Resolver404, clear_url_caches, resolve
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from core.cache_service import cache_service
from problems.models import (
    Choice, MediaAsset, MediaAssetContent, Problem, ProblemMediaAsset, Subject,
)

User = get_user_model()

CONTENT_TABLE = "media_asset_contents"
LEGACY_KEYS = {"question_image", "explanation_image"}


def image_bytes(color=(10, 20, 30), fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format=fmt)
    return buf.getvalue()


PNG = image_bytes()
PNG2 = image_bytes((200, 100, 50))


def upload(name, data=PNG, content_type="image/png"):
    return SimpleUploadedFile(name, data, content_type=content_type)


def media_url(asset):
    return f"/api/media/{asset.id}/"


def client_for(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


@pytest.fixture
def world(db):
    cat = OrganizationCategory.objects.create(name="I587", slug="cat-i587")
    org_a = Organization.objects.create(name="組織A587", slug="org-a587", category=cat)
    org_b = Organization.objects.create(name="組織B587", slug="org-b587", category=cat)
    subj_a = Subject.objects.create(name="科目A587", slug="subj-a587", organization=org_a)
    subj_b = Subject.objects.create(name="科目B587", slug="subj-b587", organization=org_b)

    def user(name, org, role="user"):
        return User.objects.create_user(
            email=f"{name}@example.com", user_id=name, password="p",
            organization=org, role=role)

    return {
        "org_a": org_a, "org_b": org_b, "subj_a": subj_a, "subj_b": subj_b,
        "admin_a": user("admin_a587", org_a, "admin"),
        "learner_a": user("learner_a587", org_a),
        "admin_b": user("admin_b587", org_b, "admin"),
        "orphan": user("orphan587", None),
    }


@pytest.fixture
def no_file_writes(monkeypatch):
    """書き込みのモードの open と os.makedirs を記録する（I587: 画像をファイルに書かない）"""
    calls = []
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            calls.append(str(file))
        return real_open(file, mode, *args, **kwargs)

    def guarded_makedirs(name, *args, **kwargs):
        calls.append(str(name))

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(os, "makedirs", guarded_makedirs)
    return calls


def make_problem(world, subject=None):
    subject = subject or world["subj_a"]
    problem = Problem.objects.create(
        subject=subject, organization=subject.organization,
        created_by=world["admin_a"], question="I587の問題", problem_type="single",
        difficulty=1, explanation="I587の解説")
    correct = Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    return problem, correct


def make_asset(world, *, problem=None, usage_kind="problem", position=1, data=PNG,
               org="default", subject="default", content=True):
    org = world["org_a"] if org == "default" else org
    subject = world["subj_a"] if subject == "default" else subject
    asset = MediaAsset.objects.create(
        organization=org, subject=subject, usage_kind=usage_kind,
        storage_key=f"org/x/subjects/y/{usage_kind}/{uuid.uuid4()}.png",
        original_filename="a.png", mime_type="image/png", file_size_bytes=len(data),
        checksum_sha256=hashlib.sha256(data).hexdigest())
    if content:
        MediaAssetContent.objects.create(asset=asset, data=data)
    if problem is not None:
        ProblemMediaAsset.objects.create(
            organization=problem.organization, problem=problem, asset=asset,
            usage_kind=usage_kind, position=position)
    return asset


def content_sqls(context):
    return [q["sql"] for q in context.captured_queries if CONTENT_TABLE in q["sql"]]


def problem_payload(world, **extra):
    data = {
        "subject": world["subj_a"].id, "question": "Q587", "problem_type": "single",
        "difficulty": 1, "explanation": "E587",
        "choices": [json.dumps({"text": "A", "is_correct": True}),
                    json.dumps({"text": "B", "is_correct": False})],
    }
    data.update(extra)
    return data


# ---- TC-01: 登録・更新で中身が DB に入り、ファイルを書かない ----
def test_create_and_update_store_content_without_files(world, no_file_writes):
    client = client_for(world["admin_a"])
    created = client.post("/api/problems/", problem_payload(
        world, question_image_1=upload("q.png"), explanation_image_1=upload("e.png", PNG2)),
        format="multipart")
    assert created.status_code == 201, created.content
    problem = Problem.objects.get(id=created.json()["id"])
    assert MediaAssetContent.objects.filter(asset__problem_links__problem=problem).count() == 2
    for usage_kind, data in (("problem", PNG), ("explanation", PNG2)):
        asset = ProblemMediaAsset.objects.get(problem=problem, usage_kind=usage_kind).asset
        assert bytes(asset.content.data) == data
        assert asset.checksum_sha256 == hashlib.sha256(data).hexdigest()
        assert asset.file_size_bytes == len(data)
    old_question = ProblemMediaAsset.objects.get(problem=problem, usage_kind="problem").asset

    updated = client.patch(f"/api/problems/{problem.id}/", {
        "question_images_order": json.dumps([{"new": "question_image_9"}]),
        "question_image_9": upload("q9.png", PNG2),
    }, format="multipart")
    assert updated.status_code == 200, updated.content
    old_question.refresh_from_db()
    assert old_question.is_deleted is True
    assert not MediaAssetContent.objects.filter(asset=old_question).exists()
    new_question = ProblemMediaAsset.objects.get(problem=problem, usage_kind="problem").asset
    assert bytes(new_question.content.data) == PNG2
    assert MediaAssetContent.objects.filter(asset__problem_links__problem=problem).count() == 2
    assert no_file_writes == []


# ---- TC-02: 保存する MIME は中身から判定した値（送り手の content_type でない） ----
def test_create_stores_detected_mime_not_client_content_type(world):
    client = client_for(world["admin_a"])
    created = client.post("/api/problems/", problem_payload(
        world, question_image_1=upload("q.png", PNG, "text/html")), format="multipart")
    assert created.status_code == 201, created.content
    asset = ProblemMediaAsset.objects.get(problem_id=created.json()["id"]).asset
    assert asset.mime_type == "image/png"

    response = client.get(media_url(asset))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"


# ---- TC-04: 2 回目は 304（中身を読まない）・RFC 9110 の弱い比較・null の checksum は ETag なし ----
def test_media_etag_304_without_reading_content(world):
    asset = make_asset(world)
    client = client_for(world["learner_a"])
    first = client.get(media_url(asset))
    assert first.status_code == 200
    etag = first["ETag"]
    assert etag == f'"{hashlib.sha256(PNG).hexdigest()}"'

    with CaptureQueriesContext(connection) as context:
        second = client.get(media_url(asset), HTTP_IF_NONE_MATCH=etag)
    assert second.status_code == 304
    assert second.content == b""
    assert second["ETag"] == etag
    assert second["Cache-Control"] == "private, max-age=3600"
    assert content_sqls(context) == []

    # If-None-Match は弱い比較（RFC 9110）: W/ 付きも一致。一致しない値は 200
    assert client.get(media_url(asset), HTTP_IF_NONE_MATCH=f"W/{etag}").status_code == 304
    assert client.get(media_url(asset), HTTP_IF_NONE_MATCH='"x"').status_code == 200
    assert client.get(media_url(asset), HTTP_IF_NONE_MATCH=f'"x", {etag}').status_code == 304
    assert client.get(media_url(asset), HTTP_IF_NONE_MATCH="*").status_code == 304

    MediaAsset.objects.filter(id=asset.id).update(checksum_sha256=None)
    no_etag = client.get(media_url(asset), HTTP_IF_NONE_MATCH='"None"')
    assert no_etag.status_code == 200
    assert "ETag" not in no_etag


# ---- TC-05: 応答の見出し・許可の外の MIME は octet-stream ----
def test_media_response_headers(world):
    asset = make_asset(world)
    response = client_for(world["learner_a"]).get(media_url(asset))
    assert response.status_code == 200
    assert response.content == PNG
    assert response["Content-Type"] == "image/png"
    assert response["Cache-Control"] == "private, max-age=3600"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Content-Security-Policy"] == "default-src 'none'; sandbox"
    assert response["Content-Disposition"] == "inline"


def test_media_unknown_mime_is_octet_stream(world):
    asset = make_asset(world)
    MediaAsset.objects.filter(id=asset.id).update(mime_type="text/html")
    response = client_for(world["learner_a"]).get(media_url(asset))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/octet-stream"


# ---- TC-06: 未ログインは 401 ----
def test_media_requires_login(world):
    asset = make_asset(world)
    response = client_for().get(media_url(asset))
    assert response.status_code == 401
    assert "main_message" in response.json()["error"]


# ---- TC-07: 組織の境界（他の組織・論理削除・null・中身なし・無い ID・組織なし）は 404 ----
CASES = ["other_org", "deleted", "null_org", "null_subject", "no_content", "unknown",
         "no_org_user"]


@pytest.mark.parametrize("case", CASES)
def test_media_tenant_boundary(world, case):
    user = world["learner_a"]
    if case == "other_org":
        asset, user = make_asset(world), world["admin_b"]
    elif case == "deleted":
        asset = make_asset(world)
        MediaAsset.objects.filter(id=asset.id).update(is_deleted=True)
    elif case == "null_org":
        asset = make_asset(world, org=None)
    elif case == "null_subject":
        asset = make_asset(world, subject=None)
    elif case == "no_content":
        asset = make_asset(world, content=False)
    elif case == "unknown":
        asset = MediaAsset(id=uuid.uuid4())
    else:
        asset, user = make_asset(world), world["orphan"]
    response = client_for(user).get(media_url(asset))
    assert response.status_code == 404
    assert "main_message" in response.json()["error"]


def test_media_same_org_learner_gets_image(world):
    asset = make_asset(world)
    assert client_for(world["learner_a"]).get(media_url(asset)).status_code == 200


# ---- TC-08: 科目を作ってもフォルダを作らない ----
def test_create_subject_makes_no_folders(world, no_file_writes):
    response = client_for(world["admin_a"]).post(
        "/api/subjects/", {"name": "新科目587"}, format="json")
    assert response.status_code == 201
    assert no_file_writes == []


# ---- TC-09: images/upload も中身を DB に入れる・共通の検査（GIF は 400） ----
def test_upload_image_action_stores_content(world, no_file_writes):
    problem, _ = make_problem(world)
    client = client_for(world["admin_a"])
    url = f"/api/problems/{problem.id}/images/upload/"
    response = client.post(url, {"file": upload("u.png"), "usage_kind": "problem"},
                           format="multipart")
    assert response.status_code == 201, response.content
    asset = MediaAsset.objects.get(id=response.json()["id"])
    assert bytes(asset.content.data) == PNG
    assert response.json()["url"] == media_url(asset)
    assert ProblemMediaAsset.objects.get(asset=asset).position == 1
    assert no_file_writes == []

    before = MediaAsset.objects.count()
    gif = client.post(url, {"file": upload("g.gif", image_bytes(fmt="GIF"), "image/gif"),
                            "usage_kind": "problem"}, format="multipart")
    assert gif.status_code == 400
    assert "main_message" in gif.json()["error"]
    assert MediaAsset.objects.count() == before


# ---- TC-10: 論理削除で中身が消える（共有している画像は残る） ----
@pytest.mark.parametrize("how", ["delete_image", "empty_order", "delete_problem"])
def test_discard_removes_content(world, no_file_writes, how):
    problem, _ = make_problem(world)
    asset = make_asset(world, problem=problem)
    client = client_for(world["admin_a"])
    if how == "delete_image":
        response = client.delete(f"/api/problems/{problem.id}/images/delete/{asset.id}/")
    elif how == "empty_order":
        response = client.patch(f"/api/problems/{problem.id}/",
                                {"question_images_order": json.dumps([])}, format="multipart")
    else:
        response = client.delete(f"/api/problems/{problem.id}/")
    assert response.status_code in (200, 204), response.content
    asset.refresh_from_db()
    assert asset.is_deleted is True
    assert not MediaAssetContent.objects.filter(asset=asset).exists()
    assert no_file_writes == []


def test_delete_image_ignores_deleted_links_of_other_problems(world):
    """共有の相手の問題が論理削除済みなら、外した画像は中身ごと消える（fix-loop F1）"""
    problem, _ = make_problem(world)
    other, _ = make_problem(world)
    asset = make_asset(world, problem=problem)
    ProblemMediaAsset.objects.create(organization=world["org_a"], problem=other, asset=asset,
                                     usage_kind="problem", position=1, is_deleted=True)
    response = client_for(world["admin_a"]).delete(
        f"/api/problems/{problem.id}/images/delete/{asset.id}/")
    assert response.status_code == 200
    asset.refresh_from_db()
    assert asset.is_deleted is True
    assert not MediaAssetContent.objects.filter(asset=asset).exists()
    assert client_for(world["learner_a"]).get(media_url(asset)).status_code == 404


@pytest.mark.parametrize("case", ["no_file", "bad_usage_kind"])
def test_upload_image_action_rejects_bad_input(world, case):
    """入力の誤りは 400 で、本文は custom_exception_handler の形（追加の直し・F5）"""
    problem, _ = make_problem(world)
    data = {"usage_kind": "problem"} if case == "no_file" else {"file": upload("u.png"),
                                                                "usage_kind": "x"}
    before = MediaAsset.objects.count()
    response = client_for(world["admin_a"]).post(
        f"/api/problems/{problem.id}/images/upload/", data, format="multipart")
    assert response.status_code == 400
    assert "main_message" in response.json()["error"]
    assert MediaAsset.objects.count() == before


@pytest.mark.parametrize("case", ["not_linked", "deleted_own_link", "other_org_asset"])
def test_delete_image_rejects_missing_or_deleted_own_link(world, case):
    """自分の問題の、自分の組織の画像の有効な紐づけでなければ 404 で何も変えない（追加の直し・F5・F7）"""
    problem, _ = make_problem(world)
    if case == "not_linked":
        asset = make_asset(world)
    elif case == "deleted_own_link":
        asset = make_asset(world, problem=problem)
        ProblemMediaAsset.objects.filter(asset=asset).update(is_deleted=True)
    else:
        asset = make_asset(world, org=world["org_b"], subject=world["subj_b"])
        ProblemMediaAsset.objects.create(organization=world["org_a"], problem=problem,
                                         asset=asset, usage_kind="problem", position=1)
    links_before = ProblemMediaAsset.objects.filter(asset=asset).count()
    response = client_for(world["admin_a"]).delete(
        f"/api/problems/{problem.id}/images/delete/{asset.id}/")
    assert response.status_code == 404
    assert "main_message" in response.json()["error"]
    asset.refresh_from_db()
    assert asset.is_deleted is False
    assert MediaAssetContent.objects.filter(asset=asset).exists()
    assert ProblemMediaAsset.objects.filter(asset=asset).count() == links_before


def test_delete_image_route_accepts_only_uuid(world):
    """画像の ID は UUID の形だけを経路で受ける（形の違う値は 500 でなく 404）"""
    problem, _ = make_problem(world)
    response = client_for(world["admin_a"]).delete(
        f"/api/problems/{problem.id}/images/delete/not-a-uuid/")
    assert response.status_code == 404


def test_delete_problem_keeps_shared_content(world):
    problem, _ = make_problem(world)
    other, _ = make_problem(world)
    asset = make_asset(world, problem=problem)
    ProblemMediaAsset.objects.create(organization=world["org_a"], problem=other, asset=asset,
                                     usage_kind="problem", position=1)
    response = client_for(world["admin_a"]).delete(f"/api/problems/{problem.id}/")
    assert response.status_code == 204
    asset.refresh_from_db()
    assert asset.is_deleted is False
    assert MediaAssetContent.objects.filter(asset=asset).exists()


# ---- TC-11: 一覧・クイズの取得・回答で中身の表を読まない ----
def test_list_and_quiz_do_not_read_content(world):
    problem, correct = make_problem(world)
    question = make_asset(world, problem=problem, usage_kind="problem")
    explanation = make_asset(world, problem=problem, usage_kind="explanation", data=PNG2)
    cache_service.invalidate_problems_cache()

    admin = client_for(world["admin_a"])
    with CaptureQueriesContext(connection) as context:
        listed = admin.get("/api/problems/")
    assert listed.status_code == 200
    assert listed.json()[0]["question_images"][0]["url"] == media_url(question)
    assert content_sqls(context) == []

    learner = client_for(world["learner_a"])
    with CaptureQueriesContext(connection) as context:
        started = learner.post("/api/quiz/", {"subject": world["subj_a"].id}, format="json")
        session_id = started.json()["id"]
        shown = learner.get(f"/api/quiz/{session_id}/next_problem/")
        answered = learner.post(f"/api/quiz/{session_id}/submit_answer/", {
            "problem_id": problem.id, "selected_choice_ids": [correct.id]}, format="json")
    assert started.status_code == 201
    assert shown.status_code == 200
    assert shown.json()["question_images"][0]["url"] == media_url(question)
    assert answered.status_code == 200
    assert answered.json()["explanation_images"][0]["url"] == media_url(explanation)
    assert content_sqls(context) == []


# ---- TC-19: 応答に古い画像の項目が無い ----
def test_problem_payloads_have_no_legacy_image_fields(world):
    problem, correct = make_problem(world)
    cache_service.invalidate_problems_cache()
    listed = client_for(world["admin_a"]).get("/api/problems/").json()[0]
    learner = client_for(world["learner_a"])
    session_id = learner.post("/api/quiz/", {"subject": world["subj_a"].id},
                              format="json").json()["id"]
    shown = learner.get(f"/api/quiz/{session_id}/next_problem/").json()
    answered = learner.post(f"/api/quiz/{session_id}/submit_answer/", {
        "problem_id": problem.id, "selected_choice_ids": [correct.id]}, format="json").json()
    for body in (listed, shown, answered):
        assert not LEGACY_KEYS & set(body)
    assert {"question_images", "explanation_images"} <= set(listed)
    assert {"question_images", "explanation_images"} <= set(shown)
    assert "explanation_images" in answered


# ---- TC-23: /media/ の静的な配信の経路が無い ----
def test_media_static_route_is_gone(settings):
    import core.urls
    settings.DEBUG = True
    try:
        importlib.reload(core.urls)
        clear_url_caches()
        with pytest.raises(Resolver404):
            resolve("/media/org/x/a.png", urlconf=core.urls)
    finally:
        settings.DEBUG = False
        importlib.reload(core.urls)
        clear_url_caches()
