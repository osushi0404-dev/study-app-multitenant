"""
I590: I587 のレビューの残り（移行 0025 の判定の依存・配信の 304/412 の見出し・Subject.image_directory の削除）

TC-01〜TC-04（docs/tests/open/I590_auto_test.md）に対応。
I602 で、TC-01 に相対の読み込みを、TC-03 に見出しの全項目を足し、マイグレーションの補助を
problems/tests/migration_helpers.py にまとめた（docs/tests/open/I602_auto_test.md の TC-01・TC-02・TC-05）。
"""
import ast
import hashlib
import io
import uuid
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, migrations
from django.http import HttpResponse
from PIL import Image
from rest_framework.test import APIClient

import problems.utils
from accounts.models import Organization, OrganizationCategory
from problems import media_migration
from problems.media_migration import MediaMigrationError, move_media_files_to_db
from problems.models import (
    MediaAsset, MediaAssetContent, ProblemMediaAsset, Subject,
)
from problems.tests.migration_helpers import column_names, load_migrations, run_migration
from problems.views import MEDIA_SECURITY_HEADERS

User = get_user_model()

MEDIA_MIGRATION_SOURCE = Path(media_migration.__file__)


def png_bytes(color=(5, 9, 0)):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, format="PNG")
    return buf.getvalue()


PNG = png_bytes()


@pytest.fixture
def world(db):
    cat = OrganizationCategory.objects.create(name="I590", slug="cat-i590")
    org = Organization.objects.create(name="組織590", slug="org-590", category=cat)
    subject = Subject.objects.create(name="科目590", slug="subj-590", organization=org)
    learner = User.objects.create_user(email="l590@example.com", user_id="l590", password="p",
                                       organization=org)
    return {"org": org, "subject": subject, "learner": learner}


def make_asset(world, data):
    return MediaAsset.objects.create(
        organization=world["org"], subject=world["subject"], usage_kind="problem",
        storage_key=f"org/org-590/subjects/subj-590/problem/{uuid.uuid4()}.png",
        original_filename="a.png", mime_type="image/png", file_size_bytes=len(data),
        checksum_sha256=hashlib.sha256(data).hexdigest())


