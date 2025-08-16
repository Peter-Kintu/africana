# learnflow_ai/django_backend/api/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.db import IntegrityError
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import csv
from django.db.models import F
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Prefetch

# Models
from .models import (
    User, Student, Teacher, Lesson, Question,
    QuizAttempt, StudentProgress, Wallet
)

# Serializers
from .serializers import (
    UserSerializer, AuthSerializer, StudentSerializer, TeacherSerializer,
    LessonSerializer, QuestionSerializer, QuizAttemptSerializer,
    StudentProgressSerializer, WalletSerializer
)

# Permissions
from .permissions import IsTeacher, IsStudent, IsStudentOrTeacher

# AI Integration
from .ai_integration import get_quiz_feedback, get_recommendations

class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            serializer = AuthSerializer(user)
            return Response({'token': token.key, 'user': serializer.data})
        else:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def register(self, request):
        try:
            with transaction.atomic():
                user_data = request.data
                user_type = user_data.get('user_type', 'student').lower()

                serializer = UserSerializer(data=user_data)
                serializer.is_valid(raise_exception=True)
                user = serializer.save()

                if user_type == 'student':
                    student_data = {
                        'user': user.id,
                        'student_id_code': user_data.get('student_id_code'),
                        'gender': user_data.get('gender')
                    }
                    student_serializer = StudentSerializer(data=student_data)
                    student_serializer.is_valid(raise_exception=True)
                    student_serializer.save()
                elif user_type == 'teacher':
                    teacher_data = {
                        'user': user.id,
                        'school_id_code': user_data.get('school_id_code'),
                        'title': user_data.get('title')
                    }
                    teacher_serializer = TeacherSerializer(data=teacher_data)
                    teacher_serializer.is_valid(raise_exception=True)
                    teacher_serializer.save()

                token = Token.objects.create(user=user)
                response_serializer = AuthSerializer(user)
                return Response({'token': token.key, 'user': response_serializer.data}, status=status.HTTP_201_CREATED)

        except IntegrityError:
            return Response({'detail': 'A user with that username or email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({'detail': e.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def user(self, request):
        if request.user.is_authenticated:
            serializer = AuthSerializer(request.user)
            return Response(serializer.data)
        else:
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsTeacher]

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all().order_by('id')
    serializer_class = LessonSerializer
    permission_classes = [IsStudentOrTeacher]

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsTeacher]

class QuizAttemptViewSet(viewsets.ModelViewSet):
    queryset = QuizAttempt.objects.all().order_by('-attempted_at')
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsStudentOrTeacher]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            return QuizAttempt.objects.filter(student=user.student).order_by('-attempted_at')
        return super().get_queryset()

    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    def submit_answer(self, request, pk=None):
        quiz_attempt = get_object_or_404(QuizAttempt, pk=pk, student=request.user.student)
        question_id = request.data.get('question_id')
        answer = request.data.get('answer')

        question = get_object_or_404(Question, pk=question_id)
        is_correct = (answer == question.correct_answer)

        quiz_attempt.score = F('score') + (1 if is_correct else 0)
        quiz_attempt.save(update_fields=['score'])

        StudentProgress.objects.update_or_create(
            student=request.user.student,
            lesson=quiz_attempt.lesson,
            defaults={'score': F('score') + (1 if is_correct else 0), 'attempts': F('attempts') + 1}
        )

        return Response({'is_correct': is_correct, 'correct_answer': question.correct_answer})

class StudentProgressViewSet(viewsets.ModelViewSet):
    queryset = StudentProgress.objects.all()
    serializer_class = StudentProgressSerializer
    permission_classes = [IsStudentOrTeacher]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            return StudentProgress.objects.filter(student=user.student)
        return super().get_queryset()

# Utility functions
@api_view(['GET'])
@permission_classes([IsTeacher])
def export_quiz_attempts_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="quiz_attempts.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student', 'Lesson', 'Score', 'Attempted At'])

    quiz_attempts = QuizAttempt.objects.all().select_related('student__user', 'lesson')
    for attempt in quiz_attempts:
        writer.writerow([
            attempt.student.user.username,
            attempt.lesson.title,
            attempt.score,
            attempt.attempted_at
        ])

    return response

@api_view(['GET'])
@permission_classes([IsTeacher])
def teacher_dashboard_view(request):
    total_students = Student.objects.count()
    total_lessons = Lesson.objects.count()
    total_quiz_attempts = QuizAttempt.objects.count()

    return Response({
        'total_students': total_students,
        'total_lessons': total_lessons,
        'total_quiz_attempts': total_quiz_attempts
    })

# AI Endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_quiz_feedback(request):
    try:
        user_answer = request.data.get('user_answer')
        correct_answer = request.data.get('correct_answer')
        question_text = request.data.get('question_text')

        if not all([user_answer, correct_answer, question_text]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        feedback = get_quiz_feedback(question_text, user_answer, correct_answer)
        return Response({'feedback': feedback})

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_recommendations(request):
    try:
        user_id = request.user.id
        student_progress = StudentProgress.objects.filter(student__user_id=user_id).select_related('lesson').order_by('-score')[:5]

        # Use prefetch_related for efficient fetching of related questions
        lessons = Lesson.objects.all().prefetch_related(Prefetch('questions', queryset=Question.objects.all()))

        recommendations = get_recommendations(student_progress, lessons)
        return Response({'recommendations': recommendations})

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)