# learnflow_ai/django_backend/api/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
# ADDED: Import Wallet model
from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, Wallet, GENDER_CHOICES, QUESTION_TYPE_CHOICES, DIFFICULTY_CHOICES, SYNC_STATUS_CHOICES

class UserSerializer(serializers.ModelSerializer):
    # is_staff should be writable for registration, but read-only for general updates
    is_staff = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'is_staff') # Include is_staff for teacher distinction
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            # 'is_staff': {'read_only': True} # Removed read_only to allow setting during registration
        }

    def create(self, validated_data):
        # Pop is_staff to handle it separately
        is_staff = validated_data.pop('is_staff', False)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            is_staff=is_staff # Set is_staff based on validated data
        )
        return user

# NEW: Wallet Serializer
class WalletSerializer(serializers.ModelSerializer):
    student_id = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), source='student', write_only=True, required=False) # For linking to student if not current user

    class Meta:
        model = Wallet
        fields = ['id', 'student', 'address', 'created_at', 'updated_at', 'student_id']
        read_only_fields = ['id', 'student', 'created_at', 'updated_at'] # student is set by view

class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True) # Nested serializer for user info, read-only
    student_id_code = serializers.CharField(read_only=True, allow_null=True)
    # NEW: Nested WalletSerializer to include wallet details
    wallet = WalletSerializer(read_only=True) # Read-only nested wallet

    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ('date_registered', 'last_device_sync',)

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'uuid',)

class QuestionSerializer(serializers.ModelSerializer):
    # lesson_uuid is a write-only field for input, not part of the model
    lesson_uuid = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ('created_at', 'uuid',)

    def create(self, validated_data):
        lesson_uuid = validated_data.pop('lesson_uuid', None)
        if lesson_uuid:
            try:
                lesson = Lesson.objects.get(uuid=lesson_uuid)
                validated_data['lesson'] = lesson
            except Lesson.DoesNotExist:
                raise serializers.ValidationError({"lesson_uuid": "Lesson with this UUID does not exist."})
        return super().create(validated_data)

class QuizAttemptSerializer(serializers.ModelSerializer):
    question_uuid = serializers.CharField(write_only=True, required=True)
    student_id_code = serializers.CharField(write_only=True, required=True)
    
    # Explicitly make UUID writable as it comes from the client
    uuid = serializers.UUIDField(required=True)

    student_username = serializers.CharField(source='student.user.username', read_only=True)
    question_text_preview = serializers.CharField(source='question.question_text', read_only=True)

    class Meta:
        model = QuizAttempt
        fields = (
            'uuid', 'student', 'question', 'submitted_answer', 'is_correct', 'score',
            'ai_feedback_text', 'raw_ai_response', 'attempt_timestamp', 'synced_at',
            'sync_status', 'device_id',
            'question_uuid', 'student_id_code',
            'student_username', 'question_text_preview'
        )
        read_only_fields = ('synced_at', 'student', 'question')

    def create(self, validated_data):
        validated_data.pop('question_uuid')
        validated_data.pop('student_id_code')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('question_uuid', None)
        validated_data.pop('student_id_code', None)
        return super().update(instance, validated_data)

class StudentProgressSerializer(serializers.ModelSerializer):
    student_id_code = serializers.CharField(write_only=True, required=True)
    student_username = serializers.CharField(source='student.user.username', read_only=True)

    class Meta:
        model = StudentProgress
        fields = '__all__'
        read_only_fields = ('last_updated', 'uuid', 'student')

    def create(self, validated_data):
        validated_data.pop('student_id_code')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('student_id_code', None)
        return super().update(instance, validated_data)

