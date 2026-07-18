"""
I127: DRF スロットル（API 全体の基本レート制限）の回帰テスト。

- レート超過で 429 + Retry-After + 統一 JSON（anon/user 両系統）
- RATELIMIT_ENABLE スイッチ連動（env 解釈＋スイッチ off でスロットル無効）
- スロットル設定（クラス・レート値）が settings に集約され確定値と一致
- 通常利用レンジ（10 連続リクエスト）で 429 にならない

TC-AUTO-01〜05（docs/tests/open/I127_auto_test.md）に対応。
conftest.py の autouse フィクスチャ（API_THROTTLE_ENABLED=False）が全テストで
スロットルを無効化するため、本ファイルのスロットル TC のみ
override_settings(API_THROTTLE_ENABLED=True, ...) で明示的に再有効化する。

本番の core/throttling.py アプリ専用クラスが有効スイッチ・レート値をリクエスト時に
settings からライブ評価するため、標準の override_settings だけで決定論的に制御できる
（実行順非依存・plan 調査結果の発見4=案F）。
"""
import os
import subprocess
import sys

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory

User = get_user_model()

# personal 組織の有無に関わらず 200/[] を返す既存仕様（I115）のためステータス検証に使える
PUBLIC_ROUTE = "/api/organizations/subjects/public/?slug=personal"
AUTH_ROUTE = "/api/subjects/"

# default 以外も必須（sessions はセッションミドルウェア、sessions/problems は
# core/cache_service.py が参照。default のみだと InvalidCacheBackendError で 500）
THROTTLE_TEST_CACHES = {
    alias: {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": f"throttle-test-{alias}",
    }
    for alias in ("default", "sessions", "problems", "analytics")
}


def low_rate_rest_framework():
    """低レートに差し替えた REST_FRAMEWORK 設定を返す。
    アプリ専用クラス（core/throttling.py）がレート値をリクエスト時にライブ参照する。"""
    return {
        **django_settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {"anon": "3/min", "user": "3/min"},
    }


@pytest.fixture
def auth_user(db):
    category = OrganizationCategory.objects.create(name="テストI127", slug="test-cat-i127")
    org = Organization.objects.create(name="組織A_I127", slug="org-a-i127", category=category)
    return User.objects.create_user(
        email="user_i127@example.com", user_id="user_i127", password="pass",
        organization=org, role="user",
    )


# ---- TC-AUTO-01(a) + TC-AUTO-02: 未認証のレート超過で 429 + Retry-After + 統一 JSON ----
@pytest.mark.django_db
def test_anon_rate_limit_returns_429_with_unified_body():
    with override_settings(
        API_THROTTLE_ENABLED=True,
        REST_FRAMEWORK=low_rate_rest_framework(),
        CACHES=THROTTLE_TEST_CACHES,
    ):
        caches["default"].clear()
        client = APIClient()
        for _ in range(3):
            assert client.get(PUBLIC_ROUTE).status_code == status.HTTP_200_OK
        response = client.get(PUBLIC_ROUTE)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert 1 <= int(response.headers["Retry-After"]) <= 60
        body = response.json()
        assert body["error"]["main_message"] == "リクエストが多すぎます"
        assert body["error"]["sub_message"] == "しばらく時間をおいて再度お試しください"
        assert body["error"]["details"] == {}


# ---- TC-AUTO-01(b): 認証済みユーザーのレート超過で 429 ----
@pytest.mark.django_db
def test_user_rate_limit_returns_429(auth_user):
    with override_settings(
        API_THROTTLE_ENABLED=True,
        REST_FRAMEWORK=low_rate_rest_framework(),
        CACHES=THROTTLE_TEST_CACHES,
    ):
        caches["default"].clear()
        client = APIClient()
        client.force_authenticate(user=auth_user)
        for _ in range(3):
            assert client.get(AUTH_ROUTE).status_code == status.HTTP_200_OK
        response = client.get(AUTH_ROUTE)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


# ---- TC-AUTO-03(a): RATELIMIT_ENABLE 環境変数 → API_THROTTLE_ENABLED の解釈 ----
@pytest.mark.parametrize(
    "env_value,expected_enabled",
    [
        ("false", False),  # 無効化: E2E CI と同じ設定
        (None, True),      # 既定（未設定=有効）
    ],
)
def test_api_throttle_switch_follows_ratelimit_env(env_value, expected_enabled):
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "core.settings"}
    env.pop("RATELIMIT_ENABLE", None)
    if env_value is not None:
        env["RATELIMIT_ENABLE"] = env_value
    probe = (
        "import django; django.setup(); from django.conf import settings; "
        "print(settings.API_THROTTLE_ENABLED)"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(expected_enabled)


# ---- TC-AUTO-03(b): スイッチ off なら低レート超過でも 429 にならない（無効化動作） ----
@pytest.mark.django_db
def test_throttle_disabled_when_switch_off():
    with override_settings(
        API_THROTTLE_ENABLED=False,
        REST_FRAMEWORK=low_rate_rest_framework(),
        CACHES=THROTTLE_TEST_CACHES,
    ):
        caches["default"].clear()
        client = APIClient()
        statuses = [client.get(PUBLIC_ROUTE).status_code for _ in range(10)]
        assert statuses == [status.HTTP_200_OK] * 10


# ---- TC-AUTO-04: スロットル設定の settings 集約と確定値（ハードコード検知） ----
def test_throttle_settings_centralized():
    rest_framework = django_settings.REST_FRAMEWORK
    # 文字列パスのリストで比較する（settings はクラスオブジェクトでなく文字列で定義するため）
    assert rest_framework["DEFAULT_THROTTLE_CLASSES"] == [
        "core.throttling.AppAnonRateThrottle",
        "core.throttling.AppUserRateThrottle",
    ]
    assert rest_framework["DEFAULT_THROTTLE_RATES"] == {"anon": "60/min", "user": "300/min"}
    assert rest_framework["NUM_PROXIES"] == 1


# ---- TC-AUTO-05: 通常利用レンジ（10 連続リクエスト）で 429 にならない（否定系） ----
@pytest.mark.django_db
def test_normal_usage_range_is_not_throttled_anon():
    with override_settings(
        API_THROTTLE_ENABLED=True,
        CACHES=THROTTLE_TEST_CACHES,
    ):
        caches["default"].clear()
        client = APIClient()
        statuses = [client.get(PUBLIC_ROUTE).status_code for _ in range(10)]
        assert statuses == [status.HTTP_200_OK] * 10


@pytest.mark.django_db
def test_normal_usage_range_is_not_throttled_user(auth_user):
    with override_settings(
        API_THROTTLE_ENABLED=True,
        CACHES=THROTTLE_TEST_CACHES,
    ):
        caches["default"].clear()
        client = APIClient()
        client.force_authenticate(user=auth_user)
        statuses = [client.get(AUTH_ROUTE).status_code for _ in range(10)]
        assert statuses == [status.HTTP_200_OK] * 10
