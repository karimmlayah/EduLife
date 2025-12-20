import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class MockLogement:
    def __init__(self, id, title, description, city, price, type_logement="APPARTEMENT"):
        self.id = id
        self.title = title
        self.description = description
        self.city = city
        self.price = price
        self.type_logement = type_logement

class MockEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))

    def get_recommendations(self, candidates, prefs, limit=5):
        logement_texts = [f"{l.title} {l.description} {l.city} {l.type_logement}" for l in candidates]
        user_text = prefs['text_query']

        all_texts = logement_texts + [user_text]
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)
        cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()

        scored_logements = []
        max_budget = prefs['budget_max']

        for i, logement in enumerate(candidates):
            text_score = cosine_sim[i]
            city_boost = 1.0
            if prefs['city'] and logement.city:
                if prefs['city'].lower() == logement.city.lower():
                    city_boost = 1.5
            
            budget_score = 1.0
            if logement.price and max_budget:
                if logement.price > max_budget:
                    diff_ratio = (logement.price - max_budget) / max_budget
                    budget_score = max(0.1, 1.0 - diff_ratio)
            
            final_score = text_score * city_boost * budget_score
            logement.match_score = round(final_score * 100, 2)
            scored_logements.append(logement)

        scored_logements.sort(key=lambda x: x.match_score, reverse=True)
        return scored_logements[:limit]

# Test cases
candidates = [
    MockLogement(1, "Studio calme", "Beau studio avec wifi et balcon", "Tunis", 500, "STUDIO"),
    MockLogement(2, "Appartement luxe", "Grand appartement vue mer", "Sousse", 1500, "APPARTEMENT"),
    MockLogement(3, "Chambre etudiant", "Petite chambre proche fac avec wifi", "Tunis", 300, "AUTRE")
]

prefs = {
    'city': "Tunis",
    'budget_max': 600,
    'text_query': "wifi proche fac"
}

engine = MockEngine()
recs = engine.get_recommendations(candidates, prefs)

print("--- ML Recommendation Test Results ---")
for r in recs:
    print(f"[{r.match_score}] {r.title} in {r.city} - {r.price} DT")

assert recs[0].id == 3, "Should recommend the student room first due to 'proche fac' and budget"
assert recs[1].id == 1, "Should recommend the studio second due to 'wifi' and city match"
print("\n✅ Test passed!")
