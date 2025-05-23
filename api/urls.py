from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, ProfileViewSet, StudyMaterialViewSet, 
    QuestionViewSet, QuizAttemptViewSet, TransactionViewSet,
    StudyGroupViewSet, ConnectWalletView, CourseViewSet, health_check
)
from .dashboard import DashboardView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'study-materials', StudyMaterialViewSet, basename='study-material')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'quiz-attempts', QuizAttemptViewSet, basename='quiz-attempt')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'study-groups', StudyGroupViewSet, basename='study-group')
router.register(r'courses', CourseViewSet, basename='course')

urlpatterns = [
    path('', include(router.urls)),
    path('connect-wallet/', ConnectWalletView.as_view(), name='connect-wallet'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('health/', health_check, name='health-check'),
] 