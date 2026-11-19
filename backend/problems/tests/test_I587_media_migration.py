"""
I587: 画像のファイルを DB に移すマイグレーションと、古い画像の列を外すマイグレーション

TC-03・TC-12〜TC-15（docs/tests/open/I587_auto_test.md）に対応。
pytest は --no-migrations なので、本物のマイグレーションは MigrationLoader で読んで apply／unapply する（I492 と同じ）。
"""
import hashlib
import io
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from PIL import Image

from accounts.models import Organization, OrganizationCategory
from problems import media_migration
from problems.media_migration import MediaMigrationError, move_media_files_to_db
from problems.models import (
    Choice, MediaAsset, MediaAssetContent, Problem, ProblemMediaAsset, Subject,
)

User = get_user_model()


def png_bytes(color=(1, 2, 3)):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, format="PNG")
    return buf.getvalue()


PNG = png_bytes()


@pytest.fixture
def world(db):
    cat = OrganizationCategory.objects.create(name="I587M", slug="cat-i587m")
    org = Organization.objects.create(name="組織587M", slug="org-587m", category=cat)
    subject = Subject.objects.create(name="科目587M", slug="subj-587m", organization=org)
    admin = User.objects.create_user(email="m587@example.com", user_id="m587", password="p",
                                     organization=org, role="admin")
    problem = Problem.objects.create(subject=subject, organization=org, created_by=admin,
                                     question="Q", problem_type="single", difficulty=1,
                                     explanation="E")
    Choice.objects.create(problem=problem, text="A", is_correct=True, order=1)
    return {"org": org, "subject": subject, "problem": problem}


def make_asset(world, *, key=None, data=PNG, checksum="auto", size="auto", deleted=False,
               link=False):
    asset = MediaAsset.objects.create(
        organization=world["org"], subject=world["subject"], usage_kind="problem",
        storage_key=key or f"org/org-587m/subjects/subj-587m/problem/{uuid.uuid4()}.png",
        original_filename="a.png", mime_type="image/png",
        file_size_bytes=len(data) if size == "auto" else size,
        checksum_sha256=hashlib.sha256(data).hexdigest() if checksum == "auto" else checksum,
        is_deleted=deleted)
    if link:
        ProblemMediaAsset.objects.create(organization=world["org"], problem=world["problem"],
                                         asset=asset, usage_kind="problem", position=1)
    return asset


def put_file(root, asset, data=PNG):
    path = root / asset.storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def run_move(root, dry_run=False):
    return move_media_files_to_db(asset_model=MediaAsset, link_model=ProblemMediaAsset,
                                  content_model=MediaAssetContent, media_root=root,
                                  dry_run=dry_run)


def _loader(settings):
    settings.MIGRATION_MODULES = {}  # pytest の --no-migrations を外し、本物のマイグレーションを読む
    return MigrationLoader(connection)


def _run(step, state):
    """遅延の外部キーの検査を済ませてから DDL を流す（I492 と同じ）"""
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    with connection.schema_editor() as editor:
        step(state.clone(), editor)


def _tables():
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


def _columns(table):
    with connection.cursor() as cursor:
        return {c.name for c in connection.introspection.get_table_description(cursor, table)}


def _attstorage():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT attstorage FROM pg_attribute "
            "WHERE attrelid = 'media_asset_contents'::regclass AND attname = 'data'")
        return cursor.fetchone()[0]


# ---- TC-03: 0024 は中身の列を EXTERNAL（圧縮しない）にする ----
def test_0024_sets_external_storage(db, settings):
    loader = _loader(settings)
    migration = loader.get_migration("problems", "0024_mediaassetcontent")
    before = loader.project_state(("problems", "0023_quizsession_mode_weak"))
    _run(migration.unapply, before)
    try:
        assert "media_asset_contents" not in _tables()
        _run(migration.apply, before)
        assert _attstorage() == "e"
    finally:
        if "media_asset_contents" not in _tables():
            _run(migration.apply, before)


