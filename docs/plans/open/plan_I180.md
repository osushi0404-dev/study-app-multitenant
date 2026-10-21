# plan_I180: Pillow を 13.0.0 に更新（既知脆弱性 8 件の解消）

## 基本情報
- **計画書ID**: plan_I180
- **関連イシュー**: #301
- **Draft PR**: #303
- **作成根拠資料**: docs/issues/open/I180.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I180_review.md
- **作成日**: 2026-10-21
- **ブランチ**: `feature/I180-update-pillow-13`（`origin/develop` 起点）
- **テスト文書**: docs/tests/open/I180_auto_test.md / docs/tests/open/I180_manual_test.md

---

## 1. 背景/目的

### 背景
CI の「Backend Lint & Security」ジョブの `pip-audit -r requirements.txt` が、Pillow 12.3.0 に公開された脆弱性 8 件で失敗している。同じ `backend/requirements.txt` を使う全 PR と develop が同じ理由で落ちる。I179（PR #300）の `/code-review` は、このイシューのマージ待ちで止まっている。

### 目的
Pillow を修正版 13.0.0 に上げて `pip-audit` を exit 0 に戻す。画像アップロード検証が更新後も同じように動くことを、既存テストと、今回追加する再発防止テストで確かめる。

### 原因の概要（平易な説明）
固定している Pillow 12.3.0 に新しい脆弱性が見つかり、直った版は 13.0.0 しかない。だから 13.0.0 に上げる以外に直す方法がない。

### 詳細な原因分析
1. `pip-audit` は PyPI の脆弱性データベースを参照し、`backend/requirements.txt:8` の `Pillow==12.3.0` に該当する advisory を 8 件検出する。
2. 8 件すべての Fix Versions は `13.0.0` だけ（12.x 系の修正版は無い）。
3. 公開は 2026-10-20 11:53（UTC）以降。develop の CI はその時刻まで成功していた。アプリ側の変更が原因ではない。

### 根本原因（コードレベル）
- `backend/requirements.txt:8` `Pillow==12.3.0`（脆弱性のある版への固定）

---

## 2. 調査結果（必須）

### 2-1. ベースライン計測（2026-10-21・`origin/develop` 起点・wt-harness の Docker 実環境）

| 項目 | コマンド | 結果 |
|---|---|---|
| backend テスト | `docker compose exec -T backend python -m pytest --tb=short -q` | **94 passed**（5 warnings・22.61s） |
| 本体依存の監査 | `docker compose exec -T backend pip-audit -r requirements.txt` | **8 件検出・exit 1**（イシュー記載の 8 件と同じ ID） |
| インストール済み Pillow | `docker compose exec -T backend python -c "import PIL; print(PIL.__version__)"` | `12.3.0` |

> 実行環境: このワークツリー専用の compose プロジェクト `wt-harness`（ポートは `.env` でオフセット済み: backend 8010 / db 5442 / redis 6389 / frontend 3010）。主作業側（`study-app-multitenant`）のコンテナには触れていない。

### 2-2. 更新後の監査（ツール実走で完了基準を確定・2026-10-21）

`backend/requirements.txt` の Pillow 行だけを `13.0.0` にした写しを、ホストの使い捨て venv の `pip-audit` で監査した（リポジトリは無変更）。

| 対象 | 結果 |
|---|---|
| 現行（Pillow 12.3.0） | `Found 8 known vulnerabilities in 1 package`・exit 1 |
| Pillow だけ 13.0.0 | **`No known vulnerabilities found`・exit 0** |

→ 受け入れ条件「`pip-audit` exit 0」は達成できる。Pillow 以外の依存には検出が無いので、別イシューにするものも無い。

### 2-3. 8 件の CVE が影響する処理（AC: 計画書への記録）

`pip-audit -f json --desc` の別名（GHSA）と、Pillow 13.0.0 リリースノートの Security 節で突き合わせた。

