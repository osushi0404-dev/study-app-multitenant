from django.db import models
from django.contrib.auth import get_user_model
from problems.models import Subject, Problem

User = get_user_model()


class StudyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_logs')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    problems_attempted = models.IntegerField(default=0)
    problems_correct = models.IntegerField(default=0)
    points_earned = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"

    def calculate_duration(self):
        if self.ended_at and self.started_at:
            delta = self.ended_at - self.started_at
            self.duration = int(delta.total_seconds())
            self.save()

    @property
    def accuracy(self):
        if self.problems_attempted > 0:
            return round((self.problems_correct / self.problems_attempted) * 100, 2)
        return 0


class DailyStudySummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_summaries')
    date = models.DateField()
    total_study_time = models.IntegerField(default=0, help_text="Total study time in seconds")
    total_problems_attempted = models.IntegerField(default=0)
    total_problems_correct = models.IntegerField(default=0)
    total_points_earned = models.IntegerField(default=0)
    subjects_studied = models.ManyToManyField(Subject)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    @property
    def accuracy(self):
        if self.total_problems_attempted > 0:
            return round((self.total_problems_correct / self.total_problems_attempted) * 100, 2)
        return 0


class ProblemAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_attempts')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='attempts')
    study_log = models.ForeignKey(StudyLog, on_delete=models.CASCADE, null=True, blank=True, related_name='attempts')
    attempted_at = models.DateTimeField(auto_now_add=True)
    is_correct = models.BooleanField(default=False)
    time_taken = models.IntegerField(default=0, help_text="Time taken in seconds")
    attempt_number = models.IntegerField(default=1)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"{self.user.username} - {self.problem.question[:30]}... - Attempt {self.attempt_number}"


class StudyGoal(models.Model):
    GOAL_TYPE_CHOICES = [
        ('daily_time', '毎日の学習時間'),
        ('daily_problems', '毎日の問題数'),
        ('weekly_time', '週間学習時間'),
        ('weekly_problems', '週間問題数'),
        ('accuracy', '正答率'),
        ('streak', '連続学習日数'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_goals')
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES)
    target_value = models.IntegerField()
    current_value = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'goal_type']
        ordering = ['goal_type']

    def __str__(self):
        return f"{self.user.username} - {self.get_goal_type_display()}: {self.target_value}"

    @property
    def progress_percentage(self):
        if self.target_value > 0:
            return min(round((self.current_value / self.target_value) * 100, 2), 100)
        return 0


