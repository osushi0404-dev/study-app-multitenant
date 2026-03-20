"""
問題画像アップロード用のユーティリティ関数
イシュー#031対応: 強化されたファイルバリデーションとサニタイゼーション
"""
import os
import re
import hashlib
import unicodedata
from pathlib import Path
from typing import Tuple, Optional
from django.core.exceptions import ValidationError
from django.conf import settings
from PIL import Image
import magic


# 対応画像形式の定義
ALLOWED_IMAGE_FORMATS = {
    'image/png': ['.png'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/webp': ['.webp'],
}

# ファイルサイズ制限（5MB）
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

# 画像サイズ制限（4096x4096ピクセル）
MAX_IMAGE_DIMENSION = 4096

# ファイル名長制限
MAX_FILENAME_LENGTH = 255


def validate_image_file(file) -> Tuple[bool, Optional[str]]:
    """
    画像ファイルの包括的なバリデーション

    Args:
        file: アップロードされたファイルオブジェクト (InMemoryUploadedFile)

    Returns:
        Tuple[bool, Optional[str]]: (検証成功, エラーメッセージ)

    検証項目:
        - ファイルサイズ: 5MB以下
        - ファイル形式: PNG, JPEG, WebP のみ許可
        - MIMEタイプ検証: 拡張子偽装対策
        - 画像サイズ: 4096x4096ピクセル以下
        - ファイル名の安全性: パストラバーサル対策、特殊文字チェック
    """

    # 1. ファイルサイズチェック
    if file.size > MAX_FILE_SIZE_BYTES:
        size_mb = file.size / (1024 * 1024)
        return False, f"ファイルサイズが大きすぎます（{size_mb:.2f}MB）。最大5MBまでです。"

    # 2. 拡張子チェック（基本的な検証）
    file_ext = Path(file.name).suffix.lower()
    allowed_extensions = [ext for exts in ALLOWED_IMAGE_FORMATS.values() for ext in exts]
    if file_ext not in allowed_extensions:
        return False, f"非対応の画像形式です。対応形式: PNG, JPEG, WebP"

    # 3. MIMEタイプ検証（拡張子偽装対策）
    try:
        # ファイルの先頭バイトからMIMEタイプを検出
        file.seek(0)
        mime = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)  # ファイルポインタを先頭に戻す

        if mime not in ALLOWED_IMAGE_FORMATS:
            return False, f"ファイルの内容が画像形式ではありません（検出: {mime}）"

        # 拡張子とMIMEタイプの整合性チェック
        if file_ext not in ALLOWED_IMAGE_FORMATS[mime]:
            return False, f"ファイル拡張子（{file_ext}）とファイル内容（{mime}）が一致しません"

    except Exception as e:
        return False, f"ファイル形式の検証に失敗しました: {str(e)}"

    # 4. 画像サイズ（ピクセル数）チェック
    try:
        file.seek(0)
        image = Image.open(file)
        width, height = image.size

        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            return False, f"画像サイズが大きすぎます（{width}x{height}）。最大{MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}ピクセルまでです。"

        file.seek(0)  # ファイルポインタを先頭に戻す

    except Exception as e:
        return False, f"画像ファイルの読み込みに失敗しました: {str(e)}"

    # 5. ファイル名の安全性チェック
    is_safe, error_msg = _validate_filename_safety(file.name)
    if not is_safe:
        return False, error_msg

    return True, None


def _validate_filename_safety(filename: str) -> Tuple[bool, Optional[str]]:
    """
    ファイル名の安全性検証（内部関数）

    検証項目:
        - パストラバーサル対策（../ 等の除去）
        - Null byte 対策
        - ファイル名長チェック
        - 不正な文字のチェック
    """

    # Null byte チェック
    if '\x00' in filename:
        return False, "ファイル名に不正な文字（null byte）が含まれています"

    # パストラバーサル対策
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, "ファイル名にパス区切り文字（../, /, \\）を含めることはできません"

    # ファイル名長チェック
    if len(filename) > MAX_FILENAME_LENGTH:
        return False, f"ファイル名が長すぎます（最大{MAX_FILENAME_LENGTH}文字）"

    # 制御文字チェック
    if any(ord(char) < 32 for char in filename):
        return False, "ファイル名に制御文字が含まれています"

    return True, None