| CVE | GHSA | 影響する処理（画像形式・関数） | 本リポジトリでの到達性 |
|---|---|---|---|
| CVE-2026-112895 | GHSA-p4wg-p73j-c528 | PDF 解析（`PdfParser`）の再帰が無制限。`Image.save(..., format="PDF", append=True)` でスタック枯渇 | 到達しない（PDF の保存・追記を使っていない） |
| CVE-2026-112400 | GHSA-65qm-jvmh-6pqg | GIF の `seek()` が decompression bomb 判定後のサイズを保持（DoS） | 到達しない（GIF は MIME 判定で `Image.open` の前に拒否・`seek` 未使用） |
| CVE-2026-112397 | GHSA-58r4-6rv3-gfh8 | 幅 0 の PPM/PGM を `ImageMorph.MorphOp.apply()` に渡すと範囲外書き込み | 到達しない（`ImageMorph` 未使用・PPM/PGM は拒否） |
| CVE-2026-112896 | GHSA-pchr-8j38-3x4p | TIFF エンコーダが不正な ColorMap を受け入れ範囲外読み取り（TIFF 保存時） | 到達しない（TIFF を保存しない） |
| CVE-2026-112897 | GHSA-q45j-58j2-45rg | TIFF デコード（JPEG ストリップが短い場合）で未初期化メモリを返す | 到達しない（TIFF は拒否） |
| CVE-2026-112395 | GHSA-462x-pgg6-55fp | TIFF タイル・YCbCr デコードの範囲外読み取り | 到達しない（TIFF は拒否） |
| CVE-2026-112404 | GHSA-c6hw-5grf-ff96 | TIFF タイル・RGBA 経路の範囲外読み取り | 到達しない（TIFF は拒否） |
| CVE-2026-112899 | GHSA-vx6w-vv9f-6gvg | EPS の `load(scale)` で Ghostscript 描画が decompression bomb 上限を超える | 到達しない（EPS は拒否） |

**到達性の根拠**: Pillow を呼ぶのは `backend/problems/utils.py:82` の `Image.open(file)` と `:83` の `.size` だけ。その前の `:66` で python-magic が先頭 2048 バイトから MIME を判定し、`image/png` / `image/jpeg` / `image/webp` 以外を `:69-70` で拒否する。拡張子との整合も `:73` で確認する。

**それでも更新する理由**: 到達しないのは「いまのコードでは」という条件付きである。MIME 判定をすり抜ける入力が将来見つかる可能性はゼロではないし、`pip-audit` のゲートは到達性を区別しない。CI の復旧には更新が必要で、更新のコストも小さい（2-5 のスパイクで無退行を確認済み）。なお 13.0.0 のリリースノートには、pip-audit の 8 件以外にも、本アプリが受け付ける **JPEG** のデコーダの修正（GHSA-5x8w-8jj5-q52h・Critical）が含まれる。本アプリは `Image.open` でヘッダを読むだけで画素はデコードしないが、受理形式に関わる修正も更新で取り込まれる。

### 2-4. 13.0.0 の非互換変更と本リポジトリの利用箇所（AC: 計画書への記録）

リリースノート（https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html）の「Backwards Incompatible Changes」「Deprecations」の全項目を、利用箇所と突き合わせた。

| 非互換変更・非推奨 | 本リポジトリの利用 | 影響 |
|---|---|---|
| Python 3.10 のサポート終了 | `backend/Dockerfile:2` `python:3.11-slim`・`.github/workflows/ci.yml:17,70` `3.11` | なし |
| モード `I` の画像を PNG 保存するときの 16 bit への切り詰めを廃止 | テストは `Image.new("RGB", ...)` の PNG 保存だけ（モード `I` 不使用） | なし |
| `Image.fromarray()` の `mode` 引数の一部用途を廃止 | 未使用 | なし |
| `Image.Image.get_child_images()` → `ImageFile.ImageFile.get_child_images()` へ移動 | 未使用 | なし |
| `Image._show` の削除 | 未使用 | なし |
| `ImageCms.ImageCmsProfile.product_name` / `.product_info` の削除 | 未使用 | なし |
| `ExifTags.IFD.Makernote` の削除 | 未使用 | なし |
| IM 形式の非推奨化（15.0.0 で削除予定） | 未使用（IM は MIME 判定で拒否） | なし |
| `JpegImageFile.load_djpeg` の非推奨化 | 未使用 | なし |
| `ImageQt.align8to32()` の非推奨化 | 未使用 | なし |

