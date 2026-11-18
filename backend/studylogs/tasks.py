"""
学習関連のバックグラウンドタスク

Celeryを使用した非同期処理とスケジュールタスク
"""

from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import SpacedRepetitionCard, SpacedRepetitionReview
from problems.models import QuizAnswer
from .services import SpacedRepetitionService
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

        # 過去7日間にクイズに答えた・復習をしたユーザーを対象（I492: 学習の記録は QuizAnswer が正）
        active_since = timezone.now() - timedelta(days=7)
        # 結合の OR（答え × 復習の行）を作らないよう、日時で絞った ID の副問い合わせにする
        # 組織で絞らない: 利用者を選ぶだけ（値は出さず、集計は利用者ごとの SpacedRepetitionService が本人の記録で行う）
        answered = QuizAnswer.objects.filter(answered_at__gte=active_since).values('session__user_id')
        # 組織で絞らない: 同上
        reviewed = SpacedRepetitionReview.objects.filter(reviewed_at__gte=active_since).values('user_id')
        active_users = User.objects.filter(Q(id__in=answered) | Q(id__in=reviewed))

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


@shared_task(bind=True)
def bulk_update_spaced_repetition_task(self):
    """期限が来たすべてのスペースドリピティションカードを更新"""
    try:
        # 期限が来ているカードを取得
        # 組織で絞らない: 利用者を持たない一括処理（中身を外に出さない）
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
