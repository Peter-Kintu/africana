# learnflow_ai/django_backend/api/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, Wallet, GENDER_CHOICES, QUESTION_TYPE_CHOICES, DIFFICULTY_CHOICES, SYNC_STATUS_CHOICES

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
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False) # For linking existing user

    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ('user',) # user field is handled by nested serializer/user_id

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    # THIS IS THE CRUCIAL LINE: It tells Django to include the UUID of the related lesson.
    lesson_uuid = serializers.CharField(source='lesson.uuid', read_only=True)

    class Meta:
        model = Question
        fields = (
            'uuid', 'lesson', 'lesson_uuid', 'question_text', 'question_type',
            'options', 'correct_answer_text', 'difficulty_level',
            'expected_time_seconds', 'ai_generated_feedback', 'created_at'
        )
        # Make 'lesson' (the integer ID) write-only so it's not included in read responses
        # but can still be used for creating/updating questions.
        extra_kwargs = {
            'lesson': {'write_only': True, 'required': False}
        }


class QuizAttemptSerializer(serializers.ModelSerializer):
    # Explicitly define uuid to ensure it's writable and handled
    # This overrides the default ModelSerializer behavior for primary key UUIDs
    uuid = serializers.CharField(required=True) # Make it required as Flutter sends it

    # To display related info for dashboard
    question_text_preview = serializers.CharField(source='question.question_text', read_only=True)
    lesson_title = serializers.CharField(source='question.lesson.title', read_only=True) # Added for dashboard
    student_username = serializers.CharField(source='student.user.username', read_only=True) # Added for dashboard

    # For bulk upload, allow providing UUIDs instead of objects
    question_uuid = serializers.CharField(write_only=True, required=False) # Used for creating/linking
    student_id_code = serializers.CharField(write_only=True, required=False) # Used for creating/linking

    class Meta:
        model = QuizAttempt
        fields = (
            'uuid', 'student', 'question', 'submitted_answer', 'is_correct', 'score',
            'ai_feedback_text', 'raw_ai_response', 'attempt_timestamp', 'synced_at',
            'sync_status', 'device_id',
            'question_uuid', 'student_id_code', # These are write_only or for data linking
            'student_username', 'question_text_preview', 'lesson_title' # These are read_only
        )
        # student and question will be resolved from UUIDs/ID code in create/update
        read_only_fields = ('synced_at', 'student', 'question') 

    def create(self, validated_data):
        # Pop uuid first, as it's a special field (primary key from client)
        quiz_attempt_uuid = validated_data.pop('uuid') # Get the UUID from validated data

        # Resolve Question and Student from UUIDs/ID codes
        question_uuid = validated_data.pop('question_uuid', None)
        student_id_code = validated_data.pop('student_id_code', None)

        if question_uuid:
            try:
                validated_data['question'] = Question.objects.get(uuid=question_uuid)
            except Question.DoesNotExist:
                raise serializers.ValidationError({"question_uuid": "Question with this UUID does not exist."})

        if student_id_code:
            try:
                validated_data['student'] = Student.objects.get(student_id_code=student_id_code)
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student_id_code": "Student with this ID code does not exist."})

        # Ensure that both student and question are resolved before creating
        if 'student' not in validated_data or 'question' not in validated_data:
            raise serializers.ValidationError("Both student and question must be provided or resolvable.")

        # Create the QuizAttempt instance, explicitly passing the UUID
        instance = QuizAttempt.objects.create(uuid=quiz_attempt_uuid, **validated_data)
        return instance

    def update(self, instance, validated_data):
        # Prevent updates to question_uuid or student_id_code after creation
        validated_data.pop('question_uuid', None)
        validated_data.pop('student_id_code', None)
        # Also prevent update to uuid if it's considered immutable after creation
        validated_data.pop('uuid', None) # UUID should not be updated after creation
        return super().update(instance, validated_data)


class StudentProgressSerializer(serializers.ModelSerializer):
    student_id_code = serializers.CharField(write_only=True, required=True)
    student_username = serializers.CharField(source='student.user.username', read_only=True)

    class Meta:
        model = StudentProgress
        fields = '__all__'
        read_only_fields = ('last_updated', 'uuid', 'student')

    def create(self, validated_data):
        student_id_code = validated_data.pop('student_id_code')
        try:
            student = Student.objects.get(student_id_code=student_id_code)
        except Student.DoesNotExist:
            raise serializers.ValidationError({"student_id_code": "Student with this ID code does not exist."})

        if StudentProgress.objects.filter(student=student).exists():
            raise serializers.ValidationError("Student progress for this student already exists. Use PUT to update.")

        validated_data['student'] = student
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('student_id_code', None) # student_id_code is write_only and not for update
        return super().update(instance, validated_data)

class WalletSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), required=False) # Make optional for update
    student_user_id = serializers.IntegerField(write_only=True, required=False) # New field to receive student ID from Flutter

    class Meta:
        model = Wallet
        fields = '__all__'
        read_only_fields = ('student',) # student field is handled by student_user_id on write

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
        validated_data.pop('student_user_id', None) # Not used for update
        return super().update(instance, validated_data)
