# learnflow_ai/django_backend/api/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, Wallet, GENDER_CHOICES, QUESTION_TYPE_CHOICES, DIFFICULTY_CHOICES, SYNC_STATUS_CHOICES
import json # Ensure json is imported for parsing JSONField

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
        fields = '__all__'  # or explicitly add 'uuid' if you use a list

    def create(self, validated_data):
        user_id = validated_data.pop('user_id', None)
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                validated_data['user'] = user
            except User.DoesNotExist:
                raise serializers.ValidationError({"user_id": "User with this ID does not exist."})
        
        # Ensure student_id_code is unique if provided
        student_id_code = validated_data.get('student_id_code')
        if student_id_code and Student.objects.filter(student_id_code=student_id_code).exists():
            raise serializers.ValidationError({"student_id_code": "Student with this ID code already exists."})

        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('user_id', None) # user_id is write_only and not for update
        return super().update(instance, validated_data)

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class QuestionSerializer(serializers.ModelSerializer):
    # This field is for receiving the UUID from Flutter
    lesson_uuid = serializers.CharField(source='lesson.uuid', write_only=True, required=True)
    # This field is for sending the title back (read-only)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)

    class Meta:
        model = Question
        # Explicitly list all fields that should be part of the API,
        # but exclude the direct 'lesson' foreign key field from input.
        # 'lesson_uuid' handles the input for the lesson relationship.
        fields = [
            'uuid', 'lesson_uuid', 'lesson_title', 'question_text',
            'question_type', 'options', 'correct_answer_text',
            'difficulty_level', 'expected_time_seconds', 'ai_generated_feedback',
            'created_at', 'updated_at'
        ]
        read_only_fields = (
            'created_at', 'updated_at', 'ai_generated_feedback', 'lesson_title'
        )

    def create(self, validated_data):
        # Pop the nested 'lesson' dictionary which contains 'uuid'
        lesson_data = validated_data.pop('lesson')
        lesson_uuid = lesson_data['uuid'] # Extract lesson_uuid from the popped data
        
        try:
            lesson = Lesson.objects.get(uuid=lesson_uuid)
        except Lesson.DoesNotExist:
            raise serializers.ValidationError({"lesson_uuid": "Lesson with this UUID does not exist."})
        
        # Create the Question instance, associating it with the found Lesson object
        question = Question.objects.create(lesson=lesson, **validated_data)
        return question

    def update(self, instance, validated_data):
        if 'lesson' in validated_data:
            lesson_data = validated_data.pop('lesson')
            lesson_uuid = lesson_data['uuid']
            try:
                lesson = Lesson.objects.get(uuid=lesson_uuid)
                instance.lesson = lesson
            except Lesson.DoesNotExist:
                raise serializers.ValidationError({"lesson_uuid": "Lesson with this UUID does not exist."})
        return super().update(instance, validated_data)


