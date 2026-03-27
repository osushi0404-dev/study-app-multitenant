"""
間隔反復学習サービス

学習効率を最大化するためのビジネスロジック
"""

from datetime import timedelta, date
from typing import List, Dict, Optional
from django.db import transaction
from django.utils import timezone
from django.db.models import Avg, Sum
from django.contrib.auth import get_user_model

from .models import (
    SpacedRepetitionCard,
    SpacedRepetitionReview,
    LearningAnalytics,
    StudyLog,
)
from .spaced_repetition import SpacedRepetitionCalculator
from problems.models import Problem
from core.cache_service import cache_service

User = get_user_model()


class SpacedRepetitionService:
    """間隔反復学習システムのメインサービス"""

    def __init__(self, user):
        self.user = user
        self.calculator = SpacedRepetitionCalculator()

    def get_due_cards(self, limit: int = 20) -> List[SpacedRepetitionCard]:
        """復習が必要なカードを取得"""
        cache_key = f"due_cards_{limit}"
        cached_cards = cache_service.get_spaced_repetition_cache(self.user.id, cache_key)

        if cached_cards is not None:
            return cached_cards

        cards = list(SpacedRepetitionCard.objects.filter(
            user=self.user,
            is_active=True,
            next_review_date__lte=timezone.now()
        ).select_related('problem', 'problem__subject').order_by(
            'next_review_date',
            '-ease_factor'  # 難しいカードを優先
        )[:limit])

        # 短期間キャッシュ（5分）
        cache_service.set_spaced_repetition_cache(self.user.id, cache_key, cards)
        return cards

    def get_new_cards(self, limit: int = 5) -> List[Problem]:
        """新しく学習する問題を取得"""
        # まだカードが作成されていない問題を取得
        existing_card_problems = SpacedRepetitionCard.objects.filter(
            user=self.user
        ).values_list('problem_id', flat=True)

        return Problem.objects.filter(
            is_active=True
        ).exclude(
            id__in=existing_card_problems
        ).select_related('subject').order_by('?')[:limit]

    def create_card_for_problem(self, problem: Problem) -> SpacedRepetitionCard:
        """問題用の新しいカードを作成"""
        card, created = SpacedRepetitionCard.objects.get_or_create(
            user=self.user,
            problem=problem,
            defaults={
                'ease_factor': self.calculator.INITIAL_EASE_FACTOR,
                'interval_days': self.calculator.INITIAL_INTERVAL,
                'repetition_count': 0,
                'next_review_date': timezone.now(),
            }
        )
        return card

    @transaction.atomic
    def review_card(
        self,
        card: SpacedRepetitionCard,
        quality_score: int,
        response_time_seconds: int,
        hint_used: bool = False,
        study_session: Optional[StudyLog] = None
    ) -> SpacedRepetitionReview:
        """カードを復習し、スケジューリングを更新"""

        # 復習前の状態を記録
        previous_ease_factor = card.ease_factor
        previous_interval = card.interval_days
        previous_repetition_count = card.repetition_count

        # 新しいスケジューリングを計算
        next_review_date, new_interval, new_ease_factor = self.calculator.calculate_next_review(
            current_interval=card.interval_days,
            ease_factor=card.ease_factor,
            repetition_count=card.repetition_count,
            quality_score=quality_score,
            last_review_date=timezone.now()
        )

        # カードを更新
        card.ease_factor = new_ease_factor
        card.interval_days = new_interval
        card.repetition_count = previous_repetition_count + 1 if quality_score >= 3 else 0
        card.next_review_date = next_review_date
        card.last_reviewed_at = timezone.now()
        card.total_reviews += 1

        if quality_score >= 3:  # 正解の場合
            card.correct_reviews += 1

        card.save()

        # 復習記録を作成
        review = SpacedRepetitionReview.objects.create(
            card=card,
            user=self.user,
            problem=card.problem,
            quality_score=quality_score,
            response_time_seconds=response_time_seconds,
            is_correct=quality_score >= 3,
            hint_used=hint_used,
            previous_ease_factor=previous_ease_factor,
            previous_interval=previous_interval,
            previous_repetition_count=previous_repetition_count,
            new_ease_factor=new_ease_factor,
            new_interval=new_interval,
            new_repetition_count=card.repetition_count,
            next_review_date=next_review_date,
            study_session=study_session
        )

        # 関連キャッシュを無効化
        cache_service.invalidate_spaced_repetition_cache(self.user.id)
        cache_service.invalidate_statistics_cache(self.user.id)
        cache_service.invalidate_analytics_cache(self.user.id)

        return review

    def get_daily_study_plan(self, available_time_minutes: int = 30) -> Dict:
        """1日の学習プランを生成"""
        due_cards = self.get_due_cards(limit=50)

        # ユーザーの学習レベルを判定
        user_stats = self.get_user_statistics()
        user_level = self._determine_user_level(user_stats)

        # 現在のストリークを取得
        current_streak = self._get_current_streak()

        # 推奨問題数を計算
        recommendations = self.calculator.get_recommended_daily_problems(
            current_streak=current_streak,
            user_level=user_level,
            available_time_minutes=available_time_minutes
        )

        # 新しい問題を導入すべきかチェック
        should_introduce_new = self.calculator.should_introduce_new_problems(
            current_due_count=len(due_cards),
            user_accuracy=user_stats.get('overall_accuracy', 0.8),
            daily_goal=recommendations['total_problems']
        )

        new_cards = []
        if should_introduce_new:
            new_problems = self.get_new_cards(limit=recommendations['new_problems'])
            new_cards = [self.create_card_for_problem(problem) for problem in new_problems]

        return {
            'due_cards': due_cards[:recommendations['review_problems']],
            'new_cards': new_cards,
            'total_cards': len(due_cards) + len(new_cards),
            'estimated_time_minutes': recommendations['estimated_time_minutes'],
            'recommendations': recommendations,
            'user_level': user_level,
            'current_streak': current_streak
        }

    def get_user_statistics(self) -> Dict:
        """ユーザーの学習統計を取得"""
        cached_stats = cache_service.get_statistics_cache(self.user.id, 'spaced_repetition')

        if cached_stats is not None:
            return cached_stats

        cards = SpacedRepetitionCard.objects.filter(user=self.user)
        reviews = SpacedRepetitionReview.objects.filter(user=self.user)

        total_cards = cards.count()
        if total_cards == 0:
            stats = {
                'total_cards': 0,
                'overall_accuracy': 0,
                'average_ease_factor': 2.5,
                'mastery_distribution': {}
            }
            cache_service.set_statistics_cache(self.user.id, 'spaced_repetition', stats)
            return stats

        # 習熟度分布
        mastery_distribution = {}
        for level in ['new', 'learning', 'familiar', 'mastered']:
            count = sum(1 for card in cards if card.mastery_level == level)
            mastery_distribution[level] = count

        # 全体的な統計
        recent_reviews = reviews.filter(
            reviewed_at__gte=timezone.now() - timedelta(days=30)
        )

        overall_accuracy = 0
        if recent_reviews.exists():
            correct_count = recent_reviews.filter(is_correct=True).count()
            overall_accuracy = correct_count / recent_reviews.count()

        average_ease_factor = cards.aggregate(
            avg_ease=Avg('ease_factor')
        )['avg_ease'] or 2.5

        stats = {
            'total_cards': total_cards,
            'overall_accuracy': overall_accuracy,
            'average_ease_factor': average_ease_factor,
            'mastery_distribution': mastery_distribution,
            'total_reviews': reviews.count(),
            'recent_reviews_count': recent_reviews.count()
        }

        cache_service.set_statistics_cache(self.user.id, 'spaced_repetition', stats)
        return stats

    def _determine_user_level(self, stats: Dict) -> str:
        """ユーザーの学習レベルを判定"""
        total_cards = stats.get('total_cards', 0)
        accuracy = stats.get('overall_accuracy', 0)

        if total_cards < 20:
            return 'beginner'
        elif total_cards < 100 or accuracy < 0.7:
            return 'intermediate'
        else:
            return 'advanced'

    def _get_current_streak(self) -> int:
        """現在の連続学習日数を取得"""
        today = date.today()
        streak = 0

        # 過去30日分をチェック
        for i in range(30):
            check_date = today - timedelta(days=i)

            # その日に復習があったかチェック
            has_reviews = SpacedRepetitionReview.objects.filter(
                user=self.user,
                reviewed_at__date=check_date
            ).exists()

            if has_reviews:
                if i == 0 or streak > 0:  # 今日または連続している場合
                    streak += 1
                else:
                    break  # 連続が途切れた
            elif i == 0:
                break  # 今日やっていない
            else:
                break  # 連続が途切れた

        return streak

    def update_daily_analytics(self, target_date: date = None) -> LearningAnalytics:
        """日次の学習分析データを更新"""
        if target_date is None:
            target_date = date.today()

        cards = SpacedRepetitionCard.objects.filter(user=self.user)
        reviews_today = SpacedRepetitionReview.objects.filter(
            user=self.user,
            reviewed_at__date=target_date
        )

        # 基本統計
        total_cards = cards.count()
        new_cards = cards.filter(repetition_count=0).count()
        due_cards = cards.filter(
            next_review_date__date__lte=target_date,
            is_active=True
        ).count()
        reviewed_cards = reviews_today.count()

        # パフォーマンス
        avg_ease = cards.aggregate(avg=Avg('ease_factor'))['avg'] or 0.0
        avg_interval = cards.aggregate(avg=Avg('interval_days'))['avg'] or 0.0

        # 定着率計算
        if reviewed_cards > 0:
            correct_reviews = reviews_today.filter(is_correct=True).count()
            retention_rate = correct_reviews / reviewed_cards
        else:
            retention_rate = 0.0

        # 時間統計
        total_review_time = reviews_today.aggregate(
            total=Sum('response_time_seconds')
        )['total'] or 0

        avg_response_time = reviews_today.aggregate(
            avg=Avg('response_time_seconds')
        )['avg'] or 0.0

        # 難易度別統計
        difficulty_counts = {
            'easy': cards.filter(problem__difficulty='easy').count(),
            'medium': cards.filter(problem__difficulty='medium').count(),
            'hard': cards.filter(problem__difficulty='hard').count(),
        }

        # データを更新または作成
        analytics, created = LearningAnalytics.objects.update_or_create(
            user=self.user,
            date=target_date,
            defaults={
                'total_cards': total_cards,
                'new_cards': new_cards,
                'due_cards': due_cards,
                'reviewed_cards': reviewed_cards,
                'average_ease_factor': avg_ease,
                'average_interval': avg_interval,
                'retention_rate': retention_rate,
                'total_review_time': total_review_time,
                'average_response_time': avg_response_time,
                'easy_cards_count': difficulty_counts['easy'],
                'medium_cards_count': difficulty_counts['medium'],
                'hard_cards_count': difficulty_counts['hard'],
            }
        )

        return analytics

    def get_learning_insights(self, days: int = 7) -> Dict:
        """学習洞察を生成"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)

        analytics = LearningAnalytics.objects.filter(
            user=self.user,
            date__range=[start_date, end_date]
        ).order_by('date')

        if not analytics.exists():
            return {'insights': [], 'recommendations': []}

        insights = []
        recommendations = []

        # 定着率の分析
        retention_rates = [a.retention_rate for a in analytics if a.reviewed_cards > 0]
        if retention_rates:
            avg_retention = sum(retention_rates) / len(retention_rates)
            if avg_retention < 0.7:
                insights.append("記憶定着率が低下しています")
                recommendations.append("復習頻度を上げることをお勧めします")
            elif avg_retention > 0.9:
                insights.append("優秀な記憶定着率を維持しています")
                recommendations.append("新しい問題に挑戦してみましょう")

        # 学習継続性の分析
        study_days = analytics.filter(reviewed_cards__gt=0).count()
        if study_days < days * 0.7:
            insights.append("学習の継続性に改善の余地があります")
            recommendations.append("毎日短時間でも学習することをお勧めします")

        # 回答時間の分析
        response_times = [a.average_response_time for a in analytics if a.average_response_time > 0]
        if response_times:
            recent_avg = sum(response_times[-3:]) / min(len(response_times), 3)
            if recent_avg > 30:  # 30秒以上
                insights.append("回答に時間がかかっています")
                recommendations.append("基礎知識の復習をお勧めします")

        return {
            'insights': insights,
            'recommendations': recommendations,
            'period_days': days,
            'analytics_data': list(analytics.values())
        }