**利用箇所の全件**（`git grep -n -i -E "from PIL|import PIL|pillow|ImageField|Image\." -- backend`）:
- `backend/problems/utils.py:12` `from PIL import Image` / `:82` `Image.open(file)` / `:83` `image.size`
- `backend/problems/tests/test_I073_image_update.py:16` `from PIL import Image` / `:33` `Image.new("RGB", size, color).save(buf, format="PNG")`
- `backend/problems/migrations/0008_add_problem_images.py:16,28` `models.ImageField`（0009 で `CharField` に変更済みの過去のマイグレーション。`ImageField` の検査は現行モデルに無い）
- `backend/problems/validators.py:21,24,39` の `image.size` / `image.name` は Django の `UploadedFile` の属性（バイト数・ファイル名）で、Pillow ではない

→ **関係する非互換変更は 0 件**。アプリのコードは変更しない。

### 2-5. 事前スパイク（使い捨てコンテナ・リポジトリ無変更）

`docker compose run --rm` の使い捨てコンテナに `pip install Pillow==13.0.0` を入れて確かめた（コンテナ終了で消える。イメージ・リポジトリは不変）。

| 検証項目 | 12.3.0 | 13.0.0 |
|---|---|---|
| Python 3.11 向けのビルド済み wheel | — | `pillow-13.0.0-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` が存在 |
| backend 全テスト | 94 passed | **94 passed** |
| `validate_image_file`: PNG 10x10 | `(True, None)` | `(True, None)` |
| 同: JPEG 10x10 | `(True, None)` | `(True, None)` |
| 同: WebP 10x10 | `(True, None)` | `(True, None)` |
| 同: PNG 4096x1 | `(True, None)` | `(True, None)` |
| 同: PNG 4097x1 | `(False, '画像サイズが大きすぎます（4097x1）。最大4096x4096ピクセルまでです。')` | 同じ |
| 同: 先頭 16 バイトだけの PNG | `(False, '画像ファイルの読み込みに失敗しました: Truncated File Read')` | 同じ |
| 新規テスト案（9 件）＋ミューテーション・プローブ | 全 9 件 pass・4 種すべて検知（exit 0） | 全 9 件 pass・4 種すべて検知（exit 0） |
| プローブ自体の反証（中身のないテストを渡す） | 4 種すべて「見逃し」・exit 1 | — |
| 新規テスト案・プローブの ruff（`backend/pyproject.toml`） | `All checks passed!` | — |

→ 更新は無退行で成立する。新規テストは回帰を実際に検知でき、プローブも中身のないテストを正しく不合格にする（false-green ではない）。

### 2-6. 既存テストの抜け（再発防止テストを追加する理由）

`validate_image_file` の Pillow 依存分岐のうち、既存テストが通るのは「正しい PNG を受理する」だけ（`test_I073_image_update.py` の `png_upload`）。`bad.png`（`b"not an image"`）は python-magic の段階で拒否されるので、Pillow まで届かない。

| 分岐 | 既存テスト |
|---|---|
| PNG の受理 | あり（I073） |
| JPEG / WebP の受理 | **なし** |
| 4096 ピクセル境界の受理・4097 の拒否（`utils.py:85-89`） | **なし** |
| MIME は通るが Pillow で読めない画像の拒否（`utils.py:93-94`） | **なし** |

→ 設計確認メモ（2026-10-21・ユーザー回答「追加する」）のとおり、この 3 つの分岐を確かめるユニットテストを追加する。Pillow の版を上げるたびに同じ確認が自動で行われる。

### 2-7. 環境前提の確認（`plan-writing-rules.md`「環境前提確認」）

| 前提 | 確認方法 | 結果 |
|---|---|---|
| Docker | `docker compose --project-directory /mnt/c/app/wt-harness up -d --build --wait backend` | backend / db / redis が healthy（2026-10-21） |
| `.env`（ポートのオフセット） | `docker compose config` の published ports | 8010 / 5442 / 6389 / 3010。主作業側と衝突しない |
| pip-audit | `backend/requirements-dev.txt` に含まれ、dev イメージに入っている | コンテナ内で実行できる（2-1） |
| Python | `backend/Dockerfile:2`・`ci.yml:17,70` | 3.11。13.0.0 の対応範囲内 |

