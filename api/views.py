# learnflow_ai/django_backend/api/views.py

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.db import IntegrityError, transaction
import csv
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Avg, Prefetch
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required

from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa

import requests
import json

from .models import Student, Lesson, Question, QuizAttempt, StudentProgress
from .serializers import (
    UserSerializer, StudentSerializer, LessonSerializer, QuestionSerializer,
    QuizAttemptSerializer, StudentProgressSerializer,
)

class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid():
            user = user_serializer.save()
            try:
                student_data = request.data.get('student_data', {})
                student = Student.objects.create(
                    user=user,
                    student_id_code=student_data.get('student_id_code'),
                    grade_level=student_data.get('grade_level'),
                    class_name=student_data.get('class_name'),
                    gender=student_data.get('gender')
                )
                student_serializer = StudentSerializer(student)
                return Response({
                    "message": "User and Student registered successfully",
                    "user": user_serializer.data,
                    "student": student_serializer.data,
                }, status=status.HTTP_201_CREATED)
            except IntegrityError:
                user.delete()
                return Response({"error": "A student with this ID code already exists or there's a database integrity issue."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "user_id": user.pk}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='user')
    def current_user(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Student.objects.all()
        return Student.objects.filter(user=self.request.user)

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        lesson_uuid = self.request.query_params.get('lesson_uuid')
        if lesson_uuid:
            queryset = queryset.filter(lesson__uuid=lesson_uuid)
        return queryset

class QuizAttemptViewSet(viewsets.ModelViewSet):
    queryset = QuizAttempt.objects.all()
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return QuizAttempt.objects.all().order_by('-attempt_timestamp')
        return QuizAttempt.objects.filter(student__user=self.request.user).order_by('-attempt_timestamp')

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['student_user_id'] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class StudentProgressViewSet(viewsets.ModelViewSet):
    queryset = StudentProgress.objects.all()
    serializer_class = StudentProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return StudentProgress.objects.all()
        return StudentProgress.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        student = get_object_or_404(Student, user=self.request.user)
        serializer.save(student=student)

    def perform_update(self, serializer):
        serializer.save(last_updated=timezone.now())

@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_quiz_attempts_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="quiz_attempts_report.csv"'

    writer = csv.writer(response)
    
    writer.writerow([
        'Attempt UUID',
        'Student Username',
        'Student ID Code',
        'Lesson Title',
        'Question Text',
        'Question Type',
        'Submitted Answer',
        'Is Correct',
        'Score',
        'AI Feedback Text',
        'Attempt Timestamp',
        'Device ID'
    ])

    quiz_attempts = QuizAttempt.objects.select_related('student__user', 'question__lesson').all().order_by('attempt_timestamp')

    for attempt in quiz_attempts:
        writer.writerow([
            str(attempt.uuid),
            attempt.student.user.username,
            attempt.student.student_id_code,
            attempt.question.lesson.title if attempt.question.lesson else 'N/A',
            attempt.question.question_text,
            attempt.question.question_type,
            attempt.submitted_answer,
            'Yes' if attempt.is_correct else 'No',
            attempt.score,
            attempt.ai_feedback_text if attempt.ai_feedback_text else '',
            attempt.attempt_timestamp.isoformat(),
            attempt.device_id if attempt.device_id else ''
        ])
    return response

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teacher_dashboard_view(request):
    if not request.user.is_staff:
        return Response({'detail': 'You do not have permission to access this page.'}, status=status.HTTP_403_FORBIDDEN)
    
    context = {}
    return Response(context)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_quiz_feedback(request):
    try:
        submitted_answer = request.data.get('submitted_answer', '')
        correct_answer = request.data.get('correct_answer_text', '')
        
        is_correct = submitted_answer.strip().lower() == correct_answer.strip().lower()
        score = 100 if is_correct else 0
        
        feedback = f"The submitted answer was {submitted_answer}. The correct answer is {correct_answer}."
        
        return Response({
            'success': True,
            'feedback_text': feedback,
            'score': score
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_recommendations(request):
    try:
        student_id_code = request.data.get('student_id_code')
        
        recommendations = [
            "Review Lesson A on 'Algebraic Expressions'",
            "Try more practice questions on 'Linear Equations'",
            "Proceed to the next lesson, 'Introduction to Geometry'"
        ]
        
        return Response({
            'success': True,
            'recommendations': recommendations
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)