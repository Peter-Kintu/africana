# learnflow_ai/django_backend/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet, StudentViewSet, LessonViewSet,
    QuestionViewSet, QuizAttemptViewSet, StudentProgressViewSet
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth') # For /api/auth/register, /api/auth/login, /api/auth/logout
router.register(r'students', StudentViewSet)
router.register(r'lessons', LessonViewSet)
router.register(r'questions', QuestionViewSet)
router.register(r'quiz-attempts', QuizAttemptViewSet)
router.register(r'student-progress', StudentProgressViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

