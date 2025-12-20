import os
import requests
import json
from django.conf import settings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class MotivationLetterGenerator:
    """
    Hybrid AI Generator for Motivation Letters.
    Phase 1: Domain-based Template Selection (Local ML logic)
    Phase 2: LLM Personalization (Groq API)
    """

    TEMPLATES = {
        "informatique": {
            "name": "Technical/Software Engineering",
            "structure": "Focused on technologies, projects, and problem-solving skills.",
            "keywords": ["python", "java", "coding", "software", "development", "it", "technique", "développement"]
        },
        "finance": {
            "name": "Finance/Accounting",
            "structure": "Focused on rigor, analytical skills, and attention to detail.",
            "keywords": ["finance", "comptabilité", "audit", "banque", "chiffres", "analytique", "excel"]
        },
        "marketing": {
            "name": "Marketing/Communication",
            "structure": "Focused on creativity, social media, and communication strategy.",
            "keywords": ["marketing", "communication", "réseaux sociaux", "stratégie", "créatif", "digital"]
        },
        "management": {
            "name": "Management/HR",
            "structure": "Focused on organization, soft skills, and team coordination.",
            "keywords": ["management", "rh", "organisation", "équipe", "coordination", "ressources humaines"]
        },
        "general": {
            "name": "General Internship",
            "structure": "Professional and balanced structure suitable for any domain.",
            "keywords": []
        }
    }

    def __init__(self):
        self.api_key = getattr(settings, "EDUBOT_API_KEY", "")
        self.api_base = getattr(settings, "EDUBOT_API_BASE", "https://api.groq.com/openai/v1")
        self.model = getattr(settings, "EDUBOT_MODEL", "llama-3.1-8b-instant")
        
        # Prepare vectorizer for domain matching
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.domain_keys = list(self.TEMPLATES.keys())
        self.domain_texts = [" ".join(self.TEMPLATES[d]["keywords"]) for d in self.domain_keys]

    def _select_template_modele(self, title, description, domain_input):
        """
        Modele IA : Sélectionne le template le plus adapté en utilisant la similarité textuelle.
        """
        input_text = f"{title} {description} {domain_input}".lower()
        
        if not any(self.domain_texts): # Fallback if keywords are missing
            return self.TEMPLATES["general"]

        try:
            # Vectorize templates and input
            tfidf_matrix = self.vectorizer.fit_transform(self.domain_texts + [input_text])
            
            # Compute similarity between the last (input) and others
            similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
            
            best_match_idx = similarities.argmax()
            
            # If similarity is too low, fallback to general
            if similarities[best_match_idx] < 0.1:
                return self.TEMPLATES["general"]
                
            return self.TEMPLATES[self.domain_keys[best_match_idx]]
        except:
            return self.TEMPLATES["general"]

    def generate(self, title, description, domain, user_context=None):
        """Generates the personalized letter using Hybrid approach."""
        
        # Phase 1: Local Model Selection
        selected_template = self._select_template_modele(title, description, domain)
        
        if not self.api_key:
            raise Exception("Groq API Key not configured.")

        # Phase 2: LLM Generation
        prompt = f"""
        Generate a professional motivation letter in French for the following internship:
        Title: {title}
        Domain: {domain}
        Description: {description}
        
        Template Strategy: Use a {selected_template['name']} structure. {selected_template['structure']}
        
        Context: The user is a student applying via the EduLife platform.
        Requirements:
        1. Professional tone.
        2. Keep it between 250 and 400 words.
        3. Do not include placeholders like [Name] or [Date] if you don't have them, just leave space or use generic polite forms.
        4. Focus on matching the user's potential skills with the internship requirements.
        
        Structure your response as a standard motivation letter (Header, Purpose, Body, Conclusion).
        """

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Tu es un coach de carrière expert en rédaction de lettres de motivation."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise Exception(f"AI Generation failed: {str(e)}")
