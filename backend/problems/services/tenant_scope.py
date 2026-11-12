"""
組織の境界（ユーザーの組織の科目・問題）の判定

境界の判定のためキャッシュは使わない。組織に属さないユーザーは何も扱えない。
全体共有科目（Subject.organization が空）は含めない。
記録の絞り込みの本体（scope_to_user_org・各モデルの for_user の土台）は problems.querysets にある。
"""
from typing import Optional

from django.db.models import QuerySet

from problems.models import Problem, Subject
from problems.querysets import scope_to_user_org

__all__ = ['available_subjects', 'available_problems', 'scope_to_user_org']


def available_subjects(user) -> QuerySet[Subject]:
    """ユーザーの組織の科目"""
    if user.organization_id is None:
        return Subject.objects.none()
    return Subject.objects.filter(organization_id=user.organization_id)


def available_problems(user, subject: Optional[Subject] = None) -> QuerySet[Problem]:
    """
    ユーザーの組織の未削除の問題（科目の指定があればその科目）

    問題の組織は subject 経由で判定する（Problem.organization は null 可のため使わない）。
    """
    if user.organization_id is None:
        return Problem.objects.none()
    problems = Problem.objects.filter(
        is_deleted=False, subject__organization_id=user.organization_id
    )
    if subject is not None:
        problems = problems.filter(subject=subject)
    return problems