def sanitize_filename(filename: str) -> str:
    """
    ファイル名のサニタイズ（強化版・ホワイトリスト方式）

    Args:
        filename: 元のファイル名

    Returns:
        str: サニタイズ後のファイル名

    処理内容:
        - Unicode正規化（NFKC形式）
        - ホワイトリスト方式による安全文字のみ許可
        - パストラバーサル文字列の除去
        - Null byte の除去
        - 連続スペースの単一化
        - 前後の空白削除
        - 日本語ファイル名は許可（UTF-8）
    """

    # 1. Unicode正規化（NFKC: 互換文字を標準形に統一）
    filename = unicodedata.normalize('NFKC', filename)

    # 2. Null byte 除去
    filename = filename.replace('\x00', '')

    # 3. パストラバーサル文字列の除去
    filename = filename.replace('..', '')
    filename = filename.replace('/', '')
    filename = filename.replace('\\', '')

    # 4. ホワイトリスト方式: 許可する文字のみを抽出
    # 許可: 英数字、日本語（ひらがな、カタカナ、漢字）、アンダースコア、ハイフン、ドット、スペース
    def is_allowed_char(char):
        # 英数字
        if char.isalnum():
            return True
        # 日本語文字（ひらがな、カタカナ、漢字）
        if '\u3040' <= char <= '\u309F':  # ひらがな
            return True
        if '\u30A0' <= char <= '\u30FF':  # カタカナ
            return True
        if '\u4E00' <= char <= '\u9FFF':  # 漢字
            return True
        # 許可する記号
        if char in ('_', '-', '.', ' '):
            return True
        return False

    filename = ''.join(char for char in filename if is_allowed_char(char))

    # 5. 連続スペースを単一スペースに統一
    filename = re.sub(r'\s+', ' ', filename)

    # 6. 前後の空白を削除
    filename = filename.strip()

    # 7. ファイル名が空になった場合のフォールバック
    if not filename:
        filename = 'sanitized_file'

    # 8. 拡張子が失われた場合の検出と警告
    if '.' not in filename:
        # 拡張子がない場合は元のファイル名から拡張子を抽出
        # （この関数単体では対応不可、呼び出し側で対応）
        pass

    return filename


def check_duplicate_filename(
    organization_id: int,
    subject_slug: str,
    usage_kind: str,
    original_filename: str
) -> Tuple[bool, Optional[str]]:
    """
    ファイル名の重複チェック（厳格版）

    Args:
        organization_id: 組織ID
        subject_slug: 科目スラッグ
        usage_kind: 用途種別（'problem' or 'explanation'）
        original_filename: チェック対象のファイル名

    Returns:
        Tuple[bool, Optional[str]]: (重複なし, エラーメッセージ)

    チェック対象:
        同じ組織の同じ科目の同じ用途（問題/解説）フォルダ配下の
        既存ファイル名と重複していないかをチェック
    """
    from problems.models import MediaAsset

    # MediaAssetテーブルから該当ディレクトリ配下のファイルを検索
    existing_assets = MediaAsset.objects.filter(
        organization_id=organization_id,
        subject__slug=subject_slug,
        usage_kind=usage_kind,
        original_filename=original_filename,
        is_deleted=False  # 論理削除されていないもののみ
    )

    if existing_assets.exists():
        usage_label = '問題画像' if usage_kind == 'problem' else '解説画像'
        return False, f'ファイル名 "{original_filename}" は既に{usage_label}として登録されています'

    return True, None


def check_directory_exists(directory_path: str) -> Tuple[bool, Optional[str]]:
    """
    ディレクトリの存在確認

    Args:
        directory_path: 確認対象のディレクトリパス（MEDIA_ROOT からの相対パス）

    Returns:
        Tuple[bool, Optional[str]]: (存在する, エラーメッセージ)

    注意:
        ディレクトリが存在しない場合はエラーとし、自動作成は行わない
        （ディレクトリは科目登録時に作成済みの想定）
    """
    full_path = os.path.join(settings.MEDIA_ROOT, directory_path)

    if not os.path.exists(full_path):
        return False, f"ディレクトリが存在しません: {directory_path}（科目登録時にディレクトリが作成されているか確認してください）"

    if not os.path.isdir(full_path):
        return False, f"指定されたパスがディレクトリではありません: {directory_path}"

    # 書き込み権限の確認
    if not os.access(full_path, os.W_OK):
        return False, f"ディレクトリへの書き込み権限がありません: {directory_path}"

    return True, None


def calculate_file_checksum(file) -> str:
    """
    ファイルのSHA256チェックサムを計算

    Args:
        file: ファイルオブジェクト

    Returns:
        str: SHA256ハッシュ値（16進数文字列）
    """
    file.seek(0)
    sha256_hash = hashlib.sha256()

    # チャンク単位で読み込んでハッシュ計算（メモリ効率化）
    for chunk in iter(lambda: file.read(4096), b''):
        sha256_hash.update(chunk)

    file.seek(0)  # ファイルポインタを先頭に戻す
    return sha256_hash.hexdigest()


def get_storage_path(
    organization_slug: str,
    subject_slug: str,
    usage_kind: str,
    filename: str
) -> str:
    """
    ストレージパスの生成

    Args:
        organization_slug: 組織スラッグ
        subject_slug: 科目スラッグ
        usage_kind: 用途種別（'problem' or 'explanation'）
        filename: ファイル名（UUIDベース）

    Returns:
        str: ストレージパス（例: org/cute_school/subjects/aws-saa/problem/uuid.png）
    """
    return f"org/{organization_slug}/subjects/{subject_slug}/{usage_kind}/{filename}"
