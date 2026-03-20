from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    StudyLog, DailyStudySummary, ProblemAttempt, StudyGoal,
    SpacedRepetitionCard, SpacedRepetitionReview, LearningAnalytics,
    MistakePattern, LearningSuggestion, LearningWeakness
)
from .serializers import (
    StudyLogSerializer, StudyLogCreateSerializer, StudyLogEndSerializer,
    DailyStudySummarySerializer, ProblemAttemptSerializer,
    StudyGoalSerializer, StudyStatisticsSerializer, SubjectStatisticsSerializer,
    SpacedRepetitionCardSerializer, SpacedRepetitionReviewSerializer,
    SpacedRepetitionSubmissionSerializer, LearningAnalyticsSerializer,
    DailyStudyPlanSerializer, LearningInsightsSerializer, UserStatisticsSerializer,
    MistakePatternSerializer, LearningSuggestionSerializer, LearningWeaknessSerializer,
    MistakeAnalysisSerializer, SuggestionFeedbackSerializer,
    ProficiencyAnalysisSerializer, PersonalizedRecommendationSerializer,
    AdaptiveProblemSelectionSerializer, SelectedProblemsSerializer
)
from .services import SpacedRepetitionService
from .mistake_analysis import MistakeAnalysisService
from .adaptive_selection import AdaptiveProblemSelector
from core.subject_service import subject_service


class StudyLogViewSet(viewsets.ModelViewSet):
    serializer_class = StudyLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudyLog.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return StudyLogCreateSerializer
        return StudyLogSerializer

    def create(self, request):
        # End any active study logs first
        StudyLog.objects.filter(
            user=request.user,
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
        recent_logs = study_logs.filter(started_at__gte=seven_days_ago).order_by('-started_at')[:10]
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
        ).order_by('-date')

        serializer = DailyStudySummarySerializer(summaries, many=True)
        return Response(serializer.data)

    def _calculate_current_streak(self, user):
        today = timezone.now().date()
        streak = 0
        current_date = today

        while True:
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
            subject_logs = StudyLog.objects.filter(user=user, subject=subject)
            
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
                today_time = StudyLog.objects.filter(
                    user=user,
                    started_at__date=timezone.now().date()
                ).aggregate(total=Sum('duration'))['total'] or 0
                goal.current_value = today_time // 60  # Convert to minutes

            elif goal.goal_type == 'daily_problems':
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
            # カードを取得
            card = SpacedRepetitionCard.objects.get(
                id=data['card_id'],
                user=request.user
            )
            
            # 現在のアクティブなスタディログを取得（オプション）
            active_study_log = StudyLog.objects.filter(
                user=request.user,
                is_active=True
            ).first()
            
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
            problem = Problem.objects.get(id=problem_id, is_deleted=False)
            
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
        queryset = SpacedRepetitionCard.objects.filter(
            user=self.request.user
        ).select_related('problem', 'problem__subject')
        
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
        queryset = SpacedRepetitionReview.objects.filter(
            user=self.request.user
        ).select_related('card', 'problem', 'problem__subject')
        
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


