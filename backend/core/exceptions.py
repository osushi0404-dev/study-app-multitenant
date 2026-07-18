from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    カスタム例外ハンドラー
    エラーレスポンスをメインメッセージとサブメッセージの形式に変換します
    """
    response = exception_handler(exc, context)

    if response is not None:
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
