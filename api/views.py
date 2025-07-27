# learnflow_ai/django_backend/api/views.py

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.db import IntegrityError, transaction
import csv
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Avg, Prefetch
from django.contrib.auth.decorators import login_required, user_passes_test # NEW IMPORTS
from django.contrib.admin.views.decorators import staff_member_required # Import this for clarity, though user_passes_test is more general

from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa

import requests
import json # Ensure json is imported for parsing AI responses

# NEW: Imports for Web3 and Blockchain interaction
from web3 import Web3
from django.conf import settings # To access settings variables like BLOCKCHAIN_NODE_URL
from web3.exceptions import Web3Exception # Import specific Web3 exceptions

# Import the serializers module itself
import rest_framework.serializers as serializers

from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, Wallet
from .serializers import (
    StudentSerializer, LessonSerializer, QuestionSerializer,
    QuizAttemptSerializer, StudentProgressSerializer, UserSerializer,
    WalletSerializer
)

# --- Blockchain Helper Functions ---
# Initialize Web3 connection
w3 = None
LEARNFLOW_TOKEN_CONTRACT = None
CONTRACT_OWNER_ACCOUNT = None

try:
    # Check if BLOCKCHAIN_NODE_URL is configured
    if hasattr(settings, 'BLOCKCHAIN_NODE_URL') and settings.BLOCKCHAIN_NODE_URL:
        w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_NODE_URL))
        if not w3.is_connected():
            print("WARNING: Not connected to Ethereum node. Blockchain features will be disabled.")
            w3 = None # Set to None if not connected
        else:
            print(f"Connected to Ethereum node: {settings.BLOCKCHAIN_NODE_URL}")
            # Ensure ABI, contract address, and private key are configured
            if hasattr(settings, 'LEARNFLOW_TOKEN_ABI') and settings.LEARNFLOW_TOKEN_ABI and \
               hasattr(settings, 'LEARNFLOW_TOKEN_CONTRACT_ADDRESS') and settings.LEARNFLOW_TOKEN_CONTRACT_ADDRESS and \
               hasattr(settings, 'CONTRACT_OWNER_PRIVATE_KEY') and settings.CONTRACT_OWNER_PRIVATE_KEY:

                LEARNFLOW_TOKEN_CONTRACT = w3.eth.contract(
                    address=settings.LEARNFLOW_TOKEN_CONTRACT_ADDRESS,
                    abi=json.loads(settings.LEARNFLOW_TOKEN_ABI) # ABI is typically a JSON string
                )
                CONTRACT_OWNER_ACCOUNT = w3.eth.account.from_key(settings.CONTRACT_OWNER_PRIVATE_KEY)
                print(f"Loaded LearnFlow Token Contract: {settings.LEARNFLOW_TOKEN_CONTRACT_ADDRESS}")
                print(f"Contract Owner Account: {CONTRACT_OWNER_ACCOUNT.address}")
            else:
                print("WARNING: Blockchain contract details (ABI, address, owner key) not fully configured. Blockchain features will be disabled.")
                w3 = None
                LEARNFLOW_TOKEN_CONTRACT = None
                CONTRACT_OWNER_ACCOUNT = None
    else:
        print("WARNING: BLOCKCHAIN_NODE_URL is not configured. Blockchain features will be disabled.")
except Web3Exception as e:
    print(f"ERROR: Web3 connection or contract loading failed: {e}")
    w3 = None
    LEARNFLOW_TOKEN_CONTRACT = None
    CONTRACT_OWNER_ACCOUNT = None
except Exception as e:
    print(f"ERROR: Unexpected error during blockchain setup: {e}")
    w3 = None
    LEARNFLOW_TOKEN_CONTRACT = None
    CONTRACT_OWNER_ACCOUNT = None


