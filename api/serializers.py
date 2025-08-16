# learnflow_ai/django_backend/api/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Student, Teacher, Lesson, Question, QuizAttempt, StudentProgress
import json

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'is_staff')
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
        }

    def create(self, validated_data):
        is_staff = validated_data.pop('is_staff', False)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            is_staff=is_staff
        )
        return user

class AuthSerializer(serializers.ModelSerializer):
    is_teacher = serializers.SerializerMethodField()
    is_student = serializers.SerializerMethodField()
    teacher_uuid = serializers.SerializerMethodField()
    student_uuid = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_teacher', 'is_student', 'teacher_uuid', 'student_uuid')

    def get_is_teacher(self, obj):
        return hasattr(obj, 'teacher')

    def get_is_student(self, obj):
        return hasattr(obj, 'student')

    def get_teacher_uuid(self, obj):
        return getattr(obj.teacher, 'uuid', None)

    def get_student_uuid(self, obj):
        return getattr(obj.student, 'uuid', None)

class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Student
        fields = '__all__'

class TeacherSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Teacher
        fields = '__all__'

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = '__all__'

class StudentProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProgress
        fields = '__all__'