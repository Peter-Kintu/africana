# learnflow_ai/django_backend/api/models.py

from django.db import models
from django.conf import settings # To link to Django's built-in User model
import uuid # For unique IDs
from django.utils import timezone

# Fallback for JSONField if not using PostgreSQL (e.g., SQLite in development)
try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField # This would require psycopg2

# Choices for various fields
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

SYNC_STATUS_CHOICES = [
    ('PENDING', 'Pending Sync'),
    ('SYNCED', 'Synced'),
    ('CONFLICT', 'Conflict'), # For future conflict resolution
]

class Student(models.Model):
    # Link to Django's built-in User model for authentication and basic user info
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    # A unique code for the student, e.g., generated in-app or by teacher for easy identification
    student_id_code = models.CharField(max_length=50, unique=True, blank=True, null=True,
                                       help_text="A unique code for the student, e.g., generated in-app or by teacher.")
    date_registered = models.DateTimeField(auto_now_add=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    grade_level = models.CharField(max_length=50, blank=True, null=True,
                                   help_text="e.g., 'Primary 5', 'Secondary 2'")
    class_name = models.CharField(max_length=100, blank=True, null=True,
                                  help_text="e.g., 'Class A', 'Morning Session'")
    school_name = models.CharField(max_length=255, blank=True, null=True)
    # Last time data was pushed from this student's device
    last_device_sync = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.student_id_code or 'N/A'})"

class Lesson(models.Model):
    # This represents a 'module' or a 'lesson pack' that can be downloaded
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100, blank=True, null=True,
                               help_text="e.g., 'Mathematics', 'Science', 'English'")
    difficulty_level = models.CharField(max_length=50, choices=DIFFICULTY_CHOICES, default='Medium')
    # Prerequisites can be a list of lesson UUIDs or topic names
    prerequisites = models.JSONField(blank=True, null=True,
                                     help_text="JSON array of prerequisite lesson UUIDs or topic names.")
    # File field to store the actual lesson content (e.g., a ZIP file with JSON/HTML/PDFs)
    lesson_file = models.FileField(upload_to='lessons/', blank=True, null=True,
                                   help_text="Upload a ZIP file containing lesson content (e.g., JSON, HTML, images).")
    version = models.IntegerField(default=1, help_text="Version number for content updates.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subject', 'title', 'version'] # Order for easier content management

    def __str__(self):
        return f"{self.title} (v{self.version}) - {self.subject or 'N/A'}"

class Question(models.Model):
    # Individual question within a lesson/quiz
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPE_CHOICES)
    # For MCQs, store options as a JSON field (e.g., ["Option A", "Option B"])
    options = models.JSONField(blank=True, null=True,
                               help_text="JSON array of options for MCQ type questions.")
    # For MCQs, store correct answer text. For SA, this can be keywords/ideal answer for AI.
    correct_answer_text = models.TextField(blank=True, null=True,
                                           help_text="For MCQ: exact correct option text. For SA: ideal answer/keywords for AI.")
    difficulty_level = models.CharField(max_length=50, choices=DIFFICULTY_CHOICES, default='Medium')
    expected_time_seconds = models.IntegerField(blank=True, null=True,
                                                help_text="Estimated time a student should take to answer (in seconds).")
    # NEW FIELD ADDED HERE: ai_generated_feedback
    ai_generated_feedback = models.TextField(blank=True, null=True,
                                             help_text="AI-generated general feedback/explanation for the question.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Added updated_at for consistency

    class Meta:
        ordering = ['lesson', 'created_at'] # Order questions within a lesson

    def __str__(self):
        return f"Q: {self.question_text[:50]}... ({self.lesson.title})"

class QuizAttempt(models.Model):
    # Records a student's attempt at a question
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    submitted_answer = models.TextField()
    # AI's initial grading. Null until graded.
    is_correct = models.BooleanField(null=True, blank=True,
                                     help_text="True if AI/Teacher marked correct, False if incorrect, Null if ungraded.")
    # AI's score for short answers (e.g., 0.0 to 1.0)
    score = models.FloatField(null=True, blank=True,
                              help_text="Score for short answer questions (e.g., 0.0 to 1.0).")
    # AI's textual feedback/suggestion
    ai_feedback_text = models.TextField(blank=True, null=True,
                                        help_text="Textual feedback from AI (e.g., 'Review algebra basics').")
    # Raw JSON response from AI model (for debugging/detailed analysis)
    raw_ai_response = models.JSONField(blank=True, null=True,
                                       help_text="Raw JSON output from the on-device AI model.")
    attempt_timestamp = models.DateTimeField(default=timezone.now,
                                            help_text="Timestamp when the attempt was made on the device.")
    # When this record was successfully synced to the server
    synced_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Status for offline sync management
    sync_status = models.CharField(max_length=10, choices=SYNC_STATUS_CHOICES, default='PENDING', db_index=True)
    # Unique ID of the device that made the attempt (for multi-device sync)
    device_id = models.CharField(max_length=255, blank=True, null=True,
                                 help_text="Unique identifier for the student's device.")

    class Meta:
        ordering = ['-attempt_timestamp'] # Latest attempts first
        # Add a unique constraint to prevent duplicate attempts from the same device for the same question
        # This might need refinement for multiple attempts on the same question
        # unique_together = ('student', 'question', 'attempt_timestamp', 'device_id')


    def __str__(self):
        return f"{self.student.user.username} - Q{self.question.uuid.hex[:8]} - {self.sync_status}"

class StudentProgress(models.Model):
    # Aggregate progress per student across all lessons/topics
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='overall_progress')
    # Structured JSON field to store detailed progress per lesson/topic
    # Example:
    # {
    #   "lesson_uuid_1": {
    #     "status": "completed", # "started", "completed"
    #     "score_avg": 85.5,
    #     "mcq_correct_count": 10,
    #     "sa_avg_score": 0.75,
    #     "last_attempt_date": "2024-07-30T10:00:00Z",
    #     "recommendations": ["review_topic_A", "next_lesson_B"]
    #   },
    #   "lesson_uuid_2": { ... }
    # }
    overall_progress_data = models.JSONField(default=dict,
                                             help_text="Aggregated progress data per lesson/topic.")
    last_updated = models.DateTimeField(auto_now=True,
                                        help_text="Timestamp when this progress record was last updated on the server.")

    class Meta:
        verbose_name_plural = "Student Progress" # Better name in admin

    def __str__(self):
        return f"Progress for {self.student.user.username}"

# NEW MODEL: Wallet
class Wallet(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='wallet')
    address = models.CharField(max_length=42, unique=True, help_text="Ethereum wallet address (0x...)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.student.user.username}: {self.address}"
