# learnflow_ai/django_backend/api/models.py

from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone

try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]

QUESTION_TYPE_CHOICES = [
    ('MCQ', 'Multiple Choice Question'),
    ('SA', 'Short Answer'),
]

DIFFICULTY_CHOICES = [
    ('Easy', 'Easy'),
    ('Medium', 'Medium'),
    ('Hard', 'Hard'),
]

class Student(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    student_id_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    grade_level = models.CharField(max_length=50, blank=True, null=True)
    class_name = models.CharField(max_length=50, blank=True, null=True)
    date_registered = models.DateTimeField(auto_now_add=True)
    last_device_sync = models.DateTimeField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    school_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.username

class Lesson(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100, blank=True, null=True)
    difficulty_level = models.CharField(max_length=50, choices=DIFFICULTY_CHOICES, default='Medium')
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    lesson_file = models.FileField(upload_to='lessons/', blank=True, null=True)
    prerequisites = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='MCQ')
    options = models.JSONField(default=list, blank=True, null=True, help_text="List of options for MCQ, stored as JSON array.")
    correct_answer_text = models.CharField(max_length=255)
    difficulty_level = models.CharField(max_length=50, choices=DIFFICULTY_CHOICES, default='Medium')
    expected_time_seconds = models.IntegerField(default=60, help_text="Expected time to answer in seconds")
    ai_generated_feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Q: {self.question_text[:50]}..."

class QuizAttempt(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='quiz_attempts')
    submitted_answer = models.TextField()
    is_correct = models.BooleanField()
    score = models.FloatField(default=0.0)
    ai_feedback_text = models.TextField(blank=True, null=True)
    raw_ai_response = models.JSONField(default=dict, blank=True, null=True)
    attempt_timestamp = models.DateTimeField(default=timezone.now)
    device_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID of the device where the attempt was made.")

    def __str__(self):
        return f"Attempt by {self.student.user.username} on {self.question.question_text[:20]}..."

class StudentProgress(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='progress')
    overall_progress_data = models.JSONField(default=dict,
                                             help_text="Aggregated progress data per lesson/topic.")
    last_updated = models.DateTimeField(auto_now=True,
                                        help_text="Timestamp when this progress record was last updated on the server.")

    class Meta:
        verbose_name_plural = "Student Progress"

    def __str__(self):
        return f"Progress for {self.student.user.username}"