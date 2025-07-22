# learnflow_ai/django_backend/api/admin.py

from django.contrib import admin
from django.utils.html import format_html # Import format_html for rendering HTML
import json # Import json for parsing JSON strings
import csv # Import csv for CSV export
from django.http import HttpResponse # Import HttpResponse for serving files

# ADDED: Import Wallet model
from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, Wallet
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
    # REMOVED: prepopulated_fields = {'uuid': ('title',)}\

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionAdminForm # NEW: Tell Django admin to use our custom form
    list_display = ('question_text', 'lesson', 'question_type', 'difficulty_level', 'created_at')
    search_fields = ('question_text', 'lesson__title', 'question_type', 'difficulty_level')
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

# Define the admin action function outside the ModelAdmin class
def export_selected_quiz_attempts_csv(modeladmin, request, queryset):
    """
    Admin action to export selected quiz attempts to a CSV file.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="selected_quiz_attempts_report.csv"'

    writer = csv.writer(response)
    
    # Define CSV header row
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
        'Sync Status',
        'Device ID'
    ])

    # Fetch data with select_related for efficient joining
    # Use the provided queryset (selected items)
    for attempt in queryset.select_related('student__user', 'question__lesson').order_by('attempt_timestamp'):
        writer.writerow([
            str(attempt.uuid), # Convert UUID to string
            attempt.student.user.username,
            attempt.student.student_id_code,
            attempt.question.lesson.title if attempt.question.lesson else 'N/A', # Handle potential null lesson
            attempt.question.question_type,
            attempt.submitted_answer,
            'Yes' if attempt.is_correct else 'No', # Human-readable boolean
            attempt.score,
            attempt.ai_feedback_text if attempt.ai_feedback_text else '', # Handle null feedback
            attempt.attempt_timestamp.isoformat(), # ISO format for timestamp
            attempt.sync_status,
            attempt.device_id if attempt.device_id else ''
        ])
    return response

# Set a short description for the action, which will appear in the dropdown
export_selected_quiz_attempts_csv.short_description = "Export selected quiz attempts to CSV"


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'submitted_answer', 'is_correct', 'score', 'attempt_timestamp', 'synced_at', 'sync_status', 'device_id')
    search_fields = ('student__user__username', 'question__question_text', 'submitted_answer', 'device_id')
    list_filter = ('is_correct', 'sync_status', 'attempt_timestamp', 'synced_at')
    raw_id_fields = ('student', 'question')
    actions = [export_selected_quiz_attempts_csv] # REGISTER THE ACTION HERE


@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'last_updated', 'formatted_overall_progress') # Changed to use custom method
    search_fields = ('student__user__username',)
    list_filter = ('last_updated',)
    raw_id_fields = ('student',)

    def formatted_overall_progress(self, obj):
        """
        Displays the overall_progress_data JSONField in a more readable format.
        Ensures the data is treated as a dictionary, handling potential non-dict values.
        """
        progress_data = obj.overall_progress_data
        
        # If it's a string, try to parse it as JSON
        if isinstance(progress_data, str):
            try:
                progress_data = json.loads(progress_data)
            except json.JSONDecodeError:
                # If it's a string but not valid JSON, display it as an error
                return format_html(f"<span style='color: red;'>Invalid JSON string: {progress_data}</span>")
        
        # If it's not a dictionary (e.g., it was an int, or parsing failed), treat as empty dict
        if not isinstance(progress_data, dict):
            # Display the raw value if it's not a dict, for debugging
            return format_html(f"<span style='color: orange;'>Unexpected data type: {type(progress_data).__name__} - {progress_data}</span>")
        
        if not progress_data:
            return "-"
        
        html = "<table>"
        html += "<tr><th>Lesson UUID</th><th>Status</th><th>Score Avg</th><th>Last Attempt</th></tr>"
        
        for lesson_uuid, data in progress_data.items(): # Now safe to call .items()
            # Ensure 'data' is a dictionary too, as nested JSON can also be malformed
            if not isinstance(data, dict):
                html += f"<tr><td>{lesson_uuid[:8]}...</td><td colspan='3'><span style='color: orange;'>Malformed lesson data</span></td></tr>"
                continue

            status = data.get('status', 'N/A')
            score_avg = data.get('score_avg', 'N/A')
            last_attempt_date = data.get('last_attempt_date', 'N/A')
            
            # Truncate UUID for display
            display_uuid = lesson_uuid[:8] + "..." if len(lesson_uuid) > 8 else lesson_uuid
            
            html += f"<tr><td>{display_uuid}</td><td>{status}</td><td>{score_avg}</td><td>{last_attempt_date}</td></tr>"
        
        html += "</table>"
        return format_html(html)

    formatted_overall_progress.short_description = 'Overall Progress' # Column header in admin

# NEW: Register Wallet model in admin
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('student', 'address', 'created_at')
    search_fields = ('student__user__username', 'address')
    raw_id_fields = ('student',)
    readonly_fields = ('created_at', 'updated_at')

