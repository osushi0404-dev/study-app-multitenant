from django.db.models import Q
from .models import UserSubjectAccess, UserFieldAccess, Subject, Field, Problem


class AccessPermissionChecker:
    @staticmethod
    def get_allowed_subjects(user):
        """
        ユーザーがアクセス可能な科目を取得
        UserSubjectAccessレコードベースで管理
        """
        # UserSubjectAccessレコードに基づいて許可された科目を取得
        allowed_subject_ids = UserSubjectAccess.objects.filter(
            user=user
        ).values_list('subject_id', flat=True)
        
        # レコードがない場合は空のQuerySetを返す
        if not allowed_subject_ids:
            return Subject.objects.none()
        
        return Subject.objects.filter(id__in=allowed_subject_ids)
    
    @staticmethod
    def get_allowed_fields(user):
        """
        ユーザーがアクセス可能な分野を取得
        UserFieldAccessレコードベースで管理
        """
        # UserFieldAccessレコードに基づいて許可された分野を取得
        allowed_field_ids = UserFieldAccess.objects.filter(
            user=user
        ).values_list('field_id', flat=True)
        
        # 分野はオプショナルなので、レコードがない場合は空のQuerySetを返す
        if not allowed_field_ids:
            return Field.objects.none()
        
        return Field.objects.filter(id__in=allowed_field_ids)
    
    @staticmethod
    def filter_problems_by_access(queryset, user):
        """
        ユーザーのアクセス権限に基づいて問題をフィルタリング
        UserSubjectAccessレコードベースで管理
        """
        # 許可された科目と分野を取得
        allowed_subjects = AccessPermissionChecker.get_allowed_subjects(user)
        allowed_fields = AccessPermissionChecker.get_allowed_fields(user)
        
        # 科目でフィルタリング
        queryset = queryset.filter(subject__in=allowed_subjects)
        
        # 分野が設定されている問題は、許可された分野のみ
        # 分野がnullの問題は科目のアクセス権限のみで判断
        queryset = queryset.filter(
            Q(field__isnull=True) | Q(field__in=allowed_fields)
        )
        
        return queryset
    
    @staticmethod
    def can_access_subject(user, subject):
        """
        特定の科目へのアクセス権限をチェック
        UserSubjectAccessレコードベースで管理
        """
        return UserSubjectAccess.objects.filter(
            user=user,
            subject=subject
        ).exists()
    
    @staticmethod
    def can_access_field(user, field):
        """
        特定の分野へのアクセス権限をチェック
        UserFieldAccessレコードベースで管理
        """
        # まず科目へのアクセス権限をチェック
        if not AccessPermissionChecker.can_access_subject(user, field.subject):
            return False
        
        return UserFieldAccess.objects.filter(
            user=user,
            field=field
        ).exists()
    
    @staticmethod
    def can_access_problem(user, problem):
        """
        特定の問題へのアクセス権限をチェック
        UserSubjectAccessレコードベースで管理
        """
        # 科目へのアクセス権限をチェック
        if not AccessPermissionChecker.can_access_subject(user, problem.subject):
            return False
        
        # 分野が設定されている場合は分野へのアクセス権限もチェック
        if problem.field and not AccessPermissionChecker.can_access_field(user, problem.field):
            return False
        
        return True