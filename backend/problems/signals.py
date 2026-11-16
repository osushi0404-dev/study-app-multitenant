"""
problems アプリのシグナル定義
UserSubjectAccess の変更時にキャッシュを無効化
"""

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from core.cache_service import cache_service
from core.subject_service import user_subjects_cache_key
from .models import UserSubjectAccess

logger = logging.getLogger(__name__)


def invalidate_user_subjects_cache(user):
    """利用者が選んだ科目のキャッシュを消す（キーは読む側と同じ関数で作る・組織に関係なく 1 つ・I491）"""
    cache_service.invalidate_subjects_cache(user_subjects_cache_key(user.id))


def invalidate_user_subjects_cache_now_and_on_commit(user):
    """
    今すぐ消し、トランザクションの確定の後にもう一度消す（I494）

    確定の前に別の読み取りが古い一覧をキャッシュに入れ直す隙を塞ぐ。トランザクションの外では
    on_commit はすぐ動く（2 回消すだけで害は無い）。bulk_create はシグナルを送らないので、
    まとめて書く処理（problems.services.user_subject_service）は自分でこれを呼ぶ
    """
    invalidate_user_subjects_cache(user)
    transaction.on_commit(lambda: invalidate_user_subjects_cache(user))


@receiver(post_save, sender=UserSubjectAccess)
def invalidate_user_subjects_cache_on_save(sender, instance, created, **kwargs):
    """
    UserSubjectAccess が作成・更新された時にユーザーの科目キャッシュを無効化
    """
    invalidate_user_subjects_cache_now_and_on_commit(instance.user)
    logger.debug(f"Invalidated cache for user {instance.user_id} after UserSubjectAccess save")


@receiver(post_delete, sender=UserSubjectAccess)
def invalidate_user_subjects_cache_on_delete(sender, instance, **kwargs):
    """
    UserSubjectAccess が削除された時にユーザーの科目キャッシュを無効化
    """
    invalidate_user_subjects_cache_now_and_on_commit(instance.user)
    logger.debug(f"Invalidated cache for user {instance.user_id} after UserSubjectAccess delete")
