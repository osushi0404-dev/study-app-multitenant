from rest_framework import serializers

from problems.serializers import OrgSubjectField

from .selectors import KIND_UNSTUDIED, KIND_WEAK

ANALYTICS_DEFAULT_DAYS = 30
ANALYTICS_MAX_DAYS = 365


class AnalyticsQuerySerializer(serializers.Serializer):
    """学習統計（analytics）のクエリ。days は 1〜365 の整数・省略時は 30"""

    days = serializers.IntegerField(
        min_value=1, max_value=ANALYTICS_MAX_DAYS, default=ANALYTICS_DEFAULT_DAYS)


# ---- ダッシュボードの概要（overview・I473）----
# 比率は 0〜1（答えが 0 件なら null）。画面の型（frontend/src/services/types.ts の DashboardOverview）と同じ形


class OverviewQuerySerializer(serializers.Serializer):
    """概要の入力（科目は省略可。自組織の科目だけ・context に request が要る）"""
    subject_id = OrgSubjectField(required=False)


class TotalsSerializer(serializers.Serializer):
    answered_count = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    accuracy_rate = serializers.FloatField(allow_null=True)


class TodaySerializer(TotalsSerializer):
    study_seconds = serializers.IntegerField()


class StreakSerializer(serializers.Serializer):
    current_days = serializers.IntegerField()


class DaySerializer(serializers.Serializer):
    date = serializers.DateField()
    study_seconds = serializers.IntegerField()
    answered_count = serializers.IntegerField()
    correct_count = serializers.IntegerField()


class WeakSubjectSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    subject_name = serializers.CharField()
    answered_count = serializers.IntegerField()
    accuracy_rate = serializers.FloatField()


class RecommendationSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[KIND_WEAK, KIND_UNSTUDIED])
    subject_id = serializers.IntegerField()
    subject_name = serializers.CharField()
    reason = serializers.CharField()


class OverviewSerializer(serializers.Serializer):
    """GET /api/dashboard/overview/ の応答（キーは全部必須）"""
    has_data = serializers.BooleanField()
    today = TodaySerializer()
    streak = StreakSerializer()
    totals = TotalsSerializer()
    last_7_days = DaySerializer(many=True)
    weak_subjects = WeakSubjectSerializer(many=True)
    recommendations = RecommendationSerializer(many=True)
