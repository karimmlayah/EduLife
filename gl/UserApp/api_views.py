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

from .models import CustomUser, Connection, Post, Comment, Message, Notification
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

