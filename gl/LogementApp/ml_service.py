"""
Service pour la prédiction du prix des logements avec le modèle ML
Compatible avec un Pipeline sklearn (ColumnTransformer + modèle)
"""

import joblib
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

# ======================================================
# 📦 CHEMIN DU MODÈLE
# ======================================================

MODEL_PATH = Path(__file__).parent / "ml_models" / "rent_price_model.joblib"

_loaded_model = None


# ======================================================
# 🔄 CHARGEMENT DU MODÈLE (UNE FOIS)
# ======================================================

def load_model():
    global _loaded_model

    if _loaded_model is not None:
        return _loaded_model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modèle introuvable : {MODEL_PATH}")

    try:
        _loaded_model = joblib.load(MODEL_PATH)
        logger.info(f"✅ Modèle ML chargé depuis {MODEL_PATH}")
        return _loaded_model

    except AttributeError as e:
        msg = (
            "❌ Incompatibilité scikit-learn.\n"
            "Le modèle a été entraîné avec sklearn 1.6.1.\n"
            "Installe exactement cette version :\n"
            "pip install scikit-learn==1.6.1"
        )
        logger.error(msg)
        raise ValueError(msg) from e


# ======================================================
# 🔮 PRÉDICTION DU PRIX (SIGNATURE ALIGNÉE AU PIPELINE)
# ======================================================

def predict_price(*, city, region, surface, bathrooms, rooms, logement_type):
    """
    Prédit le prix mensuel d'un logement (DT/mois)
    """
    try:
        model = load_model()

        # ⚠️ DataFrame IDENTIQUE à l'entraînement
        X = pd.DataFrame([{
            "city": city,
            "region": region,
            "surface": float(surface),
            "bathrooms": int(bathrooms),
            "rooms": int(rooms),
            "type": logement_type
        }])

        prediction = model.predict(X)[0]
        predicted_price = max(0, float(prediction))

        logger.info(
            f"🏠 Prédiction OK | {city} | {surface}m² | {rooms}p → {predicted_price} DT"
        )

        return round(predicted_price, 0)

    except Exception as e:
        logger.error("❌ Erreur lors de la prédiction ML", exc_info=True)
        raise ValueError(f"Erreur lors de la prédiction du prix : {e}")
