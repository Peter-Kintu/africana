# learnflow_ai/django_backend/api/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, GENDER_CHOICES, QUESTION_TYPE_CHOICES, DIFFICULTY_CHOICES
import json

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

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'

    def create(self, validated_data):
        user_id = validated_data.pop('user_id', None)
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                validated_data['user'] = user
            except User.DoesNotExist:
                raise serializers.ValidationError({"user_id": "User with this ID does not exist."})
        return super().create(validated_data)

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    lesson_uuid = serializers.PrimaryKeyRelatedField(
        queryset=Lesson.objects.all(),
        source='lesson',
        write_only=True
    )
    
    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ('lesson',)

class QuizAttemptSerializer(serializers.ModelSerializer):
    student_user_id = serializers.IntegerField(write_only=True)
    question_uuid = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(),
        source='question',
        write_only=True
    )

    class Meta:
        model = QuizAttempt
        fields = '__all__'
        read_only_fields = ('student', 'question')
    
    def create(self, validated_data):
        student_user_id = validated_data.pop('student_user_id', None)
        question_uuid = validated_data.pop('question', None)

        if not student_user_id:
            raise serializers.ValidationError({"student_user_id": "This field is required."})

        if not question_uuid:
            raise serializers.ValidationError({"question_uuid": "This field is required."})

        try:
            student = Student.objects.get(user__id=student_user_id)
        except Student.DoesNotExist:
            raise serializers.ValidationError({"student_user_id": "Student with this user ID does not exist."})

        try:
            question = Question.objects.get(uuid=question_uuid.uuid)
        except Question.DoesNotExist:
            raise serializers.ValidationError({"question_uuid": "Question with this UUID does not exist."})

        validated_data['student'] = student
        validated_data['question'] = question

        return super().create(validated_data)

class StudentProgressSerializer(serializers.ModelSerializer):
    student_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = StudentProgress
        fields = '__all__'
        read_only_fields = ('student',)

    def create(self, validated_data):
        student_user_id = validated_data.pop('student_user_id', None)
        if student_user_id:
            try:
                student = Student.objects.get(user__id=student_user_id)
                validated_data['student'] = student
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student_user_id": "Student with this user ID does not exist."})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        overall_progress_data = validated_data.get('overall_progress_data')
        if overall_progress_data and isinstance(overall_progress_data, str):
            try:
                validated_data['overall_progress_data'] = json.loads(overall_progress_data)
            except json.JSONDecodeError:
                raise serializers.ValidationError({"overall_progress_data": "Invalid JSON format for overall_progress_data."})
        
        return super().update(instance, validated_data)