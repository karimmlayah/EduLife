# Guide d'implémentation du modèle de prédiction de prix

## 📋 Étapes d'implémentation

### 1. Placer le fichier du modèle

Placez votre fichier `rent_price_model.joblib` dans le dossier suivant :

```
gl/LogementApp/ml_models/rent_price_model.joblib
```

**Chemin complet :** `C:\Users\Mega-PC\Desktop\projet_GL\gl\LogementApp\ml_models\rent_price_model.joblib`

### 2. Installer les dépendances Python

Ouvrez un terminal dans le dossier du projet et exécutez :

```bash
# Activer l'environnement virtuel (si vous en utilisez un)
# Windows:
.\env\Scripts\activate
# Linux/Mac:
source env/bin/activate

# Installer les dépendances nécessaires
# IMPORTANT: Le modèle a été sauvegardé avec scikit-learn 1.6.1
# Vous DEVEZ utiliser cette version exacte pour éviter les erreurs de compatibilité
pip install scikit-learn==1.6.1 joblib numpy pandas
```

**⚠️ IMPORTANT - Version de scikit-learn :**
Le modèle `rent_price_model.joblib` a été sauvegardé avec **scikit-learn 1.6.1**. Vous devez utiliser cette version exacte pour éviter les erreurs de compatibilité comme `Can't get attribute '_RemainderColsList'`.

Si vous avez une version différente installée, désinstallez-la d'abord :
```bash
pip uninstall scikit-learn
pip install scikit-learn==1.6.1
```

**Note :** `joblib` est généralement inclus avec scikit-learn. `numpy` et `pandas` sont nécessaires pour le traitement des données.

### 3. Vérifier la structure du modèle

Le code actuel suppose que votre modèle accepte un array avec 3 valeurs dans cet ordre :
- Nombre de pièces (rooms)
- Nombre de salles de bain (bathrooms)  
- Surface en m² (surface)

**Si votre modèle a une structure différente**, vous devrez modifier le fichier `gl/LogementApp/ml_service.py`, fonction `predict_price()`, ligne 80.

Exemples de modifications possibles :

#### Si votre modèle utilise un DataFrame pandas :
```python
import pandas as pd
features_df = pd.DataFrame({
    'rooms': [rooms],
    'bathrooms': [bathrooms],
    'surface': [surface]
})
prediction = model.predict(features_df)[0]
```

#### Si votre modèle nécessite l'encodage de la ville :
```python
# Vous devrez créer un encodage pour les villes
city_encoded = encode_city(city)  # Fonction à créer
prediction = model.predict([[rooms, bathrooms, surface, city_encoded]])[0]
```

### 4. Tester l'implémentation

1. **Démarrer le serveur Django :**
   ```bash
   cd gl
   python manage.py runserver
   ```

2. **Tester l'API directement :**
   - Ouvrez votre navigateur sur `http://localhost:8000/logement/add/`
   - Remplissez les champs : adresse, ville, nombre de pièces, salles de bain, surface
   - Cliquez sur le bouton "Prédire le prix avec l'IA"
   - Le prix devrait être automatiquement rempli dans le champ prix

3. **Tester avec curl (optionnel) :**
   ```bash
   curl -X POST http://localhost:8000/logement/predict-price/ \
     -H "Content-Type: application/json" \
     -d "{\"address\": \"123 Rue Example\", \"city\": \"Tunis\", \"rooms\": 3, \"bathrooms\": 2, \"surface\": 80.5}"
   ```

### 5. Structure des fichiers créés

```
gl/LogementApp/
├── ml_models/
│   ├── __init__.py
│   ├── README.md
│   └── rent_price_model.joblib  ← À PLACER ICI
├── ml_service.py                 ← Service de prédiction
├── views.py                      ← Vue API ajoutée (predict_price_api)
└── urls.py                       ← Route API ajoutée (/predict-price/)
```

### 6. Fonctionnalités implémentées

✅ **Service ML** (`ml_service.py`) :
- Chargement du modèle depuis le fichier joblib
- Fonction de prédiction avec validation des données
- Gestion des erreurs et logging

✅ **API Endpoint** (`views.py`) :
- Route `/logement/predict-price/`
- Validation des paramètres d'entrée
- Retour JSON avec le prix prédit ou les erreurs

✅ **Interface utilisateur** (`logement_add.html`) :
- Bouton "Prédire le prix avec l'IA"
- Appel AJAX à l'API
- Remplissage automatique du champ prix
- Messages d'erreur et de succès

### 7. Dépannage

#### Erreur : "Le fichier modèle n'existe pas"
- Vérifiez que le fichier `rent_price_model.joblib` est bien dans `gl/LogementApp/ml_models/`
- Vérifiez l'orthographe du nom du fichier (doit être exactement `rent_price_model.joblib`)

#### Erreur : "ModuleNotFoundError: No module named 'joblib'"
- Installez joblib : `pip install joblib`

#### Erreur : "Can't get attribute '_RemainderColsList'"
- **Cause :** Incompatibilité de version de scikit-learn. Le modèle a été sauvegardé avec scikit-learn 1.6.1, mais votre environnement utilise une version différente (par exemple 1.8.0).
- **Solution :** Installez la version exacte requise dans votre environnement virtuel :
  ```bash
  # Activer l'environnement virtuel
  .\env\Scripts\activate  # Windows
  # ou
  source env/bin/activate  # Linux/Mac
  
  # Désinstaller la version actuelle et installer la version requise
  pip uninstall scikit-learn
  pip install scikit-learn==1.6.1
  ```
- **Vérification :** Vérifiez la version installée :
  ```bash
  python -c "import sklearn; print(sklearn.__version__)"
  ```
  Elle doit afficher `1.6.1`

#### Erreur lors de la prédiction
- Vérifiez les logs Django pour voir l'erreur exacte
- Vérifiez que le format d'entrée du modèle correspond à ce qui est attendu dans `ml_service.py`
- Adaptez la fonction `predict_price()` si nécessaire

#### Le prix n'est pas rempli automatiquement
- Ouvrez la console du navigateur (F12) pour voir les erreurs JavaScript
- Vérifiez que l'URL de l'API est correcte
- Vérifiez que le serveur Django est bien démarré

### 8. Personnalisation

#### Changer la devise
Modifiez la ligne dans `views.py` (fonction `predict_price_api`) :
```python
'currency': 'TND'  # Changez en EUR, USD, etc.
```

#### Modifier le format d'entrée du modèle
Modifiez la fonction `predict_price()` dans `ml_service.py` selon les besoins de votre modèle.

## ✅ Checklist finale

- [ ] Fichier `rent_price_model.joblib` placé dans `gl/LogementApp/ml_models/`
- [ ] Dépendances installées (`joblib`, `scikit-learn`, `numpy`, `pandas`)
- [ ] Format d'entrée du modèle vérifié et adapté si nécessaire
- [ ] Serveur Django démarré
- [ ] Test effectué sur la page d'ajout de logement
- [ ] Prix prédit correctement rempli dans le formulaire

## 📞 Support

Si vous rencontrez des problèmes, vérifiez :
1. Les logs Django dans la console
2. La console JavaScript du navigateur (F12)
3. Que tous les fichiers sont bien en place
4. Que les dépendances sont installées

