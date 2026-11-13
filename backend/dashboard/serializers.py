from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from problems.serializers import OrgSubjectField

from .selectors import (
    GRANULARITY_DAY, GRANULARITY_MONTH, GRANULARITY_WEEK, KIND_UNSTUDIED, KIND_WEAK,
)

ANALYTICS_DEFAULT_DAYS = 30
ANALYTICS_MAX_DAYS = 365


class AnalyticsQuerySerializer(serializers.Serializer):
    """
    学習統計（analytics）のクエリ。days は 1〜365 の整数・省略時は 30。
    科目は省略可（自組織の科目だけ・context に request が要る）
    """

    days = serializers.IntegerField(
        min_value=1, max_value=ANALYTICS_MAX_DAYS, default=ANALYTICS_DEFAULT_DAYS)
    subject_id = OrgSubjectField(required=False)


# ---- 学習統計の応答（analytics・I488）----
# 比率は 0〜1（答えが 0 件なら null）。部品の名前は他の API とぶつからないよう DashboardAnalytics で始める

# 推移の区切り（選択肢の正。SPECTACULAR_SETTINGS の ENUM_NAME_OVERRIDES もこれを指す）
GRANULARITY_CHOICES = (GRANULARITY_DAY, GRANULARITY_WEEK, GRANULARITY_MONTH)


@extend_schema_serializer(component_name='DashboardAnalyticsPeriod')
class AnalyticsPeriodSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    granularity = serializers.ChoiceField(choices=GRANULARITY_CHOICES)


@extend_schema_serializer(component_name='DashboardAnalyticsCounts')
class AnalyticsCountsSerializer(serializers.Serializer):
    study_seconds = serializers.IntegerField()
    answered_count = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    accuracy_rate = serializers.FloatField(allow_null=True)


@extend_schema_serializer(component_name='DashboardAnalyticsTotals')
class AnalyticsTotalsSerializer(AnalyticsCountsSerializer):
    studied_days = serializers.IntegerField()


@extend_schema_serializer(component_name='DashboardAnalyticsBucket')
class AnalyticsBucketSerializer(AnalyticsCountsSerializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


@extend_schema_serializer(component_name='DashboardAnalyticsSubject')
class AnalyticsSubjectSerializer(AnalyticsCountsSerializer):
    subject_id = serializers.IntegerField()
    subject_name = serializers.CharField()


@extend_schema_serializer(component_name='DashboardAnalytics')
class AnalyticsSerializer(serializers.Serializer):
    """GET /api/dashboard/analytics/ の応答（キーは全部必須）"""
    has_data = serializers.BooleanField()
    period = AnalyticsPeriodSerializer()
    totals = AnalyticsTotalsSerializer()
    trend = AnalyticsBucketSerializer(many=True)
    subject_breakdown = AnalyticsSubjectSerializer(many=True)


# ---- ダッシュボードの概要（overview・I473）----
# 比率は 0〜1（答えが 0 件なら null）。この形から backend/openapi.yaml と画面の型
# （frontend/src/types/api/schema.d.ts）を作る（I493）。部品の名前は他の API とぶつからないよう Dashboard で始める

# おすすめの種類（選択肢の正。SPECTACULAR_SETTINGS の ENUM_NAME_OVERRIDES もこれを指す）
RECOMMENDATION_KIND_CHOICES = (KIND_WEAK, KIND_UNSTUDIED)


class OverviewQuerySerializer(serializers.Serializer):
    """概要の入力（科目は省略可。自組織の科目だけ・context に request が要る）"""
    subject_id = OrgSubjectField(required=False)


@extend_schema_serializer(component_name='DashboardTotals')
class TotalsSerializer(serializers.Serializer):
    answered_count = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    accuracy_rate = serializers.FloatField(allow_null=True)


# 継承すると親の部品の名前も引き継ぐので、個別に付ける
@extend_schema_serializer(component_name='DashboardToday')
class TodaySerializer(TotalsSerializer):
    study_seconds = serializers.IntegerField()


@extend_schema_serializer(component_name='DashboardStreak')
class StreakSerializer(serializers.Serializer):
    current_days = serializers.IntegerField()


@extend_schema_serializer(component_name='DashboardDay')
class DaySerializer(serializers.Serializer):
    date = serializers.DateField()
    study_seconds = serializers.IntegerField()
    answered_count = serializers.IntegerField()
    correct_count = serializers.IntegerField()


@extend_schema_serializer(component_name='DashboardWeakSubject')
class WeakSubjectSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    subject_name = serializers.CharField()
    answered_count = serializers.IntegerField()
    accuracy_rate = serializers.FloatField()


@extend_schema_serializer(component_name='DashboardRecommendation')
class RecommendationSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=RECOMMENDATION_KIND_CHOICES)
    subject_id = serializers.IntegerField()
    subject_name = serializers.CharField()
    reason = serializers.CharField()


@extend_schema_serializer(component_name='DashboardOverview')
class OverviewSerializer(serializers.Serializer):
    """GET /api/dashboard/overview/ の応答（キーは全部必須）"""
    has_data = serializers.BooleanField()
    today = TodaySerializer()
    streak = StreakSerializer()
    totals = TotalsSerializer()
    last_7_days = DaySerializer(many=True)
    weak_subjects = WeakSubjectSerializer(many=True)
    recommendations = RecommendationSerializer(many=True)
