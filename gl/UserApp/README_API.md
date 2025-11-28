# Documentation API UserApp

## Structure du module

Ce module contient une API complète pour la gestion des utilisateurs et des fonctionnalités sociales.

### Modèles

#### CustomUser (étendu)
- **Champs existants** : email, phone, avatar, is_verified, etc.
- **Nouveaux champs ajoutés** :
  - `headline` : Titre professionnel
  - `bio` : Biographie
  - `location` : Localisation
  - `skills` : Compétences (JSON)
  - `education` : Formation (JSON)
  - `experience` : Expérience (JSON)
  - `date_of_birth` : Date de naissance

#### Connection
- Gestion des connexions entre utilisateurs
- Statuts : pending, accepted, rejected, blocked
- Champs : from_user, to_user, status, created_at

#### Post
- Publications des utilisateurs
- Champs : author, content, media, created_at, updated_at

#### Comment
- Commentaires sur les posts
- Champs : post, author, text, created_at

#### Message
- Messages privés entre utilisateurs
- Champs : sender, receiver, text, sent_at, read

#### Notification
- Notifications pour les utilisateurs
- Champs : user, verb, data, read, created_at

## Installation

### 1. Installer Django REST Framework (optionnel mais recommandé)

```bash
pip install djangorestframework
```

Ajouter dans `settings.py` :
```python
INSTALLED_APPS = [
    # ...
    'rest_framework',
]
```

### 2. Créer les migrations

```bash
python manage.py makemigrations UserApp
python manage.py migrate
```

## Utilisation de l'API

### Avec Django REST Framework (recommandé)

Si DRF est installé, l'API utilise automatiquement les ViewSets.

#### Endpoints disponibles :

- **Users** : `/api/users/`
  - GET : Liste des utilisateurs
  - POST : Créer un utilisateur
  - GET `/api/users/me/` : Profil de l'utilisateur connecté
  - PUT/PATCH `/api/users/me/` : Mettre à jour son profil
  - GET `/api/users/{id}/` : Détail d'un utilisateur
  - GET `/api/users/{id}/profile/` : Profil complet

- **Connections** : `/api/connections/`
  - GET : Liste des connexions
  - POST : Créer une connexion
  - POST `/api/connections/{id}/accept/` : Accepter une connexion
  - POST `/api/connections/{id}/reject/` : Refuser une connexion

- **Posts** : `/api/posts/`
  - GET : Liste des posts
  - POST : Créer un post
  - GET `/api/posts/?author={id}` : Posts d'un auteur

- **Comments** : `/api/comments/`
  - GET : Liste des commentaires
  - POST : Créer un commentaire
  - GET `/api/comments/?post={id}` : Commentaires d'un post

- **Messages** : `/api/messages/`
  - GET : Liste des messages
  - POST : Envoyer un message
  - POST `/api/messages/{id}/mark_read/` : Marquer comme lu
  - GET `/api/messages/conversation/?user={id}` : Conversation avec un utilisateur

- **Notifications** : `/api/notifications/`
  - GET : Liste des notifications
  - POST : Créer une notification
  - POST `/api/notifications/{id}/mark_read/` : Marquer comme lue
  - POST `/api/notifications/mark_all_read/` : Marquer toutes comme lues

### Sans Django REST Framework

Si DRF n'est pas installé, des vues JSON simples sont disponibles :
- `/api/users/` : Liste des utilisateurs
- `/api/users/{id}/` : Détail d'un utilisateur

## Exemples d'utilisation

### Créer un utilisateur

```python
POST /api/users/
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword123",
    "password2": "securepassword123",
    "first_name": "John",
    "last_name": "Doe"
}
```

### Mettre à jour le profil

```python
PATCH /api/users/me/
{
    "headline": "Développeur Full Stack",
    "bio": "Passionné par le développement web",
    "location": "Paris, France",
    "skills": ["Python", "Django", "React"],
    "education": [
        {
            "school": "Université XYZ",
            "degree": "Master Informatique",
            "year": "2020"
        }
    ],
    "experience": [
        {
            "company": "Tech Corp",
            "position": "Développeur",
            "start_date": "2021-01-01",
            "end_date": null
        }
    ]
}
```

### Créer une connexion

```python
POST /api/connections/
{
    "to_user_id": 2,
    "status": "pending"
}
```

### Créer un post

```python
POST /api/posts/
{
    "content": "Mon premier post !",
    "media": null
}
```

### Créer un commentaire

```python
POST /api/comments/
{
    "post_id": 1,
    "text": "Excellent post !"
}
```

### Envoyer un message

```python
POST /api/messages/
{
    "receiver_id": 2,
    "text": "Bonjour, comment allez-vous ?"
}
```

## Authentification

L'API nécessite une authentification. Utilisez :
- **Session authentication** (par défaut)
- **Token authentication** (si configuré)

Pour utiliser l'API avec DRF, ajoutez dans `settings.py` :

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

## Fichiers créés

- `models.py` : Tous les modèles (mis à jour)
- `serializers.py` : Serializers pour tous les modèles
- `api_views.py` : ViewSets et vues API
- `api_urls.py` : URLs de l'API
- `admin.py` : Configuration admin (mis à jour)

## Notes importantes

1. Les champs JSON (skills, education, experience) acceptent des listes/dictionnaires Python qui seront automatiquement sérialisés en JSON.

2. Les fichiers média (avatar, media des posts) sont stockés dans :
   - `media/avatars/` pour les avatars
   - `media/posts/media/` pour les médias des posts

3. Assurez-vous que `MEDIA_URL` et `MEDIA_ROOT` sont correctement configurés dans `settings.py`.

4. Pour utiliser l'API complète avec toutes les fonctionnalités, il est fortement recommandé d'installer Django REST Framework.

