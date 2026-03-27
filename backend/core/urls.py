"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from problems.views import SubjectViewSet

# 組織科目用のルーター
organizations_router = DefaultRouter()
organizations_router.register(r'subjects', SubjectViewSet, basename='organization-subject')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('problems.urls')),
    path('api/study/', include('studylogs.urls')),
    path('api/', include('dashboard.urls')),
    path('api/organizations/', include(organizations_router.urls)),
    path('', include('core.monitoring_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customization
admin.site.site_header = "学習アプリ 管理画面"
admin.site.site_title = "学習アプリ Admin"
admin.site.index_title = "管理メニュー"
