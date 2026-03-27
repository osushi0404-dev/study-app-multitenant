from rest_framework import serializers
from .models import (
    StudyLog, DailyStudySummary, ProblemAttempt, StudyGoal,
    SpacedRepetitionCard, SpacedRepetitionReview, LearningAnalytics,
    MistakePattern, LearningSuggestion, LearningWeakness
)
from problems.serializers import ProblemSerializer


class StudyLogSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    accuracy = serializers.ReadOnlyField()

    class Meta:
        model = StudyLog
        fields = [
            'id', 'subject', 'subject_name', 'started_at', 'ended_at',
            'duration', 'problems_attempted', 'problems_correct',
            'points_earned', 'notes', 'is_active', 'accuracy'
        ]
        read_only_fields = [
            'started_at', 'ended_at', 'duration', 'problems_attempted',
            'problems_correct', 'points_earned'
        ]


class StudyLogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyLog
        fields = ['subject']


class StudyLogEndSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


class DailyStudySummarySerializer(serializers.ModelSerializer):
    subjects_studied = serializers.StringRelatedField(many=True, read_only=True)
    accuracy = serializers.ReadOnlyField()
    study_time_hours = serializers.SerializerMethodField()

    class Meta:
        model = DailyStudySummary
        fields = [
            'id', 'date', 'total_study_time', 'study_time_hours',
            'total_problems_attempted', 'total_problems_correct',
            'total_points_earned', 'subjects_studied', 'accuracy'
        ]

    def get_study_time_hours(self, obj):
        hours = obj.total_study_time // 3600
        minutes = (obj.total_study_time % 3600) // 60
        return f"{hours}時間{minutes}分"


class ProblemAttemptSerializer(serializers.ModelSerializer):
    problem_question = serializers.CharField(source='problem.question', read_only=True)
    subject_name = serializers.CharField(source='problem.subject.name', read_only=True)

    class Meta:
        model = ProblemAttempt
        fields = [
            'id', 'problem', 'problem_question', 'subject_name',
            'attempted_at', 'is_correct', 'time_taken', 'attempt_number'
        ]


class StudyGoalSerializer(serializers.ModelSerializer):
    goal_type_display = serializers.CharField(source='get_goal_type_display', read_only=True)
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = StudyGoal
        fields = [
            'id', 'goal_type', 'goal_type_display', 'target_value',
            'current_value', 'progress_percentage', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['current_value']


class StudyStatisticsSerializer(serializers.Serializer):
    total_study_time = serializers.IntegerField()
    total_study_time_display = serializers.CharField()
    total_problems_attempted = serializers.IntegerField()
    total_problems_correct = serializers.IntegerField()
    overall_accuracy = serializers.FloatField()
    total_points = serializers.IntegerField()
    study_days = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    average_daily_time = serializers.IntegerField()
    average_daily_time_display = serializers.CharField()
    best_subject = serializers.DictField()
    weakest_subject = serializers.DictField()
    recent_activity = serializers.ListField()


class SubjectStatisticsSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    subject_name = serializers.CharField()
    total_time = serializers.IntegerField()
    total_time_display = serializers.CharField()
    problems_attempted = serializers.IntegerField()
    problems_correct = serializers.IntegerField()
    accuracy = serializers.FloatField()
    points_earned = serializers.IntegerField()
    last_studied = serializers.DateTimeField()


class SpacedRepetitionCardSerializer(serializers.ModelSerializer):
    problem = ProblemSerializer(read_only=True)
    accuracy_rate = serializers.ReadOnlyField()
    is_due = serializers.ReadOnlyField()
    mastery_level = serializers.ReadOnlyField()

    class Meta:
        model = SpacedRepetitionCard
        fields = [
            'id', 'problem', 'ease_factor', 'interval_days', 'repetition_count',
            'next_review_date', 'last_reviewed_at', 'total_reviews', 'correct_reviews',
            'accuracy_rate', 'is_due', 'mastery_level', 'created_at'
        ]
        read_only_fields = [
            'ease_factor', 'interval_days', 'repetition_count', 'next_review_date',
            'last_reviewed_at', 'total_reviews', 'correct_reviews'
        ]


class SpacedRepetitionReviewSerializer(serializers.ModelSerializer):
    quality_score_display = serializers.CharField(source='get_quality_score_display', read_only=True)
    problem_question = serializers.CharField(source='problem.question', read_only=True)

    class Meta:
        model = SpacedRepetitionReview
        fields = [
            'id', 'quality_score', 'quality_score_display', 'response_time_seconds',
            'is_correct', 'hint_used', 'problem_question', 'reviewed_at',
            'new_ease_factor', 'new_interval', 'next_review_date'
        ]


class SpacedRepetitionSubmissionSerializer(serializers.Serializer):
    """間隔反復学習の復習提出用シリアライザー"""
    card_id = serializers.IntegerField()
    quality_score = serializers.IntegerField(min_value=0, max_value=5)
    response_time_seconds = serializers.IntegerField(min_value=1)
    hint_used = serializers.BooleanField(default=False)

    def validate_quality_score(self, value):
        if value not in range(6):  # 0-5
            raise serializers.ValidationError("Quality score must be between 0 and 5")
        return value


class LearningAnalyticsSerializer(serializers.ModelSerializer):
    retention_rate_percentage = serializers.SerializerMethodField()

    class Meta:
        model = LearningAnalytics
        fields = [
            'date', 'total_cards', 'new_cards', 'due_cards', 'reviewed_cards',
            'average_ease_factor', 'average_interval', 'retention_rate',
            'retention_rate_percentage', 'total_review_time', 'average_response_time',
            'easy_cards_count', 'medium_cards_count', 'hard_cards_count'
        ]

    def get_retention_rate_percentage(self, obj):
        return round(obj.retention_rate * 100, 1)


class DailyStudyPlanSerializer(serializers.Serializer):
    """1日の学習プラン用シリアライザー"""
    due_cards = SpacedRepetitionCardSerializer(many=True, read_only=True)
    new_cards = SpacedRepetitionCardSerializer(many=True, read_only=True)
    total_cards = serializers.IntegerField()
    estimated_time_minutes = serializers.IntegerField()
    user_level = serializers.CharField()
    current_streak = serializers.IntegerField()
    recommendations = serializers.DictField()


class LearningInsightsSerializer(serializers.Serializer):
    """学習洞察用シリアライザー"""
    insights = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())
    period_days = serializers.IntegerField()
    analytics_data = serializers.ListField()


