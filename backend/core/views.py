"""
監視システム API ビュー
"""

import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from .monitoring import (
    PerformanceMonitor,
    ErrorTracker,
    AlertManager,
    UserActivityMonitor,
)
from .cache_service import CacheService


class HealthCheckView(View):
    """ヘルスチェックAPI"""

    def get(self, request):
        """システムヘルスチェック"""
        try:
            health_data = PerformanceMonitor.get_comprehensive_health_check()

            status_code = 200
            if health_data['overall_status'] == 'error':
                status_code = 503
            elif health_data['overall_status'] == 'warning':
                status_code = 200

            return JsonResponse(health_data, status=status_code)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e),
                'overall_status': 'error',
                'timestamp': timezone.now().isoformat()
            }, status=503)


@method_decorator([login_required, staff_member_required], name='dispatch')
class SystemStatusView(View):
    """システム状態詳細API（管理者のみ）"""

    def get(self, request):
        """詳細なシステム状態を取得"""
        try:
            # 基本ヘルスチェック
            health_data = PerformanceMonitor.get_comprehensive_health_check()

            # エラーサマリー
            error_summary = ErrorTracker.get_error_summary(days=1)

            # アクティビティサマリー
            activity_summary = UserActivityMonitor.get_activity_summary(days=1)

            # アラート
            alerts = AlertManager.check_and_send_alerts()

            # システム情報
            system_info = {
                'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
                'debug_mode': settings.DEBUG,
                'allowed_hosts': settings.ALLOWED_HOSTS,
                'timezone': str(settings.TIME_ZONE),
                'database_engine': settings.DATABASES['default']['ENGINE'],
                'cache_backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown'),
            }

            return JsonResponse({
                'health': health_data,
                'errors': error_summary,
                'activity': activity_summary,
                'alerts': alerts,
                'system_info': system_info,
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)


@method_decorator([login_required, staff_member_required], name='dispatch')
class ErrorSummaryView(View):
    """エラーサマリーAPI（管理者のみ）"""

    def get(self, request):
        """エラーサマリーを取得"""
        try:
            days = int(request.GET.get('days', 7))
            days = min(days, 30)  # 最大30日

            error_summary = ErrorTracker.get_error_summary(days=days)

            return JsonResponse(error_summary)

        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)


@method_decorator([login_required, staff_member_required], name='dispatch')
class PerformanceMetricsView(View):
    """パフォーマンスメトリクスAPI（管理者のみ）"""

    def get(self, request):
        """パフォーマンスメトリクスを取得"""
        try:
            # リアルタイムメトリクス
            current_metrics = {
                'database': PerformanceMonitor.monitor_database_performance(),
                'redis': PerformanceMonitor.monitor_redis_performance(),
                'system': PerformanceMonitor.monitor_system_resources(),
            }

            # 履歴データ（過去24時間の平均）
            historical_metrics = self._get_historical_metrics()

            return JsonResponse({
                'current': current_metrics,
                'historical': historical_metrics,
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)

    def _get_historical_metrics(self):
        """過去のメトリクスを取得（簡易実装）"""
        # 本格的な実装では時系列データベースや詳細なキャッシュが必要
        return {
            'note': 'Historical metrics would require time-series storage',
            'database_avg_response_time': 50.0,
            'redis_avg_response_time': 10.0,
            'system_avg_cpu': 45.0,
            'system_avg_memory': 60.0
        }


@method_decorator([login_required, staff_member_required], name='dispatch')
class ActivitySummaryView(View):
    """アクティビティサマリーAPI（管理者のみ）"""

    def get(self, request):
        """ユーザーアクティビティサマリーを取得"""
        try:
            days = int(request.GET.get('days', 7))
            days = min(days, 30)

            activity_summary = UserActivityMonitor.get_activity_summary(days=days)

            return JsonResponse(activity_summary)

        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)


@method_decorator([login_required, staff_member_required], name='dispatch')
class AlertsView(View):
    """アラートAPI（管理者のみ）"""

    def get(self, request):
        """現在のアラートを取得"""
        try:
            alerts = AlertManager.check_and_send_alerts()

            return JsonResponse({
                'alerts': alerts,
                'count': len(alerts),
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)


@method_decorator([login_required, staff_member_required, csrf_exempt], name='dispatch')
class ClearCacheView(View):
    """キャッシュクリアAPI（管理者のみ）"""

    def post(self, request):
        """キャッシュをクリア"""
        try:
            cache_service = CacheService()

            # クリアするキャッシュタイプ
            cache_types = json.loads(request.body).get('types', ['all'])

            results = {}

            if 'all' in cache_types:
                cache.clear()
                results['default_cache'] = 'cleared'

            if 'problems' in cache_types:
                cache_service.clear_problems_cache()
                results['problems_cache'] = 'cleared'

            if 'users' in cache_types:
                cache_service.clear_user_cache()
                results['users_cache'] = 'cleared'

            if 'statistics' in cache_types:
                cache_service.clear_statistics_cache()
                results['statistics_cache'] = 'cleared'

            return JsonResponse({
                'success': True,
                'results': results,
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)


@method_decorator([login_required, staff_member_required], name='dispatch')
class CacheStatsView(View):
    """キャッシュ統計API（管理者のみ）"""

    def get(self, request):
        """キャッシュ統計を取得"""
        try:
            # Redis統計（利用可能な場合）
            stats = {}

            try:
                redis_client = cache._cache.get_client()
                info = redis_client.info()

                stats['redis'] = {
                    'used_memory': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'total_commands_processed': info.get('total_commands_processed'),
                    'keyspace_hits': info.get('keyspace_hits'),
                    'keyspace_misses': info.get('keyspace_misses'),
                    'hit_rate': round(
                        info.get('keyspace_hits', 0) /
                        max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100,
                        2
                    )
                }
            except Exception as redis_error:
                stats['redis'] = {'error': str(redis_error)}

            # アプリケーションレベルの統計
            cache_service = CacheService()
            app_stats = cache_service.get_cache_stats()
            stats['application'] = app_stats

            return JsonResponse({
                'stats': stats,
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=500)
