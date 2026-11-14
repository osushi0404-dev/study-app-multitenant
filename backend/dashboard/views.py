from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, views
from rest_framework.response import Response

from core.exceptions import create_error_response

from .selectors import build_analytics, build_overview
from .serializers import (
    ANALYTICS_MAX_DAYS, AnalyticsQuerySerializer, AnalyticsSerializer, OverviewQuerySerializer,
    OverviewSerializer,
)


class DashboardOverviewView(views.APIView):
    """ダッシュボードの数字（クイズの答えの記録から数える・I473）"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(parameters=[OverviewQuerySerializer], responses={200: OverviewSerializer})
    def get(self, request):
        query = OverviewQuerySerializer(data=request.query_params, context={'request': request})
        if not query.is_valid():
            # 数字でない・他組織・全体共有・存在しない科目は同じ 400（違いを見せない）
            return create_error_response(
                '科目の指定が正しくありません',
                'ダッシュボードの科目の選択からやり直してください',
                status.HTTP_400_BAD_REQUEST,
            )

        overview = build_overview(request.user, query.validated_data.get('subject_id'))
        return Response(OverviewSerializer(overview).data)


class DashboardAnalyticsView(views.APIView):
    """学習統計（期間の推移・科目別の内訳。クイズの答えの記録から数える・I488）"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(parameters=[AnalyticsQuerySerializer], responses={200: AnalyticsSerializer})
    def get(self, request):
        query = AnalyticsQuerySerializer(data=request.query_params, context={'request': request})
        if not query.is_valid():
            if 'days' in query.errors:
                return create_error_response(
                    '期間の指定が正しくありません',
                    f'日数は 1〜{ANALYTICS_MAX_DAYS} の整数で指定してください',
                    status.HTTP_400_BAD_REQUEST,
                )
            # 数字でない・他組織・全体共有・存在しない科目は同じ 400（違いを見せない）
            return create_error_response(
                '科目の指定が正しくありません',
                '学習統計の科目の選択からやり直してください',
                status.HTTP_400_BAD_REQUEST,
            )

        analytics = build_analytics(
            request.user, query.validated_data['days'], query.validated_data.get('subject_id'))
        return Response(AnalyticsSerializer(analytics).data)
