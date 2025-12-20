import os
import sys
import json
import django
from django.test import RequestFactory
from unittest.mock import MagicMock, patch

# Configure Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gl.settings")
django.setup()

from LogementApp.views import predict_price_api
from django.contrib.auth import get_user_model

User = get_user_model()

def test_prediction_api():
    print("--- Testing Prediction API ---")
    
    # Setup
    factory = RequestFactory()
    user = User.objects.create_user(username='pred_test_user', password='password')
    
    # Check ML Service first (mocking it if model missing, but let's try real if available)
    # We will mock predict_price to isolate View testing from ML model existence
    with patch('LogementApp.views.predict_price') as mock_predict:
        mock_predict.return_value = 1200
        
        # Test Case 1: Valid Request
        data = {
            'city': 'Tunis',
            'surface': 100,
            'rooms': 3,
            'type': 'APPARTEMENT',
            'bathrooms': 1
        }
        
        request = factory.post(
            '/logement/predict-price/', 
            data=json.dumps(data), 
            content_type='application/json'
        )
        request.user = user
        
        response = predict_price_api(request)
        print(f"Status: {response.status_code}")
        content = json.loads(response.content)
        print(f"Response: {content}")
        
        if response.status_code == 200 and content.get('price') == 1200:
            print("✅ Valid request passed")
        else:
            print("❌ Valid request failed")

        # Test Case 2: Missing Fields
        bad_data = {'city': 'Tunis'} # Missing surface etc
        request = factory.post(
            '/logement/predict-price/', 
            data=json.dumps(bad_data), 
            content_type='application/json'
        )
        request.user = user
        
        response = predict_price_api(request)
        if response.status_code == 400:
             print("✅ Missing field handled correctly")
        else:
             print(f"❌ Missing field failed with {response.status_code}")

    # Cleanup
    user.delete()

if __name__ == "__main__":
    try:
        test_prediction_api()
    except Exception as e:
        print(f"❌ Error: {e}")
