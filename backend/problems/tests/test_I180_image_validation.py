"""
I180: 画像アップロード検証（validate_image_file）の Pillow 依存分岐のユニットテスト。

Pillow 更新（12.3.0 → 13.0.0）で挙動が変わっていないことを、
形式別の受理・ピクセル寸法の境界・壊れた画像の拒否で検証する。

対応: docs/tests/open/I180_auto_test.md（TC-AUTO-04）
"""
import io

import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from problems.utils import validate_image_file


def image_upload(name, fmt, content_type, size=(10, 10)):
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 180, 60)).save(buf, format=fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type)


@pytest.mark.parametrize(
    "name, fmt, content_type",
    [
        ("a.png", "PNG", "image/png"),
        ("a.jpg", "JPEG", "image/jpeg"),
        ("a.jpeg", "JPEG", "image/jpeg"),
        ("a.webp", "WEBP", "image/webp"),
    ],
)
def test_allowed_formats_pass(name, fmt, content_type):
    assert validate_image_file(image_upload(name, fmt, content_type)) == (True, None)


@pytest.mark.parametrize("size", [(4096, 1), (1, 4096)])
def test_max_dimension_boundary_passes(size):
    assert validate_image_file(image_upload("b.png", "PNG", "image/png", size)) == (True, None)


@pytest.mark.parametrize("size", [(4097, 1), (1, 4097)])
def test_over_max_dimension_rejected(size):
    width, height = size
    assert validate_image_file(image_upload("c.png", "PNG", "image/png", size)) == (
        False,
        f"画像サイズが大きすぎます（{width}x{height}）。最大4096x4096ピクセルまでです。",
    )


def test_truncated_png_rejected_by_pillow():
    # 先頭 16 バイト（PNG シグネチャ＋IHDR の途中）だけ残す。
    # MIME 判定（python-magic）は image/png で通過し、Pillow の読み込みで失敗させる。
    head = image_upload("d.png", "PNG", "image/png").read()[:16]
    is_valid, error_msg = validate_image_file(
        SimpleUploadedFile("d.png", head, content_type="image/png")
    )
    assert is_valid is False
    assert error_msg.startswith("画像ファイルの読み込みに失敗しました: ")
