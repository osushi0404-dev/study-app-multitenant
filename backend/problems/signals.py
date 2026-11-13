"""
problems アプリのシグナル定義
UserSubjectAccess の変更時にキャッシュを無効化
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from core.cache_service import cache_service
from core.subject_service import user_subjects_cache_key
from .models import UserSubjectAccess

logger = logging.getLogger(__name__)


def _invalidate_user_subjects_cache(user):
    """利用者が選んだ科目のキャッシュを消す（キーは読む側と同じ関数で作る・I473）"""
    for annotate_count in (False, True):
        cache_service.invalidate_subjects_cache(
            user_subjects_cache_key(user.id, user.organization_id, annotate_count))


@receiver(post_save, sender=UserSubjectAccess)
def invalidate_user_subjects_cache_on_save(sender, instance, created, **kwargs):
    """
    UserSubjectAccess が作成・更新された時にユーザーの科目キャッシュを無効化
    """
    _invalidate_user_subjects_cache(instance.user)
    logger.debug(f"Invalidated cache for user {instance.user.id} after UserSubjectAccess save")


@receiver(post_delete, sender=UserSubjectAccess)
def invalidate_user_subjects_cache_on_delete(sender, instance, **kwargs):
    """
    UserSubjectAccess が削除された時にユーザーの科目キャッシュを無効化
    """
    _invalidate_user_subjects_cache(instance.user)
    logger.debug(f"Invalidated cache for user {instance.user.id} after UserSubjectAccess delete")
