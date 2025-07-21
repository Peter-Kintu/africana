# learnflow_ai/django_backend/api/admin.py

from django.contrib import admin
from .models import Student, Lesson, Question, QuizAttempt, StudentProgress
from .forms import QuestionAdminForm # NEW: Import the custom form

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id_code', 'grade_level', 'class_name', 'date_registered', 'last_device_sync')
    search_fields = ('user__username', 'student_id_code', 'grade_level', 'class_name')
    list_filter = ('grade_level', 'class_name', 'gender')
    raw_id_fields = ('user',) # Use a raw ID input for ForeignKey to User

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'difficulty_level', 'version', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'subject')
    list_filter = ('subject', 'difficulty_level', 'version')
    # REMOVED: prepopulated_fields = {'uuid': ('title',)}

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionAdminForm # NEW: Tell Django admin to use our custom form
    list_display = ('question_text', 'lesson', 'question_type', 'difficulty_level', 'created_at')
    search_fields = ('question_text', 'lesson__title')
    list_filter = ('lesson', 'question_type', 'difficulty_level')
    raw_id_fields = ('lesson',) # Use a raw ID input for ForeignKey to Lesson
    # We explicitly define fieldsets to control the order and inclusion of fields.
    # The 'options' field from the model is implicitly handled by the form's clean() method.
    fieldsets = (
        (None, {
            'fields': (
                'lesson',
                'question_text',
                'question_type',
                'option_a', # These are the custom fields from QuestionAdminForm
                'option_b',
                'option_c',
                'option_d',
                'correct_answer_text',
                'difficulty_level',
                'expected_time_seconds',
                # The actual 'options' JSONField is hidden by the form
            )
        }),
    )

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'submitted_answer', 'is_correct', 'score', 'attempt_timestamp', 'synced_at', 'sync_status', 'device_id')
    search_fields = ('student__user__username', 'question__question_text', 'submitted_answer', 'device_id')
    list_filter = ('is_correct', 'sync_status', 'attempt_timestamp', 'synced_at')
    raw_id_fields = ('student', 'question')

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'last_updated')
    search_fields = ('student__user__username',)
    raw_id_fields = ('student',)
