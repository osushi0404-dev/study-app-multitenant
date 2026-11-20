"""
今ある画像ファイルを DB（MediaAssetContent）に移す（I587）

マイグレーション 0025（実際に移す）と管理コマンド check_media_migration（試し・読むだけ）の両方から使う。
モデルは引数で受ける（マイグレーションの中では過去のモデル、コマンドでは今のモデル）。
食い違い（中身の不一致・画像でない・置き場の外を指すキー）は黙って直さずに止める（C7）。
このモジュールはマージ済みの 0025 の一部として扱う: アプリのモジュール（problems.*）を読まない（I590・TC-01 が固定）。
ここを変えることは 0025 を変えることになる（規約 §4）。
"""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import magic
from django.conf import settings
from django.db import connection, transaction

# 移行の判定はアプリのモジュール（problems.utils）を読まず、ここに写しを持つ（I590 F3）。
# 0025 は一度流したら書き換えない（規約 §4）ので、アプリの許可する形式や判定の変更に引きずられないようにする
MIGRATION_ALLOWED_MIMES = frozenset({'image/png', 'image/jpeg', 'image/webp'})
MIGRATION_SNIFF_BYTES = 2048

# 移す前のファイルの置き場（I587 で設定の MEDIA_ROOT を外したので、移行が読む場所はここに置く）
LEGACY_MEDIA_ROOT = Path(settings.BASE_DIR) / 'media'

ACTION_MOVE = '移す'
ACTION_ALREADY = '済み'
ACTION_DELETE = '消す（ファイル無し）'


class MediaMigrationError(RuntimeError):
    """移行を止める食い違い（画像の ID・キー・理由を文に入れる。中身は入れない）"""


@dataclass
class MediaMigrationResult:
    moved: int = 0
    already: int = 0
    deleted_assets: int = 0
    deleted_links: int = 0
    planned: list = field(default_factory=list)  # [(画像の ID, キー, 判定), ...]

    def summary(self) -> str:
        return (f'moved={self.moved} already={self.already} '
                f'deleted_assets={self.deleted_assets} deleted_links={self.deleted_links}')


def _detect_mime(data: bytes) -> str:
    """中身の先頭のバイト列から MIME を判定する（送り手の content_type は使わない）"""
    return magic.from_buffer(data[:MIGRATION_SNIFF_BYTES], mime=True)


def _resolve_inside(root: Path, asset_id, storage_key: str) -> Path:
    """キーから読む場所を作る。置き場の外（../・シンボリックリンク）を指せば止める"""
    path = (root / storage_key).resolve()
    if not path.is_relative_to(root):
        raise MediaMigrationError(
            f'I587 media: 置き場の外を指すキーです id={asset_id} key={storage_key}')
    return path


def _checked_content(asset, data: bytes) -> tuple:
    """中身を確かめて (sha256, MIME) を返す。値のある checksum・大きさと違えば止める"""
    checksum = hashlib.sha256(data).hexdigest()
    if asset.checksum_sha256 and asset.checksum_sha256 != checksum:
        raise MediaMigrationError(
            f'I587 media: 中身が checksum_sha256 と違います id={asset.id} key={asset.storage_key}')
    if asset.file_size_bytes is not None and asset.file_size_bytes != len(data):
        raise MediaMigrationError(
            f'I587 media: 中身の大きさが file_size_bytes と違います id={asset.id} key={asset.storage_key}')
    mime = _detect_mime(data)
    if mime not in MIGRATION_ALLOWED_MIMES:
        raise MediaMigrationError(
            f'I587 media: 中身が画像ではありません（{mime}）id={asset.id} key={asset.storage_key}')
    return checksum, mime


def _assets_with_content(content_model) -> set:
    """中身のある画像の ID。中身の表がまだ無い（0024 の前に試しを流した）ときは空"""
    if content_model._meta.db_table not in connection.introspection.table_names():
        return set()
    return set(content_model.objects.values_list('asset_id', flat=True))


def move_media_files_to_db(*, asset_model, link_model, content_model, media_root: Path,
                           dry_run: bool) -> MediaMigrationResult:
    """
    消されていない画像のファイルを読み、中身を DB に入れる。ファイルの無い行は紐づけと一緒に消す

    - すでに中身のある行は飛ばす（やり直しで二重に入らない）
    - 論理削除の行は触らない（今もファイルが消されていて、配信もしない）
    - dry_run=True は何も書かず、行ごとの判定と件数だけを返す
    """
    root = Path(media_root).resolve()
    result = MediaMigrationResult()
    with transaction.atomic():
        has_content = _assets_with_content(content_model)
        missing_ids = []
        for asset in asset_model.objects.filter(is_deleted=False).order_by('created_at', 'id'):
            if asset.id in has_content:
                result.already += 1
                result.planned.append((asset.id, asset.storage_key, ACTION_ALREADY))
                continue
            path = _resolve_inside(root, asset.id, asset.storage_key)
            if not path.is_file():
                missing_ids.append(asset.id)
                result.planned.append((asset.id, asset.storage_key, ACTION_DELETE))
                continue
            data = path.read_bytes()
            checksum, mime = _checked_content(asset, data)
            result.moved += 1
            result.planned.append((asset.id, asset.storage_key, ACTION_MOVE))
            if not dry_run:
                content_model.objects.create(asset_id=asset.id, data=data)
                asset_model.objects.filter(id=asset.id).update(
                    mime_type=mime, checksum_sha256=checksum, file_size_bytes=len(data))

        links = link_model.objects.filter(asset_id__in=missing_ids)
        result.deleted_links = links.count()
        result.deleted_assets = len(missing_ids)
        if not dry_run and missing_ids:
            # 紐づけは RESTRICT なので先に消す
            links.delete()
            asset_model.objects.filter(id__in=missing_ids).delete()
    return result


def write_back_media_files(*, asset_model, content_model, media_root: Path) -> int:
    """0025 の戻し: 中身のある画像をファイルの置き場に書き戻す（消した行は戻らない）。書いた数を返す"""
    root = Path(media_root).resolve()
    written = 0
    keys = dict(asset_model.objects.values_list('id', 'storage_key'))
    # 中身を全部同時にメモリに載せない
    for asset_id, data in content_model.objects.values_list('asset_id', 'data').iterator(chunk_size=50):
        path = _resolve_inside(root, asset_id, keys[asset_id])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(data))
        written += 1
    return written