### 2-8. 依存ファイル変更の波及（Dockerfile・compose）

| 対象 | 波及 |
|---|---|
| `backend/Dockerfile:18-19` | `base` ステージで `requirements.txt` をインストールする。`dev`（`:22`）も `production`（`:33`）も `base` から作るので、両方に 13.0.0 が入る。**Dockerfile の変更は不要** |
| `docker-compose.yml` | `backend`（`:36-39`）・`celery`（`:75-78`）・`celery-beat`（`:96-99`）・`e2e-init`（`:143-146`・profile 配下）が `backend/Dockerfile` の `dev` を使う。**3 サービスの再ビルドが必要**（e2e-init は CI の E2E ジョブがビルドする）。frontend（`Dockerfile.dev`）は無関係 |
| `backend/requirements-dev.txt` | Pillow を含まない。変更不要 |
| `.github/workflows/ci.yml` / `dependency-audit.yml` | `requirements.txt` を読むだけ。変更不要 |

### 2-9. 既知の非ブロッキング事項
- `backend/core/storage_service.py:2` の `import imghdr` の `DeprecationWarning`、`rest_framework/pagination.py` の `UnorderedObjectListWarning` は、ベースラインから出ている警告。本イシューの対象外。

---

## 3. 受け入れ条件

イシューの AC をそのまま採用する（番号は本計画での参照用）。

| AC | 内容 | 検証 |
|---|---|---|
| AC-1 | `backend/requirements.txt` が `Pillow==13.0.0` になっている | TC-AUTO-01 |
| AC-2 | `backend/` で `pip-audit -r requirements.txt` が exit 0 | TC-AUTO-02 |
| AC-3 | backend の Docker イメージが再ビルドでき、コンテナ内の `PIL.__version__` が `13.0.0` | TC-AUTO-00・TC-AUTO-03 |
| AC-4 | 画像関連の既存テストと backend の全テストが通る | TC-AUTO-06 |
| AC-5 | `test_I180_image_validation.py` の 9 件が通り、ミューテーション・プローブが exit 0 | TC-AUTO-04・TC-AUTO-05 |
| AC-6 | CI（Backend Lint & Security を含む全ジョブ）が緑 | TC-AUTO-07 |
| AC-7 | 非互換変更の該当有無と、8 件の CVE が影響する処理が計画書に記録されている | 本計画 §2-3・§2-4（review.md の観点 4 で確認） |

---

## 4. 影響範囲

| 区分 | 内容 |
|---|---|
| Backend | `backend/requirements.txt`（Pillow の版）。テスト追加 `backend/problems/tests/test_I180_image_validation.py`。アプリのコードは変更しない |
| Frontend | なし |
| DB | なし（マイグレーションなし） |
| Config/Infra | backend / celery / celery-beat のイメージ再ビルド。`backend/Dockerfile`・`docker-compose.yml`・CI ワークフローは変更なし（§2-8） |
| Docs | `docs/tests/open/I180_mutation_probe.py`（検証用プローブ）・`docs/tests/open/I180_probe_vacuous_fixture.py`（プローブ自体の反証用。中身のないテスト） |

---

## 5. 変更点一覧（具体）

### 修正アプローチ
依存の 1 行を上げ、Pillow を呼ぶ唯一の箇所（アップロード検証）の分岐を確かめるテストを足す。テストが本当に回帰を捕まえるかを、本番コードを実行時だけ壊すプローブで確かめる。

### 5-1. `backend/requirements.txt`
**修正方針**: 脆弱性 8 件の修正版に上げる。`==` の完全固定を保つ。

```diff
-Pillow==12.3.0
+Pillow==13.0.0
```

### 5-2. `backend/problems/tests/test_I180_image_validation.py`（新規）
**修正方針**: `validate_image_file` を直接呼ぶユニットテスト。DB は使わない。期待値は現行の戻り値（`(True, None)`・エラーメッセージの完全一致）で固定する。

