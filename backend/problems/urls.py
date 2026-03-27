from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubjectViewSet, ProblemViewSet, QuizSessionViewSet
from api.views.user_subjects import get_user_subjects

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'problems', ProblemViewSet, basename='problem')
router.register(r'quiz', QuizSessionViewSet, basename='quiz')

urlpatterns = [
    path('', include(router.urls)),
    path('user/subjects/', get_user_subjects, name='user-subjects'),
]
