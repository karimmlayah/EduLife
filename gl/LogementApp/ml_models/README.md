# Modèles de Machine Learning

## Fichier du modèle

Placez votre fichier `rent_price_model.joblib` dans ce dossier.

### Structure attendue

```
LogementApp/
├── ml_models/
│   ├── __init__.py
│   ├── README.md
│   └── rent_price_model.joblib  ← Placez votre fichier ici
└── ml_service.py
```

## Format du modèle

Le modèle doit être un fichier joblib sauvegardé avec `joblib.dump()`.

Le modèle doit accepter en entrée un array numpy ou une liste avec les caractéristiques suivantes dans cet ordre :
- Nombre de pièces (rooms)
- Nombre de salles de bain (bathrooms)
- Surface en m² (surface)

**Note:** Si votre modèle a une structure différente (par exemple, il utilise un DataFrame pandas avec des colonnes nommées, ou il nécessite un encodage des villes), vous devrez modifier la fonction `predict_price()` dans `ml_service.py` pour adapter le format d'entrée.

## Exemple de format d'entrée attendu

```python
# Le modèle sera appelé avec :
model.predict([[rooms, bathrooms, surface]])
# Exemple: model.predict([[3, 2, 80.5]])
```

## Installation des dépendances

Assurez-vous d'avoir installé les dépendances suivantes :

```bash
pip install joblib scikit-learn numpy pandas
```

Si vous utilisez un environnement virtuel (recommandé) :

```bash
# Activer l'environnement virtuel
# Windows:
.\env\Scripts\activate
# Linux/Mac:
source env/bin/activate

# Installer les dépendances
pip install joblib scikit-learn numpy pandas
```

## Vérification

Pour vérifier que le modèle fonctionne, vous pouvez tester l'API :

```bash
curl -X POST http://localhost:8000/logement/predict-price/ \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Rue Example",
    "city": "Tunis",
    "rooms": 3,
    "bathrooms": 2,
    "surface": 80.5
  }'
```

