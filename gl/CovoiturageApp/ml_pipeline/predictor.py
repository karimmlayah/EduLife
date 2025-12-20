"""
Service de prédiction pour le modèle ML de prix de covoiturage
"""

import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

class PrixCovoituragePredictor:
    """Service pour prédire le prix d'un trajet de covoiturage"""
    
    def __init__(self):
        self.pipeline = None
        self.load_model()
    
    def load_model(self):
        """Charge le modèle depuis le fichier .pkl"""
        current_file = os.path.abspath(__file__)
        ml_pipeline_dir = os.path.dirname(current_file)
        models_dir = os.path.join(ml_pipeline_dir, 'models')
        model_file = os.path.join(models_dir, 'ml_model.pkl')
        
        if not os.path.exists(model_file):
            raise FileNotFoundError(
                f"Modèle non trouvé: {model_file}. "
                f"Exécutez d'abord ml_pipeline_complete.py"
            )
        
        try:
            self.pipeline = joblib.load(model_file)
            print(f"[OK] Modèle chargé depuis: {model_file}")
        except Exception as e:
            raise Exception(f"Erreur lors du chargement du modèle: {str(e)}")
    
    def _extract_day_of_week(self, date_obj):
        """Extrait le jour de la semaine en français depuis un datetime"""
        if date_obj is None:
            return 'lundi'  # Valeur par défaut
        
        jours_fr = {
            0: 'lundi', 1: 'mardi', 2: 'mercredi', 3: 'jeudi',
            4: 'vendredi', 5: 'samedi', 6: 'dimanche'
        }
        return jours_fr.get(date_obj.weekday(), 'lundi')
    
    def _extract_hour(self, date_obj):
        """Extrait l'heure au format HH:MM depuis un datetime"""
        if date_obj is None:
            return '12:00'  # Valeur par défaut
        
        return date_obj.strftime('%H:%M')
    
    def predict(self, offre_data):
        """
        Prédit le prix d'un trajet de covoiturage
        
        Args:
            offre_data (dict): Dictionnaire contenant:
                - depart (str): Ville de départ
                - destination (str): Ville de destination (arrivee)
                - distance_km (float): Distance en km (requis)
                - duration_min (int): Durée en minutes (requis)
                - climatisation (bool): Présence de climatisation
                - date_covoiturage (datetime): Date et heure du trajet
        
        Returns:
            float: Prix prédit arrondi à 2 décimales
        """
        if self.pipeline is None:
            raise Exception("Modèle non chargé. Appelez load_model() d'abord.")
        
        # Extraire jour_semaine et heure de date_covoiturage
        date_obj = offre_data.get('date_covoiturage')
        if isinstance(date_obj, str):
            try:
                # Format: '2024-01-15T14:30' ou '2024-01-15 14:30'
                date_obj = datetime.strptime(date_obj.replace('T', ' '), '%Y-%m-%d %H:%M')
            except:
                try:
                    date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                except:
                    date_obj = None
        elif hasattr(date_obj, 'strftime'):  # C'est déjà un datetime
            pass
        else:
            date_obj = None
        
        jour_semaine = self._extract_day_of_week(date_obj)
        heure = self._extract_hour(date_obj)
        
        # Préparer les données pour la prédiction
        # Ordre des colonnes: depart, arrivee, jour_semaine, heure, distance_km, duration_min, climatisation
        prediction_data = pd.DataFrame([{
            'depart': str(offre_data.get('depart', '')),
            'arrivee': str(offre_data.get('destination', '') or offre_data.get('arrivee', '')),
            'jour_semaine': jour_semaine,
            'heure': heure,
            'distance_km': float(offre_data.get('distance_km', 0)),
            'duration_min': int(offre_data.get('duration_min', 0)),
            'climatisation': 1 if offre_data.get('climatisation', False) else 0
        }])
        
        # Faire la prédiction
        try:
            predicted_price = self.pipeline.predict(prediction_data)[0]
            
            # Arrondir à 2 décimales et s'assurer que c'est positif
            predicted_price = max(0, round(float(predicted_price), 2))
            
            return predicted_price
        except Exception as e:
            raise Exception(f"Erreur lors de la prédiction: {str(e)}")

# Singleton pour éviter de charger le modèle plusieurs fois
_predictor_instance = None

def get_predictor():
    """Retourne l'instance singleton du prédicteur"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = PrixCovoituragePredictor()
    return _predictor_instance

def reload_predictor():
    """Force le rechargement du prédicteur (utile après réentraînement)"""
    global _predictor_instance
    _predictor_instance = PrixCovoituragePredictor()
    return _predictor_instance

