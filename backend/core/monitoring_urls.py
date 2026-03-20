"""
監視システム API URLs
"""

from django.urls import path
from . import views

urlpatterns = [
    # システム監視エンドポイント
    path('health/', views.HealthCheckView.as_view(), name='health_check'),
    path('monitoring/status/', views.SystemStatusView.as_view(), name='system_status'),
    path('monitoring/errors/', views.ErrorSummaryView.as_view(), name='error_summary'),
    path('monitoring/performance/', views.PerformanceMetricsView.as_view(), name='performance_metrics'),
    path('monitoring/activity/', views.ActivitySummaryView.as_view(), name='activity_summary'),
    path('monitoring/alerts/', views.AlertsView.as_view(), name='alerts'),
    
    # キャッシュ管理
    path('cache/clear/', views.ClearCacheView.as_view(), name='clear_cache'),
    path('cache/stats/', views.CacheStatsView.as_view(), name='cache_stats'),
]