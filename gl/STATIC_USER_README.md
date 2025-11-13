# Utilisateur Statique - Guide d'utilisation

## 📋 Description

Ce système permet d'utiliser un utilisateur statique (hardcodé) dans le code pour les tests, sans avoir besoin de s'authentifier.

## 🔧 Configuration

Pour changer l'ID de l'utilisateur statique, modifiez la variable `STATIC_USER_ID` dans le fichier :

**Fichier :** `gl/gl/settings.py`

```python
# ============================================
# UTILISATEUR STATIQUE POUR TESTS (SANS AUTH)
# ============================================
# Changez cette valeur pour utiliser un autre utilisateur
# Par défaut: ID 1 (admin)
STATIC_USER_ID = 1  # Changez ce nombre pour utiliser un autre utilisateur
```

## 📝 Exemples

### Utiliser l'utilisateur avec ID 1 (admin)
```python
STATIC_USER_ID = 1
```

### Utiliser l'utilisateur avec ID 2 (covoitureur)
```python
STATIC_USER_ID = 2
```

### Utiliser l'utilisateur avec ID 3 (passager)
```python
STATIC_USER_ID = 3
```

## 🔄 Fonctionnement

1. **Si l'utilisateur est connecté** : Le système utilise `request.user` (l'utilisateur authentifié)

2. **Si l'utilisateur n'est pas connecté** : Le système utilise automatiquement l'utilisateur avec l'ID configuré dans `STATIC_USER_ID`

3. **Si l'utilisateur avec cet ID n'existe pas** : Le système utilise le premier utilisateur disponible, ou en crée un par défaut

## 📍 Où est utilisé l'utilisateur statique ?

- ✅ Création d'offres de covoiturage (`offre_create`)
- ✅ Création de réservations (`reservation_create`)
- ✅ Affichage des réservations du conducteur (`mes_reservations`)
- ✅ Affichage des réservations du passager (`mes_reservations_passager`)
- ✅ Acceptation/Rejet de réservations (`reservation_accept`, `reservation_reject`)
- ✅ Annulation de réservations (`reservation_cancel`)

## ⚠️ Important

- Ce système est uniquement pour les **tests et le développement**
- En production, vous devriez toujours utiliser l'authentification réelle
- L'utilisateur statique est utilisé uniquement si l'utilisateur n'est **pas authentifié**

## 🚀 Utilisation

1. Ouvrez `gl/gl/settings.py`
2. Trouvez la ligne `STATIC_USER_ID = 1`
3. Changez le nombre selon l'ID de l'utilisateur que vous voulez utiliser
4. Sauvegardez le fichier
5. Redémarrez le serveur Django si nécessaire

## 📌 Liste des utilisateurs de test

- **ID 1** : admin (username: `admin`, password: `admin123`)
- **ID 2** : covoitureur (username: `covoitureur`, password: `covoitureur123`)
- **ID 3** : passager (username: `passager`, password: `passager123`)

Pour voir tous les utilisateurs disponibles, utilisez le shell Django :
```python
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.all()
```