class UserStatisticsSerializer(serializers.Serializer):
    """ユーザー統計用シリアライザー"""
    total_cards = serializers.IntegerField()
    overall_accuracy = serializers.FloatField()
    average_ease_factor = serializers.FloatField()
    mastery_distribution = serializers.DictField()
    total_reviews = serializers.IntegerField()
    recent_reviews_count = serializers.IntegerField()


class MistakePatternSerializer(serializers.ModelSerializer):
    """間違いパターン用シリアライザー"""
    pattern_type_display = serializers.CharField(source='get_pattern_type_display', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    error_rate = serializers.ReadOnlyField()
    severity_level = serializers.ReadOnlyField()

    class Meta:
        model = MistakePattern
        fields = [
            'id', 'pattern_type', 'pattern_type_display', 'subject', 'subject_name',
            'problem_difficulty', 'occurrence_count', 'total_attempts', 'error_rate',
            'last_occurrence', 'description', 'confidence_score', 'improvement_rate',
            'severity_level', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['occurrence_count', 'total_attempts', 'last_occurrence']


class LearningSuggestionSerializer(serializers.ModelSerializer):
    """学習提案用シリアライザー"""
    suggestion_type_display = serializers.CharField(source='get_suggestion_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    difficulty_level_display = serializers.CharField(source='get_difficulty_level_display', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    mistake_pattern_description = serializers.CharField(source='mistake_pattern.description', read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = LearningSuggestion
        fields = [
            'id', 'suggestion_type', 'suggestion_type_display', 'priority', 'priority_display',
            'title', 'description', 'action_steps', 'subject', 'subject_name',
            'estimated_time_minutes', 'difficulty_level', 'difficulty_level_display',
            'mistake_pattern', 'mistake_pattern_description', 'is_read', 'is_applied',
            'applied_at', 'effectiveness_rating', 'is_active', 'expires_at', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['applied_at']


class LearningWeaknessSerializer(serializers.ModelSerializer):
    """学習弱点用シリアライザー"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    error_rate = serializers.ReadOnlyField()

    class Meta:
        model = LearningWeakness
        fields = [
            'id', 'subject', 'subject_name', 'concept_name', 'problem_count',
            'error_count', 'error_rate', 'last_error_date', 'improvement_score',
            'practice_recommendations', 'severity', 'severity_display', 'is_resolved',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['problem_count', 'error_count', 'last_error_date']


class MistakeAnalysisSerializer(serializers.Serializer):
    """間違い分析結果用シリアライザー"""
    patterns = MistakePatternSerializer(many=True, read_only=True)
    weaknesses = LearningWeaknessSerializer(many=True, read_only=True)
    suggestions = LearningSuggestionSerializer(many=True, read_only=True)
    summary = serializers.DictField(read_only=True)
    improvement_trends = serializers.ListField(read_only=True)


class SuggestionFeedbackSerializer(serializers.Serializer):
    """学習提案フィードバック用シリアライザー"""
    suggestion_id = serializers.IntegerField()
    effectiveness_rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback_comment = serializers.CharField(required=False, allow_blank=True)

    def validate_effectiveness_rating(self, value):
        if value not in range(1, 6):
            raise serializers.ValidationError("効果評価は1-5の範囲で入力してください")
        return value


class ProficiencyAnalysisSerializer(serializers.Serializer):
    """習熟度分析結果用シリアライザー"""
    difficulty_proficiency = serializers.DictField(read_only=True)
    subject_proficiency = serializers.DictField(read_only=True)
    learning_patterns = serializers.DictField(read_only=True)
    growth_rate = serializers.FloatField(read_only=True)
    total_attempts = serializers.IntegerField(read_only=True)
    overall_accuracy = serializers.FloatField(read_only=True)
    confidence_level = serializers.FloatField(read_only=True)


class PersonalizedRecommendationSerializer(serializers.Serializer):
    """個人化推奨用シリアライザー"""
    suggested_focus_areas = serializers.ListField(read_only=True)
    difficulty_recommendation = serializers.CharField(read_only=True)
    learning_goal_suggestion = serializers.CharField(read_only=True)
    estimated_study_time = serializers.IntegerField(read_only=True)
    confidence_level = serializers.FloatField(read_only=True)


class AdaptiveProblemSelectionSerializer(serializers.Serializer):
    """適応的問題選択パラメータ用シリアライザー"""
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    count = serializers.IntegerField(default=10, min_value=1, max_value=50)
    difficulty_preference = serializers.ChoiceField(
        choices=['easy', 'medium', 'hard', 'adaptive'],
        default='adaptive'
    )
    learning_goal = serializers.ChoiceField(
        choices=['review', 'learning', 'challenge', 'balanced'],
        default='balanced'
    )


class SelectedProblemsSerializer(serializers.Serializer):
    """選択された問題用シリアライザー"""
    problems = serializers.ListField(read_only=True)
    selection_criteria = serializers.DictField(read_only=True)
    proficiency_summary = serializers.DictField(read_only=True)
    recommendation = serializers.DictField(read_only=True)
