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


def _edubot_core_answer(user_message: str, system_prompt: str):
    """
    Fonction interne qui envoie la requête à l'API IA et renvoie (reply, error, status_code)
    """
    api_key = getattr(settings, "EDUBOT_API_KEY", "")
    api_base = getattr(settings, "EDUBOT_API_BASE", "https://api.openai.com/v1")
    model = getattr(settings, "EDUBOT_MODEL", "gpt-4.1-mini")

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
            return JsonResponse(
                {"error": "EduBot n'est pas autorisé (401). Vérifiez la clé API ou le compte."},
                status=502,
            )
        if resp.status_code == 402:
            # Cas actuel : Payment Required sur OpenRouter
            return JsonResponse(
                {"error": "EduBot n'est pas disponible : crédit ou facturation requis sur l'API (402 Payment Required)."},
                status=502,
            )
        if resp.status_code == 429:
            return JsonResponse(
                {"error": "EduBot a atteint la limite de requêtes (429). Réessayez plus tard."},
                status=502,
            )
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
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Requête invalide"}, status=400)

    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return JsonResponse({"error": "Message vide"}, status=400)

    admin_prompt = (
        "Tu es EduBot, un assistant IA pour le dashboard admin EduLife. "
        "Tu aides les administrateurs à gérer les utilisateurs, logements, stages, startups, etc. "
        "Réponds de façon claire, courte et en français."
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
        "Tu es EduBot, l'assistant IA d'EduLife pour les étudiants et utilisateurs du site. "
        "Réponds simplement, clairement et en français, sans parler de dashboard ou de backoffice."
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
