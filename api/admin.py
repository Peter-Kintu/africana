# learnflow_ai/django_backend/api/admin.py

from django.contrib import admin
from django.utils.html import format_html
import json
import csv
from django.http import HttpResponse

from .models import Student, Lesson, Question, QuizAttempt, StudentProgress
from .forms import QuestionAdminForm

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id_code', 'grade_level', 'class_name', 'date_registered', 'last_device_sync')
    search_fields = ('user__username', 'student_id_code', 'grade_level', 'class_name')
    list_filter = ('grade_level', 'class_name', 'gender')
    raw_id_fields = ('user',)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'difficulty_level', 'version', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'subject')
    list_filter = ('subject', 'difficulty_level', 'version')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionAdminForm
    list_display = ('question_text', 'question_type', 'lesson', 'difficulty_level', 'created_at')
    search_fields = ('question_text', 'lesson__title')
    list_filter = ('question_type', 'difficulty_level', 'lesson')
    raw_id_fields = ('lesson',)

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'is_correct', 'score', 'attempt_timestamp')
    list_filter = ('is_correct', 'attempt_timestamp', 'student__grade_level', 'student__class_name', 'question__lesson__subject')
    search_fields = ('student__user__username', 'question__question_text', 'submitted_answer')
    raw_id_fields = ('student', 'question')

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'formatted_overall_progress', 'last_updated')
    search_fields = ('student__user__username',)
    raw_id_fields = ('student',)
    
    def formatted_overall_progress(self, obj):
        progress_data = obj.overall_progress_data
        if not progress_data:
            return "-"
        
        html = "<table>"
        html += "<tr><th>Lesson UUID</th><th>Status</th><th>Score Avg</th><th>Last Attempt</th></tr>"
        
        for lesson_uuid, data in progress_data.items():
            if not isinstance(data, dict):
                html += f"<tr><td>{lesson_uuid[:8]}...</td><td colspan='3'><span style='color: orange;'>Malformed lesson data</span></td></tr>"
                continue

            status = data.get('status', 'N/A')
            score_avg = data.get('score_avg', 'N/A')
            last_attempt_date = data.get('last_attempt_date', 'N/A')
            
            display_uuid = lesson_uuid[:8] + "..." if len(lesson_uuid) > 8 else lesson_uuid
            
            html += f"<tr><td>{display_uuid}</td><td>{status}</td><td>{score_avg}</td><td>{last_attempt_date}</td></tr>"
        
        html += "</table>"
        return format_html(html)

    formatted_overall_progress.short_description = 'Overall Progress'