class QuizAttemptSerializer(serializers.ModelSerializer):
    # CRITICAL FIX: Explicitly define UUID as a CharField for input/output
    uuid = serializers.CharField(max_length=36, required=True)
    
    # student_id_code is used for linking student, but not a direct model field
    student_id_code = serializers.CharField(write_only=True, required=False, allow_null=True)
    
    # Ensure question_uuid is handled correctly for input/output
    question_uuid = serializers.CharField(source='question.uuid', write_only=True, required=True)
    
    # Add read-only fields for display in API responses if needed (e.g., in bulk upload success)
    lesson_title = serializers.CharField(source='question.lesson.title', read_only=True, allow_null=True)
    question_text_preview = serializers.CharField(source='question.question_text', read_only=True, allow_null=True)

    class Meta:
        model = QuizAttempt
        # Explicitly list fields, ensuring 'student' and 'question' FKs are not expected as direct input.
        # 'student_id_code' and 'question_uuid' handle their respective relationships.
        fields = [
            'uuid', 'student_id_code', 'question_uuid', 'submitted_answer',
            'is_correct', 'score', 'ai_feedback_text', 'raw_ai_response',
            'attempt_timestamp', 'synced_at', 'sync_status', 'device_id',
            'lesson_title', 'question_text_preview',
            # Include 'student' and 'question' for read operations (output), but they are read-only
            'student',
            'question'
        ]
        read_only_fields = (
            'synced_at', 'sync_status', 'ai_feedback_text', 'raw_ai_response',
            'lesson_title', 'question_text_preview',
            'student', # Make student read-only as it's set in create based on student_id_code/user
            'question' # Make question read-only as it's set in create based on question_uuid
        )

    def create(self, validated_data):
        student_id_code = validated_data.pop('student_id_code', None)
        # Pop the nested 'question' dictionary which contains 'uuid'
        question_data = validated_data.pop('question')
        question_uuid = question_data['uuid'] # Extract question_uuid from the popped data

        student = None
        if student_id_code:
            try:
                student = Student.objects.get(student_id_code=student_id_code)
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student_id_code": "Student with this ID code does not exist."})
        elif self.context and 'request' in self.context and self.context['request'].user.is_authenticated:
            try:
                student = Student.objects.get(user=self.context['request'].user)
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student": "No student profile found for the current user."})
        
        if not student:
            raise serializers.ValidationError({"student": "Student could not be identified for this quiz attempt."})

        try:
            question = Question.objects.get(uuid=question_uuid)
        except Question.DoesNotExist:
            raise serializers.ValidationError({"question_uuid": "Question with this UUID does not exist."})

        quiz_attempt_uuid = validated_data.pop('uuid') # Pop the UUID field
        
        quiz_attempt = QuizAttempt.objects.create(
            uuid=quiz_attempt_uuid, # Assign the client-provided UUID
            student=student,
            question=question,
            **validated_data
        )
        return quiz_attempt

    def update(self, instance, validated_data):
        # Prevent updating immutable fields if they are passed in validated_data
        validated_data.pop('uuid', None) # UUID should not be updated after creation
        validated_data.pop('student_id_code', None) # Not used for update
        if 'question' in validated_data:
            validated_data.pop('question') # Question should not be updated after creation

        return super().update(instance, validated_data)


class StudentProgressSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), required=False)
    student_id_code = serializers.CharField(write_only=True, required=False, allow_null=True) # For linking student by ID code

    class Meta:
        model = StudentProgress
        fields = '__all__'
        read_only_fields = ('last_updated',) # last_updated is auto_now

    def create(self, validated_data):
        student_id_code = validated_data.pop('student_id_code', None)
        student_instance = validated_data.get('student', None)

        if student_id_code:
            try:
                student = Student.objects.get(student_id_code=student_id_code)
                validated_data['student'] = student
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student_id_code": "Student with this ID code does not exist."})
        elif not student_instance and self.context and 'request' in self.context and self.context['request'].user.is_authenticated:
            try:
                student = Student.objects.get(user=self.context['request'].user)
                validated_data['student'] = student
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student": "No student profile found for the current user."})
        
        # Ensure overall_progress_data is stored as a dictionary
        overall_progress_data = validated_data.get('overall_progress_data', {})
        if isinstance(overall_progress_data, str):
            try:
                validated_data['overall_progress_data'] = json.loads(overall_progress_data)
            except json.JSONDecodeError:
                raise serializers.ValidationError({"overall_progress_data": "Invalid JSON format for overall_progress_data."})

        # Check if progress already exists for this student
        existing_progress = StudentProgress.objects.filter(student=validated_data['student']).first()
        if existing_progress:
            # If exists, update it instead of creating a new one
            return self.update(existing_progress, validated_data)
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('student_id_code', None) # Not used for update

        # Ensure overall_progress_data is handled as a dictionary
        if 'overall_progress_data' in validated_data:
            overall_progress_data = validated_data['overall_progress_data']
            if isinstance(overall_progress_data, str):
                try:
                    validated_data['overall_progress_data'] = json.loads(overall_progress_data)
                except json.JSONDecodeError:
                    raise serializers.ValidationError({"overall_progress_data": "Invalid JSON format for overall_progress_data."})
        
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
    