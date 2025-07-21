# learnflow_ai/django_backend/api/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, GENDER_CHOICES, QUESTION_TYPE_CHOICES, DIFFICULTY_CHOICES, SYNC_STATUS_CHOICES

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'is_staff') # Include is_staff for teacher distinction
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            'is_staff': {'read_only': True} # is_staff should not be set by user registration
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True) # Nested serializer for user info, read-only
    # Explicitly declare student_id_code to ensure it's always included in output
    student_id_code = serializers.CharField(read_only=True, allow_null=True) # Allow null if it can be null in model

    class Meta:
        model = Student
        fields = '__all__' # This should now correctly include student_id_code via explicit declaration
        read_only_fields = ('date_registered', 'last_device_sync',) # These are set by the server

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'uuid',)

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ('created_at', 'uuid',)

class QuizAttemptSerializer(serializers.ModelSerializer):
    # These fields will be sent from the client (Flutter app)
    # We use CharField for UUIDs and student_id_code as they come as strings
    question_uuid = serializers.CharField(write_only=True, required=True)
    student_id_code = serializers.CharField(write_only=True, required=True) # This is for receiving from client
    
    # Force uuid to be writable by explicitly declaring it
    uuid = serializers.UUIDField(required=True) # ADDED: Explicitly make UUID writable

    # These fields are read-only as they are resolved on the server side
    student_username = serializers.CharField(source='student.user.username', read_only=True)
    question_text_preview = serializers.CharField(source='question.question_text', read_only=True)

    class Meta:
        model = QuizAttempt
        fields = (
            'uuid', 'student', 'question', 'submitted_answer', 'is_correct', 'score',
            'ai_feedback_text', 'raw_ai_response', 'attempt_timestamp', 'synced_at',
            'sync_status', 'device_id',
            'question_uuid', 'student_id_code', # Write-only fields for client input
            'student_username', 'question_text_preview' # Read-only fields for server output
        )
        # REMOVED 'uuid' from read_only_fields. It is provided by the client.
        read_only_fields = ('synced_at', 'student', 'question') # student and question are resolved by view

    def create(self, validated_data):
        # Remove write-only fields before passing to model creation
        validated_data.pop('question_uuid')
        # student_id_code is handled in the view's bulk_upload logic
        validated_data.pop('student_id_code')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Remove write-only fields if present during update
        validated_data.pop('question_uuid', None)
        validated_data.pop('student_id_code', None)
        return super().update(instance, validated_data)


class StudentProgressSerializer(serializers.ModelSerializer):
    # Similar to QuizAttemptSerializer, client sends student_id_code
    student_id_code = serializers.CharField(write_only=True, required=True)
    student_username = serializers.CharField(source='student.user.username', read_only=True)

    class Meta:
        model = StudentProgress
        fields = '__all__'
        read_only_fields = ('last_updated', 'uuid', 'student') # student resolved by view

    def create(self, validated_data):
        validated_data.pop('student_id_code')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('student_id_code', None)
        return super().update(instance, validated_data)
