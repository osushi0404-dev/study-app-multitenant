from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    StudyLog, DailyStudySummary, StudyGoal,
    SpacedRepetitionCard, SpacedRepetitionReview, LearningAnalytics,
)
from .serializers import (
    StudyLogSerializer, StudyLogCreateSerializer, StudyLogEndSerializer,
    DailyStudySummarySerializer,
    StudyGoalSerializer, StudyStatisticsSerializer, SubjectStatisticsSerializer,
    SpacedRepetitionCardSerializer, SpacedRepetitionReviewSerializer,
    SpacedRepetitionSubmissionSerializer, LearningAnalyticsSerializer,
    DailyStudyPlanSerializer, LearningInsightsSerializer, UserStatisticsSerializer,
    ReviewSummaryQuerySerializer, ReviewSummarySerializer,
)
from core.exceptions import create_error_response
from .services import SpacedRepetitionService
from core.subject_service import subject_service
from problems.services.tenant_scope import available_problems, available_subjects


class StudyLogViewSet(viewsets.ModelViewSet):
    serializer_class = StudyLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 他組織の科目の記録は存在しないものとして扱う（科目が空の記録は残す）
        return StudyLog.objects.for_user(self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return StudyLogCreateSerializer
        return StudyLogSerializer

    def create(self, request):
        # 進行中の記録を閉じる（自組織の科目・科目なしの記録だけ。他組織の科目の記録は触らない・I473）
        StudyLog.objects.for_user(request.user).filter(
            is_active=True
        ).update(is_active=False, ended_at=timezone.now())

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        study_log = serializer.save(user=request.user)

        return Response(
            StudyLogSerializer(study_log).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        study_log = self.get_object()

        if not study_log.is_active:
            return Response(
                {'error': 'Study log is already ended'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = StudyLogEndSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        study_log.is_active = False
        study_log.ended_at = timezone.now()
        study_log.notes = serializer.validated_data.get('notes', '')
        study_log.calculate_duration()
        study_log.save()

        # Update daily summary
        self._update_daily_summary(study_log)

        return Response(StudyLogSerializer(study_log).data)

    def _update_daily_summary(self, study_log):
        date = study_log.started_at.date()

        summary, created = DailyStudySummary.objects.get_or_create(
            user=study_log.user,
            date=date
        )

        summary.total_study_time += study_log.duration
        summary.total_problems_attempted += study_log.problems_attempted
        summary.total_problems_correct += study_log.problems_correct
        summary.total_points_earned += study_log.points_earned

        if study_log.subject:
            summary.subjects_studied.add(study_log.subject)

        summary.save()


class StudyStatisticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        user = request.user
        now = timezone.now()

        # Get all study logs
        # 組織で絞らない: 件数・時間・正答率だけの集計（中身を返さない・I431 扱いの基準 3）
        study_logs = StudyLog.objects.filter(user=user)

        # Calculate total statistics
        totals = study_logs.aggregate(
            total_time=Sum('duration'),
            total_problems=Sum('problems_attempted'),
            total_correct=Sum('problems_correct'),
            total_points=Sum('points_earned')
        )

        total_time = totals['total_time'] or 0
        total_problems = totals['total_problems'] or 0
        total_correct = totals['total_correct'] or 0
        total_points = totals['total_points'] or 0

        # Calculate accuracy
        overall_accuracy = 0
        if total_problems > 0:
            overall_accuracy = round((total_correct / total_problems) * 100, 2)

        # Calculate study days and streaks
        study_dates = study_logs.values_list('started_at__date', flat=True).distinct()
        study_days = len(set(study_dates))

        current_streak = self._calculate_current_streak(user)
        longest_streak = self._calculate_longest_streak(user)

        # Calculate average daily time
        if study_days > 0:
            average_daily_time = total_time // study_days
        else:
            average_daily_time = 0

        # Get subject statistics
        subject_stats = self._get_subject_statistics(user)
        best_subject = max(subject_stats, key=lambda x: x['accuracy']) if subject_stats else None
        weakest_subject = min(subject_stats, key=lambda x: x['accuracy']) if subject_stats else None

        # Get recent activity (last 7 days)
        seven_days_ago = now - timedelta(days=7)
        recent_logs = StudyLog.objects.for_user(user).filter(
            started_at__gte=seven_days_ago).order_by('-started_at')[:10]
        recent_activity = StudyLogSerializer(recent_logs, many=True).data

        data = {
            'total_study_time': total_time,
            'total_study_time_display': self._format_time(total_time),
            'total_problems_attempted': total_problems,
            'total_problems_correct': total_correct,
            'overall_accuracy': overall_accuracy,
            'total_points': total_points,
            'study_days': study_days,
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'average_daily_time': average_daily_time,
            'average_daily_time_display': self._format_time(average_daily_time),
            'best_subject': best_subject,
            'weakest_subject': weakest_subject,
            'recent_activity': recent_activity
        }

        serializer = StudyStatisticsSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_subject(self, request):
        user = request.user
        subject_stats = self._get_subject_statistics(user)

        serializer = SubjectStatisticsSerializer(subject_stats, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        user = request.user
        days = int(request.query_params.get('days', 30))

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        summaries = DailyStudySummary.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).prefetch_related(
            Prefetch('subjects_studied', queryset=available_subjects(user))
        ).order_by('-date')

        serializer = DailyStudySummarySerializer(summaries, many=True)
        return Response(serializer.data)

    def _calculate_current_streak(self, user):
        today = timezone.now().date()
        streak = 0
        current_date = today

        while True:
            # 組織で絞らない: 件数・時間・正答率だけの集計（中身を返さない・I431 扱いの基準 3）
            if StudyLog.objects.filter(
                user=user,
                started_at__date=current_date
            ).exists():
                streak += 1
                current_date -= timedelta(days=1)
            else:
                # Check if yesterday was studied (allow 1 day gap for today)
                if current_date == today:
                    current_date -= timedelta(days=1)
                    # 組織で絞らない: 件数・時間・正答率だけの集計（中身を返さない・I431 扱いの基準 3）
                    if StudyLog.objects.filter(
                        user=user,
                        started_at__date=current_date
                    ).exists():
                        streak = 1
                        current_date -= timedelta(days=1)
                    else:
                        break
                else:
                    break

        return streak

    def _calculate_longest_streak(self, user):
        # 組織で絞らない: 件数・時間・正答率だけの集計（中身を返さない・I431 扱いの基準 3）
        study_dates = StudyLog.objects.filter(user=user).values_list(
            'started_at__date', flat=True
        ).distinct().order_by('started_at__date')

        if not study_dates:
            return 0

        longest = 1
        current = 1

        for i in range(1, len(study_dates)):
            if study_dates[i] - study_dates[i-1] == timedelta(days=1):
                current += 1
                longest = max(longest, current)
            else:
                current = 1

        return longest

    def _get_subject_statistics(self, user):
        # 統計画面では会員が選択した科目のみ表示
        subjects = subject_service.get_user_selected_subjects(user, use_cache=True)
        stats = []

        for subject in subjects:
            subject_logs = StudyLog.objects.for_user(user).filter(subject=subject)

            if not subject_logs.exists():
                continue

            totals = subject_logs.aggregate(
                total_time=Sum('duration'),
                total_problems=Sum('problems_attempted'),
                total_correct=Sum('problems_correct'),
                total_points=Sum('points_earned')
            )

            total_time = totals['total_time'] or 0
            total_problems = totals['total_problems'] or 0
            total_correct = totals['total_correct'] or 0
            total_points = totals['total_points'] or 0

            accuracy = 0
            if total_problems > 0:
                accuracy = round((total_correct / total_problems) * 100, 2)

            last_studied = subject_logs.order_by('-started_at').first().started_at

            stats.append({
                'subject_id': subject.id,
                'subject_name': subject.name,
                'total_time': total_time,
                'total_time_display': self._format_time(total_time),
                'problems_attempted': total_problems,
                'problems_correct': total_correct,
                'accuracy': accuracy,
                'points_earned': total_points,
                'last_studied': last_studied
            })

        return stats

    def _format_time(self, seconds):
        if seconds is None:
            return "0時間0分"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}時間{minutes}分"


class StudyGoalViewSet(viewsets.ModelViewSet):
    serializer_class = StudyGoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudyGoal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def update_progress(self, request):
        # This would be called by a scheduled task or triggered by events
        user = request.user
        goals = StudyGoal.objects.filter(user=user, is_active=True)

        for goal in goals:
            if goal.goal_type == 'daily_time':
                # 組織で絞らない: 件数・時間・正答率だけの集計（中身を返さない・I431 扱いの基準 3）
                today_time = StudyLog.objects.filter(
                    user=user,
                    started_at__date=timezone.now().date()
                ).aggregate(total=Sum('duration'))['total'] or 0
                goal.current_value = today_time // 60  # Convert to minutes

            elif goal.goal_type == 'daily_problems':
                # 組織で絞らない: 件数・時間・正答率だけの集計（中身を返さない・I431 扱いの基準 3）
                today_problems = StudyLog.objects.filter(
                    user=user,
                    started_at__date=timezone.now().date()
                ).aggregate(total=Sum('problems_attempted'))['total'] or 0
                goal.current_value = today_problems

            elif goal.goal_type == 'streak':
                goal.current_value = self._calculate_current_streak(user)

            goal.save()

        serializer = StudyGoalSerializer(goals, many=True)
        return Response(serializer.data)

    def _calculate_current_streak(self, user):
        # Reuse the method from StudyStatisticsViewSet
        stats_viewset = StudyStatisticsViewSet()
        return stats_viewset._calculate_current_streak(user)


class SpacedRepetitionViewSet(viewsets.ViewSet):
    """間隔反復学習システムのAPIエンドポイント"""
    permission_classes = [permissions.IsAuthenticated]

    def get_service(self):
        """ユーザー用のSpacedRepetitionServiceインスタンスを取得"""
        return SpacedRepetitionService(self.request.user)

    @action(detail=False, methods=['get'])
    def due_cards(self, request):
        """復習が必要なカードを取得"""
        service = self.get_service()
        limit = int(request.query_params.get('limit', 20))

        due_cards = service.get_due_cards(limit=limit)
        serializer = SpacedRepetitionCardSerializer(due_cards, many=True)

        return Response({
            'cards': serializer.data,
            'count': len(due_cards),
            'has_more': len(due_cards) == limit
        })

    @action(detail=False, methods=['get'])
    def review_summary(self, request):
        """今日の復習の件数と次の復習日（科目の指定は自組織で選べる科目だけ）"""
        query = ReviewSummaryQuerySerializer(
            data=request.query_params, context={'request': request})
        if not query.is_valid():
            # 数字でない・他組織・全体共有・存在しない科目は同じ 400（違いを見せない）
            return create_error_response(
                '科目の指定が正しくありません',
                'ダッシュボードの科目の選択からやり直してください',
                status.HTTP_400_BAD_REQUEST,
            )

        summary = self.get_service().review_summary(query.validated_data.get('subject_id'))
        return Response(ReviewSummarySerializer(summary).data)

    @action(detail=False, methods=['get'])
    def daily_plan(self, request):
        """1日の学習プランを取得"""
        service = self.get_service()
        available_time = int(request.query_params.get('available_time_minutes', 30))

        plan = service.get_daily_study_plan(available_time_minutes=available_time)
        serializer = DailyStudyPlanSerializer(plan)

        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def submit_review(self, request):
        """復習結果を提出"""
        service = self.get_service()
        serializer = SpacedRepetitionSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            # カードを取得（他組織の問題のカードは存在しないカードと同じ扱い）
            card = SpacedRepetitionCard.objects.for_user(request.user).get(id=data['card_id'])

            # 現在のアクティブなスタディログを取得（オプション・他組織の科目の記録は使わない）
            active_study_log = StudyLog.objects.for_user(request.user).filter(
                is_active=True).first()

            # 復習を記録
            review = service.review_card(
                card=card,
                quality_score=data['quality_score'],
                response_time_seconds=data['response_time_seconds'],
                hint_used=data['hint_used'],
                study_session=active_study_log
            )

            # 学習分析データを更新
            service.update_daily_analytics()

            review_serializer = SpacedRepetitionReviewSerializer(review)
            card_serializer = SpacedRepetitionCardSerializer(card)

            return Response({
                'review': review_serializer.data,
                'updated_card': card_serializer.data,
                'message': '復習を記録しました'
            }, status=status.HTTP_201_CREATED)

        except SpacedRepetitionCard.DoesNotExist:
            return Response(
                {'error': 'カードが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'復習の記録に失敗しました: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def create_card(self, request):
        """新しい問題用のカードを作成"""
        service = self.get_service()
        problem_id = request.data.get('problem_id')

        if not problem_id:
            return Response(
                {'error': 'problem_idが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from problems.models import Problem
            # 他組織・削除済み・全体共有科目の問題は、存在しない問題と同じ 404
            problem = available_problems(request.user).get(id=problem_id)

            # カードを作成
            card = service.create_card_for_problem(problem)
            serializer = SpacedRepetitionCardSerializer(card)

            return Response({
                'card': serializer.data,
                'message': 'カードを作成しました'
            }, status=status.HTTP_201_CREATED)

        except Problem.DoesNotExist:
            return Response(
                {'error': '問題が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def user_statistics(self, request):
        """ユーザーの学習統計を取得"""
        service = self.get_service()
        stats = service.get_user_statistics()
        serializer = UserStatisticsSerializer(stats)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def learning_insights(self, request):
        """学習洞察を取得"""
        service = self.get_service()
        days = int(request.query_params.get('days', 7))

        insights = service.get_learning_insights(days=days)
        serializer = LearningInsightsSerializer(insights)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """学習分析データを取得"""
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)

        analytics = LearningAnalytics.objects.filter(
            user=request.user,
            date__range=[start_date, end_date]
        ).order_by('date')

        serializer = LearningAnalyticsSerializer(analytics, many=True)

        return Response({
            'analytics': serializer.data,
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            }
        })

    @action(detail=False, methods=['post'])
    def update_analytics(self, request):
        """学習分析データを手動更新"""
        service = self.get_service()
        target_date_str = request.data.get('date')

        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': '日付の形式が正しくありません (YYYY-MM-DD)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = None

        analytics = service.update_daily_analytics(target_date=target_date)
        serializer = LearningAnalyticsSerializer(analytics)

        return Response({
            'analytics': serializer.data,
            'message': '分析データを更新しました'
        })


class SpacedRepetitionCardViewSet(viewsets.ReadOnlyModelViewSet):
    """間隔反復学習カードの読み取り専用ビューセット"""
    serializer_class = SpacedRepetitionCardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = SpacedRepetitionCard.objects.for_user(self.request.user).select_related(
            'problem', 'problem__subject')

        # フィルタリングオプション
        is_due = self.request.query_params.get('is_due')
        mastery_level = self.request.query_params.get('mastery_level')
        subject_id = self.request.query_params.get('subject_id')

        if is_due == 'true':
            queryset = queryset.filter(
                next_review_date__lte=timezone.now(),
                is_active=True
            )

        if mastery_level:
            # カスタムフィルタリングが必要な場合
            cards = [card for card in queryset if card.mastery_level == mastery_level]
            return cards

        if subject_id:
            queryset = queryset.filter(problem__subject_id=subject_id)

        return queryset.order_by('next_review_date', '-ease_factor')


class SpacedRepetitionReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """間隔反復学習復習記録の読み取り専用ビューセット"""
    serializer_class = SpacedRepetitionReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = SpacedRepetitionReview.objects.for_user(self.request.user).select_related(
            'card', 'problem', 'problem__subject')

        # フィルタリングオプション
        card_id = self.request.query_params.get('card_id')
        days = self.request.query_params.get('days')

        if card_id:
            queryset = queryset.filter(card_id=card_id)

        if days:
            try:
                days_int = int(days)
                start_date = timezone.now() - timedelta(days=days_int)
                queryset = queryset.filter(reviewed_at__gte=start_date)
            except ValueError:
                pass

        return queryset.order_by('-reviewed_at')
