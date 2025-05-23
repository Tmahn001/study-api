from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import (
    Profile, StudyMaterial, Question, Answer, 
    QuizAttempt, UserAnswer, Transaction, StudyGroup, Course
)
from .serializers import (
    UserSerializer, ProfileSerializer, StudyMaterialSerializer, 
    StudyMaterialDetailSerializer, QuestionSerializer, AnswerSerializer, 
    QuizAttemptSerializer, UserAnswerSerializer, TransactionSerializer, 
    StudyGroupSerializer, CourseSerializer, ExamSerializer
)
from .permissions import IsOwnerOrReadOnly
import uuid
import os
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import serializers
from .services.ai_service import generate_questions
from django.utils import timezone
import logging
import openai

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing user information.
    
    Only authenticated users can view user data.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get the current authenticated user's information",
        responses={200: UserSerializer()}
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
class ConnectWalletView(APIView):
    """
    API endpoint for connecting a wallet to the user's account.
    """

    permission_classes = []

    def post(self, request):
        wallet_address = request.data.get('wallet_address')
        if not wallet_address:
            return Response({"error": "Wallet address is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = Profile.objects.get(wallet_address=wallet_address)
            user = profile.user  # 🔥 Get the correct user
            token = RefreshToken.for_user(user)
            access_token = str(token.access_token)
            refresh_token = str(token)
            return Response({
                "message": "Wallet connected successfully",
                "data": {
                    "wallet_address": wallet_address,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            }, status=status.HTTP_200_OK)

        except Profile.DoesNotExist:
            # Wallet not connected yet
            user = User.objects.create_user(username=wallet_address, password=wallet_address)

            profile = Profile.objects.create(
                wallet_address=wallet_address,
                user=user
            )

            token = RefreshToken.for_user(user)
            access_token = str(token.access_token)
            refresh_token = str(token)

            return Response({
                "message": "Wallet connected successfully",
                "data": {
                    "wallet_address": wallet_address,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            }, status=status.HTTP_200_OK)


class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user profiles.
    
    Staff can see all profiles, regular users can only see their own.
    """
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Profile.objects.all()
        return Profile.objects.filter(user=self.request.user)

class StudyMaterialViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing study materials.
    
    Users can only access and manipulate their own study materials.
    Supports filtering, searching, and ordering.
    File type is automatically determined from the uploaded file.
    
    Query Parameters:
    - course: Filter study materials by course ID
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        queryset = StudyMaterial.objects.filter(user=self.request.user)
        
        # Filter by course if provided
        course_id = self.request.query_params.get('course', None)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
            
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return StudyMaterialDetailSerializer
        return StudyMaterialSerializer
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'course', 
                openapi.IN_QUERY, 
                description="Filter study materials by course ID", 
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        Get a list of all study materials.
        Can be filtered by course ID using the 'course' query parameter.
        """
        return super().list(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        # Get the uploaded file
        file = self.request.FILES.get('file')
        if not file:
            raise serializers.ValidationError({"file": "No file was uploaded."})
        
        # Get file extension and determine file type
        file_name = file.name.lower()
        extension = file_name.split('.')[-1] if '.' in file_name else ''
        
        # Define acceptable file types and their corresponding model values
        allowed_extensions = {
            'pdf': 'PDF',
            'doc': 'DOCX',
            'docx': 'DOCX',
            'txt': 'TXT',
            'ppt': 'PPTX',
            'pptx': 'PPTX',
        }
        
        # Check if file type is supported
        if extension not in allowed_extensions:
            raise serializers.ValidationError({
                "file": f"Unsupported file type: .{extension}. Supported types: .pdf, .doc, .docx, .txt, .ppt, .pptx"
            })
        
        # Save with automatically determined file type
        file_type = allowed_extensions[extension]
        
        # Check if course is provided and exists
        course_id = self.request.data.get('course')
        if course_id:
            try:
                course = Course.objects.get(id=course_id, user=self.request.user)
                serializer.save(user=self.request.user, file_type=file_type, course=course)
            except Course.DoesNotExist:
                raise serializers.ValidationError({"course": "This course does not exist or doesn't belong to you"})
        else:
            raise serializers.ValidationError({"course": "Course ID is required"})
    
    def perform_update(self, serializer):
        # For updates, also check file type if a new file is uploaded
        file = self.request.FILES.get('file')
        
        if file:
            # Get file extension and determine file type
            file_name = file.name.lower()
            extension = file_name.split('.')[-1] if '.' in file_name else ''
            
            # Define acceptable file types and their corresponding model values
            allowed_extensions = {
                'pdf': 'PDF',
                'doc': 'DOCX',
                'docx': 'DOCX',
                'txt': 'TXT',
                'ppt': 'PPTX',
                'pptx': 'PPTX',
            }
            
            # Check if file type is supported
            if extension not in allowed_extensions:
                raise serializers.ValidationError({
                    "file": f"Unsupported file type: .{extension}. Supported types: .pdf, .doc, .docx, .txt, .ppt, .pptx"
                })
            
            # Update with automatically determined file type
            file_type = allowed_extensions[extension]
            serializer.save(file_type=file_type)
        else:
            serializer.save()
    
    @action(detail=True, methods=['get'], url_path='processing-status')
    def processing_status(self, request, pk=None):
        """
        Check the processing status of a study material.
        """
        try:
            material = self.get_object()
            return Response({
                "id": material.id,
                "title": material.title,
                "processed": material.processed,
                "questions_count": material.questions.count(),
                "file_type": material.file_type,
                "created_at": material.created_at,
                "status": "completed" if material.processed else "pending"
            }, status=status.HTTP_200_OK)
        except StudyMaterial.DoesNotExist:
            return Response({"detail": "Study material not found."}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Generate AI-powered questions based on the study material",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'force_regenerate': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Force regeneration even if questions already exist')
            },
            required=[]
        ),
        responses={
            200: openapi.Response(
                description="Questions generated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'questions_count': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            400: "Bad request",
            404: "Study material not found"
        }
    )
    @action(detail=True, methods=['post'])
    def generate_questions(self, request, pk=None):
        material = self.get_object()
        force_regenerate = request.data.get('force_regenerate', False)
        
        # Check if material is already processed and questions exist
        existing_questions_count = material.questions.count()
        if material.processed and existing_questions_count > 0 and not force_regenerate:
            return Response({
                "message": f"This study material already has {existing_questions_count} questions. Set force_regenerate=true to generate new questions.",
                "questions_count": existing_questions_count
            }, status=status.HTTP_200_OK)
        
        # If force_regenerate, delete existing questions
        if force_regenerate and existing_questions_count > 0:
            material.questions.all().delete()
            logger.info(f"Deleted {existing_questions_count} existing questions for material {material.id}")
        
        try:
            # Log material details for debugging
            logger.info(f"Generating questions for material: {material.title}, file: {material.file.name}, type: {material.file_type}")
            
            # Generate new questions
            success = generate_questions(material.id)
            
            # Refresh the material object to get updated question count
            material.refresh_from_db()
            new_questions_count = material.questions.count()
            
            if success and new_questions_count > 0:
                return Response({
                    "message": "Questions generated successfully",
                    "questions_count": new_questions_count,
                    "debug_info": {
                        "material_id": material.id,
                        "material_title": material.title,
                        "file_type": material.file_type,
                        "processed": material.processed
                    }
                }, status=status.HTTP_200_OK)
            elif success and new_questions_count == 0:
                return Response({
                    "error": "Question generation completed but no questions were saved",
                    "questions_count": new_questions_count,
                    "debug_info": {
                        "material_id": material.id,
                        "material_title": material.title,
                        "file_type": material.file_type,
                        "processed": material.processed,
                        "suggestion": "Check the file content and ensure it contains readable text"
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    "error": "Failed to generate questions. Please check the file content and try again.",
                    "questions_count": new_questions_count,
                    "debug_info": {
                        "material_id": material.id,
                        "material_title": material.title,
                        "file_type": material.file_type,
                        "processed": material.processed
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Exception in generate_questions endpoint: {e}")
            return Response({
                "error": f"Server error during question generation: {str(e)}",
                "questions_count": 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Fetch an exam containing all questions for a particular study material",
        responses={200: ExamSerializer()}
    )
    @action(detail=True, methods=['get'], url_path='exam')
    def fetch_exam(self, request, pk=None):
        """
        Fetch an exam containing all questions for a particular study material.
        """
        try:
            material = self.get_object()
            serializer = ExamSerializer(material)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except StudyMaterial.DoesNotExist:
            return Response({"detail": "Study material not found."}, status=status.HTTP_404_NOT_FOUND)
    
    @swagger_auto_schema(
        operation_description="Fetch all exams with their questions and answers",
        responses={200: ExamSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='all-exams')
    def fetch_all_exams(self, request):
        """
        Fetch all exams with their questions and answers.
        """
        materials = self.get_queryset()
        serializer = ExamSerializer(materials, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CourseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing courses.
    
    Users can create, update, and delete their own courses.
    """
    serializer_class = CourseSerializer 
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        return Course.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user) 


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing questions.
    
    Users can only view questions related to their own study materials.
    This is a read-only endpoint.
    """
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Question.objects.filter(study_material__user=self.request.user)

class QuizAttemptViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing quiz attempts.
    
    Users can create quiz attempts, submit answers, and complete quizzes.
    """
    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], url_path='submit-answer')
    def submit_answer(self, request, pk=None):
        """
        Submit an answer to a question in a quiz attempt.
        
        Expected payload:
        {
            "question": <question_id>,
            "answer": <answer_id>  # Optional for non-multiple choice questions
            "text_answer": "<text>" # Optional for short answer/essay questions
        }
        """
        try:
            quiz_attempt = self.get_object()
            
            if quiz_attempt.is_completed:
                return Response({"error": "This quiz attempt is already completed"},
                                status=status.HTTP_400_BAD_REQUEST)
            
            question_id = request.data.get('question')
            answer_id = request.data.get('answer')
            text_answer = request.data.get('text_answer', '')
            
            if not question_id:
                return Response({"error": "Question ID is required"},
                                status=status.HTTP_400_BAD_REQUEST)
            
            try:
                question = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                return Response({"error": "Question not found"},
                                status=status.HTTP_404_NOT_FOUND)
            
            # Check if question belongs to the study material
            if question.study_material_id != quiz_attempt.study_material_id:
                return Response({"error": "Question does not belong to this quiz"},
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Delete previous answer if it exists
            UserAnswer.objects.filter(quiz_attempt=quiz_attempt, question=question).delete()
            
            answer = None
            is_correct = False
            
            if question.question_type == 'MULTIPLE_CHOICE':
                if not answer_id:
                    return Response({"error": "Answer ID is required for multiple choice questions"},
                                    status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    answer = Answer.objects.get(id=answer_id, question=question)
                    is_correct = answer.is_correct
                except Answer.DoesNotExist:
                    return Response({"error": "Answer not found"},
                                    status=status.HTTP_404_NOT_FOUND)
            else:
                # For non-multiple choice, store the text answer
                # This would need additional processing for checking correctness
                if not text_answer and not answer_id:
                    return Response({"error": "Either text answer or answer ID is required"},
                                    status=status.HTTP_400_BAD_REQUEST)
            
            # Create the user answer
            user_answer = UserAnswer.objects.create(
                quiz_attempt=quiz_attempt,
                question=question,
                answer=answer,
                text_answer=text_answer,
                is_correct=is_correct
            )
            
            return Response(UserAnswerSerializer(user_answer).data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='complete')
    def complete_quiz(self, request, pk=None):
        """
        Complete a quiz attempt and calculate the score.
        
        This will:
        1. Mark the quiz as completed
        2. Calculate the final score
        3. Store the end time
        4. Return the complete quiz attempt details with score
        """
        try:
            quiz_attempt = self.get_object()
            
            if quiz_attempt.is_completed:
                return Response({"error": "This quiz attempt is already completed"},
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Get all questions for this study material
            total_questions = Question.objects.filter(study_material=quiz_attempt.study_material).count()
            
            if total_questions == 0:
                return Response({"error": "This study material has no questions"},
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Get answers that were submitted and are correct
            answered_questions = UserAnswer.objects.filter(quiz_attempt=quiz_attempt).count()
            correct_answers = UserAnswer.objects.filter(quiz_attempt=quiz_attempt, is_correct=True).count()
            
            # Calculate score (percentage)
            score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            
            # Update quiz attempt
            quiz_attempt.score = score
            quiz_attempt.is_completed = True
            quiz_attempt.end_time = timezone.now()
            quiz_attempt.save()
            
            # Return detailed results
            result = {
                "quiz_attempt": QuizAttemptSerializer(quiz_attempt).data,
                "details": {
                    "total_questions": total_questions,
                    "answered_questions": answered_questions,
                    "correct_answers": correct_answers,
                    "score": score,
                    "completion_time": quiz_attempt.end_time,
                    "time_taken_minutes": (quiz_attempt.end_time - quiz_attempt.start_time).total_seconds() / 60
                }
            }
            
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing payment transactions.
    
    Users can view their transaction history and create new transactions.
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Verify a SUI blockchain payment and update user subscription status",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['transaction_hash', 'amount', 'wallet_address', 'transaction_type'],
            properties={
                'transaction_hash': openapi.Schema(type=openapi.TYPE_STRING),
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'wallet_address': openapi.Schema(type=openapi.TYPE_STRING),
                'transaction_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['SUBSCRIPTION', 'PAY_PER_USE']
                ),
            }
        ),
        responses={
            200: TransactionSerializer,
            400: "Invalid transaction details"
        }
    )
    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        # This would integrate with SUI blockchain to verify payments
        # Placeholder for now
        transaction_hash = request.data.get('transaction_hash')
        amount = request.data.get('amount')
        wallet_address = request.data.get('wallet_address')
        transaction_type = request.data.get('transaction_type')
        
        # Create transaction record
        transaction = Transaction.objects.create(
            user=request.user,
            amount=amount,
            transaction_type=transaction_type,
            wallet_address=wallet_address,
            transaction_hash=transaction_hash,
            status='COMPLETED'  # In a real implementation, this would start as PENDING
        )
        
        # Update user's subscription status if applicable
        if transaction_type == 'SUBSCRIPTION':
            profile, created = Profile.objects.get_or_create(user=request.user)
            profile.subscription_status = 'PREMIUM'
            # Set expiry date logic would go here
            profile.save()
        
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)

class StudyGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing study groups.
    
    Users can create, join, and leave study groups.
    """
    serializer_class = StudyGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        user = self.request.user
        return StudyGroup.objects.filter(members=user)
    
    def perform_create(self, serializer):
        group = serializer.save(creator=self.request.user)
        group.members.add(self.request.user)
    
    @swagger_auto_schema(
        operation_description="Join a study group",
        responses={
            200: openapi.Response(
                description="Successfully joined the group",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'message': openapi.Schema(type=openapi.TYPE_STRING)}
                )
            ),
            404: "Study group not found"
        }
    )
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        group = self.get_object()
        group.members.add(request.user)
        return Response({"message": "Successfully joined the group"})
    
    @swagger_auto_schema(
        operation_description="Leave a study group",
        responses={
            200: openapi.Response(
                description="Successfully left the group",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'message': openapi.Schema(type=openapi.TYPE_STRING)}
                )
            ),
            404: "Study group not found"
        }
    )
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        group = self.get_object()
        group.members.remove(request.user)
        return Response({"message": "Successfully left the group"})

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint to verify API status and configuration
    """
    status = {
        'status': 'healthy',
        'debug': settings.DEBUG,
        'openai_configured': bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != 'sk-your_openai_api_key_here'),
        'database': 'connected',
    }
    
    # Test database connection
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        status['database'] = 'connected'
    except Exception as e:
        status['database'] = f'error: {str(e)}'
        status['status'] = 'degraded'
    
    # Test OpenAI configuration (without making actual API call)
    if not status['openai_configured']:
        status['openai_status'] = 'not_configured'
        status['openai_message'] = 'Add OPENAI_API_KEY to .env file'
    else:
        status['openai_status'] = 'configured'
        status['openai_message'] = 'API key is set'
    
    return Response(status)