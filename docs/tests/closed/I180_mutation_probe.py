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
