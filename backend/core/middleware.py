"""
Django ミドルウェア - 監視システム統合
"""

import time
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from .monitoring import (
    RequestMonitor,
    ErrorTracker,
    UserActivityMonitor,
)


class MonitoringMiddleware(MiddlewareMixin):
    """監視システム統合ミドルウェア"""

    def process_request(self, request):
        """リクエスト開始時の処理"""
        request._monitoring_start_time = time.time()
        return None

    def process_response(self, request, response):
        """レスポンス処理時の監視"""
        # レスポンス時間計算
        if hasattr(request, '_monitoring_start_time'):
            response_time_ms = (time.time() - request._monitoring_start_time) * 1000

            # 遅いリクエストの監視
            RequestMonitor.log_slow_request(request, response_time_ms)

            # ユーザーアクティビティの記録
            if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
                activity_type = self._get_activity_type(request)
                if activity_type:
                    UserActivityMonitor.log_user_activity(
                        user=request.user,
                        activity_type=activity_type,
                        details={
                            'method': request.method,
                            'path': request.path,
                            'status_code': response.status_code,
                            'response_time_ms': round(response_time_ms, 2)
                        }
                    )

        return response

    def process_exception(self, request, exception):
        """例外処理時のエラー追跡"""
        context = {
            'method': request.method,
            'path': request.path,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': self._get_client_ip(request),
        }

        user = request.user if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) else None

        ErrorTracker.log_error(
            error=exception,
            context=context,
            user=user
        )

        return None

    def _get_activity_type(self, request) -> str:
        """リクエストからアクティビティタイプを判定"""
        path = request.path.lower()
        method = request.method.upper()

        # API エンドポイントベースの判定
        if '/api/auth/' in path:
            if 'login' in path:
                return 'login'
            elif 'logout' in path:
                return 'logout'
            elif 'register' in path:
                return 'register'

        elif '/api/problems/' in path:
            if method == 'GET':
                return 'view_problems'
            elif method == 'POST':
                return 'create_problem'
            elif method in ['PUT', 'PATCH']:
                return 'edit_problem'
            elif method == 'DELETE':
                return 'delete_problem'

        elif '/api/quiz/' in path:
            if 'start' in path:
                return 'start_quiz'
            elif 'submit' in path:
                return 'submit_answer'
            elif 'complete' in path:
                return 'complete_quiz'

        elif '/api/study/' in path:
            return 'study_session'

        elif '/api/spaced-repetition/' in path:
            return 'spaced_repetition'

        elif '/api/statistics/' in path:
            return 'view_statistics'

        elif '/api/settings/' in path:
            return 'update_settings'

        # デフォルトは一般的なページアクセス
        return 'page_access'

    def _get_client_ip(self, request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class HealthCheckMiddleware(MiddlewareMixin):
    """ヘルスチェックエンドポイント用ミドルウェア"""

    def process_request(self, request):
        """ヘルスチェックリクエストの処理"""
        if request.path == '/health/' and request.method == 'GET':
            from .monitoring import PerformanceMonitor

            try:
                health_data = PerformanceMonitor.get_comprehensive_health_check()

                # HTTPステータスコードの決定
                status_code = 200
                if health_data['overall_status'] == 'error':
                    status_code = 503  # Service Unavailable
                elif health_data['overall_status'] == 'warning':
                    status_code = 200  # OK but with warnings

                return JsonResponse(health_data, status=status_code)

            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e),
                    'overall_status': 'error'
                }, status=503)

        return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """リクエスト開始/終了ログ出力ミドルウェア"""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        import logging
        self.logger = logging.getLogger('django')

        # エンドポイントと処理名のマッピング
        self.endpoint_mapping = {
            '/api/auth/register/': '会員登録処理',
            '/api/auth/login/': 'ログイン処理',
            '/api/auth/logout/': 'ログアウト処理',
            '/api/auth/verify-email/': 'メール認証処理',
            '/api/auth/password-reset/': 'パスワードリセット処理',
            '/api/auth/password-reset-confirm/': 'パスワードリセット確認処理',
            '/api/auth/change-password/': 'パスワード変更処理',
            '/api/profile/': 'プロフィール処理',
            '/api/settings/': '設定変更処理',
            '/api/streak/': 'ストリーク取得処理',
            '/api/problems/': '問題管理処理',
            '/api/quiz/': 'クイズ処理',
            '/api/quiz/start/': 'クイズ開始処理',
            '/api/quiz/submit/': '解答送信処理',
            '/api/quiz/complete/': 'クイズ完了処理',
            '/api/study/': '学習セッション処理',
            '/api/spaced-repetition/': '間隔反復処理',
            '/api/statistics/': '統計情報処理',
            '/api/dashboard/': 'ダッシュボード処理',
        }

    def _get_process_name(self, path, method):
        """パスとメソッドから処理名を取得"""
        # 完全一致を優先
        if path in self.endpoint_mapping:
            return self.endpoint_mapping[path]

        # 部分一致でチェック
        for endpoint, process_name in self.endpoint_mapping.items():
            if path.startswith(endpoint):
                # メソッドに応じて処理名を調整
                if method == 'GET':
                    if '一覧' not in process_name and '取得' not in process_name:
                        return process_name.replace('処理', '取得処理')
                elif method == 'POST':
                    if '登録' not in process_name and '作成' not in process_name:
                        return process_name.replace('処理', '作成処理')
                elif method == 'PUT' or method == 'PATCH':
                    return process_name.replace('処理', '更新処理')
                elif method == 'DELETE':
                    return process_name.replace('処理', '削除処理')
                return process_name

        # マッピングにない場合は汎用的な名前
        return f'API処理({path})'

    def process_request(self, request):
        """リクエスト開始時のログ出力"""
        # 静的ファイルやヘルスチェックは除外
        if request.path.startswith('/static/') or request.path == '/health/':
            return None

        # APIリクエストのみログ出力
        if request.path.startswith('/api/'):
            process_name = self._get_process_name(request.path, request.method)
            user_info = 'anonymous'
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_info = f'{request.user.email}'

            self.logger.info(f'[START] {process_name} - Method: {request.method} - User: {user_info}')

            # リクエストに処理名を保存（レスポンス時に使用）
            request._process_name = process_name
            request._start_time = time.time()

        return None

    def process_response(self, request, response):
        """レスポンス処理時のログ出力"""
        # 処理名が保存されている場合のみログ出力
        if hasattr(request, '_process_name'):
            process_name = request._process_name
            status_code = response.status_code

            # 処理時間の計算
            elapsed_time = 0
            if hasattr(request, '_start_time'):
                elapsed_time = (time.time() - request._start_time) * 1000  # ミリ秒

            self.logger.info(f'[END  ] {process_name} - Status: {status_code} - Time: {elapsed_time:.2f}ms')

        return response

    def process_exception(self, request, exception):
        """例外発生時のログ出力"""
        if hasattr(request, '_process_name'):
            process_name = request._process_name
            self.logger.error(f'[ERROR] {process_name} - Exception: {str(exception)}')

        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """セキュリティヘッダー追加ミドルウェア"""

    def process_response(self, request, response):
        """セキュリティヘッダーの追加"""
        # HTTPS 強制 (本番環境)
        if not request.is_secure() and hasattr(request, 'get_host'):
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # XSS 保護
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'

        # リファラーポリシー
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # コンテンツセキュリティポリシー（基本的な設定）
        if not response.get('Content-Security-Policy'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
            response['Content-Security-Policy'] = csp

        return response
