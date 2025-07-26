# learnflow_ai/django_backend/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet, StudentViewSet, LessonViewSet, QuestionViewSet,
    QuizAttemptViewSet, StudentProgressViewSet,
    export_quiz_attempts_csv,
    teacher_dashboard_view,
    ai_quiz_feedback, ai_recommendations, # AI views - These are correctly named
    WalletViewSet, # NEW: Wallet ViewSet
    get_wallet_balance # NEW: Specific wallet balance endpoint
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'quiz-attempts', QuizAttemptViewSet, basename='quiz-attempt')
router.register(r'student-progress', StudentProgressViewSet, basename='student-progress')
router.register(r'wallets', WalletViewSet, basename='wallet') # NEW: Wallet URL

urlpatterns = [
    path('', include(router.urls)),
    path('quiz-attempts/export-csv/', export_quiz_attempts_csv, name='export-quiz-attempts-csv'),
    path('teacher-dashboard/', teacher_dashboard_view, name='teacher-dashboard'),
    # AI URLs
    path('ai/quiz-feedback/', ai_quiz_feedback, name='ai-quiz-feedback'),
    path('ai/recommendations/', ai_recommendations, name='ai-recommendations'),
    # NEW Blockchain/Wallet URLs
    path('wallets/balance/', get_wallet_balance, name='wallet-balance'), # Custom action for balance
]
