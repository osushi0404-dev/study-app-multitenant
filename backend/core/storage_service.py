import os
import imghdr
import logging
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class StorageService:
    """ローカルストレージ操作（将来的にS3対応可能）"""

    # セキュリティ設定
    ALLOWED_MIME_TYPES = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
    ]
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def validate_file(file_data):
        """
        ファイルバリデーション（セキュリティ必須）

        - ファイルサイズチェック
        - MIMEタイプチェック
        - マジックナンバー検証（偽装対策）
        """
        # ファイルサイズチェック
        if file_data.size > StorageService.MAX_FILE_SIZE:
            max_size_mb = StorageService.MAX_FILE_SIZE // 1024 // 1024
            raise ValidationError(
                f'ファイルサイズは{max_size_mb}MB以下にしてください。'
                f'（現在: {file_data.size // 1024 // 1024}MB）'
            )

        # MIMEタイプチェック
        if file_data.content_type not in StorageService.ALLOWED_MIME_TYPES:
            raise ValidationError(
                f'許可されていないファイル形式です。'
                f'（許可形式: {", ".join(StorageService.ALLOWED_MIME_TYPES)}）'
            )

        # マジックナンバー検証（偽装対策）
        file_data.seek(0)
        detected_type = imghdr.what(file_data)
        file_data.seek(0)

        if detected_type not in StorageService.ALLOWED_EXTENSIONS:
            raise ValidationError(
                '画像ファイルの内容が不正です。正しい画像ファイルをアップロードしてください。'
            )

        logger.info(
            f"File validated: {file_data.name}, "
            f"size={file_data.size}, type={file_data.content_type}"
        )

    @staticmethod
    def generate_storage_key(org_slug, subject_slug, usage_kind, asset_id, extension):
        """
        ストレージキーを生成

        Args:
            org_slug (str): 組織のslug（例: 'cute_school', 'personal'）
            subject_slug (str): 科目のslug（例: 'aws-saa', 'database-fundamentals'）
            usage_kind (str): 'problem' または 'explanation'
            asset_id (UUID): アセットID
            extension (str): ファイル拡張子（例: 'png', 'jpg'）

        Returns:
            str: ストレージキー（例: 'org/cute_school/subjects/aws-saa/problem/uuid.png'）
        """
        # 拡張子のバリデーション
        extension = extension.lower().lstrip('.')
        if extension not in StorageService.ALLOWED_EXTENSIONS:
            raise ValidationError(f'許可されていない拡張子です: {extension}')

        # パス要素のバリデーション（セキュリティ対策）
        if not org_slug or '/' in org_slug or '..' in org_slug:
            raise ValidationError('不正な組織slugです')
        if not subject_slug or '/' in subject_slug or '..' in subject_slug:
            raise ValidationError('不正な科目slugです')

        return f"org/{org_slug}/subjects/{subject_slug}/{usage_kind}/{asset_id}.{extension}"

    @staticmethod
    def save_file(storage_key, file_data):
        """
        ファイルを保存

        Args:
            storage_key: ストレージキー
            file_data: UploadedFileオブジェクト

        Raises:
            ValidationError: バリデーション失敗時
        """
        # バリデーション実行
        StorageService.validate_file(file_data)

        file_path = os.path.join(settings.MEDIA_ROOT, storage_key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # ファイル保存
        with open(file_path, 'wb') as f:
            for chunk in file_data.chunks():
                f.write(chunk)

        logger.info(f"File saved: {storage_key}")

    @staticmethod
    def copy_file(src_key, dst_key):
        """ファイルをコピー"""
        src_path = os.path.join(settings.MEDIA_ROOT, src_key)
        dst_path = os.path.join(settings.MEDIA_ROOT, dst_key)

        if not os.path.exists(src_path):
            raise ValidationError(f'コピー元ファイルが存在しません: {src_key}')

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        import shutil
        shutil.copy2(src_path, dst_path)

        logger.info(f"File copied: {src_key} -> {dst_key}")

    @staticmethod
    def delete_file(storage_key):
        """ファイルを削除"""
        file_path = os.path.join(settings.MEDIA_ROOT, storage_key)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File deleted: {storage_key}")