| テスト | パラメータ | 期待値 |
|---|---|---|
| `test_allowed_formats_pass` | `a.png`/PNG/`image/png`・`a.jpg`/JPEG/`image/jpeg`・`a.jpeg`/JPEG/`image/jpeg`・`a.webp`/WEBP/`image/webp`（10x10） | `(True, None)` |
| `test_max_dimension_boundary_passes` | `(4096, 1)`・`(1, 4096)` | `(True, None)` |
| `test_over_max_dimension_rejected` | `(4097, 1)`・`(1, 4097)` | `(False, "画像サイズが大きすぎます（{w}x{h}）。最大4096x4096ピクセルまでです。")` |
| `test_truncated_png_rejected_by_pillow` | 正しい PNG の先頭 16 バイトだけ（MIME 判定は通る） | `is_valid is False` かつ `error_msg` が `"画像ファイルの読み込みに失敗しました: "` で始まる |

計 9 件。寸法テストは 1 ピクセル幅にしてメモリと実行時間を抑える。壊れた PNG のメッセージは後半（Pillow の例外文）が版で変わりうるため、前半の固定文だけを検証する。

```python
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
```

### 5-3. `docs/tests/open/I180_mutation_probe.py`（新規）
**修正方針**: 新規テストの false-green 検証。`problems.utils` を **pytest のセッション開始時にだけ** 書き換え（リポジトリのファイルは変更しない）、書き換えごとに子プロセスで pytest を走らせる。無改変で exit 0、4 種の書き換えでそれぞれ exit 1（テスト失敗）なら合格（exit 0）。

| ミューテーション | 書き換え | 検知するテスト |
|---|---|---|
| `max_dimension_plus_1` | `MAX_IMAGE_DIMENSION = 4097` | `test_over_max_dimension_rejected` |
| `max_dimension_minus_1` | `MAX_IMAGE_DIMENSION = 4095` | `test_max_dimension_boundary_passes` |
| `drop_webp` | `ALLOWED_IMAGE_FORMATS` から `image/webp` を除く | `test_allowed_formats_pass[a.webp]` |
| `skip_pillow_open` | `utils.Image` を「開かずに 1x1 を返す」偽物に差し替え | `test_truncated_png_rejected_by_pillow` |

判定は pytest の exit code が **ちょうど 1**（テスト失敗）であること。収集エラー（2）・テスト無し（5）は検知扱いにしない。置き場所は I151 の `docs/tests/closed/I151_celery_probe.py` と同じく docs/tests（backend の CI には載せない）。backend コンテナは `docs/` を `/app/docs` にマウントするので、コンテナ内から実行できる。ファイル名は `test_*.py` に一致しないので、`pytest.ini`（`python_files = test_*.py`・`testpaths = .`）の通常収集には混ざらない。コードは §2-5 のスパイクで動かしたものをそのまま使う（ruff 済み）。

