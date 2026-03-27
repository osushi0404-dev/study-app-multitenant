"""
学習関連のバックグラウンドタスク

Celeryを使用した非同期処理とスケジュールタスク
"""

from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings

from .models import (
    LearningAnalytics, SpacedRepetitionCard, SpacedRepetitionReview,
    LearningSuggestion, StudyLog
)
from .services import SpacedRepetitionService
from .mistake_analysis import MistakeAnalysisService
from core.cache_service import cache_service
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def update_daily_analytics_task(self):
    """すべてのアクティブユーザーの日次分析データを更新"""
    try:
        updated_count = 0
        error_count = 0

        # 過去7日間にアクティブだったユーザーを対象
        active_since = timezone.now() - timedelta(days=7)
        active_users = User.objects.filter(
            Q(study_logs__started_at__gte=active_since) |
            Q(sr_reviews__reviewed_at__gte=active_since)
        ).distinct()

        for user in active_users:
            try:
                service = SpacedRepetitionService(user)
                service.update_daily_analytics()

                # 関連キャッシュを無効化
                cache_service.invalidate_analytics_cache(user.id)

                updated_count += 1
                logger.info(f"Updated analytics for user {user.id}")

            except Exception as e:
                error_count += 1
                logger.error(f"Error updating analytics for user {user.id}: {str(e)}")

        logger.info(f"Daily analytics update completed. Updated: {updated_count}, Errors: {error_count}")
        return {
            'updated_count': updated_count,
            'error_count': error_count,
            'total_users': active_users.count()
        }

    except Exception as exc:
        logger.error(f"Daily analytics task failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_study_reminders_task(self):
    """学習リマインダーを送信"""
    try:
        sent_count = 0

        # 過去24時間学習していないアクティブユーザー
        yesterday = timezone.now() - timedelta(days=1)
        inactive_users = User.objects.filter(
            is_active=True,
            email__isnull=False
        ).exclude(
            Q(study_logs__started_at__gte=yesterday) |
            Q(sr_reviews__reviewed_at__gte=yesterday)
        ).distinct()

        for user in inactive_users:
            try:
                # 復習が必要なカードがあるかチェック
                service = SpacedRepetitionService(user)
                due_cards = service.get_due_cards(limit=1)

                if due_cards:
                    # メール送信
                    send_mail(
                        subject='学習リマインダー - 復習が必要な問題があります',
                        message=f'''
こんにちは、{user.get_full_name() or user.username}さん

復習が必要な問題が{len(due_cards)}件あります。
効率的な学習のため、定期的な復習をお勧めします。

今すぐ学習を始める: {settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}

学習アプリチーム
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )

                    sent_count += 1
                    logger.info(f"Sent reminder to user {user.id}")

            except Exception as e:
                logger.error(f"Error sending reminder to user {user.id}: {str(e)}")

        logger.info(f"Study reminders sent to {sent_count} users")
        return {'sent_count': sent_count}

    except Exception as exc:
        logger.error(f"Study reminders task failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def analyze_mistake_patterns_task(self):
    """すべてのアクティブユーザーの間違いパターンを分析"""
    try:
        analyzed_count = 0

        # 過去30日間にアクティブだったユーザー
        active_since = timezone.now() - timedelta(days=30)
        active_users = User.objects.filter(
            Q(problem_attempts__attempted_at__gte=active_since) |
            Q(sr_reviews__reviewed_at__gte=active_since)
        ).distinct()

        for user in active_users:
            try:
                service = MistakeAnalysisService(user)
                service.analyze_mistakes(days=30)

                # 関連キャッシュを無効化
                cache_service.invalidate_mistake_patterns_cache(user.id)
                cache_service.invalidate_learning_suggestions_cache(user.id)

                analyzed_count += 1
                logger.info(f"Analyzed mistake patterns for user {user.id}")

            except Exception as e:
                logger.error(f"Error analyzing patterns for user {user.id}: {str(e)}")

        logger.info(f"Mistake pattern analysis completed for {analyzed_count} users")
        return {'analyzed_count': analyzed_count}

    except Exception as exc:
        logger.error(f"Mistake pattern analysis task failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True)
def cleanup_expired_suggestions_task(self):
    """期限切れの学習提案をクリーンアップ"""
    try:
        expired_suggestions = LearningSuggestion.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )

        expired_count = expired_suggestions.count()

        # 期限切れの提案を無効化
        expired_suggestions.update(is_active=False)

        # 関連ユーザーのキャッシュを無効化
        for suggestion in expired_suggestions:
            cache_service.invalidate_learning_suggestions_cache(suggestion.user.id)

        logger.info(f"Cleaned up {expired_count} expired suggestions")
        return {'expired_count': expired_count}

    except Exception as exc:
        logger.error(f"Cleanup suggestions task failed: {str(exc)}")
        return {'error': str(exc)}


@shared_task(bind=True)
def update_user_proficiency_task(self, user_id: int, subject_id: int = None):
    """特定ユーザーの習熟度を更新（即座に実行）"""
    try:
        user = User.objects.get(id=user_id)

        # 習熟度キャッシュを無効化
        cache_service.invalidate_proficiency_cache(user_id)

        # 適応的学習サービスで習熟度を再計算
        from .adaptive_selection import AdaptiveProblemSelector
        selector = AdaptiveProblemSelector(user)

        subject = None
        if subject_id:
            from problems.models import Subject
            subject = Subject.objects.get(id=subject_id)

        proficiency_data = selector.analyze_user_proficiency(subject)

        logger.info(f"Updated proficiency for user {user_id}")
        return {
            'user_id': user_id,
            'subject_id': subject_id,
            'overall_accuracy': proficiency_data.get('overall_accuracy', 0)
        }

    except Exception as exc:
        logger.error(f"Update proficiency task failed for user {user_id}: {str(exc)}")
        return {'error': str(exc)}


@shared_task(bind=True)
def generate_learning_insights_task(self, user_id: int):
    """学習洞察を生成"""
    try:
        user = User.objects.get(id=user_id)
        service = MistakeAnalysisService(user)

        insights = service.get_learning_insights(days=7)

        logger.info(f"Generated learning insights for user {user_id}")
        return {
            'user_id': user_id,
            'insights_count': len(insights.get('insights', [])),
            'recommendations_count': len(insights.get('recommendations', []))
        }

    except Exception as exc:
        logger.error(f"Generate insights task failed for user {user_id}: {str(exc)}")
        return {'error': str(exc)}


@shared_task(bind=True)
def bulk_update_spaced_repetition_task(self):
    """期限が来たすべてのスペースドリピティションカードを更新"""
    try:
        # 期限が来ているカードを取得
        due_cards = SpacedRepetitionCard.objects.filter(
            next_review_date__lte=timezone.now(),
            is_active=True
        ).select_related('user')

        updated_count = 0

        for card in due_cards:
            try:
                # カードのユーザーキャッシュを無効化
                cache_service.invalidate_spaced_repetition_cache(card.user.id)
                updated_count += 1

            except Exception as e:
                logger.error(f"Error updating card {card.id}: {str(e)}")

        logger.info(f"Updated {updated_count} spaced repetition cards")
        return {'updated_count': updated_count}

    except Exception as exc:
        logger.error(f"Bulk update spaced repetition task failed: {str(exc)}")
        return {'error': str(exc)}


@shared_task(bind=True)
def export_user_data_task(self, user_id: int, export_format: str = 'json'):
    """ユーザーデータをエクスポート"""
    try:
        user = User.objects.get(id=user_id)

        # ユーザーの学習データを収集
        study_logs = list(StudyLog.objects.filter(user=user).values())
        sr_cards = list(SpacedRepetitionCard.objects.filter(user=user).values())
        sr_reviews = list(SpacedRepetitionReview.objects.filter(user=user).values())
        analytics = list(LearningAnalytics.objects.filter(user=user).values())

        logger.info(f"Exported data for user {user_id}")
        return {
            'user_id': user_id,
            'export_format': export_format,
            'record_counts': {
                'study_logs': len(study_logs),
                'sr_cards': len(sr_cards),
                'sr_reviews': len(sr_reviews),
                'analytics': len(analytics),
            }
        }

    except Exception as exc:
        logger.error(f"Export data task failed for user {user_id}: {str(exc)}")
        return {'error': str(exc)}
