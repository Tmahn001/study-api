from django.contrib import admin
from .models import Course, StudyMaterial, Question, Answer, QuizAttempt, UserAnswer, Transaction, StudyGroup

# Register your models here.
admin.site.register(Course)
admin.site.register(StudyMaterial)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(QuizAttempt)
admin.site.register(UserAnswer)

