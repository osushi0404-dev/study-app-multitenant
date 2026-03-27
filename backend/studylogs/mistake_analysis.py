"""
間違いパターン分析と学習提案システム

ユーザーの学習データを分析して、間違いのパターンを特定し、
個別化された学習提案を生成する
"""

from datetime import datetime, timedelta
from typing import List, Dict
from django.utils import timezone
from django.db.models import Avg
from django.contrib.auth import get_user_model

from .models import (
    MistakePattern, LearningSuggestion, LearningWeakness,
    ProblemAttempt, SpacedRepetitionReview, StudyLog
)
from problems.models import Subject

User = get_user_model()


class MistakeAnalysisService:
    """間違いパターン分析サービス"""

    def __init__(self, user):
        self.user = user

    def analyze_mistakes(self, days: int = 30) -> Dict:
        """包括的な間違い分析を実行"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # 間違いパターンを更新
        self.update_mistake_patterns(start_date, end_date)

        # 弱点を更新
        self.update_learning_weaknesses(start_date, end_date)

        # 学習提案を生成
        self.generate_learning_suggestions()

        # 結果をまとめて返す
        return self.get_analysis_summary()

    def update_mistake_patterns(self, start_date: datetime, end_date: datetime):
        """間違いパターンを更新"""

        # 間隔反復学習からの間違いデータ
        sr_errors = SpacedRepetitionReview.objects.filter(
            user=self.user,
            reviewed_at__range=[start_date, end_date],
            is_correct=False
        ).select_related('problem', 'problem__subject')

        # 通常の問題試行からの間違いデータ
        attempt_errors = ProblemAttempt.objects.filter(
            user=self.user,
            attempted_at__range=[start_date, end_date],
            is_correct=False
        ).select_related('problem', 'problem__subject')

        # 科目別の苦手分野を分析
        self._analyze_subject_difficulties(sr_errors, attempt_errors)

        # 問題タイプ別の間違いを分析
        self._analyze_problem_type_errors(sr_errors, attempt_errors)

        # 時間制限による間違いを分析
        self._analyze_time_pressure_errors(sr_errors, attempt_errors)

        # 概念の混同を分析
        self._analyze_concept_confusion(sr_errors, attempt_errors)

    def _analyze_subject_difficulties(self, sr_errors, attempt_errors):
        """科目別の苦手分野を分析"""
        subject_stats = {}

        # 間隔反復学習のエラー統計
        for review in sr_errors:
            subject = review.problem.subject
            if subject not in subject_stats:
                subject_stats[subject] = {'errors': 0, 'total': 0}
            subject_stats[subject]['errors'] += 1

        # 全体の試行回数を取得
        for subject in subject_stats.keys():
            total_sr = SpacedRepetitionReview.objects.filter(
                user=self.user,
                problem__subject=subject,
                reviewed_at__range=[timezone.now() - timedelta(days=30), timezone.now()]
            ).count()

            total_attempts = ProblemAttempt.objects.filter(
                user=self.user,
                problem__subject=subject,
                attempted_at__range=[timezone.now() - timedelta(days=30), timezone.now()]
            ).count()

            subject_stats[subject]['total'] = total_sr + total_attempts

        # パターンを更新または作成
        for subject, stats in subject_stats.items():
            if stats['total'] > 0:
                error_rate = stats['errors'] / stats['total']

                if error_rate > 0.3:  # 30%以上のエラー率
                    pattern, created = MistakePattern.objects.get_or_create(
                        user=self.user,
                        pattern_type='subject_difficulty',
                        subject=subject,
                        defaults={
                            'description': f"{subject.name}の問題で間違いが多発しています",
                            'confidence_score': min(error_rate * 1.5, 1.0)
                        }
                    )

                    if not created:
                        pattern.occurrence_count += stats['errors']
                        pattern.total_attempts += stats['total']
                        pattern.confidence_score = min(error_rate * 1.5, 1.0)
                        pattern.save()

    def _analyze_problem_type_errors(self, sr_errors, attempt_errors):
        """問題タイプ別の間違いを分析"""
        # 難易度別の分析
        difficulty_stats = {
            'easy': {'errors': 0, 'total': 0},
            'medium': {'errors': 0, 'total': 0},
            'hard': {'errors': 0, 'total': 0},
        }

        for review in sr_errors:
            difficulty = review.problem.difficulty
            if difficulty in difficulty_stats:
                difficulty_stats[difficulty]['errors'] += 1

        for attempt in attempt_errors:
            difficulty = attempt.problem.difficulty
            if difficulty in difficulty_stats:
                difficulty_stats[difficulty]['errors'] += 1

        # 全体の試行回数を取得
        for difficulty in difficulty_stats.keys():
            total_sr = SpacedRepetitionReview.objects.filter(
                user=self.user,
                problem__difficulty=difficulty
            ).count()

            total_attempts = ProblemAttempt.objects.filter(
                user=self.user,
                problem__difficulty=difficulty
            ).count()

            difficulty_stats[difficulty]['total'] = total_sr + total_attempts

        # パターンを更新
        for difficulty, stats in difficulty_stats.items():
            if stats['total'] > 10 and stats['errors'] > 0:  # 十分なデータがある場合
                error_rate = stats['errors'] / stats['total']

                if error_rate > 0.4:  # 40%以上のエラー率
                    pattern, created = MistakePattern.objects.get_or_create(
                        user=self.user,
                        pattern_type='problem_type',
                        problem_difficulty=difficulty,
                        defaults={
                            'description': f"{difficulty}レベルの問題で間違いが多発しています",
                            'confidence_score': min(error_rate * 1.2, 1.0)
                        }
                    )

                    if not created:
                        pattern.occurrence_count += stats['errors']
                        pattern.total_attempts += stats['total']
                        pattern.save()

    def _analyze_time_pressure_errors(self, sr_errors, attempt_errors):
        """時間制限による間違いを分析"""
        time_related_errors = 0
        total_timed_attempts = 0

        # 平均回答時間を計算
        avg_time_by_user = SpacedRepetitionReview.objects.filter(
            user=self.user
        ).aggregate(avg_time=Avg('response_time_seconds'))['avg_time'] or 30

        # 通常より大幅に早い回答での間違いをチェック
        for review in sr_errors:
            if review.response_time_seconds < avg_time_by_user * 0.5:  # 平均の50%未満
                time_related_errors += 1
            total_timed_attempts += 1

        if total_timed_attempts > 20 and time_related_errors > 0:
            error_rate = time_related_errors / total_timed_attempts

            if error_rate > 0.25:  # 25%以上が時間関連エラー
                pattern, created = MistakePattern.objects.get_or_create(
                    user=self.user,
                    pattern_type='time_pressure',
                    defaults={
                        'description': "時間を急いで回答することで間違いが増加しています",
                        'confidence_score': min(error_rate * 2.0, 1.0)
                    }
                )

                if not created:
                    pattern.occurrence_count += time_related_errors
                    pattern.total_attempts += total_timed_attempts
                    pattern.save()

    def _analyze_concept_confusion(self, sr_errors, attempt_errors):
        """概念の混同を分析"""
        # 同じ科目内での異なる問題タイプでの間違いパターンを探す
        subject_error_patterns = {}

        for review in sr_errors:
            subject = review.problem.subject
            if subject not in subject_error_patterns:
                subject_error_patterns[subject] = []
            subject_error_patterns[subject].append(review.problem)

        for subject, problems in subject_error_patterns.items():
            if len(problems) >= 3:  # 同じ科目で3つ以上の間違い
                pattern, created = MistakePattern.objects.get_or_create(
                    user=self.user,
                    pattern_type='concept_confusion',
                    subject=subject,
                    defaults={
                        'description': f"{subject.name}の概念間で混同が発生しています",
                        'confidence_score': min(len(problems) / 10.0, 1.0)
                    }
                )

                if not created:
                    pattern.occurrence_count += len(problems)
                    pattern.save()

    def update_learning_weaknesses(self, start_date: datetime, end_date: datetime):
        """学習の弱点を更新"""
        subjects = Subject.objects.all()

        for subject in subjects:
            # 科目別の統計を取得
            subject_attempts = ProblemAttempt.objects.filter(
                user=self.user,
                problem__subject=subject,
                attempted_at__range=[start_date, end_date]
            )

            subject_reviews = SpacedRepetitionReview.objects.filter(
                user=self.user,
                problem__subject=subject,
                reviewed_at__range=[start_date, end_date]
            )

            total_problems = subject_attempts.count() + subject_reviews.count()
            error_count = (subject_attempts.filter(is_correct=False).count() +
                           subject_reviews.filter(is_correct=False).count())

            if total_problems >= 5:  # 十分なデータがある場合
                # 概念別の分析（簡単なバージョン）
                concept_name = f"{subject.name}の基本概念"

                weakness, created = LearningWeakness.objects.get_or_create(
                    user=self.user,
                    subject=subject,
                    concept_name=concept_name,
                    defaults={
                        'problem_count': total_problems,
                        'error_count': error_count,
                        'last_error_date': timezone.now() if error_count > 0 else None
                    }
                )

                if not created:
                    weakness.problem_count += total_problems
                    weakness.error_count += error_count
                    if error_count > 0:
                        weakness.last_error_date = timezone.now()
                    weakness.save()

                # 深刻度を更新
                weakness.update_severity()

    def generate_learning_suggestions(self):
        """学習提案を生成"""
        # アクティブな間違いパターンを取得
        active_patterns = MistakePattern.objects.filter(
            user=self.user,
            is_active=True,
            confidence_score__gte=0.3
        ).order_by('-occurrence_count', '-confidence_score')

        # 深刻な弱点を取得
        critical_weaknesses = LearningWeakness.objects.filter(
            user=self.user,
            severity__in=['critical', 'high'],
            is_resolved=False
        ).order_by('-severity', '-error_count')

        # パターンベースの提案を生成
        for pattern in active_patterns[:5]:  # 上位5つのパターン
            self._generate_pattern_based_suggestions(pattern)

        # 弱点ベースの提案を生成
        for weakness in critical_weaknesses[:3]:  # 上位3つの弱点
            self._generate_weakness_based_suggestions(weakness)

        # 一般的な学習改善提案
        self._generate_general_suggestions()

    def _generate_pattern_based_suggestions(self, pattern: MistakePattern):
        """パターンベースの学習提案を生成"""
        suggestions_map = {
            'subject_difficulty': {
                'title': f"{pattern.subject.name}の重点的な復習",
                'description': f"{pattern.subject.name}で間違いが多発しているため、基礎から復習することをお勧めします。",
                'action_steps': [
                    f"{pattern.subject.name}の基本概念を復習する",
                    "簡単な問題から段階的に練習する",
                    "間違いやすいポイントをメモにまとめる",
                    "毎日少しずつでも継続して練習する"
                ],
                'suggestion_type': 'concept_review',
                'priority': 'high' if pattern.error_rate > 60 else 'medium'
            },
            'problem_type': {
                'title': f"{pattern.get_problem_difficulty_display()}レベル問題の強化",
                'description': f"{pattern.get_problem_difficulty_display()}レベルの問題で苦戦しています。段階的なアプローチで克服しましょう。",
                'action_steps': [
                    "より簡単なレベルから始める",
                    "解法パターンを覚える",
                    "時間をかけて確実に解く練習をする",
                    "同じタイプの問題を繰り返し練習する"
                ],
                'suggestion_type': 'practice_focus',
                'priority': 'medium'
            },
            'time_pressure': {
                'title': "時間管理スキルの向上",
                'description': "急いで回答することで間違いが増えています。正確性を重視した学習を心がけましょう。",
                'action_steps': [
                    "制限時間を設けずに正確に解く練習をする",
                    "解法の手順を明確にする",
                    "見直しの時間を確保する",
                    "段階的に制限時間を短くしていく"
                ],
                'suggestion_type': 'time_management',
                'priority': 'medium'
            },
            'concept_confusion': {
                'title': f"{pattern.subject.name}の概念整理",
                'description': f"{pattern.subject.name}の概念間で混同が発生しています。概念マップで整理しましょう。",
                'action_steps': [
                    "関連概念をマインドマップで整理する",
                    "似た概念の違いを明確にする",
                    "具体例で理解を深める",
                    "定期的に概念を復習する"
                ],
                'suggestion_type': 'concept_review',
                'priority': 'high'
            }
        }

        suggestion_config = suggestions_map.get(pattern.pattern_type, {})
        if not suggestion_config:
            return

        # 既存の提案をチェック（重複防止）
        existing = LearningSuggestion.objects.filter(
            user=self.user,
            mistake_pattern=pattern,
            is_active=True
        ).exists()

        if not existing:
            LearningSuggestion.objects.create(
                user=self.user,
                mistake_pattern=pattern,
                subject=pattern.subject,
                **suggestion_config,
                estimated_time_minutes=30,
                expires_at=timezone.now() + timedelta(days=14)
            )

    def _generate_weakness_based_suggestions(self, weakness: LearningWeakness):
        """弱点ベースの学習提案を生成"""
        suggestion_title = f"{weakness.concept_name}の集中強化"
        suggestion_description = f"{weakness.concept_name}で{weakness.error_rate:.1f}%のエラー率となっています。集中的な練習が必要です。"

        action_steps = [
            f"{weakness.concept_name}の基本理論を復習する",
            "関連する例題を解いて理解を深める",
            "間違いやすいポイントを特定する",
            "毎日の練習計画を立てる"
        ]

        if weakness.severity == 'critical':
            action_steps.insert(0, "学習方法を根本的に見直す")
            priority = 'urgent'
        elif weakness.severity == 'high':
            priority = 'high'
        else:
            priority = 'medium'

        # 既存の提案をチェック
        existing = LearningSuggestion.objects.filter(
            user=self.user,
            subject=weakness.subject,
            title__icontains=weakness.concept_name,
            is_active=True
        ).exists()

        if not existing:
            LearningSuggestion.objects.create(
                user=self.user,
                subject=weakness.subject,
                suggestion_type='foundation_building',
                priority=priority,
                title=suggestion_title,
                description=suggestion_description,
                action_steps=action_steps,
                estimated_time_minutes=45,
                expires_at=timezone.now() + timedelta(days=21)
            )

    def _generate_general_suggestions(self):
        """一般的な学習改善提案を生成"""
        # ユーザーの学習統計を取得
        recent_study_logs = StudyLog.objects.filter(
            user=self.user,
            started_at__gte=timezone.now() - timedelta(days=7)
        )

        if recent_study_logs.count() < 3:
            # 学習頻度が低い場合
            LearningSuggestion.objects.get_or_create(
                user=self.user,
                suggestion_type='study_method',
                title="学習習慣の確立",
                defaults={
                    'description': "学習頻度が低下しています。継続的な学習習慣を身につけましょう。",
                    'action_steps': [
                        "毎日決まった時間に学習する",
                        "短時間でも継続することを重視する",
                        "学習カレンダーで進捗を可視化する",
                        "小さな目標から始める"
                    ],
                    'priority': 'high',
                    'estimated_time_minutes': 20,
                    'expires_at': timezone.now() + timedelta(days=10)
                }
            )

    def get_analysis_summary(self) -> Dict:
        """分析結果のサマリーを取得"""
        patterns = MistakePattern.objects.filter(
            user=self.user,
            is_active=True
        ).order_by('-occurrence_count')

        weaknesses = LearningWeakness.objects.filter(
            user=self.user,
            is_resolved=False
        ).order_by('-severity', '-error_count')

        suggestions = LearningSuggestion.objects.filter(
            user=self.user,
            is_active=True,
            is_read=False
        ).order_by('priority', '-created_at')

        # 改善トレンドの計算
        improvement_trends = self._calculate_improvement_trends()

        summary = {
            'total_patterns': patterns.count(),
            'critical_weaknesses': weaknesses.filter(severity='critical').count(),
            'active_suggestions': suggestions.count(),
            'overall_improvement_rate': self._calculate_overall_improvement_rate()
        }

        return {
            'patterns': patterns,
            'weaknesses': weaknesses,
            'suggestions': suggestions,
            'summary': summary,
            'improvement_trends': improvement_trends
        }

    def _calculate_improvement_trends(self) -> List[Dict]:
        """改善トレンドを計算"""
        trends = []

        # 過去30日間の週別改善率
        for week in range(4):
            start_date = timezone.now() - timedelta(weeks=week+1)
            end_date = timezone.now() - timedelta(weeks=week)

            week_attempts = ProblemAttempt.objects.filter(
                user=self.user,
                attempted_at__range=[start_date, end_date]
            )

            if week_attempts.exists():
                accuracy = (week_attempts.filter(is_correct=True).count() /
                            week_attempts.count()) * 100

                trends.append({
                    'week': f"{week+1}週間前",
                    'accuracy': round(accuracy, 2),
                    'problems_attempted': week_attempts.count()
                })

        return trends

    def _calculate_overall_improvement_rate(self) -> float:
        """全体的な改善率を計算"""
        patterns = MistakePattern.objects.filter(
            user=self.user,
            is_active=True
        )

        if not patterns.exists():
            return 0.0

        total_improvement = sum(pattern.improvement_rate for pattern in patterns)
        return round(total_improvement / patterns.count(), 2)

    def provide_suggestion_feedback(self, suggestion_id: int, rating: int, comment: str = ""):
        """学習提案にフィードバックを提供"""
        try:
            suggestion = LearningSuggestion.objects.get(
                id=suggestion_id,
                user=self.user
            )

            suggestion.effectiveness_rating = rating
            suggestion.mark_as_applied()
            suggestion.save()

            # フィードバックに基づいて今後の提案を調整
            if rating >= 4:  # 効果的だった場合
                if suggestion.mistake_pattern:
                    suggestion.mistake_pattern.improvement_rate += 0.1
                    suggestion.mistake_pattern.save()

            return True

        except LearningSuggestion.DoesNotExist:
            return False
