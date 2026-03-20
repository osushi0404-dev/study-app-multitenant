# backend/problems/services/quiz_service.py
from typing import Optional, Tuple
from django.db.models import QuerySet
from problems.models import Problem, QuizSession


class QuizService:
    """クイズセッション関連のビジネスロジック"""

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