class MistakeAnalysisViewSet(viewsets.ViewSet):
    """間違いパターン分析と学習提案のAPIエンドポイント"""
    permission_classes = [permissions.IsAuthenticated]

    def get_service(self):
        """ユーザー用のMistakeAnalysisServiceインスタンスを取得"""
        return MistakeAnalysisService(self.request.user)

    @action(detail=False, methods=['get'])
    def analyze(self, request):
        """包括的な間違い分析を実行"""
        service = self.get_service()
        days = int(request.query_params.get('days', 30))
        
        analysis_result = service.analyze_mistakes(days=days)
        serializer = MistakeAnalysisSerializer(analysis_result)
        
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def patterns(self, request):
        """間違いパターンの一覧を取得"""
        patterns = MistakePattern.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-occurrence_count', '-confidence_score')
        
        # フィルタリングオプション
        pattern_type = request.query_params.get('pattern_type')
        subject_id = request.query_params.get('subject_id')
        severity = request.query_params.get('severity')
        
        if pattern_type:
            patterns = patterns.filter(pattern_type=pattern_type)
        
        if subject_id:
            patterns = patterns.filter(subject_id=subject_id)
        
        if severity:
            patterns = [p for p in patterns if p.severity_level == severity]
        
        serializer = MistakePatternSerializer(patterns, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """学習提案の一覧を取得"""
        suggestions = LearningSuggestion.objects.filter(
            user=request.user,
            is_active=True
        )
        
        # フィルタリングオプション
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        priority = request.query_params.get('priority')
        suggestion_type = request.query_params.get('suggestion_type')
        
        if unread_only:
            suggestions = suggestions.filter(is_read=False)
        
        if priority:
            suggestions = suggestions.filter(priority=priority)
        
        if suggestion_type:
            suggestions = suggestions.filter(suggestion_type=suggestion_type)
        
        suggestions = suggestions.order_by('priority', '-created_at')
        serializer = LearningSuggestionSerializer(suggestions, many=True)
        
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_suggestion_read(self, request):
        """学習提案を既読にマーク"""
        suggestion_id = request.data.get('suggestion_id')
        
        if not suggestion_id:
            return Response(
                {'error': 'suggestion_idが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            suggestion = LearningSuggestion.objects.get(
                id=suggestion_id,
                user=request.user
            )
            
            suggestion.is_read = True
            suggestion.save()
            
            return Response({'message': '提案を既読にしました'})
            
        except LearningSuggestion.DoesNotExist:
            return Response(
                {'error': '提案が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def provide_feedback(self, request):
        """学習提案にフィードバックを提供"""
        serializer = SuggestionFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        service = self.get_service()
        
        success = service.provide_suggestion_feedback(
            suggestion_id=data['suggestion_id'],
            rating=data['effectiveness_rating'],
            comment=data.get('feedback_comment', '')
        )
        
        if success:
            return Response({'message': 'フィードバックを記録しました'})
        else:
            return Response(
                {'error': '提案が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def weaknesses(self, request):
        """学習の弱点一覧を取得"""
        weaknesses = LearningWeakness.objects.filter(
            user=request.user,
            is_resolved=False
        ).order_by('-severity', '-error_count')
        
        # フィルタリングオプション
        subject_id = request.query_params.get('subject_id')
        severity = request.query_params.get('severity')
        
        if subject_id:
            weaknesses = weaknesses.filter(subject_id=subject_id)
        
        if severity:
            weaknesses = weaknesses.filter(severity=severity)
        
        serializer = LearningWeaknessSerializer(weaknesses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def resolve_weakness(self, request):
        """弱点を解決済みにマーク"""
        weakness_id = request.data.get('weakness_id')
        
        if not weakness_id:
            return Response(
                {'error': 'weakness_idが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weakness = LearningWeakness.objects.get(
                id=weakness_id,
                user=request.user
            )
            
            weakness.is_resolved = True
            weakness.improvement_score = 1.0
            weakness.save()
            
            return Response({'message': '弱点を解決済みにしました'})
            
        except LearningWeakness.DoesNotExist:
            return Response(
                {'error': '弱点が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def improvement_trends(self, request):
        """改善トレンドを取得"""
        service = self.get_service()
        days = int(request.query_params.get('days', 30))
        
        # 期間別の正答率推移
        trends = []
        for i in range(days // 7):  # 週単位
            start_date = timezone.now() - timedelta(weeks=i+1)
            end_date = timezone.now() - timedelta(weeks=i)
            
            attempts = ProblemAttempt.objects.filter(
                user=request.user,
                attempted_at__range=[start_date, end_date]
            )
            
            if attempts.exists():
                correct_count = attempts.filter(is_correct=True).count()
                accuracy = (correct_count / attempts.count()) * 100
                
                trends.append({
                    'period': f"{i+1}週間前",
                    'start_date': start_date.date(),
                    'end_date': end_date.date(),
                    'accuracy': round(accuracy, 2),
                    'total_attempts': attempts.count(),
                    'correct_attempts': correct_count
                })
        
        return Response({
            'trends': trends,
            'period_days': days
        })

    @action(detail=False, methods=['post'])
    def refresh_analysis(self, request):
        """分析データを手動で更新"""
        service = self.get_service()
        days = int(request.data.get('days', 30))
        
        try:
            service.update_mistake_patterns(
                start_date=timezone.now() - timedelta(days=days),
                end_date=timezone.now()
            )
            
            service.update_learning_weaknesses(
                start_date=timezone.now() - timedelta(days=days),
                end_date=timezone.now()
            )
            
            service.generate_learning_suggestions()
            
            return Response({'message': '分析データを更新しました'})
            
        except Exception as e:
            return Response(
                {'error': f'分析の更新に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdaptiveLearningViewSet(viewsets.ViewSet):
    """適応的学習システムのAPIエンドポイント"""
    permission_classes = [permissions.IsAuthenticated]

    def get_selector(self):
        """ユーザー用のAdaptiveProblemSelectorインスタンスを取得"""
        return AdaptiveProblemSelector(self.request.user)

    @action(detail=False, methods=['get'])
    def proficiency_analysis(self, request):
        """習熟度分析を取得"""
        selector = self.get_selector()
        subject_id = request.query_params.get('subject_id')
        
        subject = None
        if subject_id:
            subject = subject_service.get_subject_by_id(subject_id, request.user)
            if not subject:
                return Response(
                    {'error': '科目が見つかりません'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        proficiency_data = selector.analyze_user_proficiency(subject)
        serializer = ProficiencyAnalysisSerializer(proficiency_data)
        
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def personalized_recommendation(self, request):
        """個人化された学習推奨を取得"""
        selector = self.get_selector()
        subject_id = request.query_params.get('subject_id')
        
        subject = None
        if subject_id:
            subject = subject_service.get_subject_by_id(subject_id, request.user)
            if not subject:
                return Response(
                    {'error': '科目が見つかりません'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        recommendation = selector.get_personalized_recommendation(subject)
        serializer = PersonalizedRecommendationSerializer(recommendation)
        
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def select_problems(self, request):
        """適応的問題選択を実行"""
        selector = self.get_selector()
        serializer = AdaptiveProblemSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # 科目を取得
        subject = None
        if data.get('subject_id'):
            subject = subject_service.get_subject_by_id(data['subject_id'], request.user)
            if not subject:
                return Response(
                    {'error': '科目が見つかりません'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        try:
            # 問題を選択
            selected_problems = selector.select_optimal_problems(
                subject=subject,
                count=data['count'],
                difficulty_preference=data['difficulty_preference'],
                learning_goal=data['learning_goal']
            )
            
            # 習熟度サマリーを取得
            proficiency_summary = selector.analyze_user_proficiency(subject)
            
            # 推奨事項を取得
            recommendation = selector.get_personalized_recommendation(subject)
            
            # 問題データをシリアライズ
            from problems.serializers import ProblemSerializer
            problem_data = ProblemSerializer(selected_problems, many=True).data
            
            result = {
                'problems': problem_data,
                'selection_criteria': {
                    'count': data['count'],
                    'difficulty_preference': data['difficulty_preference'],
                    'learning_goal': data['learning_goal'],
                    'subject': subject.name if subject else 'すべて'
                },
                'proficiency_summary': {
                    'overall_accuracy': proficiency_summary['overall_accuracy'],
                    'confidence_level': proficiency_summary['confidence_level'],
                    'total_attempts': proficiency_summary['total_attempts']
                },
                'recommendation': recommendation
            }
            
            result_serializer = SelectedProblemsSerializer(result)
            return Response(result_serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'問題選択に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def learning_path(self, request):
        """学習パスの推奨を取得"""
        selector = self.get_selector()
        subject_id = request.query_params.get('subject_id')
        
        subject = None
        if subject_id:
            subject = subject_service.get_subject_by_id(subject_id, request.user)
            if not subject:
                return Response(
                    {'error': '科目が見つかりません'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # 習熟度分析
        proficiency_data = selector.analyze_user_proficiency(subject)
        
        # 学習パスを生成
        learning_path = self._generate_learning_path(proficiency_data, subject, selector)
        
        return Response(learning_path)

    def _generate_learning_path(self, proficiency_data: dict, subject, selector) -> dict:
        """学習パスを生成"""
        overall_accuracy = proficiency_data['overall_accuracy']
        difficulty_prof = proficiency_data['difficulty_proficiency']
        
        path_steps = []
        
        # ステップ1: 基礎固め
        if overall_accuracy < 0.6 or difficulty_prof.get('easy', {}).get('accuracy', 0) < 0.8:
            path_steps.append({
                'step': 1,
                'title': '基礎固めフェーズ',
                'description': '基本概念の理解と易しい問題での練習',
                'difficulty_focus': 'easy',
                'learning_goal': 'review',
                'estimated_duration_days': 7,
                'success_criteria': '易しい問題で80%以上の正答率',
                'recommended_problems_per_day': 15
            })
        
        # ステップ2: スキル構築
        if difficulty_prof.get('medium', {}).get('accuracy', 0) < 0.7:
            path_steps.append({
                'step': len(path_steps) + 1,
                'title': 'スキル構築フェーズ',
                'description': '中程度の問題で応用力を向上',
                'difficulty_focus': 'medium',
                'learning_goal': 'learning',
                'estimated_duration_days': 10,
                'success_criteria': '中程度の問題で70%以上の正答率',
                'recommended_problems_per_day': 12
            })
        
        # ステップ3: 応用・挑戦
        if overall_accuracy >= 0.75:
            path_steps.append({
                'step': len(path_steps) + 1,
                'title': '応用・挑戦フェーズ',
                'description': '難しい問題での挑戦と応用力向上',
                'difficulty_focus': 'hard',
                'learning_goal': 'challenge',
                'estimated_duration_days': 14,
                'success_criteria': '難しい問題で60%以上の正答率',
                'recommended_problems_per_day': 8
            })
        
        # 現在のステップを判定
        current_step = 1
        for i, step in enumerate(path_steps):
            if step['difficulty_focus'] == 'easy' and overall_accuracy >= 0.6:
                current_step = i + 2
            elif step['difficulty_focus'] == 'medium' and difficulty_prof.get('medium', {}).get('accuracy', 0) >= 0.7:
                current_step = i + 2
        
        current_step = min(current_step, len(path_steps))
        
        return {
            'learning_path': path_steps,
            'current_step': current_step,
            'overall_progress': (current_step - 1) / len(path_steps) * 100 if path_steps else 100,
            'estimated_total_duration': sum(step['estimated_duration_days'] for step in path_steps),
            'subject': subject.name if subject else 'すべて',
            'proficiency_level': self._determine_proficiency_level(overall_accuracy)
        }

    def _determine_proficiency_level(self, accuracy: float) -> str:
        """習熟度レベルを判定"""
        if accuracy >= 0.9:
            return 'expert'
        elif accuracy >= 0.8:
            return 'advanced'
        elif accuracy >= 0.65:
            return 'intermediate'
        elif accuracy >= 0.4:
            return 'beginner'
        else:
            return 'novice'

    @action(detail=False, methods=['get'])
    def difficulty_distribution(self, request):
        """現在の難易度分布の推奨を取得"""
        selector = self.get_selector()
        subject_id = request.query_params.get('subject_id')
        
        subject = None
        if subject_id:
            subject = subject_service.get_subject_by_id(subject_id, request.user)
            if not subject:
                return Response(
                    {'error': '科目が見つかりません'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        proficiency_data = selector.analyze_user_proficiency(subject)
        
        # 最適な難易度分布を計算
        optimal_distribution = self._calculate_optimal_distribution(proficiency_data)
        
        return Response(optimal_distribution)

    def _calculate_optimal_distribution(self, proficiency_data: dict) -> dict:
        """最適な難易度分布を計算"""
        overall_accuracy = proficiency_data['overall_accuracy']
        difficulty_prof = proficiency_data['difficulty_proficiency']
        
        if overall_accuracy < 0.5:
            # 初心者：易しい問題中心
            distribution = {'easy': 60, 'medium': 30, 'hard': 10}
        elif overall_accuracy < 0.7:
            # 中級者：バランス重視
            distribution = {'easy': 30, 'medium': 50, 'hard': 20}
        elif overall_accuracy < 0.85:
            # 上級者：難しい問題増加
            distribution = {'easy': 20, 'medium': 40, 'hard': 40}
        else:
            # エキスパート：挑戦的な問題中心
            distribution = {'easy': 10, 'medium': 30, 'hard': 60}
        
        # 個別の難易度習熟度に基づく調整
        for difficulty in ['easy', 'medium', 'hard']:
            stats = difficulty_prof.get(difficulty, {})
            accuracy = stats.get('accuracy', 0.5)
            
            if accuracy < 0.4:  # 特に苦手
                distribution[difficulty] += 10
                # 他から削る
                for other_diff in ['easy', 'medium', 'hard']:
                    if other_diff != difficulty and distribution[other_diff] > 15:
                        distribution[other_diff] -= 5
                        break
        
        # 合計が100になるように正規化
        total = sum(distribution.values())
        if total != 100:
            factor = 100 / total
            distribution = {k: round(v * factor) for k, v in distribution.items()}
        
        return {
            'recommended_distribution': distribution,
            'current_performance': {
                'easy': difficulty_prof.get('easy', {}).get('accuracy', 0) * 100,
                'medium': difficulty_prof.get('medium', {}).get('accuracy', 0) * 100,
                'hard': difficulty_prof.get('hard', {}).get('accuracy', 0) * 100
            },
            'overall_accuracy': overall_accuracy * 100,
            'recommendation_reason': self._get_distribution_reason(overall_accuracy)
        }

    def _get_distribution_reason(self, accuracy: float) -> str:
        """分布推奨の理由を取得"""
        if accuracy < 0.5:
            return "基礎力向上のため、易しい問題での練習を重視します"
        elif accuracy < 0.7:
            return "バランス良く実力を向上させるため、中程度の問題を中心に学習します"
        elif accuracy < 0.85:
            return "応用力向上のため、難しい問題への挑戦を増やします"
        else:
            return "さらなる向上のため、挑戦的な問題を中心に学習します"