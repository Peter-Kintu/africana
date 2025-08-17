from rest_framework import viewsets
from rest_framework import permissions
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, Teacher, Book, Video
from .serializers import StudentSerializer, LessonSerializer, QuestionSerializer, QuizAttemptSerializer, StudentProgressSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
import re  # Import the regular expression module

# Placeholder for a viewset to handle user authentication, as imported in urls.py
class AuthViewSet(viewsets.ViewSet):
    # This is a placeholder. You'll need to implement the actual logic here.
    def list(self, request):
        return Response({"message": "Auth endpoint. Implement login/logout/registration logic here."})

class StudentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows students to be viewed or edited.
    """
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]

class LessonViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows lessons to be viewed or edited.
    """
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

class QuestionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows questions to be viewed or edited.
    """
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

class QuizAttemptViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows quiz attempts to be viewed or edited.
    """
    queryset = QuizAttempt.objects.all()
    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

class StudentProgressViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows student progress to be viewed or edited.
    """
    queryset = StudentProgress.objects.all()
    serializer_class = StudentProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

@login_required
def teacher_dashboard(request):
    """
    Render the teacher's dashboard page.
    """
    return render(request, 'teacher_dashboard.html')

# New views for the book store and video library
@login_required
def teacher_books(request):
    """
    Render the teacher's book publishing page.
    """
    # Use get_object_or_404 to handle cases where no Teacher object is found for the user
    teacher = get_object_or_404(Teacher, user=request.user.pk)
    books = Book.objects.filter(teacher=teacher).order_by('-published_date')
    context = {
        'books': books
    }
    return render(request, 'teacher_books.html', context)

@login_required
def publish_book(request):
    """
    Handle the form submission for publishing a new book.
    """
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        cover_image = request.FILES.get('cover_image')
        # Use get_object_or_404 with the user
        teacher = get_object_or_404(Teacher, user=request.user.pk)

        Book.objects.create(
            title=title,
            description=description,
            price=price,
            cover_image=cover_image,
            teacher=teacher
        )
        return redirect('teacher_books')
    return redirect('teacher_books')

@login_required
def video_page(request):
    """
    Render the video upload and library page.
    """
    # Use get_object_or_404 with the user
    teacher = get_object_or_404(Teacher, user=request.user.pk)
    videos = Video.objects.filter(teacher=teacher).order_by('-created_at')
    context = {
        'videos': videos
    }
    return render(request, 'video_page.html', context)

@login_required
def add_video(request):
    """
    Handle the form submission for adding a new video.
    """
    if request.method == 'POST':
        title = request.POST.get('title')
        url = request.POST.get('url')
        description = request.POST.get('description')
        
        # Extracts the YouTube video ID from the URL using a regular expression
        youtube_id_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&]+)', url)
        youtube_id = youtube_id_match.group(1) if youtube_id_match else None

        # Use get_object_or_404 with the user
        teacher = get_object_or_404(Teacher, user=request.user.pk)
        
        if youtube_id:
            Video.objects.create(
                title=title,
                url=url,
                description=description,
                youtube_id=youtube_id,
                teacher=teacher
            )
        return redirect('video_page')
    return redirect('video_page')


# I've added a placeholder view for the home page.
def home(request):
    """
    Placeholder home view.
    """
    return render(request, 'base.html')

# Placeholder functions for the AI and CSV export endpoints
@api_view(['POST'])
def ai_quiz_feedback(request):
    return Response({"message": "Placeholder for AI quiz feedback endpoint."})

@api_view(['POST'])
def ai_recommendations(request):
    return Response({"message": "Placeholder for AI recommendations endpoint."})

@api_view(['GET'])
def export_quiz_attempts_csv(request):
    return Response({"message": "Placeholder for CSV export endpoint."})
