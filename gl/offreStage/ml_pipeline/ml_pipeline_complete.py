"""
PIPELINE ML COMPLET - FROM SCRATCH
Toutes les étapes dans un seul fichier: Data Prep -> Train -> Test -> Models
Style Notebook - Pas de fonctions, tout séquentiel
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

# Essayer d'importer XGBoost si disponible
try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("[INFO] XGBoost non disponible. Installation: pip install xgboost")
import joblib
import os
from datetime import datetime
import json

# ============================================================================
# CONFIGURATION
# ============================================================================
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
np.random.seed(42)

print("=" * 80)
print("PIPELINE ML COMPLET - PREDICTION DE REMUNERATION")
print("=" * 80)

# ============================================================================
# ÉTAPE 1: CHARGEMENT DES DONNÉES
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 1: CHARGEMENT DES DONNEES")
print("=" * 80)

# Charger le CSV avec point-virgule comme séparateur
# Chemin relatif depuis le répertoire où le script est exécuté
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, 'data')
# Priorité: nouveau fichier 4000 lignes > fichier combiné > fichier 3000 lignes
csv_file_4000 = 'offres_stage_tunisie_4000.csv'
csv_file_combined = 'offres_stages_5000_combined.csv'
csv_file_fallback = 'offres_stages_3000_lignes_semicolon.csv'

if os.path.exists(os.path.join(data_dir, csv_file_4000)):
    csv_file = csv_file_4000
    print(f"[INFO] Utilisation du fichier 4000 lignes: {csv_file}")
elif os.path.exists(os.path.join(data_dir, csv_file_combined)):
    csv_file = csv_file_combined
    print(f"[INFO] Utilisation du fichier combine: {csv_file}")
else:
    csv_file = csv_file_fallback
    print(f"[INFO] Utilisation du fichier: {csv_file}")

filepath = os.path.join(data_dir, csv_file)

df = pd.read_csv(filepath, sep=';')
print(f"[OK] Donnees chargees depuis: {filepath}")
print(f"[OK] Shape: {df.shape}")
print(f"[OK] Colonnes: {len(df.columns)}")

print("\nApercu des donnees:")
print(df.head())

# ============================================================================
# ÉTAPE 2: EXPLORATORY DATA ANALYSIS (EDA)
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 2: EXPLORATORY DATA ANALYSIS (EDA)")
print("=" * 80)

# 2.1 Informations générales
print("\nInformations generales:")
print(df.info())

print("\nStatistiques descriptives:")
print(df.describe())

# 2.2 Vérification des valeurs manquantes
print("\nValeurs manquantes:")
missing = df.isnull().sum()
if missing.sum() == 0:
    print("[OK] Aucune valeur manquante")
else:
    print(missing[missing > 0])

# 2.3 Distribution de la variable cible
print("\nDistribution de la remuneration:")
print(f"   Min: {df['remuneration'].min():.2f} DT")
print(f"   Max: {df['remuneration'].max():.2f} DT")
print(f"   Mean: {df['remuneration'].mean():.2f} DT")
print(f"   Median: {df['remuneration'].median():.2f} DT")
print(f"   Std: {df['remuneration'].std():.2f} DT")

# 2.4 Analyse des variables catégorielles
print("\nDistribution des domaines:")
print(df['domaine'].value_counts())

print("\nDistribution des lieux:")
print(df['lieu'].value_counts())

# 2.5 Visualisations
print("\nGeneration des graphiques...")
os.makedirs('gl/offreStage/ml_pipeline/plots', exist_ok=True)

fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# Distribution de la rémunération
axes[0, 0].hist(df['remuneration'], bins=30, edgecolor='black', color='skyblue')
axes[0, 0].set_title('Distribution de la remuneration')
axes[0, 0].set_xlabel('Remuneration (DT)')
axes[0, 0].set_ylabel('Frequence')

# Boxplot par domaine
df.boxplot(column='remuneration', by='domaine', ax=axes[0, 1])
axes[0, 1].set_title('Remuneration par domaine')
axes[0, 1].set_xlabel('Domaine')

# Scatter: Durée vs Rémunération
axes[1, 0].scatter(df['duree'], df['remuneration'], alpha=0.6, color='coral')
axes[1, 0].set_title('Duree vs Remuneration')
axes[1, 0].set_xlabel('Duree (semaines)')
axes[1, 0].set_ylabel('Remuneration (DT)')

# Corrélation
corr_cols = ['remuneration', 'duree', 'description_length', 'nb_postulations', 'nb_favoris']
corr_matrix = df[corr_cols].corr()
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', ax=axes[1, 1])
axes[1, 1].set_title('Matrice de correlation')

plt.tight_layout()
plots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
os.makedirs(plots_dir, exist_ok=True)
plt.savefig(os.path.join(plots_dir, 'eda_analysis.png'), dpi=300, bbox_inches='tight')
plt.close()
print(f"[OK] Graphiques sauvegardes dans: {plots_dir}/eda_analysis.png")

# ============================================================================
# ÉTAPE 3: DATA PREPARATION & FEATURE ENGINEERING
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 3: DATA PREPARATION & FEATURE ENGINEERING")
print("=" * 80)

# 3.1 Copie pour preprocessing
df_processed = df.copy()
print(f"[OK] Copie creee: {df_processed.shape}")

# 3.2 Nettoyage des données
print("\nNettoyage des donnees...")

# Supprimer les doublons
before = len(df_processed)
df_processed = df_processed.drop_duplicates()
print(f"   Doublons supprimes: {before - len(df_processed)}")

# Filtrer les valeurs aberrantes
before = len(df_processed)
df_processed = df_processed[
    (df_processed['remuneration'] > 0) & 
    (df_processed['remuneration'] < 10000) &
    (df_processed['duree'] > 0) & 
    (df_processed['duree'] <= 104)
]
print(f"   Valeurs aberrantes supprimees: {before - len(df_processed)}")
print(f"   Donnees restantes: {len(df_processed)}")

# 3.3 Feature Engineering: Variables temporelles
print("\nFeature Engineering...")

df_processed['date_publication'] = pd.to_datetime(df_processed['date_publication'])
df_processed['year'] = df_processed['date_publication'].dt.year
df_processed['month'] = df_processed['date_publication'].dt.month
df_processed['day_of_week'] = df_processed['date_publication'].dt.dayofweek
df_processed['is_weekend'] = (df_processed['day_of_week'] >= 5).astype(int)
print("[OK] Variables temporelles creees")

# 3.4 Feature Engineering: Ratios et métriques
df_processed['remuneration_per_week'] = df_processed['remuneration'] / df_processed['duree']
df_processed['postulation_rate'] = df_processed['nb_postulations'] / (df_processed['nb_favoris'] + 1)
df_processed['acceptance_rate'] = df_processed['nb_postulations_acceptees'] / (df_processed['nb_postulations'] + 1)
print("[OK] Ratios creees")

# 3.5 Encodage des variables catégorielles
print("\nEncodage des variables categorielle...")

le_domaine = LabelEncoder()
le_lieu = LabelEncoder()

df_processed['domaine_encoded'] = le_domaine.fit_transform(df_processed['domaine'])
df_processed['lieu_encoded'] = le_lieu.fit_transform(df_processed['lieu'])

# Encodage de l'état
etat_mapping = {'disponible': 1, 'indisponible': 0}
df_processed['etat_encoded'] = df_processed['etat'].map(etat_mapping).fillna(0)

print(f"[OK] Domaines encodes: {len(le_domaine.classes_)} categories")
print(f"[OK] Lieux encodes: {len(le_lieu.classes_)} categories")

# 3.6 Feature Engineering: Features dérivées pour améliorer la prédiction
print("\nCreation de features derivees...")

# Catégoriser la durée
df_processed['duree_category'] = pd.cut(
    df_processed['duree'], 
    bins=[0, 4, 8, 12, 24, 104], 
    labels=[0, 1, 2, 3, 4]  # Court, Moyen, Long, Très long
).astype(int)

# Popularité du domaine (moyenne des rémunérations MENSUELLES par domaine)
# On calcule d'abord la rémunération mensuelle, puis la moyenne par domaine
df_processed['duree_mois'] = df_processed['duree'] / 4.33
df_processed['remuneration_mensuelle'] = df_processed['remuneration'] / df_processed['duree_mois']
domain_avg_remuneration = df_processed.groupby('domaine')['remuneration_mensuelle'].mean()
df_processed['domain_avg_remuneration'] = df_processed['domaine'].map(domain_avg_remuneration)

# Popularité du lieu (moyenne des rémunérations MENSUELLES par lieu)
lieu_avg_remuneration = df_processed.groupby('lieu')['remuneration_mensuelle'].mean()
df_processed['lieu_avg_remuneration'] = df_processed['lieu'].map(lieu_avg_remuneration)

# Features d'interaction pour augmenter l'impact de la durée
# Durée normalisée par la moyenne de durée du domaine
domain_avg_duree = df_processed.groupby('domaine')['duree'].mean()
df_processed['duree_normalized_by_domain'] = df_processed['duree'] / df_processed['domaine'].map(domain_avg_duree)

# NOTE: Pour la rémunération mensuelle, on ne veut PAS que la durée directe influence
# la prédiction. On garde seulement les interactions et catégories.
# Interaction catégorie durée * moyenne rémunération domaine (utilisée pour ajuster selon la catégorie)
df_processed['duree_category_interaction'] = df_processed['duree_category'] * df_processed['domain_avg_remuneration'] / 1000

print("[OK] Features derivees creees:")
print("   - duree_category")
print("   - domain_avg_remuneration")
print("   - lieu_avg_remuneration")
print("   - duree_normalized_by_domain (NOUVEAU)")
print("   - duree_interaction_domain (NOUVEAU)")
print("   - duree_category_interaction (NOUVEAU)")

# 3.7 Sélection des features
# NOTE: nb_postulations et nb_favoris sont exclus car ils ne sont pas disponibles
# lors de la création d'une nouvelle offre (toujours à 0), ce qui crée un biais
feature_columns = [
    'domaine_encoded',
    'lieu_encoded',
    # TOUTES les features liées à la durée sont RETIRÉES pour que la rémunération mensuelle
    # soit constante selon le domaine, puis on multipliera par la durée en mois
    # 'duree',  # RETIRÉ
    # 'duree_category',  # RETIRÉ
    # 'duree_normalized_by_domain',  # RETIRÉ
    # 'duree_interaction_domain',  # RETIRÉ
    # 'duree_category_interaction',  # RETIRÉ
    'description_length',
    'titre_length',
    'has_image',
    'visibilite',
    'month',
    'day_of_week',
    'is_weekend',
    'etat_encoded',
    'domain_avg_remuneration',
    'lieu_avg_remuneration'
]

print(f"\n[OK] Features selectionnees ({len(feature_columns)}):")
for i, feat in enumerate(feature_columns, 1):
    print(f"   {i}. {feat}")

# 3.7 Préparer X et y
# MODIFICATION: Prédire une rémunération MENSUELLE au lieu d'une rémunération totale
# Convertir la durée en mois (1 mois ≈ 4.33 semaines)
df_processed['duree_mois'] = df_processed['duree'] / 4.33
# Calculer la rémunération mensuelle
df_processed['remuneration_mensuelle'] = df_processed['remuneration'] / df_processed['duree_mois']

X = df_processed[feature_columns].copy()
y = df_processed['remuneration_mensuelle'].copy()  # CHANGÉ: prédire la rémunération mensuelle

print(f"\n[INFO] Modele entraine sur REMUNERATION MENSUELLE")
print(f"[INFO] Rémunération mensuelle moyenne: {y.mean():.2f} DT/mois")
print(f"[INFO] Rémunération mensuelle min: {y.min():.2f} DT/mois")
print(f"[INFO] Rémunération mensuelle max: {y.max():.2f} DT/mois")

print(f"\n[OK] Shape de X: {X.shape}")
print(f"[OK] Shape de y: {y.shape}")

# 3.8 Gérer les valeurs manquantes
X = X.fillna(X.median())
print("[OK] Valeurs manquantes remplies avec la mediane")

# 3.9 Split train/test (80/20)
print("\n" + "=" * 80)
print("SPLIT TRAIN/TEST")
print("=" * 80)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"[OK] Split train/test:")
print(f"   Train: {len(X_train)} echantillons ({len(X_train)/len(X)*100:.1f}%)")
print(f"   Test: {len(X_test)} echantillons ({len(X_test)/len(X)*100:.1f}%)")

# 3.10 Normalisation
print("\nNormalisation...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
print("[OK] Normalisation effectuee")

# ============================================================================
# ÉTAPE 4: ENTRAÎNEMENT DES MODÈLES
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 4: ENTRAINEMENT DES MODELES")
print("=" * 80)

models = {}
results = {}

# 4.1 Modèle 1: Régression Linéaire
print("\nModele 1: Regression Lineaire")
print("   Entrainement en cours...")

lr_model = LinearRegression()
lr_model.fit(X_train_scaled, y_train)
y_pred_lr = lr_model.predict(X_test_scaled)

mse_lr = mean_squared_error(y_test, y_pred_lr)
rmse_lr = np.sqrt(mse_lr)
mae_lr = mean_absolute_error(y_test, y_pred_lr)
r2_lr = r2_score(y_test, y_pred_lr)

models['LinearRegression'] = lr_model
results['LinearRegression'] = {
    'MSE': mse_lr,
    'RMSE': rmse_lr,
    'MAE': mae_lr,
    'R2': r2_lr
}

print(f"   [OK] MSE: {mse_lr:.2f}")
print(f"   [OK] RMSE: {rmse_lr:.2f}")
print(f"   [OK] MAE: {mae_lr:.2f}")
print(f"   [OK] R²: {r2_lr:.4f}")

# 4.2 Modèle 2: Random Forest Regressor avec optimisation des hyperparamètres
print("\nModele 2: Random Forest Regressor (avec optimisation)")
print("   Optimisation des hyperparamètres en cours...")

# Grille de paramètres pour l'optimisation
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [10, 15, 20, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'max_features': ['sqrt', 'log2', None]
}

# Modèle de base
rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)

# Optimisation avec RandomizedSearchCV (plus rapide que GridSearchCV)
print("   Recherche des meilleurs hyperparamètres...")
rf_search = RandomizedSearchCV(
    rf_base,
    param_distributions=param_grid,
    n_iter=50,  # Nombre de combinaisons à tester
    cv=5,  # Cross-validation avec 5 folds
    scoring='r2',
    n_jobs=-1,
    random_state=42,
    verbose=1
)

rf_search.fit(X_train, y_train)

# Utiliser le meilleur modèle trouvé
rf_model = rf_search.best_estimator_
y_pred_rf = rf_model.predict(X_test)

print(f"   [OK] Meilleurs hyperparamètres trouves:")
print(f"      n_estimators: {rf_model.n_estimators}")
print(f"      max_depth: {rf_model.max_depth}")
print(f"      min_samples_split: {rf_model.min_samples_split}")
print(f"      min_samples_leaf: {rf_model.min_samples_leaf}")
print(f"      max_features: {rf_model.max_features}")
print(f"      Score CV moyen: {rf_search.best_score_:.4f}")

mse_rf = mean_squared_error(y_test, y_pred_rf)
rmse_rf = np.sqrt(mse_rf)
mae_rf = mean_absolute_error(y_test, y_pred_rf)
r2_rf = r2_score(y_test, y_pred_rf)

models['RandomForest'] = rf_model
results['RandomForest'] = {
    'MSE': mse_rf,
    'RMSE': rmse_rf,
    'MAE': mae_rf,
    'R2': r2_rf
}

print(f"   [OK] MSE: {mse_rf:.2f}")
print(f"   [OK] RMSE: {rmse_rf:.2f}")
print(f"   [OK] MAE: {mae_rf:.2f}")
print(f"   [OK] R²: {r2_rf:.4f}")

# ============================================================================
# ÉTAPE 5: ÉVALUATION ET COMPARAISON
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 5: EVALUATION ET COMPARAISON")
print("=" * 80)

comparison_df = pd.DataFrame(results).T
print("\nResultats comparatifs:")
print(comparison_df.round(4))

# Sélectionner le meilleur modèle
best_model_name = comparison_df['R2'].idxmax()
best_model = models[best_model_name]

print(f"\n[OK] Meilleur modele: {best_model_name}")
print(f"   R² Score: {comparison_df.loc[best_model_name, 'R2']:.4f}")
print(f"   RMSE: {comparison_df.loc[best_model_name, 'RMSE']:.2f} DT")

# Importance des features (pour Random Forest)
if best_model_name == 'RandomForest':
    print("\nTop 10 features les plus importantes:")
    feature_importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)
    print(feature_importance.head(10))

# Visualisation des prédictions
print("\nGeneration des graphiques de prediction...")
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# Random Forest
axes[0].scatter(y_test, y_pred_rf, alpha=0.6, color='coral')
axes[0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
axes[0].set_xlabel('Vraies valeurs')
axes[0].set_ylabel('Predictions')
axes[0].set_title(f'Random Forest (R² = {r2_rf:.4f})')
axes[0].grid(True, alpha=0.3)

# Linear Regression
axes[1].scatter(y_test, y_pred_lr, alpha=0.6, color='skyblue')
axes[1].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
axes[1].set_xlabel('Vraies valeurs')
axes[1].set_ylabel('Predictions')
axes[1].set_title(f'Linear Regression (R² = {r2_lr:.4f})')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
os.makedirs(plots_dir, exist_ok=True)
plt.savefig(os.path.join(plots_dir, 'predictions.png'), dpi=300, bbox_inches='tight')
plt.close()
print(f"[OK] Graphiques sauvegardes dans: {plots_dir}/predictions.png")

# ============================================================================
# ÉTAPE 6: SAUVEGARDE (TOUT DANS UN SEUL FICHIER)
# ============================================================================
print("\n" + "=" * 80)
print("ETAPE 6: SAUVEGARDE")
print("=" * 80)

# Chemin relatif depuis le répertoire où le script est exécuté
script_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(script_dir, 'models')
os.makedirs(models_dir, exist_ok=True)

# Sauvegarder les moyennes de rémunération MENSUELLE pour les features dérivées
domain_avg_remuneration_dict = domain_avg_remuneration.to_dict()
lieu_avg_remuneration_dict = lieu_avg_remuneration.to_dict()

# Tout sauvegarder dans un seul fichier
ml_pipeline_data = {
    'model': best_model,
    'scaler': scaler,
    'label_encoder_domaine': le_domaine,
    'label_encoder_lieu': le_lieu,
    'feature_columns': feature_columns,
    'best_model_name': best_model_name,
    'domain_avg_remuneration': domain_avg_remuneration_dict,  # Moyenne MENSUELLE par domaine
    'lieu_avg_remuneration': lieu_avg_remuneration_dict,  # Moyenne MENSUELLE par lieu
    'metrics': {
        'best_model': best_model_name,
        'results': {k: {m: float(v) for m, v in r.items()} for k, r in results.items()},
        'n_samples': len(df_processed),
        'n_train': len(X_train),
        'n_test': len(X_test)
    }
}

# Sauvegarder tout dans un seul fichier
model_file = f'{models_dir}/ml_model.pkl'
joblib.dump(ml_pipeline_data, model_file)
print(f"[OK] Tout sauvegarde dans: {model_file}")
print(f"   - Modele: {best_model_name}")
print(f"   - Preprocesseurs: scaler, label encoders")
print(f"   - Features: {len(feature_columns)} colonnes")
print(f"   - Metriques: R² = {comparison_df.loc[best_model_name, 'R2']:.4f}, RMSE = {comparison_df.loc[best_model_name, 'RMSE']:.2f} DT")

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
print("\n" + "=" * 80)
print("[OK] PIPELINE TERMINE AVEC SUCCES!")
print("=" * 80)
print(f"\nResume:")
print(f"   - Donnees traitees: {len(df_processed)} echantillons")
print(f"   - Features utilisees: {len(feature_columns)}")
print(f"   - Meilleur modele: {best_model_name}")
print(f"   - R² Score: {comparison_df.loc[best_model_name, 'R2']:.4f}")
print(f"   - RMSE: {comparison_df.loc[best_model_name, 'RMSE']:.2f} DT")
print(f"\nFichiers crees:")
print(f"   - Modele complet: {os.path.join(models_dir, 'ml_model.pkl')} (tout dans un seul fichier)")
print(f"   - Graphiques: {plots_dir}/")
print("\n" + "=" * 80)