def mint_learnflow_tokens(recipient_address: str, amount: int):
    """
    Mints LearnFlow Tokens to a given recipient address.
    Returns transaction hash if successful, None otherwise.
    """
    if not LEARNFLOW_TOKEN_CONTRACT or not w3 or not w3.is_connected() or not CONTRACT_OWNER_ACCOUNT:
        print("Blockchain not fully configured or connected. Cannot mint tokens.")
        return None

    if not w3.is_address(recipient_address):
        print(f"Invalid recipient address: {recipient_address}")
        return None

    try:
        # Get the nonce for the owner's account
        nonce = w3.eth.get_transaction_count(CONTRACT_OWNER_ACCOUNT.address)

        # Get token decimals from the contract
        token_decimals = LEARNFLOW_TOKEN_CONTRACT.functions.decimals().call()
        amount_in_smallest_unit = amount * (10 ** token_decimals)

        # Build the transaction
        transaction = LEARNFLOW_TOKEN_CONTRACT.functions.mint(
            recipient_address,
            amount_in_smallest_unit
        ).build_transaction({
            'chainId': w3.eth.chain_id,
            'gasPrice': w3.eth.gas_price,
            'from': CONTRACT_OWNER_ACCOUNT.address,
            'nonce': nonce,
        })

        # Sign the transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key=CONTRACT_OWNER_ACCOUNT.key)

        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"Mint transaction sent. Tx Hash: {tx_hash.hex()}")
        # Wait for the transaction to be mined (optional, but good for confirmation)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Mint transaction confirmed for {recipient_address}, amount {amount}")
        return tx_hash.hex()
    except Web3Exception as e:
        print(f"Web3 error during token minting: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during token minting: {e}")
        return None

def get_token_balance(wallet_address: str):
    """
    Gets the LearnFlow Token balance for a given wallet address.
    Returns balance as a float (adjusted for decimals), or None if error.
    """
    if not LEARNFLOW_TOKEN_CONTRACT or not w3 or not w3.is_connected():
        print("Blockchain not fully configured or connected. Cannot get token balance.")
        return None

    if not w3.is_address(wallet_address):
        print(f"Invalid wallet address: {wallet_address}")
        return None

    try:
        raw_balance = LEARNFLOW_TOKEN_CONTRACT.functions.balanceOf(wallet_address).call()
        token_decimals = LEARNFLOW_TOKEN_CONTRACT.functions.decimals().call()
        balance = raw_balance / (10 ** token_decimals)
        return balance
    except Web3Exception as e:
        print(f"Web3 error getting token balance for {wallet_address}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error getting token balance for {wallet_address}: {e}")
        return None

