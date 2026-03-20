"""
適応的問題選択システム

ユーザーの習熟度に基づいて最適な問題を選択し、
学習効率を最大化するためのアルゴリズム
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from django.db.models import Avg, Count, Q, F
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
    SpacedRepetitionCard, SpacedRepetitionReview, 
    ProblemAttempt, StudyLog, LearningAnalytics
)
from problems.models import Problem, Subject
from core.cache_service import cache_service
import random
import math

User = get_user_model()


class AdaptiveProblemSelector:
    """適応的問題選択サービス"""
    
    def __init__(self, user):
        self.user = user
        self.proficiency_cache = {}
    
    def select_optimal_problems(self, 
                              subject: Optional[Subject] = None,
                              count: int = 10,
                              difficulty_preference: str = 'adaptive',
                              learning_goal: str = 'balanced') -> List[Problem]:
        """
        最適な問題を選択
        
        Args:
            subject: 対象科目（Noneの場合は全科目）
            count: 選択する問題数
            difficulty_preference: 難易度設定 ('easy', 'medium', 'hard', 'adaptive')
            learning_goal: 学習目標 ('review', 'learning', 'challenge', 'balanced')
        """
        
        # ユーザーの習熟度を分析
        proficiency_data = self.analyze_user_proficiency(subject)
        
        # 問題プールを取得
        problem_pool = self._get_problem_pool(subject)
        
        # 学習目標に基づいて選択戦略を決定
        selection_strategy = self._get_selection_strategy(learning_goal, proficiency_data)
        
        # 問題をスコアリング
        scored_problems = self._score_problems(problem_pool, proficiency_data, selection_strategy)
        
        # 最適な問題を選択
        selected_problems = self._select_problems_by_score(
            scored_problems, count, difficulty_preference
        )
        
        return selected_problems
    
    def analyze_user_proficiency(self, subject: Optional[Subject] = None) -> Dict:
        """ユーザーの習熟度を分析"""
        # Redisキャッシュから取得を試みる
        cached_proficiency = cache_service.get_proficiency_cache(
            self.user.id, 
            subject.id if subject else None
        )
        
        if cached_proficiency is not None:
            return cached_proficiency
        
        # 過去30日の学習データを分析
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # 基本統計
        attempts_filter = {'user': self.user, 'attempted_at__range': [start_date, end_date]}
        reviews_filter = {'user': self.user, 'reviewed_at__range': [start_date, end_date]}
        
        if subject:
            attempts_filter['problem__subject'] = subject
            reviews_filter['problem__subject'] = subject
        
        attempts = ProblemAttempt.objects.filter(**attempts_filter)
        reviews = SpacedRepetitionReview.objects.filter(**reviews_filter)
        
        # 難易度別の成績
        difficulty_stats = self._calculate_difficulty_proficiency(attempts, reviews)
        
        # 科目別の成績（科目指定がない場合）
        subject_stats = {}
        if not subject:
            subject_stats = self._calculate_subject_proficiency(attempts, reviews)
        
        # 学習パターンの分析
        learning_patterns = self._analyze_learning_patterns(attempts, reviews)
        
        # 成長率の計算
        growth_rate = self._calculate_growth_rate()
        
        proficiency_data = {
            'difficulty_proficiency': difficulty_stats,
            'subject_proficiency': subject_stats,
            'learning_patterns': learning_patterns,
            'growth_rate': growth_rate,
            'total_attempts': attempts.count() + reviews.count(),
            'overall_accuracy': self._calculate_overall_accuracy(attempts, reviews),
            'confidence_level': self._calculate_confidence_level(attempts, reviews)
        }
        
        # Redisキャッシュに保存
        cache_service.set_proficiency_cache(
            self.user.id, 
            proficiency_data, 
            subject.id if subject else None
        )
        
        return proficiency_data
    
    def _calculate_difficulty_proficiency(self, attempts, reviews) -> Dict:
        """難易度別の習熟度を計算"""
        difficulty_stats = {}
        
        for difficulty in ['easy', 'medium', 'hard']:
            # 問題試行からの統計
            diff_attempts = attempts.filter(problem__difficulty=difficulty)
            attempt_accuracy = 0
            if diff_attempts.exists():
                correct_attempts = diff_attempts.filter(is_correct=True).count()
                attempt_accuracy = correct_attempts / diff_attempts.count()
            
            # 間隔反復学習からの統計
            diff_reviews = reviews.filter(problem__difficulty=difficulty)
            review_accuracy = 0
            if diff_reviews.exists():
                correct_reviews = diff_reviews.filter(is_correct=True).count()
                review_accuracy = correct_reviews / diff_reviews.count()
            
            # 総合精度
            total_correct = (diff_attempts.filter(is_correct=True).count() + 
                           diff_reviews.filter(is_correct=True).count())
            total_count = diff_attempts.count() + diff_reviews.count()
            
            overall_accuracy = total_correct / total_count if total_count > 0 else 0
            
            # 平均回答時間
            avg_time = 0
            if diff_reviews.exists():
                avg_time = diff_reviews.aggregate(
                    avg_time=Avg('response_time_seconds')
                )['avg_time'] or 0
            
            # 習熟度スコア（0-1）
            proficiency_score = self._calculate_proficiency_score(
                overall_accuracy, total_count, avg_time, difficulty
            )
            
            difficulty_stats[difficulty] = {
                'accuracy': overall_accuracy,
                'total_attempts': total_count,
                'average_time': avg_time,
                'proficiency_score': proficiency_score,
                'confidence': min(total_count / 20, 1.0)  # 信頼度
            }
        
        return difficulty_stats
    
    def _calculate_subject_proficiency(self, attempts, reviews) -> Dict:
        """科目別の習熟度を計算"""
        subjects = Subject.objects.all()
        subject_stats = {}
        
        for subject in subjects:
            subj_attempts = attempts.filter(problem__subject=subject)
            subj_reviews = reviews.filter(problem__subject=subject)
            
            total_correct = (subj_attempts.filter(is_correct=True).count() + 
                           subj_reviews.filter(is_correct=True).count())
            total_count = subj_attempts.count() + subj_reviews.count()
            
            if total_count > 0:
                accuracy = total_correct / total_count
                
                # 最近の学習頻度
                recent_count = subj_attempts.filter(
                    attempted_at__gte=timezone.now() - timedelta(days=7)
                ).count()
                
                subject_stats[subject.id] = {
                    'accuracy': accuracy,
                    'total_attempts': total_count,
                    'recent_activity': recent_count,
                    'proficiency_score': min(accuracy + (recent_count / 10), 1.0)
                }
        
        return subject_stats
    
    def _analyze_learning_patterns(self, attempts, reviews) -> Dict:
        """学習パターンを分析"""
        patterns = {
            'consistency': 0,  # 継続性
            'difficulty_progression': 0,  # 難易度の適切な進行
            'time_efficiency': 0,  # 時間効率
            'retention_quality': 0  # 記憶定着の質
        }
        
        # 継続性の評価
        study_dates = set()
        for attempt in attempts:
            study_dates.add(attempt.attempted_at.date())
        for review in reviews:
            study_dates.add(review.reviewed_at.date())
        
        # 過去30日での学習日数
        patterns['consistency'] = min(len(study_dates) / 30, 1.0)
        
        # 難易度進行の評価
        if reviews.exists():
            recent_reviews = reviews.order_by('-reviewed_at')[:20]
            difficulty_progression = self._evaluate_difficulty_progression(recent_reviews)
            patterns['difficulty_progression'] = difficulty_progression
        
        # 時間効率の評価
        if reviews.exists():
            avg_response_time = reviews.aggregate(
                avg_time=Avg('response_time_seconds')
            )['avg_time'] or 0
            
            # 適切な回答時間（難易度別の期待値と比較）
            patterns['time_efficiency'] = self._evaluate_time_efficiency(avg_response_time)
        
        # 記憶定着の質
        if reviews.exists():
            retention_quality = self._evaluate_retention_quality(reviews)
            patterns['retention_quality'] = retention_quality
        
        return patterns
    
    def _calculate_growth_rate(self) -> float:
        """成長率を計算"""
        # 過去4週間の週別精度を比較
        growth_rates = []
        
        for week in range(4):
            start_week = timezone.now() - timedelta(weeks=week+1)
            end_week = timezone.now() - timedelta(weeks=week)
            
            week_attempts = ProblemAttempt.objects.filter(
                user=self.user,
                attempted_at__range=[start_week, end_week]
            )
            
            if week_attempts.exists():
                accuracy = week_attempts.filter(is_correct=True).count() / week_attempts.count()
                growth_rates.append(accuracy)
        
        if len(growth_rates) >= 2:
            # 最新週と3週間前の比較
            recent_accuracy = growth_rates[0]
            old_accuracy = growth_rates[-1]
            growth_rate = (recent_accuracy - old_accuracy) / old_accuracy if old_accuracy > 0 else 0
            return max(-1.0, min(1.0, growth_rate))  # -100% ~ +100%
        
        return 0.0
    
    def _calculate_overall_accuracy(self, attempts, reviews) -> float:
        """全体的な正答率を計算"""
        total_correct = (attempts.filter(is_correct=True).count() + 
                        reviews.filter(is_correct=True).count())
        total_count = attempts.count() + reviews.count()
        
        return total_correct / total_count if total_count > 0 else 0
    
    def _calculate_confidence_level(self, attempts, reviews) -> float:
        """信頼度レベルを計算"""
        total_data_points = attempts.count() + reviews.count()
        
        # データ点数に基づく信頼度（最大50点で100%）
        data_confidence = min(total_data_points / 50, 1.0)
        
        # 最近のアクティビティに基づく信頼度
        recent_attempts = attempts.filter(
            attempted_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        activity_confidence = min(recent_attempts / 10, 1.0)
        
        return (data_confidence + activity_confidence) / 2
    
    def _get_problem_pool(self, subject: Optional[Subject]) -> List[Problem]:
        """問題プールを取得"""
        filters = {'is_active': True}
        if subject:
            filters['subject'] = subject
        
        # ユーザーが最近解いていない問題を優先
        recent_attempts = ProblemAttempt.objects.filter(
            user=self.user,
            attempted_at__gte=timezone.now() - timedelta(days=7)
        ).values_list('problem_id', flat=True)
        
        recent_reviews = SpacedRepetitionReview.objects.filter(
            user=self.user,
            reviewed_at__gte=timezone.now() - timedelta(days=7)
        ).values_list('problem_id', flat=True)
        
        recent_problem_ids = set(recent_attempts) | set(recent_reviews)
        
        problems = Problem.objects.filter(**filters).exclude(
            id__in=recent_problem_ids
        ).select_related('subject')
        
        return list(problems)
    
    def _get_selection_strategy(self, learning_goal: str, proficiency_data: Dict) -> Dict:
        """選択戦略を決定"""
        strategies = {
            'review': {
                'easy_weight': 0.4,
                'medium_weight': 0.4,
                'hard_weight': 0.2,
                'known_concept_weight': 0.6,
                'new_concept_weight': 0.4
            },
            'learning': {
                'easy_weight': 0.3,
                'medium_weight': 0.5,
                'hard_weight': 0.2,
                'known_concept_weight': 0.3,
                'new_concept_weight': 0.7
            },
            'challenge': {
                'easy_weight': 0.1,
                'medium_weight': 0.3,
                'hard_weight': 0.6,
                'known_concept_weight': 0.2,
                'new_concept_weight': 0.8
            },
            'balanced': {
                'easy_weight': 0.3,
                'medium_weight': 0.4,
                'hard_weight': 0.3,
                'known_concept_weight': 0.5,
                'new_concept_weight': 0.5
            }
        }
        
        base_strategy = strategies.get(learning_goal, strategies['balanced'])
        
        # ユーザーの習熟度に基づいて戦略を調整
        overall_accuracy = proficiency_data.get('overall_accuracy', 0.5)
        confidence_level = proficiency_data.get('confidence_level', 0.5)
        
        # 精度が低い場合は易しい問題を増やす
        if overall_accuracy < 0.6:
            base_strategy['easy_weight'] += 0.2
            base_strategy['medium_weight'] -= 0.1
            base_strategy['hard_weight'] -= 0.1
        
        # 精度が高い場合は難しい問題を増やす
        elif overall_accuracy > 0.85:
            base_strategy['easy_weight'] -= 0.1
            base_strategy['medium_weight'] -= 0.1
            base_strategy['hard_weight'] += 0.2
        
        return base_strategy
    
    def _score_problems(self, problems: List[Problem], 
                       proficiency_data: Dict, 
                       strategy: Dict) -> List[Tuple[Problem, float]]:
        """問題をスコアリング"""
        scored_problems = []
        
        for problem in problems:
            score = self._calculate_problem_score(problem, proficiency_data, strategy)
            scored_problems.append((problem, score))
        
        return sorted(scored_problems, key=lambda x: x[1], reverse=True)
    
    def _calculate_problem_score(self, problem: Problem, 
                                proficiency_data: Dict, 
                                strategy: Dict) -> float:
        """個別問題のスコアを計算"""
        score = 0.0
        
        # 難易度に基づくスコア
        difficulty = problem.difficulty
        difficulty_weights = {
            'easy': strategy['easy_weight'],
            'medium': strategy['medium_weight'], 
            'hard': strategy['hard_weight']
        }
        score += difficulty_weights.get(difficulty, 0.3)
        
        # ユーザーの習熟度に基づく調整
        difficulty_prof = proficiency_data['difficulty_proficiency'].get(difficulty, {})
        proficiency_score = difficulty_prof.get('proficiency_score', 0.5)
        
        # 習熟度が適切なレベルの問題に高スコア
        if 0.3 <= proficiency_score <= 0.8:  # 適度な難易度
            score += 0.3
        elif proficiency_score < 0.3:  # 難しすぎる
            score += 0.1
        else:  # 簡単すぎる
            score += 0.2
        
        # 科目の習熟度に基づく調整
        subject_prof = proficiency_data['subject_proficiency'].get(problem.subject.id, {})
        subject_accuracy = subject_prof.get('accuracy', 0.5)
        
        # 苦手科目により多くの機会を提供
        if subject_accuracy < 0.6:
            score += 0.2
        elif subject_accuracy > 0.9:
            score += 0.1
        
        # 最近の学習履歴に基づく調整
        recent_attempts = ProblemAttempt.objects.filter(
            user=self.user,
            problem=problem,
            attempted_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # 最近解いていない問題により高いスコア
        if recent_attempts == 0:
            score += 0.2
        elif recent_attempts <= 2:
            score += 0.1
        else:
            score -= 0.1  # 最近よく解いている問題は避ける
        
        # ランダム要素を追加（探索的学習のため）
        score += random.uniform(0, 0.1)
        
        return max(0, min(1, score))  # 0-1の範囲にクランプ
    
    def _select_problems_by_score(self, scored_problems: List[Tuple[Problem, float]], 
                                 count: int, 
                                 difficulty_preference: str) -> List[Problem]:
        """スコアに基づいて問題を選択"""
        
        if difficulty_preference != 'adaptive':
            # 特定の難易度を優先
            filtered_problems = [
                (p, s) for p, s in scored_problems 
                if p.difficulty == difficulty_preference
            ]
            if len(filtered_problems) >= count:
                scored_problems = filtered_problems
        
        # 上位の問題を選択（完全にスコア順ではなく、一定の確率的選択を含む）
        selected = []
        remaining_problems = scored_problems.copy()
        
        for _ in range(min(count, len(remaining_problems))):
            # 上位20%からランダムに選択（探索と活用のバランス）
            top_count = max(1, len(remaining_problems) // 5)
            top_problems = remaining_problems[:top_count]
            
            # 重み付きランダム選択
            weights = [score for _, score in top_problems]
            total_weight = sum(weights)
            
            if total_weight > 0:
                rand_val = random.uniform(0, total_weight)
                cumulative = 0
                
                for i, (problem, score) in enumerate(top_problems):
                    cumulative += score
                    if rand_val <= cumulative:
                        selected.append(problem)
                        remaining_problems.remove((problem, score))
                        break
            else:
                # フォールバック：ランダム選択
                problem, score = random.choice(top_problems)
                selected.append(problem)
                remaining_problems.remove((problem, score))
        
        return selected
    
    def _calculate_proficiency_score(self, accuracy: float, total_attempts: int, 
                                   avg_time: float, difficulty: str) -> float:
        """習熟度スコアを計算"""
        # 基本スコア（正答率ベース）
        base_score = accuracy
        
        # データ量による信頼度調整
        confidence_factor = min(total_attempts / 10, 1.0)
        
        # 時間効率による調整
        expected_times = {'easy': 20, 'medium': 35, 'hard': 60}
        expected_time = expected_times.get(difficulty, 35)
        
        time_efficiency = 1.0
        if avg_time > 0:
            time_efficiency = min(expected_time / avg_time, 2.0)  # 2倍まで
        
        # 最終スコア
        proficiency_score = base_score * confidence_factor * (1 + time_efficiency * 0.2)
        return max(0, min(1, proficiency_score))
    
    def _evaluate_difficulty_progression(self, recent_reviews) -> float:
        """難易度の適切な進行を評価"""
        if len(recent_reviews) < 5:
            return 0.5
        
        # 最近の問題の難易度分布
        difficulty_counts = {'easy': 0, 'medium': 0, 'hard': 0}
        for review in recent_reviews:
            difficulty = review.problem.difficulty
            difficulty_counts[difficulty] += 1
        
        total = len(recent_reviews)
        easy_ratio = difficulty_counts['easy'] / total
        medium_ratio = difficulty_counts['medium'] / total
        hard_ratio = difficulty_counts['hard'] / total
        
        # 理想的な分布との比較（30% easy, 50% medium, 20% hard）
        ideal_distribution = [0.3, 0.5, 0.2]
        actual_distribution = [easy_ratio, medium_ratio, hard_ratio]
        
        # 分布の類似度を計算
        similarity = 1 - sum(abs(ideal - actual) for ideal, actual in 
                           zip(ideal_distribution, actual_distribution)) / 2
        
        return max(0, min(1, similarity))
    
    def _evaluate_time_efficiency(self, avg_response_time: float) -> float:
        """時間効率を評価"""
        # 理想的な回答時間（30秒）との比較
        ideal_time = 30
        
        if avg_response_time <= 0:
            return 0.5
        
        # 時間効率スコア
        if avg_response_time <= ideal_time:
            # 早すぎるのも良くない（急ぎすぎ）
            return 0.8 + 0.2 * (avg_response_time / ideal_time)
        else:
            # 遅い場合はペナルティ
            return max(0.1, 1.0 - (avg_response_time - ideal_time) / 60)
    
    def _evaluate_retention_quality(self, reviews) -> float:
        """記憶定着の質を評価"""
        if not reviews.exists():
            return 0.5
        
        # スペースド・リピティションの効果を測定
        # 復習間隔が長くなっても正答率が維持されているかをチェック
        
        retention_scores = []
        for review in reviews:
            card = review.card
            if card.repetition_count > 0:
                # 前回からの間隔と正答率の関係
                interval_factor = min(card.interval_days / 7, 4)  # 最大4週間
                if review.is_correct:
                    retention_score = 1.0 * (1 + interval_factor * 0.2)  # 長期間隔での正答は高評価
                else:
                    retention_score = 0.0
                retention_scores.append(retention_score)
        
        return sum(retention_scores) / len(retention_scores) if retention_scores else 0.5
    
    def get_personalized_recommendation(self, subject: Optional[Subject] = None) -> Dict:
        """個人化された学習推奨を取得"""
        proficiency_data = self.analyze_user_proficiency(subject)
        
        recommendations = {
            'suggested_focus_areas': [],
            'difficulty_recommendation': 'medium',
            'learning_goal_suggestion': 'balanced',
            'estimated_study_time': 30,
            'confidence_level': proficiency_data['confidence_level']
        }
        
        overall_accuracy = proficiency_data['overall_accuracy']
        difficulty_prof = proficiency_data['difficulty_proficiency']
        
        # 重点分野の推奨
        for difficulty, stats in difficulty_prof.items():
            if stats['accuracy'] < 0.6 and stats['total_attempts'] >= 5:
                recommendations['suggested_focus_areas'].append({
                    'area': f"{difficulty}レベルの問題",
                    'accuracy': stats['accuracy'],
                    'priority': 'high' if stats['accuracy'] < 0.4 else 'medium'
                })
        
        # 難易度推奨
        if overall_accuracy < 0.6:
            recommendations['difficulty_recommendation'] = 'easy'
            recommendations['learning_goal_suggestion'] = 'review'
        elif overall_accuracy > 0.85:
            recommendations['difficulty_recommendation'] = 'hard'
            recommendations['learning_goal_suggestion'] = 'challenge'
        
        # 学習時間推奨
        if proficiency_data['total_attempts'] < 10:
            recommendations['estimated_study_time'] = 20  # 初心者は短時間
        elif overall_accuracy < 0.5:
            recommendations['estimated_study_time'] = 45  # 苦手な場合は長時間
        
        return recommendations