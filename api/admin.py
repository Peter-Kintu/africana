from django.contrib import admin
from django.utils.html import format_html
import json
import csv
from django.http import HttpResponse

from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, Teacher, Book, Video
# Import all three custom forms
from .forms import QuestionAdminForm, TeacherAdminForm, StudentAdminForm

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm  # Use the custom form
    list_display = ('user', 'gender', 'grade', 'parent_email', 'created_at', 'updated_at')
    search_fields = ('user__username', 'gender', 'grade', 'parent_email')
    list_filter = ('gender', 'grade')
    # The form now handles the dropdown, so raw_id_fields is not needed here
    # raw_id_fields = ('user',)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    form = TeacherAdminForm  # Use the custom form
    list_display = ('user', 'subject', 'institution', 'created_at', 'updated_at')
    search_fields = ('user__username', 'subject', 'institution')
    list_filter = ('subject', 'institution')
    # The form now handles the dropdown, so raw_id_fields is not needed here

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'created_at')
    search_fields = ('title', 'description', 'teacher__user__username')
    list_filter = ('teacher',)
    raw_id_fields = ('teacher',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionAdminForm
    list_display = ('question_text', 'question_type', 'lesson', 'difficulty', 'created_at')
    search_fields = ('question_text', 'lesson__title')
    list_filter = ('question_type', 'difficulty', 'lesson')
    raw_id_fields = ('lesson',)

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'is_correct', 'attempted_at')
    list_filter = ('is_correct', 'attempted_at', 'student__grade', 'question__lesson__title')
    search_fields = ('student__user__username', 'question__question_text')
    raw_id_fields = ('student', 'question')
    date_hierarchy = 'attempted_at'

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'overall_score', 'overall_progress_data')
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