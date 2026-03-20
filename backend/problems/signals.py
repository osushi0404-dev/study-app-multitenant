"""
problems アプリのシグナル定義
UserSubjectAccess の変更時にキャッシュを無効化
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
import logging

from .models import UserSubjectAccess

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserSubjectAccess)
def invalidate_user_subjects_cache_on_save(sender, instance, created, **kwargs):
    """
    UserSubjectAccess が作成・更新された時にユーザーの科目キャッシュを無効化
    """
    cache_keys = [
        f"user_subjects_{instance.user.id}_count_False",
        f"user_subjects_{instance.user.id}_count_True"
    ]

    for key in cache_keys:
        cache.delete(key)

    logger.debug(f"Invalidated cache for user {instance.user.id} after UserSubjectAccess save")


@receiver(post_delete, sender=UserSubjectAccess)
def invalidate_user_subjects_cache_on_delete(sender, instance, **kwargs):
    """
    UserSubjectAccess が削除された時にユーザーの科目キャッシュを無効化
    """
    cache_keys = [
        f"user_subjects_{instance.user.id}_count_False",
        f"user_subjects_{instance.user.id}_count_True"
    ]

    for key in cache_keys:
        cache.delete(key)

    logger.debug(f"Invalidated cache for user {instance.user.id} after UserSubjectAccess delete")