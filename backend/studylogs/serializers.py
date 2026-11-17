from rest_framework import serializers
from .models import (
    StudyLog, DailyStudySummary, StudyGoal,
    SpacedRepetitionCard, SpacedRepetitionReview, LearningAnalytics,
)
from problems.serializers import OrgSubjectField, ProblemSerializer


class StudyLogSerializer(serializers.ModelSerializer):
    subject = OrgSubjectField(required=False, allow_null=True)
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
    subject = OrgSubjectField(required=False, allow_null=True)

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


class ReviewSummaryQuerySerializer(serializers.Serializer):
    """今日の復習の件数の入力（科目は省略可。自組織で選べる科目だけ・context に request が要る）"""
    subject_id = OrgSubjectField(required=False)


class ReviewSummarySerializer(serializers.Serializer):
    """今日の復習の件数と、次の復習日（無ければ null）"""
    due_count = serializers.IntegerField()
    next_review_date = serializers.DateField(allow_null=True)


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