# --- End Blockchain Helper Functions ---


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            # DEBUG LOGGING: Print validated data to see what Django receives
            print(f"AuthViewSet: Registering user with validated data: {serializer.validated_data}")
            try:
                with transaction.atomic():
                    user = serializer.save()
                    student_id_code = request.data.get('student_id_code', None)
                    student_gender = request.data.get('gender', None)

                    # Create a student profile for the user
                    student, created = Student.objects.get_or_create(
                        user=user,
                        defaults={
                            'student_id_code': student_id_code,
                            'gender': student_gender,
                            'date_registered': timezone.now(),
                        }
                    )
                    if not created:
                        # Update existing student if it was just created but already existed (rare with OneToOneField)
                        if student_id_code is not None and student.student_id_code != student_id_code:
                            student.student_id_code = student_id_code
                        if student_gender is not None and student.gender != student_gender:
                            student.gender = student_gender
                        student.save()
                    
                    # Create a wallet for the student if one doesn't exist
                    Wallet.objects.get_or_create(student=student)

                token, created = Token.objects.get_or_create(user=user)
                return Response({'token': token.key, 'user_id': user.id, 'username': user.username}, status=status.HTTP_201_CREATED)
            except IntegrityError as e:
                # Catch unique constraint errors, e.g., duplicate student_id_code
                print(f"AuthViewSet: IntegrityError during registration: {e}") # Log the specific error
                return Response({'error': 'Registration failed: A user or student with this information already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(f"AuthViewSet: Unexpected error during registration: {e}") # Log unexpected errors
                return Response({'error': 'Registration failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        print(f"AuthViewSet: Serializer errors during registration: {serializer.errors}") # Log serializer errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user_id': user.id, 'username': user.username})
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

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='user')
    def get_current_user(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


# NEW VIEWSET: Wallet Management
class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only allow users to see/manage their own wallet
        return self.queryset.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        # Ensure a student profile exists for the current user
        try:
            student = Student.objects.get(user=self.request.user)
        except Student.DoesNotExist:
            # Use the imported 'serializers' module for ValidationError
            raise serializers.ValidationError({"student": "No student profile found for the current user. Please register as a student first."})

        # Check if a wallet already exists for this student
        if Wallet.objects.filter(student=student).exists():
            # If a wallet exists, raise an error or update it (depending on desired behavior)
            # For this context, we'll suggest updating.
            raise serializers.ValidationError({"address": "A wallet already exists for this student. Use PUT to update it."})

        serializer.save(student=student) # Link the wallet to the current student

    def perform_update(self, serializer):
        # Ensure the user is updating their own wallet
        instance = self.get_object()
        if instance.student.user != self.request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer.save()

# NEW API VIEW: Get Wallet Balance (non-ViewSet action)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_balance(request):
    """
    Retrieves the LearnFlow Token balance for the authenticated student's registered wallet.
    """
    try:
        student = Student.objects.get(user=request.user)
        wallet = Wallet.objects.get(student=student)
        
        balance = get_token_balance(wallet.address)
        
        if balance is not None:
            return Response({'balance': balance}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Could not retrieve token balance. Check blockchain connection or wallet address.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Student.DoesNotExist:
        return Response({'error': 'No student profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)
    except Wallet.DoesNotExist:
        return Response({'error': 'No wallet registered for this student.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in get_wallet_balance view: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().order_by('user__username')
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # If the user is not staff, they can only see their own student profile
        if not self.request.user.is_staff:
            return self.queryset.filter(user=self.request.user)
        return self.queryset

    def perform_create(self, serializer):
        student, created = Student.objects.get_or_create(
            user=self.request.user,
            defaults=serializer.validated_data
        )
        if not created:
            for attr, value in serializer.validated_data.items():
                setattr(student, attr, value)
            student.save()
        serializer.instance = student

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff and instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff and instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
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
    queryset = Lesson.objects.all().order_by('title')
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else: # For 'list' and 'retrieve'
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all().order_by('created_at')
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else: # For 'list' and 'retrieve'
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        lesson_uuid = self.request.query_params.get('lesson__uuid', None)
        if lesson_uuid is not None:
            queryset = queryset.filter(lesson__uuid=lesson_uuid)
        return queryset

class QuizAttemptViewSet(viewsets.ModelViewSet):
    queryset = QuizAttempt.objects.all().order_by('-attempt_timestamp')
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(student__user=self.request.user)
        return self.queryset

    # Explicitly defining the create method to ensure serializer is in scope
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer) # 'serializer' is passed here
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


    def perform_create(self, serializer):
        student_id_code = serializer.validated_data.get('student_id_code')
        if student_id_code:
            try:
                student = Student.objects.get(student_id_code=student_id_code)
                quiz_attempt = serializer.save(student=student, synced_at=timezone.now(), sync_status='SYNCED')
                update_student_overall_progress(student, quiz_attempt)
                # NEW: Mint tokens if quiz score is good
                if quiz_attempt.score is not None and quiz_attempt.score >= 80: # Check for None and score
                    if hasattr(student, 'wallet') and student.wallet.address:
                        mint_learnflow_tokens(student.wallet.address, 10) # Mint 10 LFT for this student
                    else:
                        print(f"Student {student.user.username} has no wallet registered. Cannot mint tokens.")
            except Student.DoesNotExist:
                # Use the imported 'serializers' module for ValidationError
                raise serializers.ValidationError({"student_id_code": "Student with this ID code does not exist."})
        else:
            try:
                student = Student.objects.get(user=self.request.user)
                quiz_attempt = serializer.save(student=student, synced_at=timezone.now(), sync_status='SYNCED')
                update_student_overall_progress(student, quiz_attempt)
                # NEW: Mint tokens if quiz score is good
                if quiz_attempt.score is not None and quiz_attempt.score >= 80: # Check for None and score
                    if hasattr(student, 'wallet') and student.wallet.address:
                        mint_learnflow_tokens(student.wallet.address, 10)
                    else:
                        print(f"Student {student.user.username} has no wallet registered. Cannot mint tokens.")
            except Student.DoesNotExist:
                # Use the imported 'serializers' module for ValidationError
                raise serializers.ValidationError({"student": "No student profile found for the current user. Please ensure your student ID code is set or register as a student."})


    @action(detail=False, methods=['post'], url_path='bulk_upload')
    def bulk_upload(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        results = []
        errors = []
        students_to_update_progress = set()

        for item_data in serializer.validated_data:
            # Initialize client_uuid_obj to None before the try block
            client_uuid_obj = None
            try:
                # Retrieve the uuid directly from validated_data using .get()
                # This avoids KeyError if 'uuid' is somehow missing (though it shouldn't be with proper serialization)
                client_uuid_obj = item_data.get('uuid')

                # If uuid is still None at this point, it's a critical error
                if client_uuid_obj is None:
                    raise ValueError("UUID is missing from client data after serialization.")

                student_id_code = item_data.get('student_id_code')
                question_uuid = item_data.get('question_uuid')

                student = None
                if student_id_code:
                    student = Student.objects.get(student_id_code=student_id_code)
                else:
                    # Fallback to current authenticated user's student profile
                    student = Student.objects.get(user=request.user)

                question = Question.objects.get(uuid=question_uuid)

                # Create a dictionary of default values for get_or_create/update
                # Ensure all fields expected by the QuizAttempt model are present
                defaults = {
                    'student': student,
                    'question': question,
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

                # Use get_or_create with the uuid and defaults
                attempt, created = QuizAttempt.objects.get_or_create(
                    uuid=client_uuid_obj, # Pass the UUID directly as the lookup field
                    defaults=defaults
                )

                if not created:
                    # If the attempt already existed, update its fields
                    for field, value in defaults.items():
                        # Exclude immutable fields from update
                        if field not in ['uuid', 'student', 'question']:
                            setattr(attempt, field, value)
                    attempt.save()

                results.append(QuizAttemptSerializer(attempt).data)
                students_to_update_progress.add(student)
                # NEW: Mint tokens if quiz score is good during bulk upload
                if attempt.score is not None and attempt.score >= 80:
                    if hasattr(student, 'wallet') and student.wallet.address:
                        mint_learnflow_tokens(student.wallet.address, 10)
                    else:
                        print(f"Student {student.user.username} has no wallet registered during bulk upload. Cannot mint tokens.")

            except (Student.DoesNotExist, Question.DoesNotExist) as e:
                # Ensure client_uuid_obj is stringified for error reporting
                error_uuid = str(client_uuid_obj) if client_uuid_obj is not None else 'unknown_uuid'
                errors.append({'uuid': error_uuid, 'error': str(e)})
            except ValueError as e: # Catch the specific ValueError if UUID is missing
                error_uuid = str(client_uuid_obj) if client_uuid_obj is not None else 'unknown_uuid'
                errors.append({'uuid': error_uuid, 'error': str(e)})
            except Exception as e:
                # Ensure client_uuid_obj is stringified for error reporting
                error_uuid = str(client_uuid_obj) if client_uuid_obj is not None else 'unknown_uuid'
                errors.append({'uuid': error_uuid, 'error': f"Unexpected error: {e}"})
        
        for student in students_to_update_progress:
            all_student_attempts = QuizAttempt.objects.filter(student=student).select_related('question__lesson')
            update_student_overall_progress_bulk(student, all_student_attempts)


        if errors:
            return Response({'message': 'Bulk upload completed with some issues.', 'successes': results, 'errors': errors}, status=status.HTTP_207_MULTI_STATUS)
        return Response(results, status=status.HTTP_201_CREATED)


class StudentProgressViewSet(viewsets.ModelViewSet):
    queryset = StudentProgress.objects.all().order_by('-last_updated')
    serializer_class = StudentProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.select_related('student__user')
        if not self.request.user.is_staff:
            try:
                current_student = Student.objects.get(user=self.request.user)
                return queryset.filter(student=current_student)
            except Student.DoesNotExist:
                return StudentProgress.objects.none()
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff and instance.student.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
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
            try:
                student_instance = Student.objects.get(user=request.user)
            except Student.DoesNotExist:
                return Response({"error": "No student profile found for the current user."},
                                status=status.HTTP_400_BAD_REQUEST)

        existing_progress = StudentProgress.objects.filter(student=student_instance).first()

        if existing_progress:
            serializer = self.get_serializer(existing_progress, data=mutable_data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        else:
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(student=student_instance)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff and instance.student.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if not request.user.is_staff and 'student' in request.data:
            return Response({"error": "Cannot change student for an existing progress record."},
                            status=status.HTTP_400_BAD_REQUEST)

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


# --- AI Endpoints (Callable by authenticated users) ---
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_quiz_feedback(request):
    """
    API endpoint for AI quiz feedback generation.
    """
    question_text = request.data.get('question_text')
    submitted_answer = request.data.get('submitted_answer')
    correct_answer = request.data.get('correct_answer')
    question_type = request.data.get('question_type')

    if not all([question_text, submitted_answer, correct_answer, question_type]):
        return Response({'error': 'Missing required parameters for AI feedback.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Calls the helper function for AI logic
        feedback_data = get_ai_quiz_feedback_helper(question_text, submitted_answer, correct_answer, question_type)
        return Response(feedback_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'AI feedback generation failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_recommendations(request):
    """
    API endpoint for AI student recommendations generation.
    """
    student_id_code = request.data.get('student_id_code')
    if not student_id_code:
        return Response({'error': 'Missing student_id_code.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        student = Student.objects.get(student_id_code=student_id_code)
        # Calls the helper function for AI logic
        recommendations = get_ai_recommendations_for_student_helper(student)
        return Response({'recommendations': recommendations}, status=status.HTTP_200_OK)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- AI Helper Functions (These are the actual logic, called by the API views above) ---
def get_ai_quiz_feedback_helper(question_text, submitted_answer, correct_answer, question_type):
    """
    Helper function for AI quiz feedback generation.
    In a real scenario, this would call an external AI model.
    """
    print(f"AI Feedback Request: Q='{question_text}', A='{submitted_answer}', Correct='{correct_answer}', Type='{question_type}'")
    # Simulate AI response
    score = 0
    feedback_text = "Feedback not generated (AI integration placeholder)."
    if question_type == 'MCQ':
        if submitted_answer == correct_answer:
            score = 100
            feedback_text = "Correct! Well done."
        else:
            score = 0
            feedback_text = f"Incorrect. The correct answer was: {correct_answer}."
    elif question_type == 'SA':
        # Simple keyword matching for SA, replace with actual AI call
        if correct_answer.lower() in submitted_answer.lower():
            score = 70
            feedback_text = "Partially correct. Your answer contains key elements."
        else:
            score = 20
            feedback_text = "Keep trying! Review the material related to this question."
    
    return {"feedback_text": feedback_text, "score": score}

def get_ai_recommendations_for_student_helper(student):
    """
    Helper function for AI student recommendations generation.
    In a real scenario, this would call an external AI model based on student progress.
    """
    print(f"AI Recommendations Request for student: {student.user.username}")
    # Simulate AI response
    recommendations_list = [
        "Review lessons on 'Trees and their types'.",
        "Practice more short answer questions on plant biology.",
        "Focus on understanding the core concepts of photosynthesis."
    ]
    summary_message = f"Based on {student.user.username}'s recent performance, here are some personalized recommendations."
    return {"recommendations_list": recommendations_list, "summary_message": summary_message}


def update_student_overall_progress(student, quiz_attempt):
    """
    Updates the overall_progress_data for a single student based on a new quiz attempt.
    """
    try:
        student_progress, created = StudentProgress.objects.get_or_create(student=student)
        
        current_progress_data = student_progress.overall_progress_data
        if not isinstance(current_progress_data, dict):
            current_progress_data = {}

        lesson_uuid = str(quiz_attempt.question.lesson.uuid) if quiz_attempt.question.lesson else 'no_lesson_uuid'
        
        lesson_data = current_progress_data.get(lesson_uuid, {
            'status': 'in_progress',
            'score_sum': 0,
            'attempt_count': 0,
            'score_avg': 0.0,
            'last_attempt_date': None,
        })

        lesson_data['score_sum'] += quiz_attempt.score if quiz_attempt.score is not None else 0
        lesson_data['attempt_count'] += 1
        lesson_data['score_avg'] = lesson_data['score_sum'] / lesson_data['attempt_count'] if lesson_data['attempt_count'] > 0 else 0.0
        lesson_data['last_attempt_date'] = quiz_attempt.attempt_timestamp.isoformat()

        if quiz_attempt.score == 100:
            lesson_data['status'] = 'completed'
        elif lesson_data['status'] != 'completed':
            lesson_data['status'] = 'in_progress'

        current_progress_data[lesson_uuid] = lesson_data
        
        student_progress.overall_progress_data = current_progress_data
        student_progress.last_updated = timezone.now()
        student_progress.save()
        print(f"Updated StudentProgress for {student.user.username}: {current_progress_data}")

    except Exception as e:
        print(f"Error updating student overall progress for {student.user.username}: {e}")


def update_student_overall_progress_bulk(student, quiz_attempts_queryset):
    """
    Recalculates and updates the overall_progress_data for a student based on a queryset of their quiz attempts.
    """
    try:
        student_progress, created = StudentProgress.objects.get_or_create(student=student)
        
        new_progress_data = {}
        
        attempts_by_lesson = {}
        for attempt in quiz_attempts_queryset:
            lesson_uuid = str(attempt.question.lesson.uuid) if attempt.question.lesson else 'no_lesson_uuid'
            if lesson_uuid not in attempts_by_lesson:
                attempts_by_lesson[lesson_uuid] = []
            attempts_by_lesson[lesson_uuid].append(attempt)
        
        for lesson_uuid, attempts in attempts_by_lesson.items():
            total_score_sum = sum(a.score for a in attempts if a.score is not None)
            total_attempt_count = len(attempts)
            average_score = total_score_sum / total_attempt_count if total_attempt_count > 0 else 0.0
            
            status = 'in_progress'
            if average_score == 100:
                status = 'completed'
            elif any(a.is_correct for a in attempts): # If any attempt was correct, it's at least in progress
                status = 'in_progress'
            
            last_attempt_date = max(a.attempt_timestamp for a in attempts).isoformat() if attempts else None

            new_progress_data[lesson_uuid] = {
                'status': status,
                'score_sum': total_score_sum,
                'attempt_count': total_attempt_count,
                'score_avg': round(average_score, 2),
                'last_attempt_date': last_attempt_date,
            }
        
        student_progress.overall_progress_data = new_progress_data
        student_progress.last_updated = timezone.now()
        student_progress.save()
        print(f"Recalculated and updated StudentProgress for {student.user.username} (Bulk): {new_progress_data}")

    except Exception as e:
        print(f"Error recalculating student overall progress for {student.user.username} (Bulk): {e}")

# Teacher Dashboard View (Django Template)
# This view is for rendering the HTML dashboard, not for API consumption directly by Flutter.
# It uses @login_required and @permission_classes for Django's template rendering context.
@login_required # Requires user to be logged in
@user_passes_test(lambda u: u.is_staff) # Requires user to be a staff member (admin)
def teacher_dashboard_view(request):
    """
    Renders a comprehensive teacher dashboard with student progress reports.
    Can also generate a PDF version if '?format=pdf' is in the URL.
    """
    students_data = []
    
    students = Student.objects.select_related('user').all().order_by('user__username')

    for student in students:
        student_progress = None
        try:
            student_progress = student.overall_progress
        except StudentProgress.DoesNotExist:
            print(f"No StudentProgress found for student: {student.user.username}")
            # Create a default progress entry if none exists
            student_progress = StudentProgress.objects.create(student=student, overall_progress_data={})


        student_info = {
            'username': student.user.username,
            'student_id_code': student.student_id_code,
            'grade_level': student.grade_level,
            'class_name': student.class_name,
            'overall_progress_summary': {},
            'recent_quiz_attempts': [],
            'total_quizzes_completed': 0,
            'average_score': 0.0,
        }

        if student_progress and student_progress.overall_progress_data:
            progress_data = student_progress.overall_progress_data
            # Ensure progress_data is a dict, it might be a string if not properly loaded/saved
            if isinstance(progress_data, str):
                try:
                    progress_data = json.loads(progress_data)
                except json.JSONDecodeError:
                    progress_data = {}
            
            if isinstance(progress_data, dict):
                student_info['overall_progress_summary'] = progress_data
        
        # Fetch recent quiz attempts, prefetching related question and lesson data
        recent_attempts = QuizAttempt.objects.filter(student=student).select_related('question__lesson').order_by('-attempt_timestamp')[:5]
        
        for attempt in recent_attempts:
            student_info['recent_quiz_attempts'].append({
                'question_text': attempt.question.question_text,
                'lesson_title': attempt.question.lesson.title if attempt.question.lesson else 'N/A',
                'submitted_answer': attempt.submitted_answer,
                'is_correct': attempt.is_correct,
                'score': attempt.score,
                'ai_feedback_text': attempt.ai_feedback_text,
                'attempt_timestamp': attempt.attempt_timestamp,
            })
        
        student_info['total_quizzes_completed'] = QuizAttempt.objects.filter(student=student).count()
        
        avg_score_result = QuizAttempt.objects.filter(student=student).aggregate(Avg('score'))
        student_info['average_score'] = avg_score_result['score__avg'] if avg_score_result['score__avg'] is not None else 0.0

        students_data.append(student_info)

    context = {
        'students_data': students_data,
        'current_date': timezone.now().strftime("%Y-%m-%d"),
    }

    if request.GET.get('format') == 'pdf':
        template_path = 'teacher_dashboard.html'
        template = get_template(template_path)
        html = template.render(context)

        result = BytesIO()

        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="teacher_dashboard_report.pdf"'
            return response
        return HttpResponse('We had some errors <pre>%s</pre>' % html)
    
    # Render the HTML template for direct browser access
    return render(request, 'teacher_dashboard.html', context)


@api_view(['GET']) # This view is specifically for CSV export
@permission_classes([IsAdminUser]) # Only staff can access this view
def export_quiz_attempts_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="quiz_attempts_report.csv"'

    writer = csv.writer(response)
    
    writer.writerow([
        'Attempt UUID',
        'Student Username',
        'Student ID Code',
        'Lesson Title',
        'Question Text',
        'Question Type',
        'Submitted Answer',
        'Is Correct',
        'Score',
        'AI Feedback Text',
        'Attempt Timestamp',
        'Sync Status',
        'Device ID'
    ])

    quiz_attempts = QuizAttempt.objects.select_related('student__user', 'question__lesson').all().order_by('attempt_timestamp')

    for attempt in quiz_attempts:
        writer.writerow([
            str(attempt.uuid),
            attempt.student.user.username,
            attempt.student.student_id_code,
            attempt.question.lesson.title if attempt.question.lesson else 'N/A',
            attempt.question.question_text,
            attempt.question.question_type,
            attempt.submitted_answer,
            'Yes' if attempt.is_correct else 'No',
            attempt.score,
            attempt.ai_feedback_text if attempt.ai_feedback_text else '',
            attempt.attempt_timestamp.isoformat(),
            attempt.sync_status,
            attempt.device_id if attempt.device_id else ''
        ])
    return response
