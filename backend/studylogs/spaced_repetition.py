"""
間隔反復学習アルゴリズム (Spaced Repetition System)

SuperMemo SM-2アルゴリズムをベースにした実装
学習者の記憶定着を最適化するため、復習間隔を動的に調整する
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
import math


class SpacedRepetitionCalculator:
    """間隔反復学習のスケジューリングを計算するクラス"""
    
    # 初期設定値
    INITIAL_INTERVAL = 1  # 初回復習間隔（日）
    INITIAL_EASE_FACTOR = 2.5  # 初期難易度係数
    MIN_EASE_FACTOR = 1.3  # 最小難易度係数
    
    # 評価スコアの定義
    SCORE_MEANINGS = {
        0: "完全に忘れた",
        1: "間違えた（ヒントありでも困難）",
        2: "間違えた（ヒントありで思い出せた）", 
        3: "正解（困難）",
        4: "正解（少し迷った）",
        5: "正解（簡単）"
    }

    @staticmethod
    def calculate_next_review(
        current_interval: int,
        ease_factor: float,
        repetition_count: int,
        quality_score: int,
        last_review_date: Optional[datetime] = None
    ) -> Tuple[datetime, int, float]:
        """
        次回復習日、新しい間隔、新しい難易度係数を計算
        
        Args:
            current_interval: 現在の復習間隔（日）
            ease_factor: 現在の難易度係数
            repetition_count: 現在の復習回数
            quality_score: 学習品質スコア (0-5)
            last_review_date: 前回復習日（Noneの場合は今日）
            
        Returns:
            Tuple[次回復習日, 新しい間隔, 新しい難易度係数]
        """
        if last_review_date is None:
            last_review_date = datetime.now()
            
        # 難易度係数の更新
        new_ease_factor = SpacedRepetitionCalculator._update_ease_factor(
            ease_factor, quality_score
        )
        
        # 間隔の計算
        if quality_score < 3:
            # 間違えた場合：最初からやり直し
            new_interval = 1
            new_repetition_count = 0
        else:
            # 正解した場合：間隔を延長
            new_repetition_count = repetition_count + 1
            new_interval = SpacedRepetitionCalculator._calculate_interval(
                current_interval, new_repetition_count, new_ease_factor
            )
        
        # 次回復習日の計算
        next_review_date = last_review_date + timedelta(days=new_interval)
        
        return next_review_date, new_interval, new_ease_factor

    @staticmethod
    def _update_ease_factor(ease_factor: float, quality_score: int) -> float:
        """難易度係数を更新"""
        # SM-2アルゴリズムによる難易度係数の更新式
        new_ease_factor = ease_factor + (0.1 - (5 - quality_score) * (0.08 + (5 - quality_score) * 0.02))
        
        # 最小値の制限
        return max(new_ease_factor, SpacedRepetitionCalculator.MIN_EASE_FACTOR)

    @staticmethod
    def _calculate_interval(current_interval: int, repetition_count: int, ease_factor: float) -> int:
        """復習間隔を計算"""
        if repetition_count == 1:
            return 1
        elif repetition_count == 2:
            return 6
        else:
            # 3回目以降は前回間隔 × 難易度係数
            new_interval = current_interval * ease_factor
            return max(1, round(new_interval))

    @staticmethod
    def get_due_problems_query_params(user_id: int) -> dict:
        """復習対象の問題を取得するためのクエリパラメータを生成"""
        today = datetime.now().date()
        
        return {
            'user_id': user_id,
            'next_review_date__lte': today,  # 今日以前が復習日の問題
            'is_active': True  # アクティブな問題のみ
        }

    @staticmethod
    def calculate_retention_rate(
        correct_answers: int, 
        total_answers: int, 
        days_since_learning: int
    ) -> float:
        """記憶定着率を計算（エビングハウスの忘却曲線ベース）"""
        if total_answers == 0:
            return 0.0
            
        # 基本的な正答率
        base_rate = correct_answers / total_answers
        
        # 時間経過による定着率の補正（忘却曲線）
        # R(t) = e^(-t/S) where S is strength
        if days_since_learning > 0:
            strength = 5.0 + (base_rate - 0.5) * 10  # 5-15の範囲で強度を設定
            time_factor = math.exp(-days_since_learning / strength)
            return base_rate * time_factor
        
        return base_rate

    @staticmethod
    def get_optimal_study_time(difficulty_level: str, user_accuracy: float) -> int:
        """最適な学習時間（分）を推奨"""
        base_times = {
            'easy': 3,
            'medium': 5,
            'hard': 8
        }
        
        base_time = base_times.get(difficulty_level, 5)
        
        # 正答率が低い場合は時間を増やす
        if user_accuracy < 0.6:
            multiplier = 1.5
        elif user_accuracy < 0.8:
            multiplier = 1.2
        else:
            multiplier = 1.0
            
        return int(base_time * multiplier)

    @staticmethod
    def get_quality_score_from_performance(
        is_correct: bool,
        time_taken_seconds: int,
        average_time_seconds: int,
        hint_used: bool = False
    ) -> int:
        """回答パフォーマンスからスコアを算出"""
        if not is_correct:
            if hint_used:
                return 2  # ヒント使用で間違い
            else:
                return 1  # ヒントなしで間違い
        
        # 正解の場合、回答時間を考慮
        time_ratio = time_taken_seconds / max(average_time_seconds, 1)
        
        if time_ratio <= 0.7:  # 平均より30%以上早い
            return 5  # 簡単
        elif time_ratio <= 1.2:  # 平均±20%
            return 4  # 少し迷った
        else:  # 平均より20%以上遅い
            return 3  # 困難

    @staticmethod
    def should_introduce_new_problems(
        current_due_count: int,
        user_accuracy: float,
        daily_goal: int = 20
    ) -> bool:
        """新しい問題を導入すべきかを判定"""
        # 復習すべき問題が多すぎる場合は新問題を控える
        if current_due_count > daily_goal * 0.7:
            return False
            
        # 正答率が低い場合は新問題を控える
        if user_accuracy < 0.7:
            return False
            
        return True

    @staticmethod
    def get_recommended_daily_problems(
        current_streak: int,
        user_level: str,
        available_time_minutes: int
    ) -> dict:
        """1日の推奨問題数を算出"""
        base_problems = {
            'beginner': 10,
            'intermediate': 15,
            'advanced': 20
        }
        
        base = base_problems.get(user_level, 15)
        
        # ストリークボーナス（継続学習への報酬）
        streak_bonus = min(current_streak // 7, 5)  # 週間ストリークごとに+1、最大+5
        
        # 利用可能時間による調整
        time_factor = min(available_time_minutes / 30, 2.0)  # 30分基準、最大2倍
        
        recommended = int((base + streak_bonus) * time_factor)
        
        return {
            'total_problems': recommended,
            'new_problems': max(1, recommended // 4),  # 25%を新問題
            'review_problems': recommended - max(1, recommended // 4),
            'estimated_time_minutes': recommended * 2  # 1問あたり2分の想定
        }