"""
問題まわりの読み取りの組み立て（I587: 画像の配信）
"""
from typing import Optional
from uuid import UUID

from problems.models import MediaAsset, MediaAssetContent


def visible_media_asset(*, user, asset_id: UUID) -> Optional[MediaAsset]:
    """
    利用者に見せてよい画像（利用者の組織の、消されていない画像）。無ければ None

    組織は request.user から決める（規約 §5）。画像の組織と科目の組織の両方が利用者の組織であること。
    organization か subject が null の行は持ち主が分からないので返さない（I587・AC11）。
    中身は読まない（304 の判定に使うメタデータだけ）。
    """
    if user.organization_id is None:
        return None
    return (
        MediaAsset.objects
        .filter(
            id=asset_id,
            is_deleted=False,
            organization_id=user.organization_id,
            subject__organization_id=user.organization_id,
        )
        .only('id', 'mime_type', 'checksum_sha256')
        .first()
    )


def media_asset_data(asset: MediaAsset) -> Optional[bytes]:
    """画像の中身のバイト列。中身の行が無ければ None"""
    data = (
        MediaAssetContent.objects
        .filter(asset_id=asset.id)
        .values_list('data', flat=True)
        .first()
    )
    return None if data is None else bytes(data)
