import logging
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Q
from .models import Logement, BinomeRequest

logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english', # Or use a list of French stop words if available
            ngram_range=(1, 2),
            min_df=1
        )

    def get_user_preferences(self, user):
        """
        Extract user preferences from their most recent BinomeRequest.
        """
        prefs = {
            'city': None,
            'budget_max': None,
            'text_query': ""
        }

        latest_request = BinomeRequest.objects.filter(
            user=user, 
            status='PENDING'
        ).order_by('-created_at').first()

        if latest_request:
            prefs['city'] = latest_request.city
            prefs['budget_max'] = float(latest_request.budget_max) if latest_request.budget_max else None
            # Combine title and description for a richer search vector
            prefs['text_query'] = f"{latest_request.title or ''} {latest_request.description or ''}".strip()
        else:
            # Fallback to user profile
            if hasattr(user, 'city') and user.city:
                prefs['city'] = user.city
            if hasattr(user, 'bio') and user.bio:
                prefs['text_query'] = user.bio
            
            prefs['budget_max'] = 2000 # Higher default fallback

        return prefs

    def get_recommendations(self, user, limit=5):
        """
        Get recommended logements for a user using Content-Based ML Filtering.
        """
        if not user.is_authenticated:
            return Logement.objects.filter(available=True, approved=True).order_by('-created_at')[:limit]

        prefs = self.get_user_preferences(user)
        
        # 1. Base filtering (pre-filter to reduce computation if needed)
        # We still want to prioritize the city if specified
        candidates_qs = Logement.objects.filter(available=True, approved=True)
        
        if not candidates_qs.exists():
            return []

        candidates = list(candidates_qs)
        
        # 2. Prepare Textual Data for ML
        # We'll match user's text_query against logement's title + description
        logement_texts = [f"{l.title} {l.description} {l.city} {l.type_logement}" for l in candidates]
        user_text = prefs['text_query']

        if not user_text and not prefs['city']:
            return candidates[:limit]

        try:
            # 3. Vectorization & Similarity
            all_texts = logement_texts + [user_text]
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Cosine similarity between the last element (user) and everything else
            cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()

            # 4. Numerical Scoring & Final Ranking
            scored_logements = []
            max_budget = prefs['budget_max'] or 10000

            for i, logement in enumerate(candidates):
                text_score = cosine_sim[i]
                
                # Boost if city matches exactly
                city_boost = 1.0
                if prefs['city'] and logement.city:
                    if prefs['city'].lower() == logement.city.lower():
                        city_boost = 1.5
                    elif prefs['city'].lower() in logement.city.lower():
                        city_boost = 1.2

                # Budget penalty (soft constraint)
                budget_score = 1.0
                if logement.price and max_budget:
                    price = float(logement.price)
                    if price > max_budget:
                        # Gradually reduce score if over budget
                        diff_ratio = (price - max_budget) / max_budget
                        budget_score = max(0.1, 1.0 - diff_ratio)
                
                final_score = text_score * city_boost * budget_score
                
                logement.match_score = round(final_score * 100, 2)
                logement.match_reasons = self._generate_reasons(logement, prefs, text_score)
                scored_logements.append(logement)

            # Sort by score descending
            scored_logements.sort(key=lambda x: x.match_score, reverse=True)
            return scored_logements[:limit]

        except Exception as e:
            logger.error(f"ML Recommendation Error: {e}", exc_info=True)
            # Fallback to simple filtering
            return candidates[:limit]

    def _generate_reasons(self, logement, prefs, text_score):
        reasons = []
        if text_score > 0.1:
            reasons.append("✨ Correspond à vos critères textuels")
        if prefs['city'] and logement.city and prefs['city'].lower() == logement.city.lower():
            reasons.append("📍 Idéalement situé")
        if logement.price and prefs['budget_max'] and float(logement.price) <= prefs['budget_max']:
            reasons.append("💰 Parfaitement dans votre budget")
        return reasons

