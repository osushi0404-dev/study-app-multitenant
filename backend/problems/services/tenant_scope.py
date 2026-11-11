"""
組織の境界（ユーザーの組織の科目・問題）の判定

境界の判定のためキャッシュは使わない。組織に属さないユーザーは何も扱えない。
全体共有科目（Subject.organization が空）は含めない。
"""
from typing import Optional

from django.db.models import Q, QuerySet

from problems.models import Problem, Subject


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


def scope_to_user_org(
    queryset: QuerySet, user, *, subject_path: str, allow_null: bool = False
) -> QuerySet:
    """
    記録の queryset を、ユーザーの組織の科目を指すものに絞る

    subject_path は記録から科目への経路（例: 'subject'・'problem__subject'）。
    allow_null=True のとき、科目が空の記録も残す（他組織の中身を含まないため）。
    組織に属さないユーザーは、allow_null なら科目が空の記録だけ、そうでなければ空。
    """
    null_cond = Q(**{f'{subject_path}__isnull': True})
    if user.organization_id is None:
        return queryset.filter(null_cond) if allow_null else queryset.none()
    cond = Q(**{f'{subject_path}__organization_id': user.organization_id})
    if allow_null:
        cond |= null_cond
    return queryset.filter(cond)
