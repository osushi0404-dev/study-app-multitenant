"""
利用者が学ぶ科目（UserSubjectAccess）の書き換え（I494）

選んだ科目の一覧を丸ごと置き換える。組織の境界はシリアライザの照合に依らず、ここでも
tenant_scope.available_subjects（組織に属さない利用者は空・全体共有の科目は含めない）で絞る。
"""
import logging
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

from problems.models import UserSubjectAccess
from problems.services.tenant_scope import available_subjects
from problems.signals import invalidate_user_subjects_cache

logger = logging.getLogger(__name__)


@transaction.atomic
def replace_user_subjects(*, user, subject_ids: Iterable[int]) -> None:
    """利用者の学ぶ科目を subject_ids（自組織の科目だけを使う）に置き換える"""
    # 同じ利用者の同時の保存を順に並べる（足す・外すが混ざらないように）
    get_user_model().objects.select_for_update().filter(pk=user.pk).first()

    wanted = set(available_subjects(user).filter(id__in=list(subject_ids))
                 .values_list('id', flat=True))
    current = set(UserSubjectAccess.objects.filter(user=user).values_list('subject_id', flat=True))
    removed = current - wanted
    added = wanted - current

    if removed:
        UserSubjectAccess.objects.filter(user=user, subject_id__in=removed).delete()
    if added:
        UserSubjectAccess.objects.bulk_create(
            [UserSubjectAccess(user=user, subject_id=subject_id, granted_by=user)
             for subject_id in sorted(added)],
            ignore_conflicts=True,
        )

    # シグナルはトランザクションの中で消すので、確定の前に古い値が入り直しうる。確定の後にも消す
    transaction.on_commit(lambda: invalidate_user_subjects_cache(user))
    logger.info('user subjects replaced', extra={
        'user_id': user.id, 'organization_id': user.organization_id,
        'added': len(added), 'removed': len(removed),
    })
