# backend/problems/services/quiz_service.py
import uuid
from typing import NamedTuple, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from problems.models import Problem, QuizSession, Subject
from problems.services import tenant_scope
from problems.services.weakness import order_weak_first


def spaced_repetition_service(user):
    """間隔反復のサービス（studylogs.models が problems.models を読むので、循環しないよう呼ぶときに読む）"""
    from studylogs.services import SpacedRepetitionService
    return SpacedRepetitionService(user)


class NextProblem(NamedTuple):
    """次の問題と、画面に伝える出し方"""
    problem: Optional[Problem]
    is_review_mode: bool             # 同じ回で全部答え、既出の問題から出している
    total_problems_in_subject: int
    is_weak_fallback: bool           # 苦手を優先の回だが、解答が少なくいつもの順で出している（I466）


class IdempotencyKeyReusedError(Exception):
    """同じ Idempotency-Key が別の内容（科目）で再利用された"""


class ActiveSessionConflictError(Exception):
    """有効セッションの一意制約に違反した（直列化をすり抜けた同時開始）"""


class QuizService:
    """クイズセッション関連のビジネスロジック"""

    @staticmethod
    def available_subjects(user) -> QuerySet[Subject]:
        """クイズで指定してよい科目（tenant_scope.available_subjects と同じ）"""
        return tenant_scope.available_subjects(user)

    @staticmethod
    def available_problems(user, subject: Optional[Subject]) -> QuerySet[Problem]:
        """クイズで出題・回答してよい問題（tenant_scope.available_problems と同じ）"""
        return tenant_scope.available_problems(user, subject)

    @staticmethod
    def start_session(
        *,
        user,
        subject: Optional[Subject],
        client_request_id: Optional[uuid.UUID],
        mode: str = QuizSession.MODE_NORMAL,
    ) -> Tuple[QuizSession, bool]:
        """
        クイズセッションを開始する

        同一ユーザーの開始処理はユーザー行のロックで直列化する。
        同じ client_request_id の再送には作成済みのセッションを返す（冪等）。
        mode が review（今日の復習）なら、total_problems はその時点で復習する日が来た問題の数。

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
                        if (existing.subject_id != (subject.pk if subject else None)
                                or existing.mode != mode):
                            raise IdempotencyKeyReusedError()
                        return existing, False

                QuizSession.objects.filter(user=user, is_active=True).update(
                    is_active=False, ended_at=timezone.now()
                )

                if mode == QuizSession.MODE_REVIEW:
                    total_problems = spaced_repetition_service(user).due_cards_queryset(subject).count()
                else:
                    total_problems = QuizService.available_problems(user, subject).count()

                session = QuizSession.objects.create(
                    user=user,
                    subject=subject,
                    client_request_id=client_request_id,
                    mode=mode,
                    total_problems=total_problems,
                )
                return session, True
        except IntegrityError as exc:
            raise ActiveSessionConflictError() from exc

    @staticmethod
    def get_next_problem(session: QuizSession) -> 'NextProblem':
        """
        次の問題を取得（N+1問題を回避した最適化実装）

        同じ回では未回答の問題を先に出し、全部答えたら既出の問題から出す（is_review_mode）。
        選ぶ順は、苦手を優先の回（I466）なら weakness.order_weak_first、それ以外は乱数。

        Returns:
            NextProblem。問題がない場合は problem が None で total_problems_in_subject が 0
            今日の復習の回は、出す問題が無くなったら problem が None で total_problems_in_subject が回の total_problems
        """
        if session.mode == QuizSession.MODE_REVIEW:
            return NextProblem(
                QuizService._next_review_problem(session), False, session.total_problems, False)

        # 回答済み問題のサブクエリ（リストに変換せずクエリのまま使用）
        answered_problem_ids_subquery = session.answers.values_list(
            'problem_id', flat=True
        )

        # 出題対象（セッション所有者の組織の問題・科目の指定があればその科目）
        total_problems_queryset = QuizService.available_problems(
            session.user, session.subject
        )

        total_problems_in_subject = total_problems_queryset.count()

        if total_problems_in_subject == 0:
            return NextProblem(None, False, 0, False)

        if session.mode == QuizSession.MODE_WEAK:
            ordered, is_weak_fallback = order_weak_first(
                total_problems_queryset, session.user, session.subject)
        else:
            ordered, is_weak_fallback = total_problems_queryset.order_by('?'), False

        # 未回答の問題を取得（サブクエリで効率化）
        next_problem = ordered.exclude(id__in=answered_problem_ids_subquery).first()

        # 既出問題から出す
        if not next_problem:
            # 最近解いた5問を除外して重複を減らす
            last_n_problems = list(
                session.answers
                .order_by('-answered_at')[:5]
                .values_list('problem_id', flat=True)
            )

            next_problem = (
                ordered
                .filter(id__in=answered_problem_ids_subquery)
                .exclude(id__in=last_n_problems)  # 最近解いた問題を除外
                .first()
            )

            # それでも問題がない場合（5問以下の科目）: 直前の 1 問だけは除く（同じ問題を続けて出さない・I466 F1）。
            # 科目の問題が 1 問だけのときは除外なし
            if not next_problem:
                answered = ordered.filter(id__in=answered_problem_ids_subquery)
                next_problem = (
                    answered.exclude(id__in=last_n_problems[:1]).first() or answered.first()
                )

            is_review_mode = True
        else:
            is_review_mode = False

        return NextProblem(next_problem, is_review_mode, total_problems_in_subject, is_weak_fallback)

    @staticmethod
    def _next_review_problem(session: QuizSession) -> Optional[Problem]:
        """
        今日の復習の回の次の問題（その時点で復習する日が来ていて、この回でまだ答えていないもの）

        答えた問題は次の復習日が明日以降になるので、毎回問い合わせれば自然に外れる。
        """
        card = (
            spaced_repetition_service(session.user)
            .due_cards_queryset(session.subject)
            .exclude(problem_id__in=session.answers.values_list('problem_id', flat=True))
            .select_related('problem', 'problem__subject')
            .order_by('next_review_date', 'id')
            .first()
        )
        return card.problem if card else None

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
