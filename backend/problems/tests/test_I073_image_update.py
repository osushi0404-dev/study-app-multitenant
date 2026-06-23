"""
I073: 問題編集時の画像更新（追加・差し替え・削除・並び替え）の結合テスト。

PUT /api/problems/{id}/ への multipart 一括差分更新を起点に、
追加・差し替え・削除・並び替え・枚数上限・共有画像・テナント境界・
トランザクション原子性を検証する。

対応: docs/tests/open/I073_auto_test.md（TC-AUTO-00〜12）
"""
import io
import json
import os
import uuid

import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from accounts.models import Organization, OrganizationCategory
from problems.models import (
    Subject, Problem, Choice, MediaAsset, ProblemMediaAsset,
)

User = get_user_model()


# ---- ヘルパ ----------------------------------------------------------------

def png_bytes(size=(10, 10), color=(120, 180, 60)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def png_upload(name, size=(10, 10)):
    return SimpleUploadedFile(name, png_bytes(size), content_type="image/png")


def ensure_dirs(media_root, org, subject):
    for kind in ("problem", "explanation"):
        os.makedirs(
            os.path.join(media_root, "org", org.slug, "subjects", subject.slug, kind),
            exist_ok=True,
        )


def make_asset_with_link(media_root, org, subject, problem, usage_kind, position,
                         filename):
    """既存画像（MediaAsset + 物理ファイル + ProblemMediaAsset link）を直接生成。"""
    asset_id = uuid.uuid4()
    storage_key = (
        f"org/{org.slug}/subjects/{subject.slug}/{usage_kind}/{asset_id}.png"
    )
    full = os.path.join(media_root, storage_key)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(png_bytes())
    asset = MediaAsset.objects.create(
        id=asset_id,
        organization=org,
        subject=subject,
        usage_kind=usage_kind,
        storage_key=storage_key,
        original_filename=filename,
        mime_type="image/png",
        file_size_bytes=100,
        checksum_sha256="x" * 64,
    )
    ProblemMediaAsset.objects.create(
        organization=org,
        problem=problem,
        asset=asset,
        usage_kind=usage_kind,
        position=position,
    )
    return asset


def make_problem(org, subject, user, question="Q?", explanation="exp"):
    p = Problem.objects.create(
        subject=subject,
        organization=org,
        created_by=user,
        question=question,
        problem_type="single",
        difficulty=1,
        explanation=explanation,
    )
    Choice.objects.create(problem=p, text="A", is_correct=True, order=0)
    Choice.objects.create(problem=p, text="B", is_correct=False, order=1)
    return p


def active_links(problem, usage_kind):
    return list(
        ProblemMediaAsset.objects.filter(
            problem=problem, usage_kind=usage_kind, is_deleted=False
        ).order_by("position")
    )


def put_payload(subject, question="Q?", explanation="exp", **extra):
    data = {
        "subject": subject.id,
        "question": question,
        "problem_type": "single",
        "difficulty": 1,
        "explanation": explanation,
    }
    data.update(extra)
    return data


def file_exists(media_root, asset):
    return os.path.exists(os.path.join(media_root, asset.storage_key))


# ---- フィクスチャ ----------------------------------------------------------

@pytest.fixture
def category(db):
    return OrganizationCategory.objects.create(name="cat", slug="cat")


@pytest.fixture
def env(db, category, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    org = Organization.objects.create(name="org1", slug="org1", category=category)
    org2 = Organization.objects.create(name="org2", slug="org2", category=category)
    user = User.objects.create_user(
        email="u1@example.com", user_id="u1", password="p", organization=org,
        role="user",
    )
    user2 = User.objects.create_user(
        email="u2@example.com", user_id="u2", password="p", organization=org2,
        role="user",
    )
    subject = Subject.objects.create(name="s1", slug="s1", organization=org)
    subject2 = Subject.objects.create(name="s2", slug="s2", organization=org2)
    ensure_dirs(str(tmp_path), org, subject)
    ensure_dirs(str(tmp_path), org2, subject2)
    client = APIClient()
    client.force_authenticate(user=user)
    return {
        "media_root": str(tmp_path), "org": org, "org2": org2,
        "user": user, "user2": user2, "subject": subject, "subject2": subject2,
        "client": client,
    }


# ---- TC-AUTO-00: 作成フロー回帰 -------------------------------------------

@pytest.mark.django_db
def test_create_with_images_regression(env):
    """_process_images リファクタ後も作成時画像が従来通り作られる。"""
    data = {
        "subject": env["subject"].id,
        "question": "新規問題",
        "problem_type": "single",
        "difficulty": 1,
        "explanation": "解説",
        "choices": [json.dumps({"text": "A", "is_correct": True}),
                    json.dumps({"text": "B", "is_correct": False})],
        "question_image_1": png_upload("c1.png"),
        "question_image_2": png_upload("c2.png"),
    }
    resp = env["client"].post("/api/problems/", data, format="multipart")
    assert resp.status_code == 201, resp.content
    problem = Problem.objects.get(question="新規問題")
    links = active_links(problem, "problem")
    assert [link.position for link in links] == [1, 2]
    assert MediaAsset.objects.filter(subject=env["subject"],
                                     usage_kind="problem").count() == 2
    for link in links:
        assert file_exists(env["media_root"], link.asset)


# ---- TC-AUTO-01: 追加 ------------------------------------------------------

@pytest.mark.django_db
def test_add_image_to_existing(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    data = put_payload(
        env["subject"],
        question_images_order=json.dumps(
            [{"existing": str(a.id)}, {"new": "question_image_1"}]),
        question_image_1=png_upload("new_b.png"),
    )
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    links = active_links(problem, "problem")
    assert [link.position for link in links] == [1, 2]
    assert str(links[0].asset_id) == str(a.id)
    # 新規 B が pos2
    assert links[1].asset.original_filename == "new_b.png"


# ---- TC-AUTO-02: order 非送信 → 無変更 ------------------------------------

@pytest.mark.django_db
def test_text_only_edit_keeps_images(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    b = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 2, "b.png")
    data = put_payload(env["subject"], question="変更後の問題文")
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    problem.refresh_from_db()
    assert problem.question == "変更後の問題文"
    links = active_links(problem, "problem")
    assert {str(link.asset_id) for link in links} == {str(a.id), str(b.id)}


# ---- TC-AUTO-03: 空配列 → 全削除 -----------------------------------------

@pytest.mark.django_db
def test_empty_order_removes_all(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    b = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 2, "b.png")
    data = put_payload(env["subject"], question_images_order=json.dumps([]))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    assert active_links(problem, "problem") == []
    for asset in (a, b):
        asset.refresh_from_db()
        assert asset.is_deleted is True
        assert not file_exists(env["media_root"], asset)


# ---- TC-AUTO-04: 並び替え -------------------------------------------------

@pytest.mark.django_db
def test_reorder(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    b = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 2, "b.png")
    c = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 3, "c.png")
    data = put_payload(env["subject"], question_images_order=json.dumps(
        [{"existing": str(c.id)}, {"existing": str(a.id)}, {"existing": str(b.id)}]))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    links = active_links(problem, "problem")
    assert [(str(link.asset_id), link.position) for link in links] == [
        (str(c.id), 1), (str(a.id), 2), (str(b.id), 3)]
    # 物理・MediaAsset は削除されない
    for asset in (a, b, c):
        asset.refresh_from_db()
        assert asset.is_deleted is False
        assert file_exists(env["media_root"], asset)


# ---- TC-AUTO-05: 共有画像の削除は紐づけ解除のみ ----------------------------

@pytest.mark.django_db
def test_shared_asset_only_unlinked(env):
    problem1 = make_problem(env["org"], env["subject"], env["user"], question="p1")
    problem2 = make_problem(env["org"], env["subject"], env["user"], question="p2")
    shared = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                                  problem1, "problem", 1, "shared.png")
    # 同一アセットを problem2 にも紐づけ（共有）
    ProblemMediaAsset.objects.create(
        organization=env["org"], problem=problem2, asset=shared,
        usage_kind="problem", position=1)
    data = put_payload(env["subject"], question_images_order=json.dumps([]))
    resp = env["client"].put(f"/api/problems/{problem1.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    assert active_links(problem1, "problem") == []
    shared.refresh_from_db()
    assert shared.is_deleted is False          # 共有のため論理削除しない
    assert file_exists(env["media_root"], shared)  # 物理ファイル残存
    # problem2 からは引き続き取得可能
    assert [str(link.asset_id) for link in active_links(problem2, "problem")] == [
        str(shared.id)]


# ---- TC-AUTO-06: 他組織は 404 ---------------------------------------------

@pytest.mark.django_db
def test_other_org_cannot_edit(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    make_asset_with_link(env["media_root"], env["org"], env["subject"],
                         problem, "problem", 1, "a.png")
    other = APIClient()
    other.force_authenticate(user=env["user2"])
    data = put_payload(env["subject"], question_images_order=json.dumps([]))
    resp = other.put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 404
    assert len(active_links(problem, "problem")) == 1  # 不変


# ---- TC-AUTO-07: atomic（新規保存失敗・物理削除遅延） ---------------------

@pytest.mark.django_db
def test_atomic_invalid_new_file_keeps_everything(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    b = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 2, "b.png")
    bad = SimpleUploadedFile("bad.png", b"not an image", content_type="image/png")
    # B を除外しつつ不正な新規ファイルを追加 → 失敗で全ロールバック
    data = put_payload(env["subject"], question_images_order=json.dumps(
        [{"existing": str(a.id)}, {"new": "question_image_1"}]),
        question_image_1=bad)
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 400, resp.content
    # DB・物理ともに元のまま（B も消えていない＝物理削除に到達していない）
    links = active_links(problem, "problem")
    assert {str(link.asset_id) for link in links} == {str(a.id), str(b.id)}
    for asset in (a, b):
        asset.refresh_from_db()
        assert asset.is_deleted is False
        assert file_exists(env["media_root"], asset)


# ---- TC-AUTO-08: 不正 order → 全ロールバック ------------------------------

@pytest.mark.django_db
def test_over_limit_order_rejected(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    order = [{"existing": str(a.id)}] + [{"new": f"question_image_{i}"} for i in range(1, 6)]
    data = put_payload(env["subject"], question_images_order=json.dumps(order))
    for i in range(1, 6):
        data[f"question_image_{i}"] = png_upload(f"x{i}.png")
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 400, resp.content
    # 画像不変
    assert [str(link.asset_id) for link in active_links(problem, "problem")] == [str(a.id)]


@pytest.mark.django_db
def test_invalid_json_order_rejected(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    data = put_payload(env["subject"], question_images_order="{not json")
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 400, resp.content
    assert [str(link.asset_id) for link in active_links(problem, "problem")] == [str(a.id)]


# ---- TC-AUTO-09: 他問題アセットの混入を拒否 -------------------------------

@pytest.mark.django_db
def test_cross_problem_asset_rejected(env):
    problem1 = make_problem(env["org"], env["subject"], env["user"], question="p1")
    problem2 = make_problem(env["org"], env["subject"], env["user"], question="p2")
    other_asset = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                                       problem2, "problem", 1, "p2.png")
    data = put_payload(env["subject"], question_images_order=json.dumps(
        [{"existing": str(other_asset.id)}]))
    resp = env["client"].put(f"/api/problems/{problem1.id}/", data, format="multipart")
    assert resp.status_code == 400, resp.content
    assert active_links(problem1, "problem") == []  # problem1 は不変（元々0枚）


# ---- TC-AUTO-10: 解説画像でも機能 -----------------------------------------

@pytest.mark.django_db
def test_explanation_images(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "explanation", 1, "ea.png")
    # 追加: 既存 A + 新規 B（problem 種別は未送信＝不変であることも確認）
    qa = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                              problem, "problem", 1, "qa.png")
    data = put_payload(env["subject"], explanation_images_order=json.dumps(
        [{"existing": str(a.id)}, {"new": "explanation_image_1"}]),
        explanation_image_1=png_upload("eb.png"))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    elinks = active_links(problem, "explanation")
    assert [link.position for link in elinks] == [1, 2]
    assert str(elinks[0].asset_id) == str(a.id)
    # problem 種別は不変
    assert [str(link.asset_id) for link in active_links(problem, "problem")] == [str(qa.id)]


# ---- TC-AUTO-10b: 解説画像の削除・並び替え（AC#5 完全性） ----------------

@pytest.mark.django_db
def test_explanation_delete_and_reorder(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "explanation", 1, "ea.png")
    b = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "explanation", 2, "eb.png")
    c = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "explanation", 3, "ec.png")
    # 並び替え [A,B,C] -> [C,A,B]
    data = put_payload(env["subject"], explanation_images_order=json.dumps(
        [{"existing": str(c.id)}, {"existing": str(a.id)}, {"existing": str(b.id)}]))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    links = active_links(problem, "explanation")
    assert [(str(link.asset_id), link.position) for link in links] == [
        (str(c.id), 1), (str(a.id), 2), (str(b.id), 3)]
    # 全削除
    data = put_payload(env["subject"], explanation_images_order=json.dumps([]))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    assert active_links(problem, "explanation") == []
    for asset in (a, b, c):
        asset.refresh_from_db()
        assert asset.is_deleted is True
        assert not file_exists(env["media_root"], asset)


# ---- TC-AUTO-13: 同一既存UUID重複指定を拒否（unique違反の500を防止） --------

@pytest.mark.django_db
def test_duplicate_existing_rejected(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    data = put_payload(env["subject"], question_images_order=json.dumps(
        [{"existing": str(a.id)}, {"existing": str(a.id)}]))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 400, resp.content
    assert [str(link.asset_id) for link in active_links(problem, "problem")] == [str(a.id)]


# ---- TC-AUTO-14: existing/new 同時指定を拒否 -------------------------------

@pytest.mark.django_db
def test_both_keys_entry_rejected(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    data = put_payload(env["subject"], question_images_order=json.dumps(
        [{"existing": str(a.id), "new": "question_image_1"}]),
        question_image_1=png_upload("x.png"))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 400, resp.content
    assert [str(link.asset_id) for link in active_links(problem, "problem")] == [str(a.id)]


# ---- TC-AUTO-11: 差し替え（existing/new 混在で B→C） ----------------------

@pytest.mark.django_db
def test_replace_image(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    a = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 1, "a.png")
    b = make_asset_with_link(env["media_root"], env["org"], env["subject"],
                             problem, "problem", 2, "b.png")
    data = put_payload(env["subject"], question_images_order=json.dumps(
        [{"existing": str(a.id)}, {"new": "question_image_1"}]),
        question_image_1=png_upload("c.png"))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 200, resp.content
    links = active_links(problem, "problem")
    assert [link.position for link in links] == [1, 2]
    assert str(links[0].asset_id) == str(a.id)
    assert links[1].asset.original_filename == "c.png"
    # B は紐づけ解除＋（非共有のため）論理削除＋物理削除
    b.refresh_from_db()
    assert b.is_deleted is True
    assert not file_exists(env["media_root"], b)


# ---- TC-AUTO-12: 越境 subject 付け替えを拒否（SEC-1） ----------------------

@pytest.mark.django_db
def test_cross_org_subject_rejected(env):
    problem = make_problem(env["org"], env["subject"], env["user"])
    data = put_payload(env["subject2"],  # org2 の subject へ付け替え
                       question_images_order=json.dumps([{"new": "question_image_1"}]),
                       question_image_1=png_upload("x.png"))
    resp = env["client"].put(f"/api/problems/{problem.id}/", data, format="multipart")
    assert resp.status_code == 400, resp.content
    problem.refresh_from_db()
    assert problem.subject_id == env["subject"].id  # 不変
    # org2 ディレクトリに新規ファイルが書かれていない
    org2_dir = os.path.join(env["media_root"], "org", env["org2"].slug,
                            "subjects", env["subject2"].slug, "problem")
    assert not os.path.exists(org2_dir) or os.listdir(org2_dir) == []
