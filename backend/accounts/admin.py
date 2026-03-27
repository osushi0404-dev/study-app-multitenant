from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, EmailVerification, PasswordResetToken, UserSettings, StudyStreak


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'email', 'role', 'is_email_verified', 'is_active',
        'failed_login_attempts', 'account_status', 'created_at'
    )
    list_filter = (
        'role', 'is_active', 'is_email_verified', 'is_staff', 'created_at'
    )
    search_fields = ('email',)
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_login')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('role', 'is_email_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Security', {'fields': ('failed_login_attempts', 'account_locked_until')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )

    def account_status(self, obj):
        if obj.is_account_locked():
            return format_html('<span style="color: red;">ロック中</span>')
        elif not obj.is_email_verified:
            return format_html('<span style="color: orange;">未認証</span>')
        elif obj.is_active:
            return format_html('<span style="color: green;">アクティブ</span>')
        else:
            return format_html('<span style="color: gray;">無効</span>')
    account_status.short_description = 'アカウント状態'


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at')

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at')

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'daily_study_goal_minutes', 'study_reminders_enabled',
        'theme_preference', 'updated_at'
    )
    list_filter = ('study_reminders_enabled', 'theme_preference', 'updated_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StudyStreak)
class StudyStreakAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'current_streak', 'longest_streak', 'last_study_date', 'updated_at'
    )
    list_filter = ('last_study_date', 'updated_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-current_streak',)
