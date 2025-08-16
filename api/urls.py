from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet, StudentViewSet, LessonViewSet, QuestionViewSet,
    QuizAttemptViewSet, StudentProgressViewSet,
    export_quiz_attempts_csv,
    teacher_dashboard, 
    ai_quiz_feedback, ai_recommendations,
    teacher_books, publish_book, video_page, add_video, home
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'quiz-attempts', QuizAttemptViewSet, basename='quiz-attempt')
router.register(r'student-progress', StudentProgressViewSet, basename='student-progress')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    path('quiz-attempts/export-csv/', export_quiz_attempts_csv, name='export-quiz-attempts-csv'),
    
    # AI URLs
    path('ai/quiz-feedback/', ai_quiz_feedback, name='ai-quiz-feedback'),
    path('ai/recommendations/', ai_recommendations, name='ai-recommendations'),

    # Custom views for the web platform
    path('teacher-dashboard/', teacher_dashboard, name='teacher-dashboard'),
    path('teacher-books/', teacher_books, name='teacher_books'),
    path('publish-book/', publish_book, name='publish_book'),
    path('video-page/', video_page, name='video_page'),
    path('add-video/', add_video, name='add_video'),
    path('', home, name='home'),
]