"""
問題モデル用のカスタムバリデーター
"""
from pathlib import Path
from django.core.exceptions import ValidationError


def validate_image_size(image):
    """
    画像ファイルサイズを検証

    Args:
        image: アップロードされた画像ファイル

    Raises:
        ValidationError: ファイルサイズが5MBを超える場合
    """
    max_size_mb = 5
    max_size_bytes = max_size_mb * 1024 * 1024

    if image.size > max_size_bytes:
        raise ValidationError(
            f'画像ファイルサイズは{max_size_mb}MB以下にしてください。'
            f'（現在: {image.size / 1024 / 1024:.2f}MB）'
        )


def validate_image_extension(image):
    """
    画像ファイルの拡張子を検証

    Args:
        image: アップロードされた画像ファイル

    Raises:
        ValidationError: 許可されていない拡張子の場合
    """
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    ext = Path(image.name).suffix.lower()

    if ext not in allowed_extensions:
        raise ValidationError(
            f'許可されていないファイル形式です。'
            f'許可されている形式: {", ".join(allowed_extensions)}'
        )
