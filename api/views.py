# learnflow_ai/django_backend/api/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone # Import timezone for setting synced_at
from django.db import transaction # For atomic operations
import uuid # Import uuid module

from .models import Student, Lesson, Question, QuizAttempt, StudentProgress
from .serializers import (
    StudentSerializer, LessonSerializer, QuestionSerializer,
    QuizAttemptSerializer, StudentProgressSerializer, UserSerializer
)

class AuthViewSet(viewsets.ViewSet):
    # Custom ViewSet for authentication (register, login, logout)
    permission_classes = [AllowAny] # Allow anyone to register/login

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic(): # Ensure user and student creation are atomic
                    user = serializer.save()
                    # Create a Student profile for the new user, passing optional fields
                    student_id_code = request.data.get('student_id_code', None)
                    student_gender = request.data.get('gender', None) # Get gender from request

                    # Use get_or_create to prevent UNIQUE constraint error if a student
                    # somehow already exists for this user (e.g., during testing)
                    student, created = Student.objects.get_or_create(
                        user=user,
                        defaults={
                            'student_id_code': student_id_code,
                            'gender': student_gender,
                            'date_registered': timezone.now(), # Set date_registered here
                        }
                    )
                    if not created:
                        # If student already existed, update fields if provided
                        if student_id_code is not None and student.student_id_code != student_id_code:
                            student.student_id_code = student_id_code
                        if student_gender is not None and student.gender != student_gender:
                            student.gender = student_gender
                        student.save()

                return Response({'message': 'User registered successfully', 'user_id': user.pk, 'token': Token.objects.get(user=user).key}, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"Error during registration: {e}") # Debug print
                return Response({'error': 'Registration failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user_id': user.pk, 'username': user.username})
        else:
            return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        try:
            request.user.auth_token.delete()
            logout(request)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().order_by('user__username') # ADDED: Default ordering
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the students
        for the currently authenticated user.
        """
        # For non-staff users, only return their own student profile
        if not self.request.user.is_staff:
            return self.queryset.filter(user=self.request.user)
        return self.queryset # Admins can see all students

    # Override create method to link student to the current user
    def perform_create(self, serializer):
        # Ensure that a student profile is created for the authenticated user
        # This prevents creating multiple student profiles for the same user
        # if the frontend sends multiple create requests.
        student, created = Student.objects.get_or_create(
            user=self.request.user,
            defaults=serializer.validated_data # Use validated data for default values
        )
        if not created:
            # If student already exists, update it instead of creating new
            # This handles cases where a student might try to "create" their profile again
            # with new details after it already exists.
            for attr, value in serializer.validated_data.items():
                setattr(student, attr, value)
            student.save()
        serializer.instance = student # Set the instance for the serializer response

    # Override retrieve, update, destroy to ensure users only access their own profile
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff and instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff and instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        # Prevent non-admin from changing user foreign key
        if not request.user.is_staff and 'user' in request.data and request.data['user'] != request.user.pk:
            return Response({"error": "Cannot change user for an existing student record."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff and instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all().order_by('title') # Default ordering
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated] # Only authenticated users can view lessons

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser] # Only admins can modify lessons
        return super().get_permissions()

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all().order_by('created_at') # Default ordering
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()

class QuizAttemptViewSet(viewsets.ModelViewSet):
    queryset = QuizAttempt.objects.all().order_by('-attempt_timestamp') # Order by most recent
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Non-staff users can only see their own quiz attempts
        if not self.request.user.is_staff:
            return self.queryset.filter(student__user=self.request.user)
        return self.queryset # Admins can see all attempts

    def perform_create(self, serializer):
        # Link the quiz attempt to the current student
        # The student_id_code is sent from the client, we need to map it to the Student instance
        student_id_code = serializer.validated_data.get('student_id_code')
        if student_id_code:
            try:
                student = Student.objects.get(student_id_code=student_id_code)
                serializer.save(student=student, synced_at=timezone.now(), sync_status='SYNCED')
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student_id_code": "Student with this ID code does not exist."})
        else:
            # Fallback: if student_id_code is not provided, try to link to current user's student profile
            try:
                student = Student.objects.get(user=self.request.user)
                serializer.save(student=student, synced_at=timezone.now(), sync_status='SYNCED')
            except Student.DoesNotExist:
                raise serializers.ValidationError({"student": "No student profile found for the current user. Please ensure your student ID code is set or register as a student."})


    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        # This endpoint expects a list of quiz attempt data
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        results = []
        errors = []
        for item_data in serializer.validated_data:
            try:
                with transaction.atomic():
                    # Get the UUID from client data and convert to UUID object
                    # Ensure 'uuid' is present in item_data before popping and conversion
                    client_uuid_str = item_data.pop('uuid') # POP the uuid string here
                    if client_uuid_str is None:
                        raise ValueError("UUID is missing from client data.")
                    client_uuid_obj = uuid.UUID(client_uuid_str) # Convert to UUID object

                    student_id_code = item_data.pop('student_id_code')
                    question_uuid = item_data.pop('question_uuid')

                    student = Student.objects.get(student_id_code=student_id_code)
                    question = Question.objects.get(uuid=question_uuid)

                    # Create or update the QuizAttempt
                    # Using get_or_create to handle potential retries/duplicates
                    attempt, created = QuizAttempt.objects.get_or_create(
                        uuid=client_uuid_obj, # Use client-provided UUID for idempotency as the primary key lookup
                        defaults={
                            'student': student,
                            'question': question,
                            # Now item_data does not contain 'uuid' when passed to defaults
                            'submitted_answer': item_data.get('submitted_answer'),
                            'is_correct': item_data.get('is_correct'),
                            'score': item_data.get('score'),
                            'ai_feedback_text': item_data.get('ai_feedback_text'),
                            'raw_ai_response': item_data.get('raw_ai_response'),
                            'attempt_timestamp': item_data.get('attempt_timestamp'),
                            'device_id': item_data.get('device_id'),
                            'synced_at': timezone.now(),
                            'sync_status': 'SYNCED',
                        }
                    )
                    if not created:
                        # If not created, it means it already existed, so update it
                        for attr, value in item_data.items():
                            # Only update fields that are not the primary key (uuid)
                            if attr != 'uuid': # This check is still good practice
                                setattr(attempt, attr, value)
                        attempt.synced_at = timezone.now()
                        attempt.sync_status = 'SYNCED'
                        attempt.save()

                    results.append(QuizAttemptSerializer(attempt).data)
            except (Student.DoesNotExist, Question.DoesNotExist) as e:
                errors.append({'uuid': client_uuid_str, 'error': str(e)}) # Use client_uuid_str for error reporting
            except Exception as e:
                errors.append({'uuid': client_uuid_str, 'error': f"Unexpected error: {e}"}) # Use client_uuid_str for error reporting

        if errors:
            # If there are errors, return a 207 Multi-Status
            return Response({'message': 'Bulk upload completed with some issues.', 'successes': results, 'errors': errors}, status=status.HTTP_207_MULTI_STATUS)
        return Response(results, status=status.HTTP_201_CREATED)


class StudentProgressViewSet(viewsets.ModelViewSet):
    queryset = StudentProgress.objects.all().order_by('-last_updated')
    serializer_class = StudentProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Students can only see their own progress
        if not self.request.user.is_staff:
            return self.queryset.filter(student__user=self.request.user)
        return self.queryset

    def create(self, request, *args, **kwargs):
        # We need to link the progress to the current user's student profile
        # The client sends student_id_code, but we need the Student instance
        mutable_data = request.data.copy()
        student_id_code = mutable_data.pop('student_id_code', None)

        student_instance = None
        if student_id_code:
            try:
                student_instance = Student.objects.get(student_id_code=student_id_code)
            except Student.DoesNotExist:
                return Response({"error": "Student with provided ID code not found."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            # Fallback to current user's student profile if no student_id_code provided
            try:
                student_instance = Student.objects.get(user=request.user)
            except Student.DoesNotExist:
                return Response({"error": "No student profile found for the current user."},
                                status=status.HTTP_400_BAD_REQUEST)

        # Check if progress already exists for this student
        existing_progress = StudentProgress.objects.filter(student=student_instance).first()

        if existing_progress:
            # Update existing progress
            serializer = self.get_serializer(existing_progress, data=mutable_data, partial=True) # Use partial for updates
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer) # This will call serializer.save()
            return Response(serializer.data)
        else:
            # Create new progress
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(student=student_instance) # Link to the student instance
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Ensure non-admin users can only update their own progress
        if not request.user.is_staff and instance.student.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # Prevent non-admin from changing student foreign key
        if not request.user.is_staff and 'student' in request.data:
            return Response({"error": "Cannot change student for an existing progress record."},
                            status=status.HTTP_400_BAD_REQUEST)

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Only admin users can delete progress records
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