```python
"""
I180: 新規テスト（test_I180_image_validation.py）の false-green 検証（ミューテーション・プローブ）。

検証対象 problems.utils を実行時にだけ書き換え（リポジトリのファイルは変更しない）、
書き換えごとに新規テストが「失敗」すること、無改変では「成功」することを確かめる。

使い方（backend コンテナ内・/app で実行）:
    python docs/tests/open/I180_mutation_probe.py [テストファイルのパス]
合格 = exit 0（無改変で pytest exit 0、かつ全ミューテーションで pytest exit 1）。
不合格 = exit 1。
"""
import subprocess
import sys

DEFAULT_TARGET = "problems/tests/test_I180_image_validation.py"


class _FakeImage:
    """Pillow で開かずに常に 1x1 を返す（壊れた画像を通してしまう状態）。"""

    size = (1, 1)

    @staticmethod
    def open(_file):
        return _FakeImage()


def _max_dimension_plus_1(utils):
    utils.MAX_IMAGE_DIMENSION = 4097


def _max_dimension_minus_1(utils):
    utils.MAX_IMAGE_DIMENSION = 4095


def _drop_webp(utils):
    utils.ALLOWED_IMAGE_FORMATS = {
        mime: exts for mime, exts in utils.ALLOWED_IMAGE_FORMATS.items() if mime != "image/webp"
    }


def _skip_pillow_open(utils):
    utils.Image = _FakeImage


# ミューテーション名 → problems.utils に適用する書き換え。
# いずれも「本番コードがこう壊れたらテストで検知できるべき」状態を表す。
MUTATIONS = {
    "max_dimension_plus_1": _max_dimension_plus_1,    # 4097 を通してしまう
    "max_dimension_minus_1": _max_dimension_minus_1,  # 4096 を拒否してしまう
    "drop_webp": _drop_webp,                          # 許可形式から WebP が落ちた
    "skip_pillow_open": _skip_pillow_open,            # Pillow で画像を開かなくなった
}
BASELINE = "baseline"


class _MutationPlugin:
    def __init__(self, name):
        self.name = name

    def pytest_sessionstart(self, session):
        if self.name != BASELINE:
            from problems import utils

            MUTATIONS[self.name](utils)


def _apply(name, target):
    """子プロセス側: 1 つのミューテーションを適用して pytest を実行し、その exit code で終わる。"""
    import pytest

    sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", target], plugins=[_MutationPlugin(name)]))


def _run(name, target):
    cmd = [sys.executable, __file__, "--apply", name, target]
    return subprocess.run(cmd, capture_output=True, text=True).returncode  # nosec B603


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--apply":
        _apply(sys.argv[2], sys.argv[3])

    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    ok = True

    rc = _run(BASELINE, target)
    print(f"{BASELINE}（無改変）: pytest exit={rc} → {'OK' if rc == 0 else 'NG（成功するべき）'}")
    ok &= rc == 0

    for name in MUTATIONS:
        rc = _run(name, target)
        print(f"{name}: pytest exit={rc} → {'OK（検知）' if rc == 1 else 'NG（見逃し）'}")
        ok &= rc == 1

    print("✅ 全ミューテーションを検知" if ok else "❌ 検知できないミューテーションあり")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

### 5-4. `docs/tests/open/I180_probe_vacuous_fixture.py`（新規）
**修正方針**: プローブ自体の反証用。何も検証しないテストを 1 つだけ持つ。プローブにこれを渡すと 4 種すべて「見逃し」で exit 1 になること（＝プローブが常に合格を返す壊れ方をしていないこと）を TC-AUTO-05 判定 2 で確かめる。ファイル名は `test_*.py` に一致しない（通常収集に混ざらない）。

```python
from problems.utils import validate_image_file


def test_vacuous():
    assert callable(validate_image_file)
