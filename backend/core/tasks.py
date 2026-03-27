"""
コア機能のバックグラウンドタスク

システム全体のメンテナンスタスク
"""

from celery import shared_task
from django.utils import timezone
from core.cache_service import cache_service
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def cache_maintenance_task(self):
    """キャッシュのメンテナンス"""
    try:
        # キャッシュ統計を取得
        stats = cache_service.get_cache_stats()

        # メモリ使用量が80%を超えた場合、古いキャッシュを削除
        if 'used_memory' in stats:
            # Redis情報から使用メモリを取得し、必要に応じてクリーンアップ
            pass

        logger.info(f"Cache maintenance completed. Stats: {stats}")
        return {
            'status': 'completed',
            'cache_stats': stats
        }

    except Exception as exc:
        logger.error(f"Cache maintenance task failed: {str(exc)}")
        return {'error': str(exc)}


@shared_task(bind=True)
def cleanup_old_sessions_task(self):
    """古いセッションをクリーンアップ"""
    try:
        # Django セッションのクリーンアップ
        from django.core.management import call_command
        call_command('clearsessions')

        logger.info("Old sessions cleaned up")
        return {'status': 'completed'}

    except Exception as exc:
        logger.error(f"Session cleanup task failed: {str(exc)}")
        return {'error': str(exc)}


@shared_task(bind=True)
def system_health_check_task(self):
    """システムヘルスチェック"""
    try:
        health_status = {
            'database': True,
            'redis': True,
            'cache': True,
            'timestamp': timezone.now().isoformat()
        }

        # データベース接続チェック
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            health_status['database'] = False
            logger.error(f"Database health check failed: {str(e)}")

        # Redis接続チェック
        try:
            cache_stats = cache_service.get_cache_stats()
            if 'error' in cache_stats:
                health_status['redis'] = False
                health_status['cache'] = False
        except Exception as e:
            health_status['redis'] = False
            health_status['cache'] = False
            logger.error(f"Redis health check failed: {str(e)}")

        # 全体的なヘルス状況
        overall_health = all(health_status[key] for key in ['database', 'redis', 'cache'])
        health_status['overall'] = overall_health

        if not overall_health:
            logger.warning(f"System health check failed: {health_status}")
        else:
            logger.info("System health check passed")

        return health_status

    except Exception as exc:
        logger.error(f"Health check task failed: {str(exc)}")
        return {
            'overall': False,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def generate_system_report_task(self):
    """システムレポートを生成"""
    try:
        from django.contrib.auth import get_user_model
        from studylogs.models import StudyLog, SpacedRepetitionReview
        from problems.models import Problem
        from datetime import timedelta
        from django.utils import timezone

        User = get_user_model()

        # 過去7日間の統計
        week_ago = timezone.now() - timedelta(days=7)

        report = {
            'generated_at': timezone.now().isoformat(),
            'total_users': User.objects.count(),
            'active_users_7d': User.objects.filter(
                last_login__gte=week_ago
            ).count(),
            'total_problems': Problem.objects.filter(is_deleted=False).count(),
            'study_logs_7d': StudyLog.objects.filter(
                started_at__gte=week_ago
            ).count(),
            'reviews_7d': SpacedRepetitionReview.objects.filter(
                reviewed_at__gte=week_ago
            ).count(),
        }

        # キャッシュ統計
        cache_stats = cache_service.get_cache_stats()
        report['cache_stats'] = cache_stats

        logger.info(f"Generated system report: {report}")
        return report

    except Exception as exc:
        logger.error(f"System report generation failed: {str(exc)}")
        return {'error': str(exc)}
