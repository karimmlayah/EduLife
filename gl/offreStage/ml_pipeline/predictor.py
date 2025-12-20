"""
Service de prédiction pour le modèle ML
Charge le modèle et fait des prédictions de rémunération
"""

import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

class RemunerationPredictor:
    """Service pour prédire la rémunération d'une offre"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.le_domaine = None
        self.le_lieu = None
        self.feature_columns = None
        self.metrics = None
        self.domain_avg_remuneration = None  # Moyennes MENSUELLES par domaine
        self.lieu_avg_remuneration = None  # Moyennes MENSUELLES par lieu
        self.load_model()
    
    def load_model(self):
        """Charge le modèle et les préprocesseurs depuis le fichier unique"""
        # Obtenir le chemin du fichier actuel
        current_file = os.path.abspath(__file__)
        # Remonter jusqu'à la racine du projet (gl/)
        # predictor.py est dans: gl/offreStage/ml_pipeline/predictor.py
        # On veut: gl/offreStage/ml_pipeline/models/ml_model.pkl
        ml_pipeline_dir = os.path.dirname(current_file)  # gl/offreStage/ml_pipeline/
        models_dir = os.path.join(ml_pipeline_dir, 'models')  # gl/offreStage/ml_pipeline/models/
        model_file = os.path.join(models_dir, 'ml_model.pkl')
        
        # Vérifier si le fichier existe
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Modèle non trouvé: {model_file}. Exécutez d'abord ml_pipeline_complete.py")
        
        try:
            # Charger tout d'un coup
            ml_data = joblib.load(model_file)
            
            self.model = ml_data['model']
            self.scaler = ml_data['scaler']
            self.le_domaine = ml_data['label_encoder_domaine']
            self.le_lieu = ml_data['label_encoder_lieu']
            self.feature_columns = ml_data['feature_columns']
            self.metrics = ml_data.get('metrics', {})
            # Charger les moyennes MENSUELLES pour les features dérivées
            self.domain_avg_remuneration = ml_data.get('domain_avg_remuneration', {})
            self.lieu_avg_remuneration = ml_data.get('lieu_avg_remuneration', {})
            
        except Exception as e:
            raise Exception(f"Erreur lors du chargement du modèle: {str(e)}")
    
    def predict(self, offre_data):
        """
        Prédit la rémunération pour une offre
        
        Le modèle prédit une rémunération MENSUELLE, puis on multiplie par le nombre de mois.
        
        Args:
            offre_data (dict): Dictionnaire contenant:
                - domaine (str): Domaine de l'offre
                - lieu (str): Lieu de l'offre
                - duree (int): Durée en semaines
                - description (str): Description de l'offre
                - titre (str): Titre de l'offre
                - has_image (bool): Si l'offre a une image
                - visibilite (bool): Si l'offre est visible
                - date_publication (datetime ou str): Date de publication
                - etat (str, optionnel): État de l'offre
        
        Returns:
            float: Rémunération totale prédite en DT (rémunération mensuelle × nombre de mois)
        """
        if self.model is None:
            raise ValueError("Modèle non chargé")
        
        # Préparer les features
        features = self._prepare_features(offre_data)
        
        # Prédire la rémunération MENSUELLE
        remuneration_mensuelle_brute = self.model.predict(features.reshape(1, -1))[0]
        
        # Limiter la rémunération mensuelle à une plage réaliste
        # Basé sur les données: rémunération mensuelle entre ~200 et ~2000 DT/mois
        # Les moyennes par domaine varient de ~967 (Commerce) à ~1497 (Informatique) DT/mois
        MIN_REMUNERATION_MENSUELLE = 200
        MAX_REMUNERATION_MENSUELLE = 2000
        
        remuneration_mensuelle = max(MIN_REMUNERATION_MENSUELLE, min(remuneration_mensuelle_brute, MAX_REMUNERATION_MENSUELLE))
        
        # Convertir la durée en mois (1 mois ≈ 4.33 semaines)
        duree_semaines = offre_data.get('duree', 0)
        duree_mois = duree_semaines / 4.33
        
        # Calculer la rémunération totale = rémunération mensuelle × nombre de mois
        remuneration_totale = remuneration_mensuelle * duree_mois
        
        return round(remuneration_totale, 2)
    
    def _prepare_features(self, offre_data):
        """Prépare les features pour la prédiction"""
        # Créer un DataFrame temporaire
        # NOTE: nb_postulations et nb_favoris ne sont pas inclus car ils ne sont
        # pas disponibles lors de la création d'une nouvelle offre
        # Créer un DataFrame avec les features (SANS les features liées à la durée)
        df = pd.DataFrame([{
            'domaine': offre_data.get('domaine', ''),
            'lieu': offre_data.get('lieu', ''),
            'description_length': len(offre_data.get('description', '')),
            'titre_length': len(offre_data.get('titre', '')),
            'has_image': 1 if offre_data.get('has_image', False) else 0,
            'visibilite': 1 if offre_data.get('visibilite', True) else 0,
            'etat_encoded': 1 if offre_data.get('etat', 'disponible') == 'disponible' else 0,
        }])
        
        # Feature engineering: variables temporelles
        date_pub = pd.to_datetime(offre_data.get('date_publication', datetime.now()))
        df['month'] = date_pub.month
        df['day_of_week'] = date_pub.dayofweek
        df['is_weekend'] = 1 if date_pub.dayofweek >= 5 else 0
        
        # Feature engineering: domain_avg_remuneration (moyenne MENSUELLE)
        domaine = offre_data.get('domaine', '')
        if self.domain_avg_remuneration and domaine in self.domain_avg_remuneration:
            df['domain_avg_remuneration'] = self.domain_avg_remuneration[domaine]
        else:
            # Valeur par défaut si le domaine n'existe pas (moyenne mensuelle générale)
            df['domain_avg_remuneration'] = 800.0  # Moyenne mensuelle générale
        
        # Feature engineering: lieu_avg_remuneration (moyenne MENSUELLE)
        lieu = offre_data.get('lieu', '')
        if self.lieu_avg_remuneration and lieu in self.lieu_avg_remuneration:
            df['lieu_avg_remuneration'] = self.lieu_avg_remuneration[lieu]
        else:
            # Valeur par défaut si le lieu n'existe pas (moyenne mensuelle générale)
            df['lieu_avg_remuneration'] = 800.0  # Moyenne mensuelle générale
        
        # Encodage
        try:
            df['domaine_encoded'] = self.le_domaine.transform([domaine])[0]
        except ValueError:
            # Si le domaine n'existe pas dans le training, utiliser 0
            df['domaine_encoded'] = 0
        
        try:
            df['lieu_encoded'] = self.le_lieu.transform([lieu])[0]
        except ValueError:
            df['lieu_encoded'] = 0
        
        # Vérifier que toutes les colonnes nécessaires sont présentes
        missing_cols = [col for col in self.feature_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colonnes manquantes dans le DataFrame: {missing_cols}. Colonnes disponibles: {list(df.columns)}")
        
        # Sélectionner les features dans le bon ordre
        features = df[self.feature_columns].values[0]
        
        # Normaliser (si le modèle l'utilise)
        if hasattr(self.model, 'feature_importances_'):  # Random Forest
            return features
        else:  # Linear Regression
            return self.scaler.transform(features.reshape(1, -1))[0]


# Instance globale pour le déploiement (singleton)
_predictor_instance = None

def get_predictor():
    """Retourne l'instance du prédicteur (singleton)"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = RemunerationPredictor()
    return _predictor_instance

def reload_predictor():
    """Force le rechargement du modèle (utile après réentraînement)"""
    global _predictor_instance
    _predictor_instance = None
    return get_predictor()

