from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
from .utils import get_chat_response

@method_decorator(csrf_exempt, name='dispatch')
class ChatbotView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_message = data.get('message')
            history = data.get('history', [])
            
            if not user_message:
                return JsonResponse({'error': 'Message is required'}, status=400)
            
            # Call the util function
            response_text = get_chat_response(history, user_message)
            
            return JsonResponse({'response': response_text})
        except Exception as e:
            # Return error details for debugging
            return JsonResponse({'error': str(e)}, status=500)