```

---

## 6. 実装手順（ステップ）

依存関係: ステップ 2 はステップ 1 の完了が前提（13.0.0 のイメージで新規テストを確かめるため）。ステップ 3 はステップ 2 の完了が前提。

### ステップ 0: 実行環境の前提
- wt-harness の compose で backend / celery / celery-beat を起動する → TC-AUTO-00 参照

### ステップ 1: Pillow 13.0.0 への更新（未知リスク先行＝依存更新とイメージ再ビルドを最初に置く）
1. `backend/requirements.txt:8` を §5-1 のとおり変更する（ガードの ask が出る。承認済みの依存更新として進める）
2. backend / celery / celery-beat のイメージを再ビルドして起動し直す → TC-AUTO-00 参照
3. 宣言・監査・インストール版を確かめる → TC-AUTO-01・TC-AUTO-02・TC-AUTO-03 参照
4. 既存テストの無退行を確かめる → TC-AUTO-06 参照（この時点では 94 件）
5. コミット: `fix(I180): Pillow を 13.0.0 に更新し既知脆弱性 8 件を解消`

### ステップ 2: 再発防止テストとプローブの追加
1. §5-2 のテスト、§5-3 のプローブ、§5-4 の反証用フィクスチャを追加する
2. 新規テストを確かめる → TC-AUTO-04 参照
3. プローブで false-green でないことを確かめる → TC-AUTO-05 参照
4. 全テストを確かめる → TC-AUTO-06 参照（103 件）
5. コミット: `test(I180): 画像アップロード検証の Pillow 依存分岐の再発防止テストを追加`

### ステップ 3: 手動テスト・CI
1. 手動テスト（`docs/tests/open/I180_manual_test.md`）を実施する
2. push して CI の全チェックを確かめる → TC-AUTO-07 参照

---

## 7. テスト計画

### テストレベル
| レベル | 対象 | 文書 |
|---|---|---|
| 静的検証（決定論ゲート） | 宣言（`requirements.txt`）・新規ファイルの存在と構文 | auto_test「決定論ゲート（自動実走）」 |
| ツール実行 | `pip-audit`・インストール版 | TC-AUTO-02・03 |
| ユニット | `validate_image_file` の Pillow 依存分岐（新規 9 件） | TC-AUTO-04 |
| テスト品質の検証 | ミューテーション・プローブ（4 種）とプローブ自体の反証 | TC-AUTO-05 |
| 結合（既存） | 画像アップロードを含む backend 全テスト（I073 の multipart 結合テストを含む） | TC-AUTO-06 |
| CI | 全 6 チェック（Backend Lint & Security / Backend Tests / Frontend Type Check / Frontend Lint & Security / Frontend Tests / E2E Tests (Playwright)） | TC-AUTO-07 |
| 手動（Claude） | 再ビルド後のコンテナの起動・ヘルスチェック・celery worker の起動 | manual_test |

### 再発防止テスト
- 本イシューはバグ修正ではなく依存更新だが、更新で壊れうる分岐（§2-6）に再発防止テストを追加する（TC-AUTO-04）。
- 認可・テナント境界の変更は無いため、その種のテストは追加しない。既存の認可テストは TC-AUTO-06 の全件実行に含まれる。

### 手動テストの範囲
アップロードの流れ（multipart → 検証 → 保存）は、既存の結合テスト（I073）が実際の Pillow とファイル保存で確かめている。手動テストでは、テストではカバーされない「再ビルドしたイメージでのサーバー起動・ヘルスチェック・celery worker の起動」を Claude が確かめる。画面は変えないので、Human の手順は置かない。

---

## 8. ロールバック
- `git revert` で 2 コミット（ステップ 2 → ステップ 1 の順）を戻し、backend / celery / celery-beat を再ビルドする。データ・マイグレーションの変更が無いため、ほかの手当ては不要。
- ただし戻すと `pip-audit` が再び 8 件で失敗する。戻すのは 13.0.0 で本番障害が出た場合に限る。

---

## 9. Risk & 回避策

| リスク | 回避策 |
|---|---|
| メジャー更新で画像の読み込みが変わる | 非互換変更の全件突き合わせ（§2-4）で該当 0。スパイク（§2-5）で 94 件と 6 パターンの検証が同じ結果。新規テスト（TC-AUTO-04）で今後も機械的に検知する |
| 再ビルド漏れ（celery 系が古いイメージのまま） | TC-AUTO-03 で 3 サービスそれぞれの `PIL.__version__` を判定する |
| 新規テストが中身のない合格（false-green）になる | TC-AUTO-05 のプローブで 4 種の書き換えを検知することと、プローブ自体が中身のないテストを不合格にすることを確かめる |
| 監査の結果が日々変わる（新しい advisory の公開） | TC-AUTO-02 をステップ 1 で実行し、CI（TC-AUTO-07）でも再確認する。Pillow 以外で新しい検出が出た場合はイシューのスコープ外として別イシューにする |
| CI 環境（ubuntu の Python 3.11）で WebP が扱えない | Pillow の公式 wheel は libwebp を同梱している。CI の Backend Tests（TC-AUTO-07）で確かめる |

---

## 10〜15. 条件付きセクション
- **データ整合性（10）**: DB 変更なし → 対象外
- **運用設計（11）**: 外部 API・非同期処理の変更なし（celery はイメージ再ビルドのみ・コード不変）→ 対象外
- **コスト・保守（12）**: 新規インフラなし。追加の保守はテスト 1 ファイル（9 件・約 0.1 秒）→ 対象外
- **性能・UX（13）**: フロントエンド変更なし・性能要件なし → 対象外（P6 影響なし）
- **学習効果（14）**: 対象外
- **プライバシー（15）**: 個人情報・テナントデータの扱いの変更なし → 対象外（P9 影響なし）

---

## 11. 計画時チェック（plan-issue 必須チェックの結果）

### 要件適合性・業務ロジック
- AC の範囲を超える仕様追加・仕様変更はない。追加テストはアプリの挙動を変えず、現行の戻り値をそのまま固定する（設計確認メモでユーザー承認済み）。
- マルチテナント・ステータス遷移・承認条件: 変更なし。
- エッジケース: 寸法の境界（4096 / 4097・幅と高さの両方）と、MIME は通るが Pillow で読めない入力をテストで押さえる。

### セキュリティ・ベストプラクティス
- 入力バリデーション: アップロード検証のロジックは変えない。Pillow 依存の分岐にテストを追加して守りを固める。
- 認証・認可・機密データ・OWASP: 変更なし。
- 依存の既知脆弱性: 更新後セットを `pip-audit` で実走済み（§2-2・0 件）。
- スキャンの重大度基準: pip-audit は検出 0 件を合格とする（CI と同じ）。bandit は MEDIUM 以上を修正対象・LOW は `# nosec` で抑制（新規テストは `backend/*/tests/` で bandit の対象外。プローブは `docs/` で対象外だが、`subprocess` の呼び出しに `# nosec B603` を付けて意図を明示する）。npm audit は frontend 変更なしで対象外。

