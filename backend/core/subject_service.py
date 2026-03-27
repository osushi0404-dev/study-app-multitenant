"""
科目取得処理の統一サービス

このモジュールは、problems_subjectテーブルへのアクセスを統一化し、
組織フィルタリング、キャッシュ管理、権限チェックを一元管理します。
"""

from __future__ import annotations

from django.db.models import Count, QuerySet
from typing import TYPE_CHECKING, Optional, List, Dict
import logging

if TYPE_CHECKING:
    from problems.models import Subject

logger = logging.getLogger(__name__)


class SubjectService:
    """科目取得処理の統一サービスクラス"""

    @staticmethod
    def get_user_subjects(
        user, use_cache: bool = True,
        annotate_count: bool = False,
    ) -> QuerySet:
        """
        ユーザーの組織に属する科目を取得する統一メソッド

        Args:
            user: リクエストユーザー
            use_cache: キャッシュを使用するか
            annotate_count: 問題数をアノテートするか

        Returns:
            組織でフィルタリングされた科目のQuerySet
        """
        from problems.models import Subject
        from .cache_service import cache_service

        if not user or not hasattr(user, 'organization_id') or not user.organization_id:
            logger.warning(f"User {user} has no organization_id")
            return Subject.objects.none()

        org_id = user.organization_id
        cache_key = f"subjects_org_{org_id}_count_{annotate_count}"

        # キャッシュ確認
        if use_cache:
            cached_data = cache_service.get_subjects_cache(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                # キャッシュからQuerySetを復元
                subject_ids = [s['id'] for s in cached_data]
                queryset = Subject.objects.filter(id__in=subject_ids)
                if annotate_count:
                    queryset = queryset.annotate(problem_count=Count('problems'))
                return queryset

        # データベースから取得
        logger.debug(f"Cache miss for key: {cache_key}, fetching from DB")
        queryset = Subject.objects.filter(organization=org_id)

        if annotate_count:
            queryset = queryset.annotate(problem_count=Count('problems'))

        # キャッシュに保存
        if use_cache:
            cache_data = list(queryset.values('id', 'name', 'description'))
            cache_service.set_subjects_cache(cache_data, cache_key)
            logger.debug(f"Cached {len(cache_data)} subjects for key: {cache_key}")

        return queryset

    @staticmethod
    def get_subject_by_id(subject_id: int, user) -> Optional['Subject']:
        """
        IDで科目を取得（組織権限チェック付き）

        Args:
            subject_id: 科目ID
            user: リクエストユーザー

        Returns:
            科目インスタンス（権限がない場合はNone）
        """
        from problems.models import Subject

        if not user or not hasattr(user, 'organization_id') or not user.organization_id:
            logger.warning(f"User {user} has no organization_id")
            return None

        try:
            subject = Subject.objects.get(
                id=subject_id,
                organization=user.organization_id
            )
            logger.debug(f"Subject {subject_id} found for user {user.id}")
            return subject
        except Subject.DoesNotExist:
            logger.warning(f"Subject {subject_id} not found or no access for user {user.id}")
            return None

    @staticmethod
    def get_user_selected_subjects(user, use_cache: bool = True,
                                   annotate_count: bool = False) -> QuerySet:
        """
        ユーザーが会員登録時に選択した科目のみを取得
        （ダッシュボード・統計画面用）

        Args:
            user: リクエストユーザー
            use_cache: キャッシュを使用するか
            annotate_count: 問題数をアノテートするか

        Returns:
            ユーザーが選択した科目のQuerySet
        """
        from problems.models import Subject, UserSubjectAccess
        from .cache_service import cache_service

        if not user or not user.is_authenticated:
            logger.warning(f"User {user} is not authenticated")
            return Subject.objects.none()

        cache_key = f"user_subjects_{user.id}_count_{annotate_count}"

        # キャッシュ確認
        if use_cache:
            cached_data = cache_service.get_subjects_cache(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                subject_ids = [s['id'] for s in cached_data]
                queryset = Subject.objects.filter(id__in=subject_ids)
                if annotate_count:
                    queryset = queryset.annotate(problem_count=Count('problems'))
                return queryset

        # UserSubjectAccessテーブルから取得
        logger.debug(f"Cache miss for key: {cache_key}, fetching from DB")
        user_subject_ids = UserSubjectAccess.objects.filter(
            user=user
        ).values_list('subject_id', flat=True)

        queryset = Subject.objects.filter(id__in=user_subject_ids).order_by('name')

        if annotate_count:
            queryset = queryset.annotate(problem_count=Count('problems'))

        # キャッシュに保存
        if use_cache and queryset.exists():
            cache_data = list(queryset.values('id', 'name', 'description'))
            cache_service.set_subjects_cache(cache_data, cache_key)
            logger.debug(f"Cached {len(cache_data)} user subjects for key: {cache_key}")

        return queryset

    @staticmethod
    def get_subjects_for_dropdown(user) -> List[Dict]:
        """
        プルダウン用の科目リストを取得

        Args:
            user: リクエストユーザー

        Returns:
            科目のリスト（id, name形式）
        """
        subjects = SubjectService.get_user_subjects(user, use_cache=True)
        return list(subjects.values('id', 'name').order_by('name'))

    @staticmethod
    def get_subject_names_dict(user) -> Dict[int, str]:
        """
        科目IDと名前のマッピング辞書を取得

        Args:
            user: リクエストユーザー

        Returns:
            {科目ID: 科目名}の辞書
        """
        subjects = SubjectService.get_user_subjects(user, use_cache=True)
        return {s.id: s.name for s in subjects}

    @staticmethod
    def invalidate_cache(org_id: int):
        """
        組織の科目キャッシュを無効化

        Args:
            org_id: 組織ID
        """
        from .cache_service import cache_service

        patterns = [
            f"subjects_org_{org_id}_count_True",
            f"subjects_org_{org_id}_count_False",
        ]
        for pattern in patterns:
            cache_service.delete_pattern(pattern)
            logger.info(f"Invalidated cache pattern: {pattern}")

    @staticmethod
    def validate_subject_access(subject_id: int, user) -> bool:
        """
        ユーザーが科目にアクセス可能かチェック

        Args:
            subject_id: 科目ID
            user: リクエストユーザー

        Returns:
            アクセス可能な場合True
        """
        subject = SubjectService.get_subject_by_id(subject_id, user)
        return subject is not None


# シングルトンインスタンス
subject_service = SubjectService()
