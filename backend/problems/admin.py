from django.contrib import admin
from .models import Subject, Problem, Choice, QuizSession, QuizAnswer


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name', 'description']


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'subject', 'difficulty', 'problem_type', 'is_deleted', 'created_by', 'created_at']
    list_filter = ['subject', 'difficulty', 'problem_type', 'is_deleted', 'is_ai_generated']
    search_fields = ['question', 'explanation']
    inlines = [ChoiceInline]
    readonly_fields = ['created_at', 'updated_at']

    def question_preview(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'total_problems', 'completed_problems', 'correct_answers', 'is_active', 'started_at']
    list_filter = ['is_active', 'subject', 'started_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['started_at', 'ended_at']


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ['session_user', 'problem_preview', 'is_correct', 'answered_at']
    list_filter = ['is_correct', 'answered_at']
    search_fields = ['session__user__username', 'problem__question']
    readonly_fields = ['answered_at']

    def session_user(self, obj):
        return obj.session.user.username
    session_user.short_description = 'User'

    def problem_preview(self, obj):
        return obj.problem.question[:50] + '...' if len(obj.problem.question) > 50 else obj.problem.question
    problem_preview.short_description = 'Problem'