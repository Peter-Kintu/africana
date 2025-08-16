# learnflow_ai/django_backend/api/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Teacher, Lesson, Question, QuizAttempt, StudentProgress
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

class AuthSerializer(serializers.ModelSerializer):
    is_teacher = serializers.SerializerMethodField()
    is_student = serializers.SerializerMethodField()
    teacher_uuid = serializers.Serializer