# backend/problems/services/quiz_service.py
import uuid
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from problems.models import Problem, QuizSession, Subject


class IdempotencyKeyReusedError(Exception):
    """同じ Idempotency-Key が別の内容（科目）で再利用された"""


class ActiveSessionConflictError(Exception):
    """有効セッションの一意制約に違反した（直列化をすり抜けた同時開始）"""


class QuizService:
    """クイズセッション関連のビジネスロジック"""

    @staticmethod
    def start_session(
        *,
        user,
        subject: Optional[Subject],
        client_request_id: Optional[uuid.UUID],
    ) -> Tuple[QuizSession, bool]:
        """
        クイズセッションを開始する

        同一ユーザーの開始処理はユーザー行のロックで直列化する。
        同じ client_request_id の再送には作成済みのセッションを返す（冪等）。

        Returns:
            (セッション, 新規作成したかどうか)
        """
        try:
            with transaction.atomic():
                get_user_model().objects.select_for_update().only('pk').get(pk=user.pk)

                if client_request_id is not None:
                    existing = QuizSession.objects.filter(
                        user=user, client_request_id=client_request_id
                    ).first()
                    if existing is not None:
                        if existing.subject_id != (subject.pk if subject else None):
                            raise IdempotencyKeyReusedError()
                        return existing, False

                QuizSession.objects.filter(user=user, is_active=True).update(
                    is_active=False, ended_at=timezone.now()
                )

                problems_queryset = Problem.objects.filter(is_deleted=False)
                if subject is not None:
                    problems_queryset = problems_queryset.filter(subject=subject)

                session = QuizSession.objects.create(
                    user=user,
                    subject=subject,
                    client_request_id=client_request_id,
                    total_problems=problems_queryset.count(),
                )
                return session, True
        except IntegrityError as exc:
            raise ActiveSessionConflictError() from exc

    @staticmethod
    def get_next_problem(
        session: QuizSession
    ) -> Tuple[Optional[Problem], bool, int]:
        """
        次の問題を取得（N+1問題を回避した最適化実装）

        Args:
            session: クイズセッション

        Returns:
            (問題, 復習モードフラグ, 科目の総問題数)
            問題がない場合は (None, False, 0)
        """
        # 回答済み問題のサブクエリ（リストに変換せずクエリのまま使用）
        answered_problem_ids_subquery = session.answers.values_list(
            'problem_id', flat=True
        )

        # 科目の全問題を取得
        total_problems_queryset = Problem.objects.filter(is_deleted=False)
        if session.subject:
            total_problems_queryset = total_problems_queryset.filter(
                subject=session.subject
            )

        total_problems_in_subject = total_problems_queryset.count()

        if total_problems_in_subject == 0:
            return None, False, 0

        # 未回答の問題を取得（サブクエリで効率化）
        next_problem = (
            total_problems_queryset
            .exclude(id__in=answered_problem_ids_subquery)
            .order_by('?')
            .first()
        )

        # 復習モード：既出問題からランダム選択
        if not next_problem:
            # 最近解いた5問を除外して重複を減らす
            last_n_problems = list(
                session.answers
                .order_by('-answered_at')[:5]
                .values_list('problem_id', flat=True)
            )

            next_problem = (
                total_problems_queryset
                .filter(id__in=answered_problem_ids_subquery)
                .exclude(id__in=last_n_problems)  # 最近解いた問題を除外
                .order_by('?')
                .first()
            )

            # それでも問題がない場合（5問未満の科目）
            if not next_problem:
                next_problem = (
                    total_problems_queryset
                    .filter(id__in=answered_problem_ids_subquery)
                    .order_by('?')
                    .first()
                )

            is_review_mode = True
        else:
            is_review_mode = False

        return next_problem, is_review_mode, total_problems_in_subject

    @staticmethod
    def calculate_session_stats(session: QuizSession) -> dict:
        """
        セッションの統計情報を計算

        Args:
            session: クイズセッション

        Returns:
            統計情報の辞書
        """
        return {
            'completed': session.completed_problems,
            'total': session.total_problems,
            'correct': session.correct_answers,
            'accuracy': (
                round((session.correct_answers / session.completed_problems) * 100, 2)
                if session.completed_problems > 0 else 0
            )
        }
