import logging

from django.conf import settings
from rest_framework.views import exception_handler, set_rollback
from rest_framework.exceptions import APIException, ValidationError
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger('django.request')


class EnvironmentMisconfiguredError(APIException):
    """環境構成の不備（サーバー起因）。クライアント入力では回復できないため 500 を返す。

    例: 必須の既定組織（type='personal'）が存在しない等、マイグレーション/初期データの不備。
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'サーバー設定に問題があります'
    default_code = 'environment_misconfigured'


def first_error_message(errors):
    """serializer.errors から先頭のエラーメッセージを 1 つだけ安全に取り出す（I142）。

    `ListField` の要素エラーは index をキーとする dict（例 `{'subject_ids': {1: [...]}}`）に
    なるため、`next(iter(errors.values()))[0]` のような添字アクセスは KeyError を投げる。
    ネストの形に依存せず、必ず文字列（該当なしは None）を返す。
    """
    if isinstance(errors, dict):
        values = errors.values()
    elif isinstance(errors, (list, tuple)):
        values = errors
    else:
        message = str(errors)
        return message or None

    for value in values:
        message = first_error_message(value)
        if message:
            return message
    return None


def custom_exception_handler(exc, context):
    """
    カスタム例外ハンドラー
    エラーレスポンスをメインメッセージとサブメッセージの形式に変換します
    """
    response = exception_handler(exc, context)

    if response is None:
        # DRF が処理しない例外＝想定外（プログラム欠陥）。
        # 握りつぶさずスタックトレースを記録し、統一 JSON の 500 で顕在化させる（I142）。
        # DRF が応答を返すと Django 標準の 500 ログ・got_request_exception シグナル・
        # ErrorContextMiddleware の例外ログを通らないため、切り分けに必要な文脈
        # （ビュー・メソッド・パス・ユーザ）をこのログに含める。
        view = context.get('view')
        request = context.get('request')
        logger.exception(
            "Unhandled exception in %s (%s %s, user=%s)",
            view.__class__.__name__ if view else 'unknown view',
            getattr(request, 'method', '-'),
            getattr(request, 'path', '-'),
            getattr(getattr(request, 'user', None), 'id', 'anonymous'))
        set_rollback()  # ATOMIC_REQUESTS 有効時にトランザクションを確実にロールバックする
        return Response({
            'error': {
                'main_message': 'サーバーエラー',
                'sub_message': (f'{type(exc).__name__}: {exc}' if settings.DEBUG
                                else 'しばらく時間をおいて再度お試しください'),
                'details': {},
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 5xx（APIException 由来）もスタックトレースを記録する（I142）。
    # 注: EnvironmentMisconfiguredError のように raise 元で既に logger.error を出している
    # ケースでは記録が二重になるが、raise 元のログは「何が不足しているか」、ここのログは
    # 「どこで発生したか」を担うため意図的に残す（5xx のみが対象で通常運用では稀）。
    if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.exception("Server error response: %s", type(exc).__name__)

    custom_error_data = {
        'error': {
            'main_message': 'エラーが発生しました',
            'sub_message': None,
            'details': {}
        }
    }

    # ValidationErrorの場合
    if isinstance(exc, ValidationError):
        custom_error_data['error']['main_message'] = '入力内容にエラーがあります'

        # フィールドごとのエラーを処理
        if hasattr(response.data, 'items'):
            errors = []
            for field, error_list in response.data.items():
                if isinstance(error_list, list):
                    errors.extend(error_list)
                else:
                    errors.append(str(error_list))

            # 最初のエラーをサブメッセージとして使用
            if errors:
                custom_error_data['error']['sub_message'] = str(errors[0])
                custom_error_data['error']['details'] = response.data
        else:
            # 単一のエラーメッセージの場合
            if isinstance(response.data, list) and response.data:
                custom_error_data['error']['sub_message'] = str(response.data[0])
            elif isinstance(response.data, dict) and 'detail' in response.data:
                custom_error_data['error']['sub_message'] = response.data['detail']

    # その他のHTTPエラー
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        custom_error_data['error']['main_message'] = 'リソースが見つかりません'
        custom_error_data['error']['sub_message'] = '要求されたデータが存在しません'

    elif response.status_code == status.HTTP_403_FORBIDDEN:
        custom_error_data['error']['main_message'] = 'アクセスが拒否されました'
        custom_error_data['error']['sub_message'] = 'この操作を実行する権限がありません'

    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        custom_error_data['error']['main_message'] = '認証が必要です'
        custom_error_data['error']['sub_message'] = 'ログインしてください'

    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        custom_error_data['error']['main_message'] = 'リクエストが多すぎます'
        custom_error_data['error']['sub_message'] = 'しばらく時間をおいて再度お試しください'

    elif response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        custom_error_data['error']['main_message'] = 'サーバーエラー'
        custom_error_data['error']['sub_message'] = 'しばらく時間をおいて再度お試しください'

    # 元のステータスコードを保持
    response.data = custom_error_data

    return response


def create_error_response(main_message, sub_message=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    統一されたエラーレスポンスを作成するヘルパー関数
    """
    return Response({
        'error': {
            'main_message': main_message,
            'sub_message': sub_message,
            'details': {}
        }
    }, status=status_code)
