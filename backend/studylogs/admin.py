from django.contrib import admin
from .models import StudyLog, DailyStudySummary, ProblemAttempt, StudyGoal


@admin.register(StudyLog)
class StudyLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'started_at', 'ended_at', 'duration', 'problems_attempted', 'problems_correct', 'is_active']
    list_filter = ['is_active', 'subject', 'started_at']
    search_fields = ['user__username', 'user__email', 'notes']
    readonly_fields = ['started_at', 'ended_at', 'duration', 'accuracy']

    def accuracy(self, obj):
        return f"{obj.accuracy}%"
    accuracy.short_description = 'Accuracy'


@admin.register(DailyStudySummary)
class DailyStudySummaryAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'total_study_time_display', 'total_problems_attempted', 'accuracy_display']
    list_filter = ['date']
    search_fields = ['user__username', 'user__email']
    filter_horizontal = ['subjects_studied']
    readonly_fields = ['accuracy']

    def total_study_time_display(self, obj):
        hours = obj.total_study_time // 3600
        minutes = (obj.total_study_time % 3600) // 60
        return f"{hours}h {minutes}m"
    total_study_time_display.short_description = 'Study Time'

    def accuracy_display(self, obj):
        return f"{obj.accuracy}%"
    accuracy_display.short_description = 'Accuracy'


@admin.register(ProblemAttempt)
class ProblemAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem_preview', 'is_correct', 'attempt_number', 'time_taken', 'attempted_at']
    list_filter = ['is_correct', 'attempted_at']
    search_fields = ['user__username', 'problem__question']
    readonly_fields = ['attempted_at']

    def problem_preview(self, obj):
        return obj.problem.question[:50] + '...' if len(obj.problem.question) > 50 else obj.problem.question
    problem_preview.short_description = 'Problem'


@admin.register(StudyGoal)
class StudyGoalAdmin(admin.ModelAdmin):
    list_display = ['user', 'goal_type', 'target_value', 'current_value', 'progress', 'is_active']
    list_filter = ['goal_type', 'is_active']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['progress_percentage']

    def progress(self, obj):
        return f"{obj.progress_percentage}%"
    progress.short_description = 'Progress'