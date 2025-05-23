from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Profile, StudyMaterial, Question, Answer, 
    QuizAttempt, UserAnswer, Transaction, StudyGroup, Course
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = ['id', 'user', 'wallet_address', 'subscription_status', 'subscription_expiry']

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'answer_text', 'is_correct']

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'difficulty', 'explanation', 'answers']

class StudyMaterialSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField()
    course_name = serializers.CharField(source='course.name', read_only=True)
    
    class Meta:
        model = StudyMaterial
        fields = ['id', 'title', 'description', 'file', 'file_type', 'course', 'course_name', 'processed', 'created_at', 'questions_count']
        read_only_fields = ['file_type']
    
    def get_questions_count(self, obj):
        return obj.questions.count()

class CourseSerializer(serializers.ModelSerializer):
    study_materials_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'study_materials_count']
    
    def get_study_materials_count(self, obj):
        return obj.study_materials.count()

class CourseDetailSerializer(CourseSerializer):
    study_materials = StudyMaterialSerializer(many=True, read_only=True)
    
    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ['study_materials']

class StudyMaterialDetailSerializer(StudyMaterialSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta(StudyMaterialSerializer.Meta):
        fields = StudyMaterialSerializer.Meta.fields + ['questions']

class UserAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    
    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'question_text', 'answer', 'text_answer', 'is_correct']

class QuizAttemptSerializer(serializers.ModelSerializer):
    user_answers = UserAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = ['id', 'study_material', 'start_time', 'end_time', 'score', 'is_completed', 'user_answers']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'transaction_type', 'wallet_address', 'transaction_hash', 'status', 'created_at']

class StudyGroupSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StudyGroup
        fields = ['id', 'name', 'description', 'creator', 'members', 'member_count', 'created_at']
    
    def get_member_count(self, obj):
        return obj.members.count()

class ExamSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = StudyMaterial
        fields = ['id', 'title', 'description', 'questions'] 