class SpacedRepetitionCard(models.Model):
    """間隔反復学習用のカードモデル"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sr_cards')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='sr_cards')
    
    # 間隔反復学習のパラメータ
    ease_factor = models.FloatField(default=2.5, help_text="難易度係数 (1.3以上)")
    interval_days = models.IntegerField(default=1, help_text="復習間隔（日）")
    repetition_count = models.IntegerField(default=0, help_text="復習回数")
    
    # 日程管理
    next_review_date = models.DateTimeField(help_text="次回復習予定日")
    last_reviewed_at = models.DateTimeField(null=True, blank=True, help_text="前回復習日")
    
    # 学習状況
    is_active = models.BooleanField(default=True)
    total_reviews = models.IntegerField(default=0, help_text="総復習回数")
    correct_reviews = models.IntegerField(default=0, help_text="正解した復習回数")
    
    # メタデータ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'problem']
        ordering = ['next_review_date', '-ease_factor']
        indexes = [
            models.Index(fields=['user', 'next_review_date', 'is_active']),
            models.Index(fields=['next_review_date', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.problem.question[:30]}... (次回: {self.next_review_date.strftime('%Y-%m-%d')})"
    
    @property
    def accuracy_rate(self):
        """この問題の正答率"""
        if self.total_reviews > 0:
            return round((self.correct_reviews / self.total_reviews) * 100, 2)
        return 0
    
    @property
    def is_due(self):
        """復習が必要かどうか"""
        from django.utils import timezone
        return self.next_review_date <= timezone.now() and self.is_active
    
    @property
    def mastery_level(self):
        """習熟度レベル"""
        if self.repetition_count >= 5 and self.accuracy_rate >= 90:
            return 'mastered'
        elif self.repetition_count >= 3 and self.accuracy_rate >= 80:
            return 'familiar'
        elif self.repetition_count >= 1:
            return 'learning'
        else:
            return 'new'


class SpacedRepetitionReview(models.Model):
    """間隔反復学習の復習記録"""
    QUALITY_CHOICES = [
        (0, '完全に忘れた'),
        (1, '間違えた（ヒントありでも困難）'),
        (2, '間違えた（ヒントありで思い出せた）'),
        (3, '正解（困難）'),
        (4, '正解（少し迷った）'),
        (5, '正解（簡単）'),
    ]
    
    card = models.ForeignKey(SpacedRepetitionCard, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sr_reviews')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='sr_reviews')
    
    # 復習結果
    quality_score = models.IntegerField(choices=QUALITY_CHOICES, help_text="学習品質スコア")
    response_time_seconds = models.IntegerField(help_text="回答時間（秒）")
    is_correct = models.BooleanField()
    hint_used = models.BooleanField(default=False)
    
    # スケジューリング情報（復習前）
    previous_ease_factor = models.FloatField()
    previous_interval = models.IntegerField()
    previous_repetition_count = models.IntegerField()
    
    # スケジューリング情報（復習後）
    new_ease_factor = models.FloatField()
    new_interval = models.IntegerField()
    new_repetition_count = models.IntegerField()
    next_review_date = models.DateTimeField()
    
    # メタデータ
    reviewed_at = models.DateTimeField(auto_now_add=True)
    study_session = models.ForeignKey(StudyLog, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-reviewed_at']
        indexes = [
            models.Index(fields=['card', '-reviewed_at']),
            models.Index(fields=['user', '-reviewed_at']),
            models.Index(fields=['reviewed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.problem.question[:30]}... - スコア: {self.quality_score}"


class LearningAnalytics(models.Model):
    """学習分析データ"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_analytics')
    date = models.DateField()
    
    # 基本統計
    total_cards = models.IntegerField(default=0)
    new_cards = models.IntegerField(default=0)
    due_cards = models.IntegerField(default=0)
    reviewed_cards = models.IntegerField(default=0)
    
    # パフォーマンス
    average_ease_factor = models.FloatField(default=0.0)
    average_interval = models.FloatField(default=0.0)
    retention_rate = models.FloatField(default=0.0, help_text="記憶定着率")
    
    # 時間統計
    total_review_time = models.IntegerField(default=0, help_text="総復習時間（秒）")
    average_response_time = models.FloatField(default=0.0, help_text="平均回答時間（秒）")
    
    # 難易度別統計
    easy_cards_count = models.IntegerField(default=0)
    medium_cards_count = models.IntegerField(default=0)
    hard_cards_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date} - 定着率: {self.retention_rate:.1%}"


class MistakePattern(models.Model):
    """間違いパターンの分析モデル"""
    PATTERN_TYPES = [
        ('subject_difficulty', '科目別の苦手分野'),
        ('problem_type', '問題タイプ別の間違い'),
        ('time_pressure', '時間制限による間違い'),
        ('concept_confusion', '概念の混同'),
        ('calculation_error', '計算ミス'),
        ('reading_comprehension', '読解力不足'),
        ('knowledge_gap', '知識不足'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mistake_patterns')
    pattern_type = models.CharField(max_length=30, choices=PATTERN_TYPES)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    problem_difficulty = models.CharField(max_length=10, choices=[('easy', '易'), ('medium', '中'), ('hard', '難')], null=True, blank=True)
    
    # 統計データ
    occurrence_count = models.IntegerField(default=1, help_text="このパターンが発生した回数")
    total_attempts = models.IntegerField(default=1, help_text="関連問題の総試行回数")
    last_occurrence = models.DateTimeField(auto_now=True)
    
    # パターンの詳細
    description = models.TextField(help_text="間違いパターンの詳細説明")
    confidence_score = models.FloatField(default=0.0, help_text="パターン認識の信頼度 (0.0-1.0)")
    
    # 改善状況
    improvement_rate = models.FloatField(default=0.0, help_text="改善率 (0.0-1.0)")
    is_active = models.BooleanField(default=True, help_text="このパターンがまだ問題となっているか")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'pattern_type', 'subject', 'problem_difficulty']
        ordering = ['-occurrence_count', '-last_occurrence']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_pattern_type_display()} ({self.occurrence_count}回)"
    
    @property
    def error_rate(self):
        """エラー率を計算"""
        if self.total_attempts > 0:
            return round((self.occurrence_count / self.total_attempts) * 100, 2)
        return 0
    
    @property
    def severity_level(self):
        """深刻度レベルを判定"""
        error_rate = self.error_rate
        if error_rate >= 70:
            return 'critical'
        elif error_rate >= 50:
            return 'high'
        elif error_rate >= 30:
            return 'medium'
        else:
            return 'low'


