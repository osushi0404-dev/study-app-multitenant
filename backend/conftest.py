import pytest


@pytest.fixture(autouse=True)
def _disable_api_throttling(settings):
    """単体テストでは DRF スロットルを無効化する（I127）。
    core/throttling.py のアプリ専用クラスが本フラグをリクエスト時に評価するため、
    ビューの import タイミングに依存せず確実に無効化される（計画 発見4・案F）。
    スロットル自体を検証するテストは override_settings(API_THROTTLE_ENABLED=True)
    で明示的に再有効化する（core/tests/test_I127_throttling.py 参照）。"""
    settings.API_THROTTLE_ENABLED = False
