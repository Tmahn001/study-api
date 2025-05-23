from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    wallet_address = models.CharField(max_length=255, blank=True, null=True)
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('FREE', 'Free'),
            ('PREMIUM', 'Premium'),
            ('TRIAL', 'Trial')
        ],
        default='FREE'
    )
    subscription_expiry = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"

class Course(models.Model):
    """
    A course created by a user that can contain multiple study materials.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class StudyMaterial(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_materials')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='study_materials', null=True, blank=True)
    file = models.FileField(upload_to='study_materials/')
    file_type = models.CharField(
        max_length=10,
        choices=[
            ('PDF', 'PDF'),
            ('DOCX', 'DOCX'),
            ('TXT', 'TXT'),
            ('PPTX', 'PPTX'),
            ('OTHER', 'Other')
        ]
    )
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class Question(models.Model):
    study_material = models.ForeignKey(StudyMaterial, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=[
            ('MULTIPLE_CHOICE', 'Multiple Choice'),
            ('SHORT_ANSWER', 'Short Answer'),
            ('ESSAY', 'Essay')
        ]
    )
    difficulty = models.CharField(
        max_length=10,
        choices=[
            ('EASY', 'Easy'),
            ('MEDIUM', 'Medium'),
            ('HARD', 'Hard')
        ],
        default='MEDIUM'
    )
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.question_text[:30]}..."

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.answer_text[:30]}..."

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    study_material = models.ForeignKey(StudyMaterial, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username}'s attempt on {self.study_material.title}"

class UserAnswer(models.Model):
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    
    def __str__(self):
        return f"Answer to {self.question}"

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('SUBSCRIPTION', 'Subscription'),
            ('PAY_PER_USE', 'Pay Per Use')
        ]
    )
    wallet_address = models.CharField(max_length=255)
    transaction_hash = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed')
        ],
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s transaction of {self.amount}"

class StudyGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(User, related_name='study_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
