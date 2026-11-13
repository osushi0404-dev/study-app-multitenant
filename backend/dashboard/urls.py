from django.urls import path
from .views import DashboardOverviewView, DashboardAnalyticsView

urlpatterns = [
    path('dashboard/overview/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('dashboard/analytics/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
]
