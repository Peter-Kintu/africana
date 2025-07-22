# learnflow_ai/django_backend/api/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
import uuid

import csv
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count

from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa

import requests
import json # Ensure json is imported for parsing AI responses

# NEW: Imports for Web3 and Blockchain interaction
from web3 import Web3
from django.conf import settings # To access settings variables like BLOCKCHAIN_NODE_URL
from web3.exceptions import Web3Exception # Import specific Web3 exceptions

from .models import Student, Lesson, Question, QuizAttempt, StudentProgress, Wallet # ADDED Wallet model
from .serializers import (
    StudentSerializer, LessonSerializer, QuestionSerializer,
    QuizAttemptSerializer, StudentProgressSerializer, UserSerializer,
    WalletSerializer # ADDED WalletSerializer
)

# --- Blockchain Helper Functions ---
# Initialize Web3 connection
w3 = None
LEARNFLOW_TOKEN_CONTRACT = None
CONTRACT_OWNER_ACCOUNT = None

try:
    w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_NODE_URL))
    if not w3.is_connected():
        print("WARNING: Not connected to Ethereum node. Blockchain features will be disabled.")
        w3 = None # Set to None if not connected
    else:
        print(f"Connected to Ethereum node: {settings.BLOCKCHAIN_NODE_URL}")
        LEARNFLOW_TOKEN_CONTRACT = w3.eth.contract(
            address=settings.LEARNFLOW_TOKEN_CONTRACT_ADDRESS,
            abi=settings.LEARNFLOW_TOKEN_ABI
        )
        CONTRACT_OWNER_ACCOUNT = w3.eth.account.from_key(settings.CONTRACT_OWNER_PRIVATE_KEY)
        print(f"Loaded LearnFlow Token Contract: {settings.LEARNFLOW_TOKEN_CONTRACT_ADDRESS}")
        print(f"Contract Owner Account: {CONTRACT_OWNER_ACCOUNT.address}")
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
            try:
                with transaction.atomic():
                    user = serializer.save()
                    student_id_code = request.data.get('student_id_code', None)
                    student_gender = request.data.get('gender', None)

                    student, created = Student.objects.get_or_create(
                        user=user,
                        defaults={
                            'student_id_code': student_id_code,
                            'gender': student_gender,
                            'date_registered': timezone.now(),
                        }
                    )
                    if not created:
                        if student_id_code is not None and student.student_id_code != student_id_code:
                            student.student_id_code = student_id_code
                        if student_gender is not None and student.gender != student_gender:
                            student.gender = student_gender
                        student.save()

                return Response({'message': 'User registered successfully', 'user_id': user.pk, 'token': Token.objects.get(user=user).key}, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"Error during registration: {e}")
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
        return super().get_permissions()

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all().order_by('created_at')
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()

class QuizAttemptViewSet(viewsets.ModelViewSet):
    queryset = QuizAttempt.objects.all().order_by('-attempt_timestamp')
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(student__user=self.request.user)
        return self.queryset

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
                raise serializers.ValidationError({"student": "No student profile found for the current user. Please ensure your student ID code is set or register as a student."})


    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        results = []
        errors = []
        students_to_update_progress = set()

        for item_data in serializer.validated_data:
            try:
                with transaction.atomic():
                    client_uuid_obj = item_data.pop('uuid')

                    if client_uuid_obj is None:
                        raise ValueError("UUID is missing from client data.")

                    student_id_code = item_data.pop('student_id_code')
                    question_uuid = item_data.pop('question_uuid')

                    student = Student.objects.get(student_id_code=student_id_code)
                    question = Question.objects.get(uuid=question_uuid)

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

                    attempt, created = QuizAttempt.objects.get_or_create(
                        uuid=client_uuid_obj,
                        defaults=defaults
                    )

                    if not created:
                        for field, value in defaults.items():
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
                errors.append({'uuid': str(client_uuid_obj), 'error': str(e)})
            except Exception as e:
                errors.append({'uuid': str(client_uuid_obj), 'error': f"Unexpected error: {e}"})
        
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


@api_view(['GET'])
@permission_classes([IsAdminUser])
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


