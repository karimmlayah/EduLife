from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
import logging
from .ml_module.generator import MotivationLetterGenerator
from offreStage.models import OffreStage

logger = logging.getLogger(__name__)

# Create your views here.

@csrf_exempt
@require_POST
def generate_motivation_letter_api(request):
    """
    API endpoint to generate a personalized motivation letter using Hybrid AI.
    """
    try:
        data = json.loads(request.body)
        offre_id = data.get('offre_id')
        
        if not offre_id:
            return JsonResponse({"success": False, "error": "Missing offre_id"}, status=400)
            
        # Fetch internship details
        offre = get_object_or_404(OffreStage, id_offre=offre_id)
        
        # Initialize generator
        generator = MotivationLetterGenerator()
        
        # Generate letter
        letter = generator.generate(
            title=offre.titre,
            description=offre.description,
            domain=offre.domaine
        )
        
        return JsonResponse({
            "success": True,
            "letter": letter
        })
        
    except Exception as e:
        logger.error(f"Error generating letter: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
