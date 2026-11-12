"""
組織の境界つきの取り出し方の土台

problems.models からも使うため、モデルを import しない（循環 import を避ける）。
科目・問題の候補の判定（available_subjects・available_problems）は services.tenant_scope にある。
"""
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet


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


class OrgScopedQuerySet(QuerySet):
    """
    利用者本人の記録を、組織の境界の中に絞る取り出し方を持つ QuerySet の土台

    サブクラスは subject_paths（記録から科目への経路。複数なら全部で絞る）と
    allow_null（科目が空の記録を残すか）を書く。絞らずに読むときは、呼び出しの直前に
    「# 組織で絞らない: <理由>」を書く（studylogs のテストが付け忘れを止める）。
    """
    subject_paths: tuple[str, ...] = ()
    allow_null: bool = False

    def for_user(self, user):
        """user 本人の記録で、user の組織の科目を指すもの（allow_null なら科目が空のものも）"""
        if not self.subject_paths:
            raise ImproperlyConfigured(f'{type(self).__name__} に subject_paths がありません')
        queryset = self.filter(user=user)
        for path in self.subject_paths:
            queryset = scope_to_user_org(
                queryset, user, subject_path=path, allow_null=self.allow_null)
        return queryset
