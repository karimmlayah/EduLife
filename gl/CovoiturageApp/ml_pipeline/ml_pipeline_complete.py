"""
PIPELINE ML COMPLET - PREDICTION PRIX COVOITURAGE
Basé sur le notebook PRIX_COVOITURAGE.ipynb
"""

import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("PIPELINE ML COMPLET - PREDICTION PRIX COVOITURAGE")
print("=" * 80)

# ============================================================================
# ÉTAPE 1: CHARGEMENT DES DONNÉES
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 1: CHARGEMENT DES DONNEES")
print("=" * 80)

# Chemin du fichier CSV
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, 'data')
csv_file = os.path.join(data_dir, 'covoiturage_price_dataset_v2_3000.csv')

if not os.path.exists(csv_file):
    raise FileNotFoundError(f"Fichier CSV non trouvé: {csv_file}")

df = pd.read_csv(csv_file)
print(f"[OK] Données chargées depuis: {csv_file}")
print(f"[OK] Shape: {df.shape}")
print(f"[OK] Colonnes: {list(df.columns)}")
print(f"\nAperçu des données:")
print(df.head())

# ============================================================================
# ÉTAPE 2: PREPARATION DES FEATURES
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 2: PREPARATION DES FEATURES")
print("=" * 80)

X = df.drop(columns=["prix"])
y = df["prix"]

num_features = [
    "distance_km",
    "duration_min",
    "climatisation"
]

cat_features = [
    "depart",
    "arrivee",
    "jour_semaine",
    "heure"
]

print(f"Features numériques: {num_features}")
print(f"Features catégorielles: {cat_features}")
print(f"Target: prix")

# ============================================================================
# ÉTAPE 3: PREPROCESSING
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 3: PREPROCESSING")
print("=" * 80)

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)
    ],
    remainder="passthrough"  # garde les numériques
)

print("[OK] Preprocessor créé")

# ============================================================================
# ÉTAPE 4: MODÈLE
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 4: CREATION DU MODELE")
print("=" * 80)

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=18,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1
)

print("[OK] RandomForestRegressor créé")

# ============================================================================
# ÉTAPE 5: PIPELINE
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 5: CREATION DU PIPELINE")
print("=" * 80)

pipeline = Pipeline(steps=[
    ("preprocessing", preprocessor),
    ("model", model)
])

print("[OK] Pipeline créé")

# ============================================================================
# ÉTAPE 6: TRAIN/TEST SPLIT
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 6: TRAIN/TEST SPLIT")
print("=" * 80)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

print(f"[OK] Split train/test:")
print(f"   Train: {len(X_train)} échantillons ({len(X_train)/len(X)*100:.1f}%)")
print(f"   Test: {len(X_test)} échantillons ({len(X_test)/len(X)*100:.1f}%)")

# ============================================================================
# ÉTAPE 7: ENTRAÎNEMENT
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 7: ENTRAINEMENT")
print("=" * 80)

print("[INFO] Démarrage de l'entraînement...")
print("[INFO] Cela peut prendre quelques minutes...")

pipeline.fit(X_train, y_train)

print("[OK] Entraînement terminé!")

# ============================================================================
# ÉTAPE 8: ÉVALUATION
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 8: EVALUATION")
print("=" * 80)

preds = pipeline.predict(X_test)

mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)

print(f"\nRésultats d'évaluation sur le dataset de test:")
print(f"   MAE : {mae:.4f}")
print(f"   R²  : {r2:.4f}")

# ============================================================================
# ÉTAPE 9: SAUVEGARDE
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 9: SAUVEGARDE")
print("=" * 80)

models_dir = os.path.join(script_dir, 'models')
os.makedirs(models_dir, exist_ok=True)

model_file = os.path.join(models_dir, 'ml_model.pkl')

# Sauvegarder le pipeline complet (inclut le preprocessor)
joblib.dump(pipeline, model_file)

print(f"[OK] Modèle sauvegardé dans: {model_file}")

# Sauvegarder aussi les métadonnées
metadata = {
    'features': {
        'num_features': num_features,
        'cat_features': cat_features
    },
    'metrics': {
        'mae': float(mae),
        'r2_score': float(r2)
    },
    'model_type': 'RandomForestRegressor',
    'train_size': len(X_train),
    'test_size': len(X_test),
    'date_entrainement': datetime.now().isoformat()
}

import json
metadata_file = os.path.join(models_dir, 'metadata.json')
with open(metadata_file, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"[OK] Métadonnées sauvegardées dans: {metadata_file}")

print("\n" + "=" * 80)
print("[OK] PIPELINE TERMINE AVEC SUCCES!")
print("=" * 80)

print("\nRésumé:")
print(f"   - Données traitées: {len(df)} échantillons")
print(f"   - Train: {len(X_train)} échantillons")
print(f"   - Test: {len(X_test)} échantillons")
print(f"   - Modèle: RandomForestRegressor (Pipeline)")
print(f"   - MAE: {mae:.4f}")
print(f"   - R² Score: {r2:.4f}")

print(f"\nFichiers créés:")
print(f"   - Modèle: {model_file}")
print(f"   - Métadonnées: {metadata_file}")

