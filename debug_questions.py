import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import StudyMaterial
from api.services.ai_service import generate_questions, extract_text_from_file
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_question_generation():
    """Debug the question generation process"""
    print("=== Question Generation Debug Script ===")
    
    # Get all study materials
    materials = StudyMaterial.objects.all()
    print(f"Found {materials.count()} study materials")
    
    if not materials.exists():
        print("No study materials found. Please upload some materials first.")
        return
    
    for material in materials:
        print(f"\n--- Material: {material.title} ---")
        print(f"ID: {material.id}")
        print(f"File: {material.file.name}")
        print(f"File Type: {material.file_type}")
        print(f"Processed: {material.processed}")
        print(f"Existing Questions: {material.questions.count()}")
        
        # Check if file exists
        if not os.path.exists(material.file.path):
            print(f"ERROR: File does not exist at {material.file.path}")
            continue
            
        # Test text extraction
        print(f"Testing text extraction...")
        try:
            text = extract_text_from_file(material.file.path, material.file_type)
            if text:
                print(f"Text extracted: {len(text)} characters")
                print(f"First 200 characters: {text[:200]}...")
                
                # Test question generation
                print(f"Testing question generation...")
                success = generate_questions(material.id)
                
                # Check results
                material.refresh_from_db()
                new_count = material.questions.count()
                print(f"Generation success: {success}")
                print(f"Questions after generation: {new_count}")
                
                if new_count > 0:
                    print("Sample questions:")
                    for i, question in enumerate(material.questions.all()[:2], 1):
                        print(f"  {i}. {question.question_text}")
                        for answer in question.answers.all():
                            marker = " ✓" if answer.is_correct else ""
                            print(f"     - {answer.answer_text}{marker}")
                else:
                    print("No questions were generated!")
                    
            else:
                print("ERROR: No text could be extracted from file")
                
        except Exception as e:
            print(f"ERROR during processing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_question_generation() 