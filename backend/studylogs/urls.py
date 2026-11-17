from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudyLogViewSet, StudyStatisticsViewSet, StudyGoalViewSet,
    SpacedRepetitionViewSet, SpacedRepetitionCardViewSet, SpacedRepetitionReviewViewSet,
)

router = DefaultRouter()
router.register(r'logs', StudyLogViewSet, basename='studylog')
router.register(r'statistics', StudyStatisticsViewSet, basename='statistics')
router.register(r'goals', StudyGoalViewSet, basename='studygoal')
router.register(r'spaced-repetition', SpacedRepetitionViewSet, basename='spaced-repetition')
router.register(r'sr-cards', SpacedRepetitionCardViewSet, basename='sr-cards')
router.register(r'sr-reviews', SpacedRepetitionReviewViewSet, basename='sr-reviews')

urlpatterns = [
    path('', include(router.urls)),
]