# ---- TC-12: 0025 はファイルを DB に移し、ファイルの無い行を消す。戻すとファイルに書き戻す ----
def test_0025_moves_files_and_reverts(world, settings, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(media_migration, "LEGACY_MEDIA_ROOT", tmp_path)
    present = make_asset(world)
    put_file(tmp_path, present)
    missing = make_asset(world, link=True)
    loader = _loader(settings)
    migration = loader.get_migration("problems", "0025_move_media_files_to_db")
    before = loader.project_state(("problems", "0024_mediaassetcontent"))

    _run(migration.apply, before)
    assert bytes(MediaAssetContent.objects.get(asset=present).data) == PNG
    assert not MediaAsset.objects.filter(id=missing.id).exists()
    assert not ProblemMediaAsset.objects.filter(asset_id=missing.id).exists()
    out = capsys.readouterr().out
    assert "I587 media: moved=1 already=0 deleted_assets=1 deleted_links=1" in out
    # 消した行のキーを出力に残す（fix-loop F2）。移した行は並べない
    assert f"I587 media: deleted id={missing.id} key={missing.storage_key}" in out
    assert f"id={present.id}" not in out

    (tmp_path / present.storage_key).unlink()
    _run(migration.unapply, before)
    assert (tmp_path / present.storage_key).read_bytes() == PNG


# ---- TC-13: やり直し・論理削除・試し・null の checksum ----
def test_move_media_files_cases(world, tmp_path):
    deleted = make_asset(world, deleted=True)
    nulls = make_asset(world, checksum=None, size=None)
    put_file(tmp_path, nulls)
    plain = make_asset(world)
    put_file(tmp_path, plain)

    dry = run_move(tmp_path, dry_run=True)
    assert (dry.moved, dry.already, dry.deleted_assets) == (2, 0, 0)
    assert MediaAssetContent.objects.count() == 0

    first = run_move(tmp_path)
    assert (first.moved, first.already) == (2, 0)
    second = run_move(tmp_path)
    assert (second.moved, second.already) == (0, 2)
    assert MediaAssetContent.objects.count() == 2

    assert MediaAsset.objects.filter(id=deleted.id).exists()
    assert not MediaAssetContent.objects.filter(asset=deleted).exists()
    nulls.refresh_from_db()
    assert nulls.checksum_sha256 == hashlib.sha256(PNG).hexdigest()
    assert nulls.file_size_bytes == len(PNG)
    assert nulls.mime_type == "image/png"


# ---- TC-14: 食い違いは止めて、DB を変えない ----
@pytest.mark.parametrize("case,reason", [
    ("checksum", "checksum_sha256 と違います"),
    ("not_image", "画像ではありません"),
    ("outside", "置き場の外を指すキー"),
])
def test_move_media_files_refuses_anomalies(world, tmp_path, case, reason):
    good = make_asset(world)
    put_file(tmp_path, good)
    if case == "checksum":
        bad = make_asset(world, checksum="0" * 64)
        put_file(tmp_path, bad)
    elif case == "not_image":
        text = b"just text, not an image"
        bad = make_asset(world, data=text)
        put_file(tmp_path, bad, text)
    else:
        bad = make_asset(world, key="../../etc/passwd")
    with pytest.raises(MediaMigrationError) as error:
        run_move(tmp_path)
    assert str(bad.id) in str(error.value)
    assert reason in str(error.value)
    assert MediaAssetContent.objects.count() == 0
    assert MediaAsset.objects.filter(id=bad.id).exists()


def test_check_media_migration_command(world, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("problems.management.commands.check_media_migration.LEGACY_MEDIA_ROOT",
                        tmp_path)
    present = make_asset(world)
    put_file(tmp_path, present)
    missing = make_asset(world, link=True)
    call_command("check_media_migration")
    out = capsys.readouterr().out
    assert f"移す\t{present.id}" in out
    assert f"消す（ファイル無し）\t{missing.id}" in out
    assert "moved=1 already=0 deleted_assets=1 deleted_links=1" in out
    assert MediaAssetContent.objects.count() == 0
    assert MediaAsset.objects.filter(id=missing.id).exists()


# ---- TC-15: 0026 は古い列に値があれば止まり、無ければ列を外す ----
def test_0026_refuses_legacy_values_then_removes_columns(world, settings):
    loader = _loader(settings)
    migration = loader.get_migration("problems", "0026_remove_problem_legacy_images")
    before = loader.project_state(("problems", "0025_move_media_files_to_db"))
    _run(migration.unapply, before)
    try:
        assert {"question_image", "explanation_image"} <= _columns("problems_problem")
        OldProblem = before.apps.get_model("problems", "Problem")
        OldProblem.objects.filter(pk=world["problem"].pk).update(question_image="x.png")
        with pytest.raises(RuntimeError, match="1"):
            _run(migration.apply, before)
        assert "question_image" in _columns("problems_problem")

        OldProblem.objects.filter(pk=world["problem"].pk).update(question_image="")
        _run(migration.apply, before)
        assert not {"question_image", "explanation_image"} & _columns("problems_problem")
    finally:
        if "question_image" in _columns("problems_problem"):
            OldProblem.objects.update(question_image=None, explanation_image=None)
            _run(migration.apply, before)
