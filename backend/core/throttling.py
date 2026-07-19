"""アプリ専用の DRF スロットルクラス（I127）。"""
from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LiveSettingsRateMixin:
    """有効スイッチとレート値をリクエスト時に settings から読む（I127）。

    DRF はスロットル設定（DEFAULT_THROTTLE_CLASSES/RATES）を初回 import 時に
    クラス属性へスナップショットするため、settings の実行時変更が反映されない。
    可変部分をここでライブ評価することで挙動を settings に一元化する（計画 発見4）。
    """

    def allow_request(self, request, view):
        if not settings.API_THROTTLE_ENABLED:
            return True
        return super().allow_request(request, view)

    def get_rate(self):
        return settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'][self.scope]


class AppAnonRateThrottle(LiveSettingsRateMixin, AnonRateThrottle):
    pass


class AppUserRateThrottle(LiveSettingsRateMixin, UserRateThrottle):
    pass
