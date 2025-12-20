import sys
from unittest.mock import MagicMock, patch

# Mock Django dependencies before importing the generator
sys.modules['django.conf'] = MagicMock()
sys.modules['django.conf'].settings = MagicMock()
sys.modules['django.conf'].settings.EDUBOT_API_KEY = "test_key"
sys.modules['django.conf'].settings.EDUBOT_API_BASE = "https://api.groq.com/openai/v1"
sys.modules['django.conf'].settings.EDUBOT_MODEL = "llama-3.1-8b-instant"

from postulation.ml_module.generator import MotivationLetterGenerator

def test_generator():
    print("--- Testing Hybrid AI Motivation Letter Generator (Standalone) ---")
    
    generator = MotivationLetterGenerator()
    
    # Fake internship details
    test_cases = [
        {
            "title": "Stagiaire Développeur Python",
            "domain": "Informatique",
            "description": "Nous cherchons un stagiaire pour développer des scripts d'automatisation en Python et Django."
        },
        {
            "title": "Assistant Comptable",
            "domain": "Finance",
            "description": "Aider à la saisie des factures et au rapprochement bancaire."
        }
    ]
    
    for case in test_cases:
        print(f"\nProcessing: {case['title']} ({case['domain']})")
        # Check template selection logic
        template = generator._select_template_modele(case['title'], case['description'], case['domain'])
        print(f"Structure selected: {template['name']}")
        
        # Mock requests.post to avoid actual API calls in this logic test
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "Cher recruteur, je suis très motivé par ce stage..."}}]
            }
            mock_post.return_value.status_code = 200
            
            letter = generator.generate(case['title'], case['description'], case['domain'])
            print(f"Letter Generated: {letter[:50]}...")
            if "motivé" in letter:
                print("✅ Generation flow verified!")

if __name__ == "__main__":
    test_generator()