@login_required
@permission_classes([IsAdminUser])
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
            if isinstance(progress_data, str):
                try:
                    progress_data = json.loads(progress_data)
                except json.JSONDecodeError:
                    progress_data = {}
            
            if isinstance(progress_data, dict):
                student_info['overall_progress_summary'] = progress_data
        
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
    
    return render(request, 'teacher_dashboard.html', context)


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

        lesson_data['score_sum'] += quiz_attempt.score
        lesson_data['attempt_count'] += 1
        lesson_data['score_avg'] = lesson_data['score_sum'] / lesson_data['attempt_count']
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
            total_score_sum = sum(a.score for a in attempts)
            total_attempt_count = len(attempts)
            average_score = total_score_sum / total_attempt_count if total_attempt_count > 0 else 0.0
            
            status = 'in_progress'
            if average_score == 100:
                status = 'completed'
            elif any(a.is_correct for a in attempts):
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_quiz_feedback(request):
    """
    Receives a question, submitted answer, and correct answer,
    then uses Gemini API to generate feedback and a score.
    """
    question_text = request.data.get('question_text')
    submitted_answer = request.data.get('submitted_answer')
    correct_answer = request.data.get('correct_answer')

    if not all([question_text, submitted_answer, correct_answer]):
        return Response({'error': 'Missing question_text, submitted_answer, or correct_answer'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        prompt = (
            f"Given the following question, a submitted answer, and the correct answer, "
            f"provide constructive feedback and a score (out of 100) for the submitted answer. "
            f"Focus on accuracy, completeness, and clarity. "
            f"Output in JSON format with 'feedback_text' and 'score' (integer). "
            f"Question: \"{question_text}\"\n"
            f"Submitted Answer: \"{submitted_answer}\"\n"
            f"Correct Answer: \"{correct_answer}\"\n\n"
            f"Example JSON output: {{ \"feedback_text\": \"Your answer is partially correct...\", \"score\": 75 }}"
        )

        api_key = ""
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "feedback_text": {"type": "STRING"},
                        "score": {"type": "NUMBER"}
                    },
                    "propertyOrdering": ["feedback_text", "score"]
                }
            }
        }

        response = requests.post(api_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        response.raise_for_status()

        gemini_result = response.json()
        
        if gemini_result and gemini_result.get('candidates') and gemini_result['candidates'][0].get('content') and gemini_result['candidates'][0]['content'].get('parts'):
            json_string = gemini_result['candidates'][0]['content']['parts'][0]['text']
            feedback_data = json.loads(json_string)
            
            score = feedback_data.get('score')
            if isinstance(score, (int, float)):
                score = max(0, min(100, score))
            else:
                score = 0

            return Response({
                'feedback_text': feedback_data.get('feedback_text', 'No feedback provided.'),
                'score': score
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid response from AI model'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except requests.exceptions.RequestException as e:
        print(f"Gemini API Request Error: {e}")
        return Response({'error': f'Failed to connect to AI service: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error from Gemini response: {e}, Response: {response.text}")
        return Response({'error': 'Invalid JSON response from AI model'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        print(f"Unexpected error in AI quiz feedback view: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_recommendations(request):
    """
    Receives student performance summary and uses Gemini API to generate recommendations.
    """
    student_performance_summary = request.data.get('student_performance_summary')

    if not student_performance_summary:
        return Response({'error': 'Missing student_performance_summary'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        prompt = (
            f"Based on the following student performance summary, provide personalized learning recommendations. "
            f"Suggest specific topics to review, next steps, or areas for improvement. "
            f"Output in JSON format with a 'recommendations_list' (array of strings) and a 'summary_message' (string). "
            f"Student Performance Summary: \"{student_performance_summary}\"\n\n"
            f"Example JSON output: {{ \"recommendations_list\": [\"Review Topic A\", \"Practice more MCQs\"], \"summary_message\": \"Great effort!\" }}"
        )

        api_key = ""
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "recommendations_list": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        },
                        "summary_message": {"type": "STRING"}
                    },
                    "propertyOrdering": ["recommendations_list", "summary_message"]
                }
            }
        }

        response = requests.post(api_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        response.raise_for_status()

        gemini_result = response.json()

        if gemini_result and gemini_result.get('candidates') and gemini_result['candidates'][0].get('content') and gemini_result['candidates'][0]['content'].get('parts'):
            json_string = gemini_result['candidates'][0]['content']['parts'][0]['text']
            recommendations_data = json.loads(json_string)
            
            return Response({
                'recommendations_list': recommendations_data.get('recommendations_list', []),
                'summary_message': recommendations_data.get('summary_message', 'No specific recommendations provided.')
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid response from AI model'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except requests.exceptions.RequestException as e:
        print(f"Gemini API Request Error: {e}")
        return Response({'error': f'Failed to connect to AI service: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error from Gemini response: {e}, Response: {response.text}")
        return Response({'error': 'Invalid JSON response from AI model'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        print(f"Unexpected error in AI recommendations view: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

