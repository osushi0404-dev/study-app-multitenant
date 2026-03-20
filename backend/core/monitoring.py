"""
包括的なエラーログと監視システム

アプリケーションの健全性とパフォーマンスを監視し、
エラーの詳細なログとアラートを提供
"""

import logging
import traceback
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import wraps
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.contrib.auth import get_user_model
from django.utils import timezone
import redis

# ログ設定を先に定義
logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None
    logger.warning("psutil module not found. Some monitoring features will be disabled.")

User = get_user_model()

class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    @staticmethod
    def monitor_database_performance():
        """データベースパフォーマンスを監視"""
        try:
            start_time = time.time()
            
            # 簡単なクエリでレスポンス時間を測定
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            response_time = (time.time() - start_time) * 1000  # ミリ秒
            
            # アクティブなコネクション数
            active_connections = len(connection.queries)
            
            return {
                'response_time_ms': round(response_time, 2),
                'active_connections': active_connections,
                'status': 'healthy' if response_time < 100 else 'slow'
            }
        except Exception as e:
            logger.error(f"Database performance monitoring failed: {str(e)}")
            return {
                'response_time_ms': -1,
                'active_connections': -1,
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def monitor_redis_performance():
        """Redis パフォーマンスを監視"""
        try:
            start_time = time.time()
            
            # Redis接続テスト
            cache.set('health_check', 'ok', 10)
            cache.get('health_check')
            
            response_time = (time.time() - start_time) * 1000
            
            # Redis情報を取得
            redis_client = cache._cache.get_client()
            info = redis_client.info()
            
            return {
                'response_time_ms': round(response_time, 2),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'status': 'healthy' if response_time < 50 else 'slow'
            }
        except Exception as e:
            logger.error(f"Redis performance monitoring failed: {str(e)}")
            return {
                'response_time_ms': -1,
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def monitor_system_resources():
        """システムリソースを監視"""
        try:
            if psutil is None:
                return {
                    'error': 'psutil not available',
                    'cpu_percent': 0,
                    'memory_percent': 0,
                    'memory_available_gb': 0,
                    'disk_percent': 0,
                    'disk_free_gb': 0,
                }
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'status': 'healthy' if cpu_percent < 80 and memory.percent < 80 else 'high_load'
            }
        except Exception as e:
            logger.error(f"System resource monitoring failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def get_comprehensive_health_check():
        """包括的なヘルスチェック"""
        health_data = {
            'timestamp': timezone.now().isoformat(),
            'database': PerformanceMonitor.monitor_database_performance(),
            'redis': PerformanceMonitor.monitor_redis_performance(),
            'system': PerformanceMonitor.monitor_system_resources(),
        }
        
        # 全体的なステータス判定
        statuses = [
            health_data['database']['status'],
            health_data['redis']['status'], 
            health_data['system']['status']
        ]
        
        if 'error' in statuses:
            health_data['overall_status'] = 'error'
        elif 'slow' in statuses or 'high_load' in statuses:
            health_data['overall_status'] = 'warning'
        else:
            health_data['overall_status'] = 'healthy'
        
        return health_data


class ErrorTracker:
    """エラー追跡クラス"""
    
    @staticmethod
    def log_error(error: Exception, context: Optional[Dict] = None, user: Optional[User] = None):
        """詳細なエラーログを記録"""
        error_data = {
            'timestamp': timezone.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'user_id': str(user.id) if user else None,
            'user_email': user.email if user else None,
        }
        
        # 詳細ログ
        logger.error(f"Application Error: {json.dumps(error_data, indent=2)}")
        
        # エラー統計の更新
        ErrorTracker._update_error_stats(error_data)
        
        return error_data
    
    @staticmethod
    def _update_error_stats(error_data: Dict):
        """エラー統計を更新"""
        try:
            # 今日のエラーカウント
            today = timezone.now().date().isoformat()
            cache_key = f"error_count_{today}"
            
            current_count = cache.get(cache_key, 0)
            cache.set(cache_key, current_count + 1, 86400)  # 24時間
            
            # エラータイプ別の統計
            error_type = error_data['error_type']
            type_key = f"error_type_{error_type}_{today}"
            
            type_count = cache.get(type_key, 0)
            cache.set(type_key, type_count + 1, 86400)
            
        except Exception as e:
            logger.error(f"Failed to update error stats: {str(e)}")
    
    @staticmethod
    def get_error_summary(days: int = 7) -> Dict:
        """エラーサマリーを取得"""
        try:
            summary = {
                'period_days': days,
                'daily_counts': {},
                'error_types': {},
                'total_errors': 0
            }
            
            for i in range(days):
                date = (timezone.now().date() - timedelta(days=i)).isoformat()
                daily_count = cache.get(f"error_count_{date}", 0)
                summary['daily_counts'][date] = daily_count
                summary['total_errors'] += daily_count
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get error summary: {str(e)}")
            return {'error': str(e)}


class RequestMonitor:
    """リクエスト監視クラス"""
    
    @staticmethod
    def log_slow_request(request, response_time_ms: float, threshold_ms: float = 1000):
        """遅いリクエストをログ"""
        if response_time_ms > threshold_ms:
            slow_request_data = {
                'timestamp': timezone.now().isoformat(),
                'method': request.method,
                'path': request.path,
                'response_time_ms': round(response_time_ms, 2),
                'user_id': str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else None,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': RequestMonitor._get_client_ip(request),
            }
            
            logger.warning(f"Slow Request: {json.dumps(slow_request_data)}")
            
            # 遅いリクエストの統計更新
            RequestMonitor._update_slow_request_stats(slow_request_data)
    
    @staticmethod
    def _get_client_ip(request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
    
    @staticmethod
    def _update_slow_request_stats(request_data: Dict):
        """遅いリクエストの統計を更新"""
        try:
            today = timezone.now().date().isoformat()
            cache_key = f"slow_requests_{today}"
            
            current_count = cache.get(cache_key, 0)
            cache.set(cache_key, current_count + 1, 86400)
            
        except Exception as e:
            logger.error(f"Failed to update slow request stats: {str(e)}")


def monitor_performance(threshold_ms: float = 1000):
    """パフォーマンス監視デコレータ"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            
            try:
                response = view_func(request, *args, **kwargs)
                
                # レスポンス時間計算
                response_time_ms = (time.time() - start_time) * 1000
                
                # 遅いリクエストをログ
                RequestMonitor.log_slow_request(request, response_time_ms, threshold_ms)
                
                return response
                
            except Exception as e:
                # エラーログ
                ErrorTracker.log_error(
                    error=e,
                    context={
                        'view': view_func.__name__,
                        'method': request.method,
                        'path': request.path,
                        'args': args,
                        'kwargs': kwargs
                    },
                    user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None
                )
                raise
        
        return wrapper
    return decorator


class AlertManager:
    """アラート管理クラス"""
    
    @staticmethod
    def check_and_send_alerts():
        """システム状態をチェックしてアラートを送信"""
        health_data = PerformanceMonitor.get_comprehensive_health_check()
        
        alerts = []
        
        # データベースアラート
        if health_data['database']['status'] == 'error':
            alerts.append({
                'type': 'database_error',
                'severity': 'critical',
                'message': 'データベースに接続できません',
                'details': health_data['database']
            })
        elif health_data['database']['response_time_ms'] > 500:
            alerts.append({
                'type': 'database_slow',
                'severity': 'warning',
                'message': f"データベースの応答が遅いです ({health_data['database']['response_time_ms']}ms)",
                'details': health_data['database']
            })
        
        # Redisアラート
        if health_data['redis']['status'] == 'error':
            alerts.append({
                'type': 'redis_error',
                'severity': 'warning',
                'message': 'Redisに接続できません',
                'details': health_data['redis']
            })
        
        # システムリソースアラート
        system = health_data['system']
        if system.get('cpu_percent', 0) > 90:
            alerts.append({
                'type': 'high_cpu',
                'severity': 'warning',
                'message': f"CPU使用率が高いです ({system['cpu_percent']}%)",
                'details': system
            })
        
        if system.get('memory_percent', 0) > 90:
            alerts.append({
                'type': 'high_memory',
                'severity': 'critical',
                'message': f"メモリ使用率が高いです ({system['memory_percent']}%)",
                'details': system
            })
        
        # アラートをログ出力
        for alert in alerts:
            if alert['severity'] == 'critical':
                logger.critical(f"CRITICAL ALERT: {alert['message']}")
            else:
                logger.warning(f"WARNING ALERT: {alert['message']}")
        
        return alerts


class UserActivityMonitor:
    """ユーザーアクティビティ監視クラス"""
    
    @staticmethod
    def log_user_activity(user: User, activity_type: str, details: Optional[Dict] = None):
        """ユーザーアクティビティをログ"""
        activity_data = {
            'timestamp': timezone.now().isoformat(),
            'user_id': str(user.id),  # UUIDを文字列に変換
            'user_email': user.email,
            'activity_type': activity_type,
            'details': details or {}
        }
        
        logger.info(f"User Activity: {json.dumps(activity_data)}")
        
        # アクティビティ統計の更新
        UserActivityMonitor._update_activity_stats(str(user.id), activity_type)
    
    @staticmethod
    def _update_activity_stats(user_id: str, activity_type: str):
        """アクティビティ統計を更新"""
        try:
            today = timezone.now().date().isoformat()
            
            # ユーザー別日次アクティビティ
            user_key = f"user_activity_{user_id}_{today}"
            current_count = cache.get(user_key, 0)
            cache.set(user_key, current_count + 1, 86400)
            
            # アクティビティタイプ別統計
            type_key = f"activity_type_{activity_type}_{today}"
            type_count = cache.get(type_key, 0)
            cache.set(type_key, type_count + 1, 86400)
            
        except Exception as e:
            logger.error(f"Failed to update activity stats: {str(e)}")
    
    @staticmethod
    def get_activity_summary(days: int = 7) -> Dict:
        """アクティビティサマリーを取得"""
        try:
            summary = {
                'period_days': days,
                'daily_activity': {},
                'activity_types': {},
                'total_activities': 0
            }
            
            # 日別アクティビティ統計
            for i in range(days):
                date = (timezone.now().date() - timedelta(days=i)).isoformat()
                
                # その日のアクティブユーザー数を推定
                # 実際の実装では、より詳細な統計が必要
                
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get activity summary: {str(e)}")
            return {'error': str(e)}