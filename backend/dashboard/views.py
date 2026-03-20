from rest_framework import views, permissions
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from problems.models import Subject, Problem, QuizSession, QuizAnswer
from studylogs.models import StudyLog, DailyStudySummary
from accounts.models import User
from core.subject_service import subject_service


class DashboardOverviewView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        today = now.date()
        
        # Get today's study data
        today_study = StudyLog.objects.filter(
            user=user,
            started_at__date=today
        ).aggregate(
            total_time=Sum('duration'),
            total_problems=Sum('problems_attempted'),
            total_correct=Sum('problems_correct')
        )

        # Get current active session
        active_session = StudyLog.objects.filter(
            user=user,
            is_active=True
        ).first()

        # Get recent quiz sessions
        recent_quizzes = QuizSession.objects.filter(
            user=user
        ).order_by('-started_at')[:5]

        quiz_data = []
        for quiz in recent_quizzes:
            accuracy = 0
            if quiz.completed_problems > 0:
                accuracy = round((quiz.correct_answers / quiz.completed_problems) * 100, 2)
            
            quiz_data.append({
                'id': str(quiz.id),
                'subject': quiz.subject.name if quiz.subject else 'All Subjects',
                'completed_problems': quiz.completed_problems,
                'total_problems': quiz.total_problems,
                'accuracy': accuracy,
                'started_at': quiz.started_at,
                'is_active': quiz.is_active
            })

        # Get study streak
        streak = self._calculate_study_streak(user)

        # Get weekly progress
        week_ago = today - timedelta(days=7)
        weekly_summary = DailyStudySummary.objects.filter(
            user=user,
            date__gte=week_ago
        ).aggregate(
            total_time=Sum('total_study_time'),
            total_problems=Sum('total_problems_attempted'),
            total_correct=Sum('total_problems_correct')
        )

        # Get subject progress
        subject_progress = self._get_subject_progress(user)

        # Get upcoming goals
        upcoming_goals = self._get_upcoming_goals(user)

        return Response({
            'today': {
                'study_time': today_study['total_time'] or 0,
                'problems_attempted': today_study['total_problems'] or 0,
                'problems_correct': today_study['total_correct'] or 0,
                'accuracy': round((today_study['total_correct'] or 0) / max(today_study['total_problems'] or 1, 1) * 100, 2)
            },
            'active_session': {
                'id': str(active_session.id) if active_session else None,
                'subject': active_session.subject.name if active_session and active_session.subject else None,
                'started_at': active_session.started_at if active_session else None
            } if active_session else None,
            'study_streak': streak,
            'weekly_summary': {
                'total_time': weekly_summary['total_time'] or 0,
                'total_problems': weekly_summary['total_problems'] or 0,
                'total_correct': weekly_summary['total_correct'] or 0,
                'accuracy': round((weekly_summary['total_correct'] or 0) / max(weekly_summary['total_problems'] or 1, 1) * 100, 2)
            },
            'recent_quizzes': quiz_data,
            'subject_progress': subject_progress,
            'upcoming_goals': upcoming_goals
        })

    def _calculate_study_streak(self, user):
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

    def _get_subject_progress(self, user):
        # ダッシュボードでは会員が選択した科目のみ表示
        subjects = subject_service.get_user_selected_subjects(user, use_cache=True)
        progress = []

        for subject in subjects:
            logs = StudyLog.objects.filter(user=user, subject=subject)
            if not logs.exists():
                continue

            totals = logs.aggregate(
                total_time=Sum('duration'),
                total_problems=Sum('problems_attempted'),
                total_correct=Sum('problems_correct')
            )

            accuracy = 0
            if totals['total_problems']:
                accuracy = round((totals['total_correct'] / totals['total_problems']) * 100, 2)

            progress.append({
                'subject_name': subject.name,
                'total_time': totals['total_time'] or 0,
                'total_problems': totals['total_problems'] or 0,
                'accuracy': accuracy,
                'last_studied': logs.order_by('-started_at').first().started_at
            })

        return sorted(progress, key=lambda x: x['last_studied'], reverse=True)

    def _get_upcoming_goals(self, user):
        from studylogs.models import StudyGoal
        
        goals = StudyGoal.objects.filter(user=user, is_active=True)
        upcoming = []

        for goal in goals:
            progress = goal.progress_percentage
            if progress < 100:
                upcoming.append({
                    'goal_type': goal.get_goal_type_display(),
                    'target_value': goal.target_value,
                    'current_value': goal.current_value,
                    'progress': progress
                })

        return upcoming


class DashboardAnalyticsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 30))
        
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
        subject_stats = StudyLog.objects.filter(
            user=user,
            started_at__date__gte=start_date
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
                avg_accuracy=Avg(
                    F('total_problems_correct') * 100.0 / F('total_problems_attempted')
                )
            )

            weeks.append({
                'week_start': current_week_start.isoformat(),
                'avg_study_time': week_summary['avg_time'] or 0,
                'avg_problems': week_summary['avg_problems'] or 0,
                'avg_accuracy': week_summary['avg_accuracy'] or 0
            })
            
            current_week_start += timedelta(days=7)

        return weeks


class SubjectRecommendationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get subjects with low accuracy that need improvement
        week_ago = timezone.now().date() - timedelta(days=7)
        
        subject_performance = StudyLog.objects.filter(
            user=user,
            started_at__date__gte=week_ago
        ).values('subject__id', 'subject__name').annotate(
            total_problems=Sum('problems_attempted'),
            total_correct=Sum('problems_correct'),
            accuracy=F('total_correct') * 100.0 / F('total_problems')
        ).filter(total_problems__gt=0).order_by('accuracy')

        recommendations = []
        
        for subject in subject_performance[:3]:  # Top 3 subjects needing improvement
            if subject['accuracy'] < 70:  # Less than 70% accuracy
                recommendations.append({
                    'subject_id': str(subject['subject__id']),
                    'subject_name': subject['subject__name'],
                    'current_accuracy': round(subject['accuracy'], 2),
                    'reason': f"正答率が{round(subject['accuracy'], 1)}%と低めです。復習をお勧めします。",
                    'recommended_problems': Problem.objects.filter(
                        subject_id=subject['subject__id'],
                        is_active=True
                    ).count()
                })

        # Get subjects that haven't been studied recently
        studied_subject_ids = StudyLog.objects.filter(
            user=user,
            started_at__date__gte=week_ago
        ).values_list('subject_id', flat=True)
        
        all_subjects = subject_service.get_user_subjects(user, use_cache=True).exclude(
            id__in=studied_subject_ids
        )

        for subject in all_subjects[:2]:  # Top 2 unstudied subjects
            recommendations.append({
                'subject_id': str(subject.id),
                'subject_name': subject.name,
                'current_accuracy': None,
                'reason': "最近学習していない科目です。定期的な復習をお勧めします。",
                'recommended_problems': Problem.objects.filter(
                    subject=subject,
                    is_active=True
                ).count()
            })

        return Response({
            'recommendations': recommendations
        })