class LearningSuggestion(models.Model):
    """学習提案モデル"""
    SUGGESTION_TYPES = [
        ('study_method', '学習方法の改善'),
        ('practice_focus', '重点練習領域'),
        ('time_management', '時間管理'),
        ('concept_review', '概念の復習'),
        ('foundation_building', '基礎固め'),
        ('advanced_practice', '応用練習'),
        ('exam_strategy', '試験戦略'),
    ]
    
    PRIORITY_LEVELS = [
        ('urgent', '緊急'),
        ('high', '高'),
        ('medium', '中'),
        ('low', '低'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_suggestions')
    mistake_pattern = models.ForeignKey(MistakePattern, on_delete=models.CASCADE, null=True, blank=True, related_name='suggestions')
    
    suggestion_type = models.CharField(max_length=20, choices=SUGGESTION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # 提案内容
    title = models.CharField(max_length=200, help_text="提案のタイトル")
    description = models.TextField(help_text="詳細な提案内容")
    action_steps = models.JSONField(default=list, help_text="具体的なアクションステップ")
    
    # 関連データ
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    estimated_time_minutes = models.IntegerField(null=True, blank=True, help_text="推定必要時間（分）")
    difficulty_level = models.CharField(max_length=20, choices=[('beginner', '初級'), ('intermediate', '中級'), ('advanced', '上級')], default='intermediate')
    
    # 追跡データ
    is_read = models.BooleanField(default=False)
    is_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    effectiveness_rating = models.IntegerField(null=True, blank=True, help_text="効果評価 (1-5)")
    
    # メタデータ
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="提案の有効期限")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active', 'priority']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.get_priority_display()})"
    
    @property
    def is_expired(self):
        """提案が期限切れかどうか"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False
    
    def mark_as_applied(self):
        """提案を適用済みとしてマーク"""
        from django.utils import timezone
        self.is_applied = True
        self.applied_at = timezone.now()
        self.save()


class LearningWeakness(models.Model):
    """学習の弱点分析モデル"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_weaknesses')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    
    # 弱点データ
    concept_name = models.CharField(max_length=200, help_text="弱点のある概念名")
    problem_count = models.IntegerField(default=0, help_text="関連問題数")
    error_count = models.IntegerField(default=0, help_text="間違い数")
    last_error_date = models.DateTimeField(null=True, blank=True)
    
    # 改善追跡
    improvement_score = models.FloatField(default=0.0, help_text="改善スコア (0.0-1.0)")
    practice_recommendations = models.JSONField(default=list, help_text="練習推奨事項")
    
    # ステータス
    severity = models.CharField(
        max_length=10, 
        choices=[('low', '軽微'), ('medium', '中程度'), ('high', '深刻'), ('critical', '重要')],
        default='medium'
    )
    is_resolved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'subject', 'concept_name']
        ordering = ['-severity', '-error_count', '-last_error_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.subject.name}: {self.concept_name} ({self.get_severity_display()})"
    
    @property
    def error_rate(self):
        """エラー率を計算"""
        if self.problem_count > 0:
            return round((self.error_count / self.problem_count) * 100, 2)
        return 0
    
    def update_severity(self):
        """深刻度を自動更新"""
        error_rate = self.error_rate
        if error_rate >= 80:
            self.severity = 'critical'
        elif error_rate >= 60:
            self.severity = 'high'
        elif error_rate >= 40:
            self.severity = 'medium'
        else:
            self.severity = 'low'
        self.save()