### テスト計画
- 再発防止テスト: TC-AUTO-04（§7）。
- テストレベル: §7 の表で明示。
- 認可・テナント境界: 認可変更なし。既存テストは TC-AUTO-06 に含まれる。

### データ整合性・運用性・コスト
- P3/P5/P8 影響なし（DB・外部 API・インフラの変更なし）。
- 依存ファイル変更の Dockerfile / compose への波及: §2-8 に記載（Dockerfile 変更不要・3 サービスの再ビルドが必要）。

### 性能・UX / プライバシー
- P6 影響なし・P9 影響なし。

### 設計品質
- アンチパターンの踏襲なし。テストは `validate_image_file` の公開インターフェースを検証し、内部実装をなぞらない。
- 設定値: テストの期待メッセージに 4096 を直書きする。これは「上限が変わったらテストが落ちるべき」という仕様の固定であり、`MAX_IMAGE_DIMENSION` を import して期待値を組み立てると、上限が誤って変わっても気づけなくなる（プローブの `max_dimension_plus_1` / `minus_1` はこれを検知する）。
- 例外処理: 変更なし。

### 設計判断の明示
| 設計判断 | 根拠 |
|---|---|
| Pillow の版を 13.0.0 にする | イシューに明記 |
| アプリのコード（`utils.py`）は変更しない | イシューに明記（「変更不要の見込み」を §2-4 で確定） |
| 再発防止テストを追加する（9 件・ユニット） | 設計確認メモ（2026-10-21 ユーザー回答） |
| テストの置き場所 `backend/problems/tests/test_I180_image_validation.py` | 既存の `test_I0xx_*.py` の命名に合わせた（設計確認メモに記載） |
| プローブを `docs/tests/open/` に置き CI に載せない | 設計確認メモに記載。I151 の `I151_celery_probe.py` と同じ扱い |
| Dockerfile・compose・CI を変えない | §2-8 の調査結果（イシューの影響範囲「変更不要の見込み」を確定） |

→ 「仮定で決めた」項目はない。

### 別イシュー候補（本イシューでは扱わない）
- `Image.open(file)` に `formats=["PNG", "JPEG", "WEBP"]` を渡し、python-magic の判定に加えて Pillow 側でも開く形式を限定する（多層防御）。アプリのコード変更で、イシューのスコープ「画像処理の仕様変更を含まない」の外になるため、本イシューでは扱わない。

---

## 12. 承認ポイント
- [ ] 計画内容: Pillow を 13.0.0 に上げる（依存の 1 行）。アプリのコードは変えない
- [ ] 再発防止テスト 9 件の追加と、テストが本当に効くかを確かめるプローブ（docs 配下・CI には載せない）
- [ ] 調査結果: 8 件の脆弱性は、いまのコードでは届かない処理（TIFF・GIF・EPS・PDF 等）だが、CI 復旧と多層防御のために更新する。非互換変更で関係するものは 0 件
- [ ] Danger Ops: 無（データ・マイグレーションの変更なし。`requirements.txt` の編集でガードの確認が出る）
- [ ] テスト計画: 自動 TC-AUTO-00〜07・手動は Claude が実施（Human の手順なし）

## レビュー結果
- [20261021_0958 判定: ✅ 完了](../../reviews/I180_plan_review_20261021_0958.md)
