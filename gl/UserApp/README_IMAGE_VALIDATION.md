# Validation d'Image de Profil avec MediaPipe

Ce module valide que les images de profil uploadées contiennent bien un être humain en utilisant MediaPipe pour la détection de visages.

## Installation

Pour utiliser la validation d'image, vous devez installer MediaPipe et OpenCV :

```bash
pip install mediapipe opencv-python pillow numpy
```

## Fonctionnement

Le service `image_validator.py` utilise MediaPipe Face Detection pour :
1. Charger l'image et la convertir en format BGR (OpenCV)
2. Détecter les visages dans l'image avec MediaPipe
3. Vérifier si au moins un visage est détecté avec une confiance suffisante
4. Retourner un résultat avec le niveau de confiance

## Avantages de MediaPipe

- **Spécialisé pour les visages** : MediaPipe est optimisé pour détecter les visages humains
- **Plus rapide** : Plus léger et plus rapide que les modèles de classification d'images
- **Plus précis** : Détecte directement les visages plutôt que de deviner à partir de catégories
- **Meilleure UX** : Messages d'erreur plus clairs ("Aucun visage détecté" au lieu de "suit détecté")

## Seuil de confiance

Par défaut, le seuil est fixé à 50% (0.5). Si un visage est détecté avec une confiance supérieure à ce seuil, l'image est acceptée.

## Gestion des erreurs

- Si MediaPipe n'est pas installé, le système accepte les images sans validation (avec un avertissement dans les logs)
- En cas d'erreur lors de la validation, l'image est acceptée pour ne pas bloquer l'utilisateur (fail-open)

## Utilisation

La validation est automatiquement appelée lors de l'upload d'un avatar dans :
- `profile_update_view` (page account-settings)
- `profile_update_public_view` (page profile publique)

## Messages d'erreur

Si l'image ne contient pas un visage humain, l'utilisateur verra un message comme :
```
❌ Aucun visage humain détecté dans l'image. Veuillez utiliser une photo de profil avec un visage visible.
```

Si l'image est valide :
```
✅ Avatar mis à jour avec succès. ✅ Visage humain détecté (confiance: 87.5%)
```

## Configuration

Le seuil de confiance peut être ajusté dans la fonction `is_human_in_image()` :
- `min_confidence=0.5` : Seuil par défaut (50%)
- Réduire à `0.3` pour être plus permissif
- Augmenter à `0.7` pour être plus strict