# ---- TC-01: 移行の判定はアプリのモジュールを読まない ----
def app_imports(source: str) -> list:
    """アプリのモジュールの読み込みの一覧（problems か problems. で始まるもの・相対の読み込み）

    media_migration.py は problems の中にあるので、相対の読み込みはどれもアプリのモジュール（I602）。
    """
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            dots = "." * node.level  # 絶対の読み込みは level 0 で ""
            if node.module:
                names.append(dots + node.module)
            else:
                names.extend(dots + alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    return [n for n in names if n.startswith(".") or n == "problems" or n.startswith("problems.")]


def test_media_migration_imports_no_app_module():
    assert app_imports(MEDIA_MIGRATION_SOURCE.read_text(encoding="utf-8")) == []
    # 数え方が効くことの確かめ（失敗の注入）
    assert app_imports("from problems.utils import detect_mime\nimport os\n") == ["problems.utils"]
    assert app_imports("from .utils import x\n") == [".utils"]
    assert app_imports("from . import utils\n") == [".utils"]


# ---- TC-02: 0025 の判定が problems.utils の変更に引きずられない ----
@pytest.mark.parametrize("patch", ["formats", "detector"])
def test_media_migration_check_ignores_utils_changes(world, tmp_path, monkeypatch, patch):
    if patch == "formats":
        monkeypatch.setitem(problems.utils.ALLOWED_IMAGE_FORMATS, "text/plain", [".txt"])
    else:
        monkeypatch.setattr(problems.utils, "detect_mime", lambda data: "image/png")
    data = b"just text, not an image"
    asset = make_asset(world, data)
    path = tmp_path / asset.storage_key
    path.parent.mkdir(parents=True)
    path.write_bytes(data)

    with pytest.raises(MediaMigrationError, match=rf"画像ではありません.*id={asset.id}"):
        move_media_files_to_db(asset_model=MediaAsset, link_model=ProblemMediaAsset,
                               content_model=MediaAssetContent, media_root=tmp_path,
                               dry_run=False)
    assert MediaAssetContent.objects.count() == 0


# ---- TC-03: 配信の 200・304・412 のどれにも守りの見出しが付く ----
def missing_security_headers(response) -> list:
    """MEDIA_SECURITY_HEADERS のうち、応答に無いか値が違う見出しの名前（I602。辞書の全項目を回す）"""
    return [name for name, value in MEDIA_SECURITY_HEADERS.items()
            if response.get(name) != value]


@pytest.mark.parametrize("name", list(MEDIA_SECURITY_HEADERS))
def test_missing_security_headers_detects_each_header(name):
    """比べ方が効くことの確かめ（失敗の注入）: 1 つを消す・値を変えると、その見出しが返る"""
    def full():
        response = HttpResponse(b"")
        for header, value in MEDIA_SECURITY_HEADERS.items():
            response[header] = value
        return response

    assert missing_security_headers(full()) == []
    dropped = full()
    del dropped[name]
    assert missing_security_headers(dropped) == [name]
    changed = full()
    changed[name] = "x"
    assert missing_security_headers(changed) == [name]


@pytest.mark.parametrize("headers, expected", [
    ({}, 200),
    ({"HTTP_IF_NONE_MATCH": f'"{hashlib.sha256(PNG).hexdigest()}"'}, 304),
    ({"HTTP_IF_MATCH": '"x"'}, 412),
], ids=["plain", "not_modified", "precondition"])
def test_media_security_headers_on_all_statuses(world, headers, expected):
    asset = make_asset(world, PNG)
    MediaAssetContent.objects.create(asset=asset, data=PNG)
    client = APIClient()
    client.force_authenticate(user=world["learner"])

    response = client.get(f"/api/media/{asset.id}/", **headers)
    assert response.status_code == expected
    assert missing_security_headers(response) == []
    assert response["Cache-Control"] == "private, max-age=3600"


# ---- TC-04: 0027 は値のある科目があれば止まり、空なら列を外す。戻すと列が '' で戻る ----
# 0027 で止まったときに人が流す SQL（docs/runbooks/backend-check.md「4. 止める判定のあるマイグレーションが
# 止まったとき」）。手順書の SQL を変えたら、ここも同じ文にそろえる（I602）
CLEAR_IMAGE_DIRECTORY_SQL = "UPDATE problems_subject SET image_directory = '' WHERE image_directory <> ''"


def _without_check(migration):
    """判定の RunPython を外した写し（失敗の注入: 判定が無ければ値があっても列が消える）"""
    copy = type(migration)(migration.name, migration.app_label)
    copy.dependencies = migration.dependencies
    copy.operations = [op for op in migration.operations
                       if not isinstance(op, migrations.RunPython)]
    return copy


@pytest.mark.parametrize("value", ["problems/x", " "])
def test_0027_refuses_values_then_removes_column(world, settings, value):
    loader = load_migrations(settings)
    migration = loader.get_migration("problems", "0027_remove_subject_image_directory")
    before = loader.project_state(("problems", "0026_remove_problem_legacy_images"))
    run_migration(migration.unapply, before)
    OldSubject = before.apps.get_model("problems", "Subject")
    try:
        assert "image_directory" in column_names("problems_subject")
        assert set(OldSubject.objects.values_list("image_directory", flat=True)) == {""}

        OldSubject.objects.filter(pk=world["subject"].pk).update(image_directory=value)
        with pytest.raises(RuntimeError, match="1 件"):
            run_migration(migration.apply, before)
        assert "image_directory" in column_names("problems_subject")

        # 判定が効いていることの確かめ: 判定を外した写しなら値があっても列が消える
        run_migration(_without_check(migration).apply, before)
        assert "image_directory" not in column_names("problems_subject")
        run_migration(migration.unapply, before)

        # 手順書の SQL で空にすれば流れる
        with connection.cursor() as cursor:
            cursor.execute(CLEAR_IMAGE_DIRECTORY_SQL)
        run_migration(migration.apply, before)
        assert "image_directory" not in column_names("problems_subject")
    finally:
        if "image_directory" in column_names("problems_subject"):
            OldSubject.objects.update(image_directory="")
            run_migration(migration.apply, before)
