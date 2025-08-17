from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
import uuid

# Custom User Model
class User(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='api_user_groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='api_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

# Gender and Question Type Choices
GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
)

QUESTION_TYPE_CHOICES = (
    ('MCQ', 'Multiple Choice Question'),
    ('TF', 'True/False'),
    ('OQ', 'Open Question'),
)

DIFFICULTY_CHOICES = (
    ('E', 'Easy'),
    ('M', 'Medium'),
    ('H', 'Hard'),
)

# Student Model
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    parent_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

# Teacher Model
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    subject = models.CharField(max_length=100)
    institution = models.CharField(max_length=100)
    temp_field = models.CharField(max_length=10, blank=True, null=True) # TEMPORARY LINE
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username



# Lesson Model
class Lesson(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='lessons')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# Question Model
class Question(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=3, choices=QUESTION_TYPE_CHOICES, default='MCQ')
    options = models.JSONField(null=True, blank=True)  # Used for MCQ
    correct_answer = models.CharField(max_length=255)
    difficulty = models.CharField(max_length=1, choices=DIFFICULTY_CHOICES, default='E')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text[:50]

# Quiz Attempt Model
class QuizAttempt(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='attempts')
    is_correct = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.username}'s attempt on {self.question.lesson.title}"

# Student Progress Model
class StudentProgress(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    lessons_completed = models.ManyToManyField(Lesson, related_name='completed_by_students', blank=True)
    overall_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    overall_progress_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.student.user.username}'s Progress"

# Book Model
class Book(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    cover_image = models.ImageField(upload_to='book_covers/')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='books')
    published_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# Updated Video Model to support file uploads
class Video(models.Model):
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='videos/')
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='videos')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title