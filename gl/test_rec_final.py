import os
import sys
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gl.settings")
django.setup()

from django.contrib.auth import get_user_model
from LogementApp.models import Logement, BinomeRequest
from LogementApp.recommendation import RecommendationEngine

User = get_user_model()

def test_recommendation():
    print("--- Starting Recommendation Test ---")
    
    # 1. Create a test user
    user_email = "test_rec_user_final@example.com"
    # Delete if exists to ensure clean state
    User.objects.filter(email=user_email).delete()
    
    user = User.objects.create_user(username="test_rec_user_final", email=user_email, password="password123")
    print(f"Created test user: {user.username}")

    # 2. Create a BinomeRequest for this user
    # Looking for a room in "Tunis" with budget 500
    req = BinomeRequest.objects.create(
        user=user,
        title="Search in Tunis",
        city="Tunis",
        budget_max=500,
        description="Looking for a quiet room with wifi",
        status='PENDING'
    )
    print(f"User preferences set: City={req.city}, Budget={req.budget_max}")

    # 3. Create some dummy Logements
    # Match: Tunis, 450 DT
    log1 = Logement.objects.create(
        title="Appartement Tunis Centre Test",
        owner=user, 
        description="Quiet place with wifi",
        city="Tunis",
        price=450,
        surface=50,
        rooms=2,
        address="123 Rue de Tunis",
        type_logement="APPARTEMENT",
        approved=True,
        available=True
    )
    
    # Partial Match: Tunis, 800 DT (Over budget)
    log2 = Logement.objects.create(
        title="Luxe Tunis Test",
        owner=user,
        description="Luxe apartment",
        city="Tunis",
        price=800,
        surface=100,
        rooms=4,
        address="456 Avenue Bourguiba",
        type_logement="APPARTEMENT",
        approved=True,
        available=True
    )

    # No Match: Sousse, 400 DT
    log3 = Logement.objects.create(
        title="Studio Sousse Test",
        owner=user,
        description="Nice beach view",
        city="Sousse",
        price=400,
        surface=30,
        rooms=1,
        address="789 Route de la Plage",
        type_logement="STUDIO",
        approved=True,
        available=True
    )
    
    # 4. Run Recommendation Engine
    engine = RecommendationEngine()
    recs = engine.get_recommendations(user, limit=5)
    
    print(f"\nRecommendations found: {len(recs)}")
    found_match = False
    for i, housing in enumerate(recs):
        print(f"{i+1}. {housing.title} - {housing.city} - {housing.price} DT")
        if hasattr(housing, 'match_reasons'):
            print(f"   Reasons: {housing.match_reasons}")
        
        if housing.title == "Appartement Tunis Centre Test" and i == 0:
            found_match = True

    # Assertions
    if found_match:
        print("\n✅ TEST PASSED: Best match is first.")
        if hasattr(recs[0], 'match_reasons') and len(recs[0].match_reasons) > 0:
             print("✅ TEST PASSED: Reasons are present.")
        else:
             print("❌ TEST FAILED: Reasons missing.")
    else:
        print("\n❌ TEST FAILED: Best match is not first.")

    # Cleanup
    print("Cleaning up...")
    log1.delete()
    log2.delete()
    log3.delete()
    req.delete()
    user.delete()

if __name__ == "__main__":
    try:
        test_recommendation()
    except Exception as e:
        print(f"❌ Error: {e}")
