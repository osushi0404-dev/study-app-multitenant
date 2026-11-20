from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MediaAssetContentView, SubjectViewSet, ProblemViewSet, QuizSessionViewSet
from api.views.user_subjects import AvailableSubjectsView, UserSubjectsView

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'problems', ProblemViewSet, basename='problem')
router.register(r'quiz', QuizSessionViewSet, basename='quiz')

urlpatterns = [
    path('', include(router.urls)),
    path('user/subjects/', UserSubjectsView.as_view(), name='user-subjects'),
    path('user/subjects/available/', AvailableSubjectsView.as_view(), name='user-subjects-available'),
    path('media/<uuid:asset_id>/', MediaAssetContentView.as_view(), name='media-asset-content'),  # I587
]
