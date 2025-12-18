"""
Views API pour UserApp
Utilise Django REST Framework si disponible, sinon retourne du JSON simple
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
import json
import requests
from django.conf import settings

from .models import CustomUser, Connection, Post, Comment, Message, Notification, AdminMessage
from .serializers import (
    CustomUserSerializer, CustomUserCreateSerializer, CustomUserUpdateSerializer,
    ConnectionSerializer, PostSerializer, CommentSerializer,
    MessageSerializer, NotificationSerializer
)

# Vérifier si DRF est disponible
try:
    from rest_framework import viewsets, status
    from rest_framework.decorators import action
    from rest_framework.response import Response
    from rest_framework.permissions import IsAuthenticated, AllowAny
    DRF_AVAILABLE = True
except ImportError:
    DRF_AVAILABLE = False


# ========== Viewsets DRF (si disponible) ==========
if DRF_AVAILABLE:
    class CustomUserViewSet(viewsets.ModelViewSet):
        """
        ViewSet pour CustomUser
        """
        queryset = CustomUser.objects.all()
        permission_classes = [IsAuthenticated]

        def get_serializer_class(self):
            if self.action == 'create':
                return CustomUserCreateSerializer
            elif self.action in ['update', 'partial_update']:
                return CustomUserUpdateSerializer
            return CustomUserSerializer

        def get_queryset(self):
            queryset = CustomUser.objects.all()
            search = self.request.query_params.get('search', None)
            if search:
                queryset = queryset.filter(
                    Q(username__icontains=search) |
                    Q(email__icontains=search) |
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search)
                )
            return queryset

        @action(detail=True, methods=['get'])
        def profile(self, request, pk=None):
            """Récupérer le profil complet d'un utilisateur"""
            user = self.get_object()
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        @action(detail=False, methods=['get'])
        def me(self, request):
            """Récupérer le profil de l'utilisateur connecté"""
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        @action(detail=False, methods=['put', 'patch'])
        def update_me(self, request):
            """Mettre à jour le profil de l'utilisateur connecté"""
            serializer = CustomUserUpdateSerializer(
                request.user,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    class ConnectionViewSet(viewsets.ModelViewSet):
        """
        ViewSet pour Connection
        """
        queryset = Connection.objects.all()
        serializer_class = ConnectionSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            user = self.request.user
            return Connection.objects.filter(
                Q(from_user=user) | Q(to_user=user)
            )

        def perform_create(self, serializer):
            serializer.save(from_user=self.request.user)

        @action(detail=True, methods=['post'])
        def accept(self, request, pk=None):
            """Accepter une connexion"""
            connection = self.get_object()
            if connection.to_user != request.user:
                return Response(
                    {'error': 'Vous ne pouvez pas accepter cette connexion.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            connection.status = Connection.Status.ACCEPTED
            connection.save()
            return Response({'status': 'accepted'})

        @action(detail=True, methods=['post'])
        def reject(self, request, pk=None):
            """Refuser une connexion"""
            connection = self.get_object()
            if connection.to_user != request.user:
                return Response(
                    {'error': 'Vous ne pouvez pas refuser cette connexion.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            connection.status = Connection.Status.REJECTED
            connection.save()
            return Response({'status': 'rejected'})


    class PostViewSet(viewsets.ModelViewSet):
        """
        ViewSet pour Post
        """
        queryset = Post.objects.all()
        serializer_class = PostSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            queryset = Post.objects.all()
            author_id = self.request.query_params.get('author', None)
            if author_id:
                queryset = queryset.filter(author_id=author_id)
            return queryset.order_by('-created_at')

        def perform_create(self, serializer):
            serializer.save(author=self.request.user)


    class CommentViewSet(viewsets.ModelViewSet):
        """
        ViewSet pour Comment
        """
        queryset = Comment.objects.all()
        serializer_class = CommentSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            queryset = Comment.objects.all()
            post_id = self.request.query_params.get('post', None)
            if post_id:
                queryset = queryset.filter(post_id=post_id)
            return queryset.order_by('-created_at')

        def perform_create(self, serializer):
            serializer.save(author=self.request.user)


    class MessageViewSet(viewsets.ModelViewSet):
        """
        ViewSet pour Message
        """
        queryset = Message.objects.all()
        serializer_class = MessageSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            user = self.request.user
            return Message.objects.filter(
                Q(sender=user) | Q(receiver=user)
            ).order_by('-sent_at')

        def perform_create(self, serializer):
            serializer.save(sender=self.request.user)

        @action(detail=True, methods=['post'])
        def mark_read(self, request, pk=None):
            """Marquer un message comme lu"""
            message = self.get_object()
            if message.receiver != request.user:
                return Response(
                    {'error': 'Vous ne pouvez pas marquer ce message comme lu.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            message.read = True
            message.save()
            return Response({'read': True})

        @action(detail=False, methods=['get'])
        def conversation(self, request):
            """Récupérer la conversation avec un utilisateur"""
            user_id = request.query_params.get('user', None)
            if not user_id:
                return Response(
                    {'error': 'Paramètre user requis.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            other_user = get_object_or_404(CustomUser, id=user_id)
            messages = Message.objects.filter(
                Q(sender=request.user, receiver=other_user) |
                Q(sender=other_user, receiver=request.user)
            ).order_by('sent_at')
            serializer = self.get_serializer(messages, many=True)
            return Response(serializer.data)


    class NotificationViewSet(viewsets.ModelViewSet):
        """
        ViewSet pour Notification
        """
        queryset = Notification.objects.all()
        serializer_class = NotificationSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            return Notification.objects.filter(user=self.request.user)

        def perform_create(self, serializer):
            serializer.save(user=self.request.user)

        @action(detail=True, methods=['post'])
        def mark_read(self, request, pk=None):
            """Marquer une notification comme lue"""
            notification = self.get_object()
            if notification.user != request.user:
                return Response(
                    {'error': 'Vous ne pouvez pas marquer cette notification comme lue.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            notification.read = True
            notification.save()
            return Response({'read': True})

        @action(detail=False, methods=['post'])
        def mark_all_read(self, request):
            """Marquer toutes les notifications comme lues"""
            Notification.objects.filter(
                user=request.user,
                read=False
            ).update(read=True)
            return Response({'status': 'all marked as read'})


# ========== Views JSON simples (fallback si DRF non disponible) ==========
@csrf_exempt
@require_http_methods(["GET", "POST"])
@login_required
def api_user_list(request):
    """Liste des utilisateurs (JSON simple)"""
    if request.method == 'GET':
        users = CustomUser.objects.all()
        serializer = CustomUserSerializer(users, many=True)
        return JsonResponse(serializer.data, safe=False)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH"])
@login_required
def api_user_detail(request, pk):
    """Détail d'un utilisateur (JSON simple)"""
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'GET':
        serializer = CustomUserSerializer(user)
        return JsonResponse(serializer.data)
    elif request.method in ['PUT', 'PATCH']:
        data = json.loads(request.body)
        serializer = CustomUserUpdateSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def _format_user_for_display(user):
    """Formate un utilisateur pour l'affichage dans le chat"""
    avatar_html = ""
    if hasattr(user, 'avatar') and user.avatar:
        try:
            avatar_html = f'<img src="{user.avatar.url}" alt="Avatar" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; margin-right: 10px;">'
        except (ValueError, AttributeError):
            pass
    
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or "Utilisateur"
    email = user.email or "N/A"
    phone = user.phone or "N/A"
    role = getattr(user, 'role', 'UTILISATEUR') or 'UTILISATEUR'
    city = getattr(user, 'city', None) or "N/A"
    is_active = "✅ Actif" if user.is_active else "❌ Banni/Inactif"
    is_verified = "✓ Vérifié" if getattr(user, 'is_verified', False) else "✗ Non vérifié"
    date_joined = user.date_joined.strftime("%d/%m/%Y") if hasattr(user, 'date_joined') and user.date_joined else "N/A"
    
    # Échapper les caractères HTML pour éviter les injections
    def escape_html(text):
        if text is None:
            return "N/A"
        return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    
    name = escape_html(name)
    email = escape_html(email)
    phone = escape_html(phone)
    role = escape_html(role)
    city = escape_html(city)
    
    return f"""
    <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 8px; background: #f9fafb;">
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
            {avatar_html}
            <div>
                <strong style="color: #111827; font-size: 1rem;">{name}</strong>
                <div style="color: #6b7280; font-size: 0.85rem;">ID: {user.id} | {email}</div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 0.85rem; color: #4b5563;">
            <div><strong>Téléphone:</strong> {phone}</div>
            <div><strong>Rôle:</strong> {role}</div>
            <div><strong>Ville:</strong> {city}</div>
            <div><strong>Inscription:</strong> {date_joined}</div>
            <div><strong>Statut:</strong> {is_active}</div>
            <div><strong>Email:</strong> {is_verified}</div>
        </div>
        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e7eb; font-size: 0.8rem; color: #6b7280;">
            💡 <strong>Commandes disponibles:</strong> "changer le rôle de l'utilisateur {user.id} en admin", "bannir l'utilisateur {user.id}", "débannir l'utilisateur {user.id}"
        </div>
    </div>
    """


def _search_users(query: str, limit: int = 20, role_filter=None, active_filter=None):
    """
    Recherche avancée des utilisateurs par n'importe quelle information
    Supporte aussi les filtres par rôle et statut actif/inactif
    """
    if not query or not query.strip():
        queryset = CustomUser.objects.all()
    else:
        query = query.strip()
        queryset = CustomUser.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(city__icontains=query) |
            Q(country__icontains=query) |
            Q(address__icontains=query) |
            Q(headline__icontains=query) |
            Q(bio__icontains=query) |
            Q(location__icontains=query)
        ).distinct()
    
    # Appliquer les filtres supplémentaires
    if role_filter:
        queryset = queryset.filter(role=role_filter)
    if active_filter is not None:
        queryset = queryset.filter(is_active=active_filter)
    
    return queryset[:limit]


def _list_all_users(limit: int = 50, role_filter=None, active_filter=None):
    """
    Liste tous les utilisateurs (limité) avec filtres optionnels
    """
    queryset = CustomUser.objects.all()
    if role_filter:
        queryset = queryset.filter(role=role_filter)
    if active_filter is not None:
        queryset = queryset.filter(is_active=active_filter)
    return queryset.order_by('-date_joined')[:limit]


def _change_user_role(user_id: int, new_role: str):
    """
    Change le rôle d'un utilisateur
    Retourne (success, message)
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        if new_role not in ['ADMIN', 'UTILISATEUR']:
            return False, f"Rôle invalide: {new_role}. Les rôles valides sont ADMIN et UTILISATEUR."
        old_role = user.role
        user.role = new_role
        user.save()
        return True, f"Rôle de {user.username} ({user.email}) changé de {old_role} à {new_role}."
    except CustomUser.DoesNotExist:
        return False, f"Utilisateur avec l'ID {user_id} introuvable."
    except Exception as e:
        return False, f"Erreur lors du changement de rôle: {str(e)}"


def _ban_user(user_id: int, ban: bool, reason: str = None):
    """
    Bannit ou débannit un utilisateur
    Retourne (success, message)
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        user.is_active = not ban
        if ban:
            user.ban_reason = reason or "Banni par un administrateur via EduBot"
            user.banned_at = timezone.now()
        else:
            user.ban_reason = None
            user.banned_at = None
        user.save()
        action = "banni" if ban else "débanni"
        return True, f"Utilisateur {user.username} ({user.email}) {action} avec succès."
    except CustomUser.DoesNotExist:
        return False, f"Utilisateur avec l'ID {user_id} introuvable."
    except Exception as e:
        return False, f"Erreur lors du bannissement: {str(e)}"


def _detect_user_intent(message: str):
    """
    Détecte l'intention de l'utilisateur concernant les utilisateurs
    Retourne (intent, query, role_filter, active_filter) où intent peut être 'list', 'search', 'change_role', 'ban', ou None
    """
    message_lower = message.lower().strip()
    
    # D'abord, détecter les salutations et questions conversationnelles simples
    # Si c'est juste une salutation ou une question générale, ne pas déclencher les outils
    greetings = ['salut', 'bonjour', 'bonsoir', 'bonne nuit', 'hello', 'hi', 'hey', 'coucou']
    simple_questions = ['comment ça va', 'ça va', 'comment allez-vous', 'comment vas-tu', 
                       'qui es-tu', 'qui êtes-vous', 'c\'est quoi', 'qu\'est-ce que', 
                       'aide-moi', 'aide moi', 'help', 'aider']
    
    # Si le message est exactement une salutation ou contient juste une salutation simple
    if message_lower in greetings:
        return (None, None, None, None, None, None)
    
    # Si le message commence par une salutation et est court (max 3 mots)
    words = message_lower.split()
    if len(words) <= 3 and any(greeting in message_lower for greeting in greetings):
        return (None, None, None, None, None, None)
    
    # Si c'est une question simple sans mots-clés d'action, passer à l'IA
    if any(sq in message_lower for sq in simple_questions) and not any(kw in message_lower for kw in ['liste', 'cherche', 'trouve', 'recherche', 'bannir', 'changer', 'modifier']):
        return (None, None, None, None, None, None)
    
    # Détecter les actions sur un utilisateur spécifique (par ID)
    import re
    
    # Chercher "changer rôle" ou "modifier rôle" avec un ID
    # Patterns plus flexibles: "changer rôle utilisateur 5", "mettre l'utilisateur 5 en admin", "utilisateur 5 admin", etc.
    role_change_patterns = [
        r'(changer|modifier|changer le|modifier le|mettre|donner|passer|promouvoir|r[ée]trograder).*r[oô]le.*(?:utilisateur|user|id).*?(\d+)',
        r'(changer|modifier|changer le|modifier le|mettre|donner|passer|promouvoir|r[ée]trograder).*r[oô]le.*?(\d+)',
        r'(?:utilisateur|user|id).*?(\d+).*(?:en|à|vers|devient).*(admin|utilisateur)',
        r'(?:utilisateur|user|id).*?(\d+).*r[oô]le.*(admin|utilisateur)',
        r'r[oô]le.*(?:utilisateur|user|id).*?(\d+).*(?:en|à|vers).*(admin|utilisateur)',
        r'(\d+).*(?:en|à|vers|devient).*(admin|utilisateur).*r[oô]le',
        r'(?:promouvoir|r[ée]trograder).*(\d+)',
    ]
    for pattern in role_change_patterns:
        match = re.search(pattern, message_lower)
        if match:
            # Extraire l'ID (généralement le dernier groupe numérique)
            user_id = None
            for group in match.groups():
                if group and group.isdigit():
                    user_id = int(group)
                    break
            if user_id:
                # Détecter quel rôle
                if 'admin' in message_lower or (match.lastindex > 1 and 'admin' in match.group(match.lastindex).lower()):
                    return ('change_role', None, 'ADMIN', None, user_id, None)
                elif 'utilisateur' in message_lower or 'user' in message_lower:
                    return ('change_role', None, 'UTILISATEUR', None, user_id, None)
                # Si on trouve "admin" ou "utilisateur" dans les groupes
                for i in range(1, len(match.groups()) + 1):
                    group_val = match.group(i)
                    if group_val and group_val.lower() in ['admin', 'utilisateur']:
                        role = 'ADMIN' if group_val.lower() == 'admin' else 'UTILISATEUR'
                        return ('change_role', None, role, None, user_id, None)
    
    # Chercher "bannir" ou "débannir" avec un ID
    # Patterns plus flexibles avec plusieurs variantes pour débannir
    # Mots pour bannir
    ban_keywords = ['bannir', 'ban', 'bloquer', 'suspendre', 'désactiver', 'désactiver le compte', 'désactiver compte']
    # Mots pour débannir (beaucoup plus de variantes)
    unban_keywords = ['débannir', 'debannir', 'dé-bannir', 'de-bannir', 'unban', 'débloquer', 'débloquer le compte', 
                     'débloquer compte', 'réactiver', 'reactiver', 'ré-activer', 're-activer', 'activer', 
                     'activer le compte', 'activer compte', 'restaurer', 'restaurer le compte', 'restaurer compte',
                     'réhabiliter', 'rehabiliter', 'ré-habiliter', 're-habiliter', 'rétablir', 'retablir',
                     'remettre', 'remettre en service', 'remettre actif', 'rendre actif', 'rendre disponible']
    
    # Patterns pour bannir
    ban_patterns = [
        r'(' + '|'.join(ban_keywords) + r').*(?:utilisateur|user|id|compte).*?(\d+)',
        r'(' + '|'.join(ban_keywords) + r').*?(\d+)',
        r'(?:utilisateur|user|id|compte).*?(\d+).*(' + '|'.join(ban_keywords) + r')',
        r'(\d+).*(' + '|'.join(ban_keywords) + r')',
    ]
    
    # Patterns pour débannir
    unban_patterns = [
        r'(' + '|'.join(unban_keywords) + r').*(?:utilisateur|user|id|compte).*?(\d+)',
        r'(' + '|'.join(unban_keywords) + r').*?(\d+)',
        r'(?:utilisateur|user|id|compte).*?(\d+).*(' + '|'.join(unban_keywords) + r')',
        r'(\d+).*(' + '|'.join(unban_keywords) + r')',
    ]
    
    # Vérifier d'abord les patterns de débannissement (plus spécifiques)
    for pattern in unban_patterns:
        match = re.search(pattern, message_lower)
        if match:
            user_id = None
            for group in match.groups():
                if group and group.isdigit():
                    user_id = int(group)
                    break
            if user_id:
                return ('ban', None, None, None, user_id, False)  # False = débannir
    
    # Ensuite vérifier les patterns de bannissement
    for pattern in ban_patterns:
        match = re.search(pattern, message_lower)
        if match:
            user_id = None
            for group in match.groups():
                if group and group.isdigit():
                    user_id = int(group)
                    break
            if user_id:
                return ('ban', None, None, None, user_id, True)  # True = bannir
    
    # Extraire les filtres de rôle et statut AVANT de détecter l'intention
    role_filter = None
    # Détecter "admin" ou "admins" pour le filtre de rôle
    if 'admin' in message_lower and ('utilisateur' not in message_lower or message_lower.index('admin') < message_lower.index('utilisateur')):
        role_filter = 'ADMIN'
    # Détecter "utilisateur" ou "utilisateurs" (sans "admin") pour le filtre de rôle UTILISATEUR
    elif ('utilisateur' in message_lower or 'users' in message_lower) and 'admin' not in message_lower:
        role_filter = 'UTILISATEUR'
    # Si on dit explicitement "rôle admin" ou "rôle utilisateur"
    elif 'rôle' in message_lower or 'role' in message_lower:
        if 'admin' in message_lower:
            role_filter = 'ADMIN'
        elif 'utilisateur' in message_lower or 'user' in message_lower:
            role_filter = 'UTILISATEUR'
    
    active_filter = None
    if 'banni' in message_lower or 'inactif' in message_lower or 'désactivé' in message_lower:
        active_filter = False
    elif 'actif' in message_lower and 'inactif' not in message_lower:
        active_filter = True
    
    # Mots-clés pour lister tous les utilisateurs
    list_keywords = [
        'liste', 'list', 'affiche', 'montre', 'voir', 'tous les utilisateurs',
        'utilisateurs', 'users', 'tous les users', 'tous utilisateurs',
        'afficher les utilisateurs', 'montrer les utilisateurs'
    ]
    
    # Vérifier si c'est une demande de liste EN PREMIER (avant la recherche)
    for keyword in list_keywords:
        if keyword in message_lower:
            # Si on dit "liste les utilisateurs" sans mentionner "admin", filtrer par rôle UTILISATEUR
            if role_filter is None and ('utilisateur' in message_lower or 'users' in message_lower) and 'admin' not in message_lower:
                role_filter = 'UTILISATEUR'
            return ('list', None, role_filter, active_filter, None, None)
    
    # Mots-clés pour rechercher (sans "utilisateur" et "user" pour éviter les conflits avec "liste les utilisateurs")
    search_keywords = [
        'cherche', 'recherche', 'trouve', 'find', 'search', 'chercher',
        'par', 'avec', 'qui a', 'qui contient'
    ]
    
    # Vérifier si c'est une recherche (après avoir vérifié la liste)
    # Seulement si on a un mot-clé explicite de recherche
    for keyword in search_keywords:
        if keyword in message_lower:
            # Extraire la requête de recherche
            parts = message_lower.split(keyword, 1)
            if len(parts) > 1:
                query = parts[1].strip()
                # Nettoyer la requête (enlever les mots vides et les filtres)
                stop_words = ['un', 'une', 'des', 'le', 'la', 'les', 'de', 'du', 'l\'', 'd\'', 'qui', 'a', 'contient', 'rôle', 'role', 'banni', 'actif', 'inactif', 'par', 'avec']
                # Ne pas enlever "admin" ou "utilisateur" s'ils font partie de la requête de recherche
                query_parts = query.split()
                cleaned_parts = []
                for part in query_parts:
                    if part not in stop_words:
                        cleaned_parts.append(part)
                    # Si c'est "admin" ou "utilisateur" mais qu'on cherche vraiment ces mots, les garder
                    elif part in ['admin', 'utilisateur', 'user'] and keyword in ['cherche', 'recherche', 'trouve', 'find', 'search', 'chercher']:
                        cleaned_parts.append(part)
                query = ' '.join(cleaned_parts)
                if query:
                    return ('search', query, role_filter, active_filter, None, None)
            # Si pas de query mais mot-clé de recherche présent, c'est une recherche
            return ('search', None, role_filter, active_filter, None, None)
    
    # Détecter les recherches directes (sans mot-clé "cherche")
    # Si le message contient un email (@), un numéro de téléphone, ou semble être un nom/prénom
    # Détecter un email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if re.search(email_pattern, message):
        email_match = re.search(email_pattern, message)
        return ('search', email_match.group(0), role_filter, active_filter, None, None)
    
    # Détecter un numéro de téléphone (séquence de chiffres avec ou sans espaces/tirets)
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,9}\b'
    phone_match = re.search(phone_pattern, message)
    if phone_match and len(re.sub(r'[-.\s()+]', '', phone_match.group(0))) >= 8:
        return ('search', phone_match.group(0), role_filter, active_filter, None, None)
    
    # Si le message ne contient pas de mots-clés de liste et semble être une recherche (nom, prénom, etc.)
    # et ne contient pas de commandes d'action (changer, bannir, etc.)
    action_keywords = ['changer', 'modifier', 'bannir', 'ban', 'débannir', 'promouvoir', 'rétrograder']
    
    # Exclure les salutations et questions conversationnelles simples
    greetings_and_simple = ['salut', 'bonjour', 'bonsoir', 'hello', 'hi', 'hey', 'coucou', 
                            'comment ça va', 'ça va', 'comment allez-vous', 'comment vas-tu',
                            'qui es-tu', 'qui êtes-vous', 'aide-moi', 'aide moi', 'help']
    
    # Si c'est juste une salutation ou question simple, ne pas déclencher les outils
    if message_lower in greetings_and_simple or any(greeting in message_lower for greeting in greetings_and_simple if len(message_lower.split()) <= 3):
        return (None, None, None, None, None, None)
    
    # Détecter les recherches automatiques (nom, prénom) seulement si pas de mots-clés de liste
    if not any(kw in message_lower for kw in action_keywords) and not any(kw in message_lower for kw in list_keywords):
        # Si c'est un message court (probablement un nom, prénom, ou autre info de recherche)
        # Mais exclure les salutations
        words = message_lower.split()
        if len(words) <= 5 and not any(word.isdigit() and len(word) > 3 for word in words):
            # Vérifier que ce n'est pas une salutation
            if not any(greeting in message_lower for greeting in greetings_and_simple):
                # Probablement une recherche par nom/prénom ou autre info
                return ('search', message.strip(), role_filter, active_filter, None, None)
    
    return (None, None, None, None, None, None)


def _edubot_core_answer(user_message: str, system_prompt: str):
    """
    Fonction interne qui envoie la requête à l'API IA et renvoie (reply, error, status_code)
    """
    api_key = getattr(settings, "EDUBOT_API_KEY", "")
    api_base = getattr(settings, "EDUBOT_API_BASE", "https://api.openai.com/v1")
    model = getattr(settings, "EDUBOT_MODEL", "gpt-3.5-turbo")

    if not api_key:
        return None, "Clé API EduBot non configurée", 500

    try:
        resp = requests.post(
            f"{api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=25,
        )
        # Gérer explicitement certains codes d'erreur HTTP courants
        if resp.status_code == 401:
            return None, "EduBot n'est pas autorisé (401). Vérifiez la clé API ou le compte.", 502
        if resp.status_code == 402:
            # Cas actuel : Payment Required sur OpenRouter
            return None, "EduBot n'est pas disponible : crédit ou facturation requis sur l'API (402 Payment Required).", 502
        if resp.status_code == 429:
            return None, "EduBot a atteint la limite de requêtes (429). Réessayez plus tard.", 502
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
        return reply, None, 200
    except requests.RequestException as e:
        return None, f"Erreur API EduBot: {e}", 502
    except Exception as e:
        return None, str(e), 500


# ========== EduBot – Chatbot IA pour le backoffice ==========
@csrf_exempt
@require_http_methods(["POST"])
@login_required
def edubot_chat(request):
    """
    Endpoint pour le chatbot EduBot réservé au backoffice (admins).
    Nécessite d'être connecté.
    Supporte les outils de recherche et liste des utilisateurs.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Requête invalide"}, status=400)

    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return JsonResponse({"error": "Message vide"}, status=400)

    # Détecter l'intention concernant les utilisateurs
    try:
        intent_result = _detect_user_intent(user_message)
        intent = intent_result[0] if len(intent_result) > 0 else None
        query = intent_result[1] if len(intent_result) > 1 else None
        role_filter = intent_result[2] if len(intent_result) > 2 else None
        active_filter = intent_result[3] if len(intent_result) > 3 else None
        user_id = intent_result[4] if len(intent_result) > 4 else None
        is_ban = intent_result[5] if len(intent_result) > 5 else None
    except Exception as e:
        # En cas d'erreur dans la détection, continuer avec l'IA normale
        intent = None
        query = None
        role_filter = None
        active_filter = None
        user_id = None
        is_ban = None
    
    # Gérer le changement de rôle
    if intent == 'change_role' and user_id:
        new_role = role_filter
        success, message = _change_user_role(user_id, new_role)
        if success:
            # Recharger l'utilisateur pour afficher les nouvelles infos
            try:
                user = CustomUser.objects.get(id=user_id)
                user_html = _format_user_for_display(user)
                reply = f"""
                <div style="margin-bottom: 12px;">
                    <div style="color: #10b981; font-weight: 600; margin-bottom: 8px;">✅ {message}</div>
                    <h4 style="color: #111827; margin-bottom: 12px; font-size: 1.1rem;">Utilisateur mis à jour:</h4>
                    {user_html}
                </div>
                """
                return JsonResponse({"reply": reply, "is_html": True})
            except:
                return JsonResponse({"reply": f"✅ {message}"})
        else:
            return JsonResponse({"reply": f"❌ {message}"})
    
    # Gérer le bannissement
    if intent == 'ban' and user_id is not None:
        success, message = _ban_user(user_id, is_ban)
        if success:
            # Recharger l'utilisateur pour afficher les nouvelles infos
            try:
                user = CustomUser.objects.get(id=user_id)
                user_html = _format_user_for_display(user)
                reply = f"""
                <div style="margin-bottom: 12px;">
                    <div style="color: #10b981; font-weight: 600; margin-bottom: 8px;">✅ {message}</div>
                    <h4 style="color: #111827; margin-bottom: 12px; font-size: 1.1rem;">Utilisateur mis à jour:</h4>
                    {user_html}
                </div>
                """
                return JsonResponse({"reply": reply, "is_html": True})
            except:
                return JsonResponse({"reply": f"✅ {message}"})
        else:
            return JsonResponse({"reply": f"❌ {message}"})
    
    # Si c'est une demande de liste ou recherche d'utilisateurs
    context_info = ""  # Information de contexte pour l'IA
    
    if intent == 'list':
        users = _list_all_users(limit=50, role_filter=role_filter, active_filter=active_filter)
        if users.exists():
            users_html = "".join([_format_user_for_display(user) for user in users])
            total_count = CustomUser.objects.count()
            filter_text = ""
            if role_filter:
                filter_text += f" avec rôle {role_filter}"
            if active_filter is not None:
                filter_text += f" {'actifs' if active_filter else 'bannis/inactifs'}"
            reply = f"""
            <div style="margin-bottom: 12px;">
                <h4 style="color: #111827; margin-bottom: 12px; font-size: 1.1rem;">
                    📋 Liste des utilisateurs{filter_text} ({users.count()} sur {total_count} affichés)
                </h4>
                {users_html}
            </div>
            """
            return JsonResponse({"reply": reply, "is_html": True})
        else:
            # Si aucun résultat, informer l'IA du contexte
            filter_desc = ""
            if role_filter:
                filter_desc += f" avec le rôle {role_filter}"
            if active_filter is not None:
                filter_desc += f" {'actifs' if active_filter else 'bannis/inactifs'}"
            context_info = f"L'utilisateur a demandé à lister les utilisateurs{filter_desc}, mais aucun utilisateur n'a été trouvé dans la base de données. Réponds de manière conversationnelle et propose des alternatives."
    
    elif intent == 'search':
        if query or role_filter or active_filter is not None:
            users = _search_users(query or "", limit=20, role_filter=role_filter, active_filter=active_filter)
            if users.exists():
                users_html = "".join([_format_user_for_display(user) for user in users])
                filter_text = f' pour "{query}"' if query else ""
                if role_filter:
                    filter_text += f" avec rôle {role_filter}"
                if active_filter is not None:
                    filter_text += f" {'actifs' if active_filter else 'bannis/inactifs'}"
                reply = f"""
                <div style="margin-bottom: 12px;">
                    <h4 style="color: #111827; margin-bottom: 12px; font-size: 1.1rem;">
                        🔍 Résultats de recherche{filter_text} ({users.count()} résultat(s))
                    </h4>
                    {users_html}
                </div>
                """
                return JsonResponse({"reply": reply, "is_html": True})
            else:
                # Si aucun résultat, informer l'IA du contexte
                search_desc = f' pour "{query}"' if query else ""
                if role_filter:
                    search_desc += f" avec le rôle {role_filter}"
                if active_filter is not None:
                    search_desc += f" {'actifs' if active_filter else 'bannis/inactifs'}"
                context_info = f"L'utilisateur a recherché des utilisateurs{search_desc}, mais aucun résultat n'a été trouvé. Réponds de manière conversationnelle, explique pourquoi il n'y a pas de résultats et propose des alternatives ou des suggestions."
        else:
            # Si recherche mais pas de query, informer l'IA
            context_info = "L'utilisateur a mentionné une recherche mais n'a pas fourni de critère de recherche. Réponds de manière conversationnelle et demande ce qu'il souhaite rechercher."
    
    # Sinon, utiliser l'IA normale
    # Construire le prompt avec le contexte si disponible
    context_section = ""
    if context_info:
        context_section = f"\n\n=== CONTEXTE ACTUEL ===\n{context_info}\n\n"
    
    # Détecter si l'intention n'est pas claire et suggérer des actions
    suggest_section = ""
    if intent is None and user_message and len(user_message.split()) > 2:
        # Si le message contient des mots liés aux actions mais pas de format clair
        action_related_words = ['utilisateur', 'user', 'bannir', 'ban', 'débannir', 'rôle', 'role', 'admin', 
                               'cherche', 'trouve', 'liste', 'affiche', 'modifier', 'changer']
        message_lower_check = user_message.lower()
        if any(word in message_lower_check for word in action_related_words):
            suggest_section = "IMPORTANT : L'utilisateur semble vouloir faire une action mais la demande n'est pas claire. Suggère-lui les actions possibles de manière amicale et propose des exemples de commandes.\n\n"
    
    admin_prompt = (
        "Tu es EduBot, un assistant IA intelligent et conversationnel pour le dashboard admin EduLife. "
        "Tu aides les administrateurs à gérer la plateforme, répondre à leurs questions et exécuter des actions. "
        "Réponds de façon claire, concise, amicale, naturelle et conversationnelle en français. "
        "Sois toujours serviable, poli et professionnel. "
        "\n\n"
        + context_section
        + suggest_section
        + "=== OUTILS DISPONIBLES POUR LES UTILISATEURS ===\n"
        "\n"
        "1. LISTER LES UTILISATEURS :\n"
        "   Commandes : 'liste les utilisateurs', 'affiche tous les utilisateurs', 'montre les users'\n"
        "   - 'liste les utilisateurs' → liste uniquement les UTILISATEUR (pas les admins)\n"
        "   - 'liste les admins' → liste uniquement les ADMIN\n"
        "   - 'liste les utilisateurs bannis' ou 'liste les utilisateurs actifs' → filtre par statut\n"
        "\n"
        "2. RECHERCHER DES UTILISATEURS :\n"
        "   Commandes : 'cherche [critère]', 'trouve [critère]', 'recherche [critère]'\n"
        "   - Recherche par email : tapez directement l'email (ex: 'jean@example.com')\n"
        "   - Recherche par téléphone : tapez directement le numéro (ex: '0612345678')\n"
        "   - Recherche par nom/prénom : tapez directement le nom (ex: 'Jean Dupont')\n"
        "   - Recherche avancée : 'cherche les admins à Paris', 'trouve les utilisateurs bannis'\n"
        "   La recherche fonctionne sur : nom, prénom, email, téléphone, ville, pays, adresse, titre professionnel, bio, localisation.\n"
        "\n"
        "3. MODIFIER LE RÔLE D'UN UTILISATEUR :\n"
        "   Formats acceptés : 'changer le rôle de l'utilisateur [ID] en admin', 'mettre l'utilisateur [ID] en utilisateur'\n"
        "   Exemples : 'changer le rôle de l'utilisateur 5 en admin', 'promouvoir l'utilisateur 10'\n"
        "\n"
        "4. BANNIR/DÉBANNIR UN UTILISATEUR :\n"
        "   Formats acceptés pour BANNIR : 'bannir l'utilisateur [ID]', 'ban l'utilisateur [ID]', 'bloquer l'utilisateur [ID]', 'suspendre l'utilisateur [ID]', 'désactiver l'utilisateur [ID]'\n"
        "   Formats acceptés pour DÉBANNIR (beaucoup de variantes) :\n"
        "   - 'débannir l'utilisateur [ID]' ou 'debannir l'utilisateur [ID]'\n"
        "   - 'débloquer l'utilisateur [ID]' ou 'débloquer le compte [ID]'\n"
        "   - 'réactiver l'utilisateur [ID]' ou 'reactiver l'utilisateur [ID]'\n"
        "   - 'activer l'utilisateur [ID]' ou 'activer le compte [ID]'\n"
        "   - 'restaurer l'utilisateur [ID]' ou 'restaurer le compte [ID]'\n"
        "   - 'réhabiliter l'utilisateur [ID]' ou 'rehabiliter l'utilisateur [ID]'\n"
        "   - 'rétablir l'utilisateur [ID]' ou 'retablir l'utilisateur [ID]'\n"
        "   - 'remettre en service l'utilisateur [ID]' ou 'remettre actif l'utilisateur [ID]'\n"
        "   - 'rendre actif l'utilisateur [ID]' ou 'rendre disponible l'utilisateur [ID]'\n"
        "   Exemples : 'bannir l'utilisateur 5', 'débannir l'utilisateur 10', 'débloquer l'utilisateur 15', 'réactiver le compte 20'\n"
        "\n"
        "=== INFORMATIONS SUR LA PLATEFORME ===\n"
        "\n"
        "RÔLES :\n"
        "- UTILISATEUR : Rôle par défaut, accès standard à la plateforme (logements, stages, startups, covoiturage, événements).\n"
        "- ADMIN : Rôle administrateur, accès au backoffice pour gérer les utilisateurs, logements, stages, startups, etc.\n"
        "\n"
        "FONCTIONNALITÉS DE LA PLATEFORME :\n"
        "- Logements : Recherche et réservation de logements étudiants\n"
        "- Stages : Offres de stage et postulations\n"
        "- Startups : Création et gestion de startups, investissements\n"
        "- Covoiturage : Partage de trajets entre utilisateurs\n"
        "- Événements : Organisation et participation à des événements\n"
        "- Réseau social : Connexions, posts, messages entre utilisateurs\n"
        "\n"
        "=== GUIDE D'UTILISATION ===\n"
        "\n"
        "QUAND L'UTILISATEUR DEMANDE :\n"
        "- À voir/lister des utilisateurs → Utilise les commandes de liste\n"
        "- À rechercher un utilisateur → Utilise les commandes de recherche ou recherche directe\n"
        "- À modifier un rôle → Exécute la commande avec l'ID de l'utilisateur\n"
        "- À bannir/débannir → Exécute la commande avec l'ID de l'utilisateur\n"
        "- Des questions générales → Réponds avec tes connaissances sur la plateforme\n"
        "- Comment faire quelque chose → Guide l'utilisateur étape par étape\n"
        "- Des informations sur les fonctionnalités → Explique clairement\n"
        "\n"
        "SOIS PROACTIF ET UTILE :\n"
        "- Si l'utilisateur dit 'je veux bannir Jean', cherche d'abord Jean, puis exécute la commande\n"
        "- Si l'utilisateur pose une question, réponds de manière complète et utile\n"
        "- Si l'utilisateur demande de l'aide, propose des solutions concrètes\n"
        "- Reste toujours poli, professionnel et serviable\n"
        "\n"
        "RÉPONDS À TOUTES LES QUESTIONS :\n"
        "- Questions sur les rôles, fonctionnalités, utilisateurs, logements, stages, startups, etc.\n"
        "- Questions sur comment utiliser la plateforme\n"
        "- Questions générales sur EduLife\n"
        "- Toute autre question pertinente\n"
    )
    reply, error, status = _edubot_core_answer(user_message, admin_prompt)
    if error:
        return JsonResponse({"error": error}, status=status)
    return JsonResponse({"reply": reply})


# ========== EduBot public – pour la home/front-office ==========
@csrf_exempt
@require_http_methods(["POST"])
def edubot_public_chat(request):
    """
    Endpoint public pour EduBot utilisé sur la page d'accueil (widget et EduVoice).
    Ne nécessite pas d'authentification.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Requête invalide"}, status=400)

    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return JsonResponse({"error": "Message vide"}, status=400)

    public_prompt = (
        "Tu es EduBot, l'assistant IA intelligent et conversationnel d'EduLife, une plateforme complète pour les étudiants. "
        "Réponds de façon claire, amicale, naturelle et conversationnelle en français. "
        "Sois toujours serviable, poli et professionnel. "
        "\n\n"
        "=== INFORMATIONS COMPLÈTES SUR LE SITE EDULIFE ===\n"
        "\n"
        "EduLife est une plateforme complète qui offre plusieurs services aux étudiants :\n"
        "\n"
        "1. LOGEMENTS (/Logement/) :\n"
        "   - Recherche et réservation de logements étudiants\n"
        "   - Colocation et recherche de binôme\n"
        "   - Marketplace de logements avec filtres avancés\n"
        "   - Prédiction de prix avec IA basée sur la localisation, surface, nombre de pièces\n"
        "   - Publication d'annonces de logements\n"
        "   - Gestion des réservations\n"
        "\n"
        "2. STAGES (/internships/ ou /dashboard/internship/) :\n"
        "   - Consultation des offres de stage\n"
        "   - Postulations et candidatures\n"
        "   - Suivi des entretiens avec calendrier\n"
        "   - Génération de CV avec IA\n"
        "   - Gestion des favoris\n"
        "\n"
        "3. STARTUPS (/startup/) :\n"
        "   - Création et gestion de startups\n"
        "   - Recherche d'investissements\n"
        "   - Recherche de membres pour rejoindre une startup\n"
        "   - Génération de logos avec IA\n"
        "   - Validation et approbation des startups par les admins\n"
        "\n"
        "4. ÉVÉNEMENTS (/Event/) :\n"
        "   - Organisation et participation à des événements\n"
        "   - Réservation de places\n"
        "   - Calendrier des événements\n"
        "   - Création d'événements\n"
        "\n"
        "5. COVOITURAGE (/covoiturage/) :\n"
        "   - Partage de trajets entre étudiants\n"
        "   - Offres et demandes de covoiturage\n"
        "   - Réservations de places\n"
        "   - Gestion des trajets\n"
        "\n"
        "6. RÉSEAU SOCIAL :\n"
        "   - Fil d'actualité avec posts et commentaires\n"
        "   - Connexions et amis\n"
        "   - Messages privés entre utilisateurs\n"
        "   - Notifications en temps réel\n"
        "   - Profils utilisateurs avec avatars\n"
        "\n"
        "=== COMMENT GUIDER LES UTILISATEURS ===\n"
        "\n"
        "QUAND L'UTILISATEUR DEMANDE :\n"
        "- À accéder à une fonctionnalité → Donne des instructions étape par étape pour y accéder\n"
        "- Comment utiliser une fonctionnalité → Explique le processus complet avec des étapes numérotées\n"
        "- Des informations sur une fonctionnalité → Décris en détail ce qu'elle fait et comment l'utiliser\n"
        "- À créer un compte → Explique comment s'inscrire (bouton Inscription/Connexion en haut)\n"
        "- À se connecter → Explique comment se connecter (bouton Connexion en haut)\n"
        "\n"
        "EXEMPLES DE GUIDES ÉTAPE PAR ÉTAPE :\n"
        "- Pour chercher un logement :\n"
        "  1. Clique sur 'Logements' dans le menu de navigation\n"
        "  2. Utilise les filtres (ville, prix, type, etc.)\n"
        "  3. Clique sur un logement pour voir les détails\n"
        "  4. Clique sur 'Réserver' si tu es connecté\n"
        "\n"
        "- Pour postuler à un stage :\n"
        "  1. Va dans la section 'Stages' ou 'Internship'\n"
        "  2. Parcours les offres disponibles\n"
        "  3. Clique sur une offre pour voir les détails\n"
        "  4. Clique sur 'Postuler' et remplis le formulaire\n"
        "\n"
        "- Pour créer une startup :\n"
        "  1. Va dans la section 'Startup'\n"
        "  2. Clique sur 'Créer une startup'\n"
        "  3. Remplis le formulaire avec les informations\n"
        "  4. Soumets pour validation par les admins\n"
        "\n"
        "=== QUESTIONS DE SUGGESTION ===\n"
        "\n"
        "Si l'utilisateur ne sait pas quoi demander, suggère-lui des questions utiles comme :\n"
        "- 'Comment chercher un logement ?'\n"
        "- 'Comment postuler à un stage ?'\n"
        "- 'Comment créer une startup ?'\n"
        "- 'Qu'est-ce qu'EduLife ?'\n"
        "- 'Comment fonctionne le covoiturage ?'\n"
        "- 'Comment créer un événement ?'\n"
        "- 'Comment utiliser le réseau social ?'\n"
        "\n"
        "SOIS PROACTIF ET UTILE :\n"
        "- Si l'utilisateur demande 'je veux chercher un logement', guide-le étape par étape\n"
        "- Si l'utilisateur pose une question, réponds de manière complète avec des instructions détaillées\n"
        "- Si l'utilisateur demande de l'aide, propose des solutions concrètes avec des étapes\n"
        "- Reste toujours amical, naturel et conversationnel\n"
        "- Donne toujours des instructions claires et numérotées quand c'est pertinent\n"
        "\n"
        "RÉPONDS À TOUTES LES QUESTIONS :\n"
        "- Questions sur les fonctionnalités (logements, stages, startups, événements, covoiturage)\n"
        "- Questions sur comment utiliser la plateforme\n"
        "- Questions générales sur EduLife\n"
        "- Salutations et conversations courantes\n"
        "- Toute autre question pertinente\n"
    )
    reply, error, status = _edubot_core_answer(user_message, public_prompt)
    if error:
        return JsonResponse({"error": error}, status=status)
    return JsonResponse({"reply": reply})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def edubox_send_message(request):
    """
    API pour envoyer un message dans EduBox (chat entre admins)
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        return JsonResponse({"error": "Accès refusé. Seuls les administrateurs peuvent envoyer des messages."}, status=403)
    
    try:
        from .models import AdminMessage
        
        # Gérer les fichiers (FormData) ou JSON
        content = ''
        audio_file = None
        file = None
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Formulaire avec fichiers
            content = request.POST.get('content', '').strip()
            audio_file = request.FILES.get('audio', None)
            file = request.FILES.get('file', None)
        else:
            # JSON simple
            try:
                data = json.loads(request.body)
                content = data.get('content', '').strip()
            except json.JSONDecodeError:
                pass
        
        if not content and not audio_file and not file:
            return JsonResponse({"error": "Le message ne peut pas être vide."}, status=400)
        
        # Créer le message
        # Si c'est uniquement un message vocal ou fichier, on laisse le contenu vide
        message_content = content if content else ""
        message = AdminMessage.objects.create(
            sender=request.user,
            content=message_content
        )
        
        # Ajouter le fichier audio si présent
        if audio_file:
            message.audio_file = audio_file
            message.save()
        
        # Ajouter le fichier si présent
        if file:
            message.file = file
            message.save()
        
        # Préparer la réponse
        response_data = {
            "id": message.id,
            "content": message.content,
            "sender": {
                "id": message.sender.id,
                "username": message.sender.username,
                "first_name": message.sender.first_name or "",
                "last_name": message.sender.last_name or "",
            },
            "sent_at": message.sent_at.isoformat(),
        }
        
        # Ajouter l'URL de l'audio si disponible
        if message.audio_file:
            try:
                response_data["audio_url"] = message.audio_file.url
            except:
                response_data["audio_url"] = None
        else:
            response_data["audio_url"] = None
        
        # Ajouter l'URL du fichier si disponible
        if message.file:
            try:
                response_data["file_url"] = message.file.url
                response_data["file_name"] = message.file.name.split('/')[-1]
            except:
                response_data["file_url"] = None
                response_data["file_name"] = None
        else:
            response_data["file_url"] = None
            response_data["file_name"] = None
        
        return JsonResponse({
            "success": True,
            "message": response_data
        })
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de l'envoi du message: {str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def edubox_get_messages(request):
    """
    API pour récupérer les messages d'EduBox
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        return JsonResponse({"error": "Accès refusé."}, status=403)
    
    try:
        from .models import AdminMessage
        # Récupérer les messages (d'abord filtrer, puis slice)
        messages_queryset = AdminMessage.objects.filter(deleted=False).select_related('sender').order_by('sent_at')
        
        # Marquer comme lus (avant le slice)
        unread_messages = messages_queryset.exclude(read_by=request.user)
        for msg in unread_messages:
            msg.mark_as_read(request.user)
        
        # Prendre les 100 derniers messages
        messages = messages_queryset[:100]
        
        messages_list = []
        for msg in messages:
            sender_data = {
                "id": msg.sender.id,
                "username": msg.sender.username,
                "first_name": msg.sender.first_name or "",
                "last_name": msg.sender.last_name or "",
                "is_superuser": msg.sender.is_superuser,
                "role": getattr(msg.sender, 'role', None),
            }
            # Ajouter l'URL de l'avatar si disponible
            if hasattr(msg.sender, 'avatar') and msg.sender.avatar:
                sender_data["avatar"] = msg.sender.avatar.url
            else:
                sender_data["avatar"] = None
            
            message_data = {
                "id": msg.id,
                "content": msg.content,
                "sender": sender_data,
                "sent_at": msg.sent_at.isoformat(),
                "is_own": msg.sender.id == request.user.id,
                "edited": msg.edited,
                "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            }
            # Ajouter l'URL de l'audio si disponible
            if hasattr(msg, 'audio_file') and msg.audio_file:
                try:
                    message_data["audio_url"] = msg.audio_file.url
                except:
                    message_data["audio_url"] = None
            else:
                message_data["audio_url"] = None
            
            # Ajouter l'URL du fichier si disponible
            if hasattr(msg, 'file') and msg.file:
                try:
                    message_data["file_url"] = msg.file.url
                    message_data["file_name"] = msg.file.name.split('/')[-1]
                except:
                    message_data["file_url"] = None
                    message_data["file_name"] = None
            else:
                message_data["file_url"] = None
                message_data["file_name"] = None
            
            messages_list.append(message_data)
        
        return JsonResponse({
            "success": True,
            "messages": messages_list
        })
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de la récupération des messages: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def edubox_update_message(request, message_id):
    """
    API pour modifier un message dans EduBox
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        return JsonResponse({"error": "Accès refusé."}, status=403)
    
    try:
        from .models import AdminMessage
        from django.utils import timezone
        
        message = AdminMessage.objects.get(id=message_id, deleted=False)
        
        # Vérifier que l'utilisateur est le propriétaire du message
        if message.sender.id != request.user.id:
            return JsonResponse({"error": "Vous ne pouvez modifier que vos propres messages."}, status=403)
        
        data = json.loads(request.body)
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return JsonResponse({"error": "Le message ne peut pas être vide."}, status=400)
        
        message.content = new_content
        message.edited = True
        message.edited_at = timezone.now()
        message.save()
        
        return JsonResponse({
            "success": True,
            "message": {
                "id": message.id,
                "content": message.content,
                "edited": message.edited,
                "edited_at": message.edited_at.isoformat(),
            }
        })
    except AdminMessage.DoesNotExist:
        return JsonResponse({"error": "Message introuvable."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Données JSON invalides."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de la modification: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def edubox_delete_message(request, message_id):
    """
    API pour supprimer un message dans EduBox
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        return JsonResponse({"error": "Accès refusé."}, status=403)
    
    try:
        from .models import AdminMessage
        
        message = AdminMessage.objects.get(id=message_id, deleted=False)
        
        # Vérifier que l'utilisateur est le propriétaire du message ou un superuser
        if message.sender.id != request.user.id and not request.user.is_superuser:
            return JsonResponse({"error": "Vous ne pouvez supprimer que vos propres messages."}, status=403)
        
        # Soft delete
        message.deleted = True
        message.save()
        
        return JsonResponse({"success": True, "message": "Message supprimé."})
    except AdminMessage.DoesNotExist:
        return JsonResponse({"error": "Message introuvable."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de la suppression: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def edubox_clear_all_messages(request):
    """
    API pour supprimer tous les messages d'EduBox
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        return JsonResponse({"error": "Accès refusé."}, status=403)
    
    try:
        from .models import AdminMessage
        
        # Vérifier que l'utilisateur est superuser (seuls les superusers peuvent vider toute la discussion)
        if not request.user.is_superuser:
            return JsonResponse({"error": "Seuls les superusers peuvent vider toute la discussion."}, status=403)
        
        # Soft delete de tous les messages
        AdminMessage.objects.update(deleted=True)
        
        return JsonResponse({"success": True, "message": "Tous les messages ont été supprimés."})
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de la suppression: {str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def edubox_unread_count(request):
    """
    API pour obtenir le nombre de messages non lus dans EduBox
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        return JsonResponse({"error": "Accès refusé."}, status=403)
    
    try:
        from .models import AdminMessage
        
        # Compter les messages non lus (non supprimés et non lus par l'utilisateur)
        unread_count = AdminMessage.objects.filter(
            deleted=False
        ).exclude(
            read_by=request.user
        ).count()
        
        return JsonResponse({
            "success": True,
            "unread_count": unread_count
        })
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors du comptage: {str(e)}"}, status=500)
