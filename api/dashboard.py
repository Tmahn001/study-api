from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.contrib.auth.models import User
from .models import StudyMaterial, Question, QuizAttempt, StudyGroup

class DashboardView(APIView):
    """
    API endpoint for retrieving dashboard data and statistics.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        current_date = timezone.now()
        
        # Get study statistics
        study_stats = {
            'materials_uploaded': StudyMaterial.objects.filter(user=user).count(),
            'questions_generated': Question.objects.filter(study_material__user=user).count(),
            'practice_exams': QuizAttempt.objects.filter(user=user).count(),
            'study_hours': 0,  # Will calculate below
        }
        
        # Calculate study hours (estimate based on quiz attempts)
        total_minutes = 0
        completed_attempts = QuizAttempt.objects.filter(user=user, is_completed=True, end_time__isnull=False)
        for attempt in completed_attempts:
            if attempt.start_time and attempt.end_time:
                duration = attempt.end_time - attempt.start_time
                total_minutes += duration.total_seconds() / 60
        
        study_stats['study_hours'] = round(total_minutes / 60, 1)  # Convert to hours
        
        # Get recent uploads
        recent_uploads = StudyMaterial.objects.filter(user=user).order_by('-created_at')[:5]
        recent_uploads_data = []
        
        for upload in recent_uploads:
            recent_uploads_data.append({
                'id': upload.id,
                'name': upload.title,
                'date': upload.created_at.strftime('%Y-%m-%d'),
                'questions': upload.questions.count(),
            })
        
        # Get upcoming exams (using incomplete quiz attempts as a proxy)
        upcoming_exams = QuizAttempt.objects.filter(
            user=user, 
            is_completed=False
        ).order_by('start_time')[:3]
        
        upcoming_exams_data = []
        for exam in upcoming_exams:
            questions_count = exam.study_material.questions.count()
            # Estimate duration based on number of questions (2 minutes per question)
            duration_hours = max(1, round(questions_count * 2 / 60, 1))
            
            upcoming_exams_data.append({
                'id': exam.id,
                'title': exam.study_material.title,
                'date': exam.start_time.strftime('%Y-%m-%d'),
                'duration': f"{duration_hours} hours",
                'questionsCount': questions_count,
            })
            
        # Get study groups
        user_study_groups = StudyGroup.objects.filter(members=user)[:4]
        study_groups_data = []
        
        for group in user_study_groups:
            # Determine activity level based on number of members
            member_count = group.members.count()
            if member_count > 10:
                activity = 'High'
            elif member_count > 5:
                activity = 'Medium'
            else:
                activity = 'Low'
                
            study_groups_data.append({
                'id': group.id,
                'name': group.name,
                'members': member_count,
                'activity': activity,
            })
            
        # Get AI study recommendations (placeholder - in a real app would use ML)
        study_recommendations = []
        materials = StudyMaterial.objects.filter(user=user).order_by('-created_at')[:3]
        
        for i, material in enumerate(materials):
            subject = material.title
            # Get a random question from this material to recommend studying
            question = material.questions.first()
            if question:
                priorities = ['high', 'medium', 'low']
                time_estimates = ['45 min', '30 min', '20 min']
                
                study_recommendations.append({
                    'subject': subject,
                    'topic': question.question_text[:30] + '...',
                    'priority': priorities[i % 3],  # Rotate priorities
                    'timeEstimate': time_estimates[i % 3],
                })
        
        # Get leaderboard (placeholder - in a real app would have a scoring system)
        # Find users with completed quiz attempts for leaderboard
        leaderboard_data = []
        top_users = User.objects.annotate(
            completed_exams=Count('quiz_attempts', filter=Q(quiz_attempts__is_completed=True)),
            avg_score=Avg('quiz_attempts__score', filter=Q(quiz_attempts__is_completed=True))
        ).order_by('-completed_exams', '-avg_score')[:5]
        
        for i, top_user in enumerate(top_users):
            # Simulate a streak (in a real app, would track daily activity)
            streak = max(0, 15 - i*2)  # Just a placeholder
            
            # Calculate a score based on completed exams and average score
            score = 0
            if hasattr(top_user, 'avg_score') and top_user.avg_score:
                score = round(top_user.avg_score)
                
            leaderboard_data.append({
                'id': top_user.id,
                'name': top_user.username,
                'score': score,
                'streak': streak,
            })
            
        return Response({
            'study_stats': study_stats,
            'recent_uploads': recent_uploads_data,
            'upcoming_exams': upcoming_exams_data,
            'study_groups': study_groups_data,
            'study_recommendations': study_recommendations,
            'leaderboard': leaderboard_data,
        }) 