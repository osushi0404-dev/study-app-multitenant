from datetime import timedelta

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import permissions, status, views
from rest_framework.response import Response

from core.exceptions import create_error_response
from core.subject_service import subject_service
from studylogs.models import DailyStudySummary, StudyLog

from .selectors import build_overview
from .serializers import (
    ANALYTICS_MAX_DAYS, AnalyticsQuerySerializer, OverviewQuerySerializer, OverviewSerializer,
)


def _accuracy_percent(correct, attempted):
    """正解数 ÷ 解いた問題数 × 100（小数第 2 位）。解いた問題数が 0・空なら 0"""
    return round(correct * 100 / attempted, 2) if attempted else 0


class DashboardOverviewView(views.APIView):
    """ダッシュボードの数字（クイズの答えの記録から数える・I473）"""
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        query = AnalyticsQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return create_error_response(
                '期間の指定が正しくありません',
                f'日数は 1〜{ANALYTICS_MAX_DAYS} の整数で指定してください',
                status.HTTP_400_BAD_REQUEST,
            )
        days = query.validated_data['days']

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Get daily study data
        daily_data = []
        current_date = start_date

        while current_date <= end_date:
            summary = DailyStudySummary.objects.filter(
                user=user,
                date=current_date
            ).first()

            daily_data.append({
                'date': current_date.isoformat(),
                'study_time': summary.total_study_time if summary else 0,
                'problems_attempted': summary.total_problems_attempted if summary else 0,
                'problems_correct': summary.total_problems_correct if summary else 0,
                'accuracy': summary.accuracy if summary else 0
            })

            current_date += timedelta(days=1)

        # Get subject distribution
        subject_stats = StudyLog.objects.for_user(user).filter(
            started_at__date__gte=start_date,
        ).values('subject__name').annotate(
            total_time=Sum('duration'),
            total_problems=Sum('problems_attempted')
        ).order_by('-total_time')

        # Get performance trends
        performance_data = self._get_performance_trends(user, start_date, end_date)

        # Get subject breakdown for dropdown
        subject_breakdown = subject_service.get_subjects_for_dropdown(user)

        return Response({
            'daily_data': daily_data,
            'subject_distribution': list(subject_stats),
            'performance_trends': performance_data,
            'subject_breakdown': subject_breakdown
        })

    def _get_performance_trends(self, user, start_date, end_date):
        # Get weekly averages for the period
        weeks = []
        current_week_start = start_date

        while current_week_start <= end_date:
            week_end = min(current_week_start + timedelta(days=6), end_date)

            week_summary = DailyStudySummary.objects.filter(
                user=user,
                date__range=[current_week_start, week_end]
            ).aggregate(
                avg_time=Avg('total_study_time'),
                avg_problems=Avg('total_problems_attempted'),
                total_attempted=Sum('total_problems_attempted'),
                total_correct=Sum('total_problems_correct'),
            )

            weeks.append({
                'week_start': current_week_start.isoformat(),
                'avg_study_time': week_summary['avg_time'] or 0,
                'avg_problems': week_summary['avg_problems'] or 0,
                'avg_accuracy': _accuracy_percent(
                    week_summary['total_correct'], week_summary['total_attempted']),
            })

            current_week_start += timedelta(days=7)

        return weeks
