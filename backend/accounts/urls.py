from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

# Router for admin endpoints
router = routers.DefaultRouter()
router.register(r'admin/users', views.AdminUserViewSet, basename='admin-users')

urlpatterns = [
    # Authentication
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/register/<slug:organization_slug>/', views.UserRegistrationView.as_view(), name='register_with_org'),

    # Field validation
    path('auth/validate-field/', views.FieldValidationView.as_view(), name='validate_field'),

    # Organization validation
    path('organizations/validate-slug/<slug:slug>/', views.OrganizationSlugValidationView.as_view(), name='validate_org_slug'),

    # Email verification
    path('auth/verify-email/', views.EmailVerificationView.as_view(), name='verify_email'),
    
    # Password reset
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # User profile and settings
    path('auth/me/', views.UserProfileView.as_view(), name='user_profile'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('settings/', views.UserSettingsView.as_view(), name='user_settings'),
    path('streak/', views.StudyStreakView.as_view(), name='study_streak'),
    
    # Admin endpoints
    path('', include(router.urls)),
]