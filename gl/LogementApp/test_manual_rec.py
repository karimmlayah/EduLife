import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gl.settings")
django.setup()

from django.contrib.auth import get_user_model
from LogementApp.models import Logement, BinomeRequest
from LogementApp.recommendation import RecommendationEngine

User = get_user_model()

def test_recommendation():
    print("--- Starting Recommendation Test ---")
    
    # 1. Create a test user
    user_email = "test_rec_user@example.com"
    user, created = User.objects.get_or_create(username="test_rec_user", email=user_email)
    if created:
        user.set_password("password123")
        user.save()
        print(f"Created test user: {user.username}")
    else:
        print(f"Using existing test user: {user.username}")

    # 2. Create a BinomeRequest for this user
    # Looking for a room in "Tunis" with budget 500
    req, _ = BinomeRequest.objects.get_or_create(
        user=user,
        defaults={
            'title': "Search in Tunis",
            'city': "Tunis",
            'budget_max': 500,
            'description': "Looking for a quiet room with wifi"
        }
    )
    # Ensure it's pending
    req.status = 'PENDING'
    req.save()
    print(f"User preferences set: City={req.city}, Budget={req.budget_max}")

    # 3. Create some dummy Logements
    # Match: Tunis, 450 DT
    log1, _ = Logement.objects.get_or_create(
        title="Appartement Tunis Centre",
        owner=user, # Owner doesn't matter for this test
        defaults={
            'description': "Quiet place with wifi",
            'city': "Tunis",
            'price': 450,
            'approved': True,
            'available': True
        }
    )
    
    # Partial Match: Tunis, 800 DT (Over budget)
    log2, _ = Logement.objects.get_or_create(
        title="Luxe Tunis",
        owner=user,
        defaults={ 
            'description': "Luxe apartment",
            'city': "Tunis",
            'price': 800,
            'approved': True,
            'available': True
        }
    )

    # No Match: Sousse, 400 DT
    log3, _ = Logement.objects.get_or_create(
        title="Studio Sousse",
        owner=user,
        defaults={
            'description': "Nice beach view",
            'city': "Sousse",
            'price': 400,
            'approved': True,
            'available': True
        }
    )
    
    # 4. Run Recommendation Engine
    engine = RecommendationEngine()
    recs = engine.get_recommendations(user, limit=5)
    
    print(f"\nRecommendations found: {len(recs)}")
    for i, housing in enumerate(recs):
        print(f"{i+1}. {housing.title} - {housing.city} - {housing.price} DT")

    # Assertions
    if len(recs) > 0 and recs[0].title == "Appartement Tunis Centre":
        print("\n✅ TEST PASSED: Best match is first.")
    else:
        print("\n❌ TEST FAILED: Best match is not first.")

if __name__ == "__main__":
    try:
        test_recommendation()
    except Exception as e:
        print(f"❌ Error: {e}")
