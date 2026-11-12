from rest_framework import serializers

ANALYTICS_DEFAULT_DAYS = 30
ANALYTICS_MAX_DAYS = 365


class AnalyticsQuerySerializer(serializers.Serializer):
    """学習統計（analytics）のクエリ。days は 1〜365 の整数・省略時は 30"""

    days = serializers.IntegerField(
        min_value=1, max_value=ANALYTICS_MAX_DAYS, default=ANALYTICS_DEFAULT_DAYS)
