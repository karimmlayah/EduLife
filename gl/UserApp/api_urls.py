"""
URLs pour l'API UserApp
"""
from django.urls import path, include

# Vérifier si DRF est disponible
try:
    from rest_framework.routers import DefaultRouter
    from .api_views import (
        CustomUserViewSet, ConnectionViewSet, PostViewSet,
        CommentViewSet, MessageViewSet, NotificationViewSet
    )
    DRF_AVAILABLE = True
except ImportError:
    DRF_AVAILABLE = False
    from .api_views import (
        api_user_list, api_user_detail
    )

if DRF_AVAILABLE:
    # Utiliser les ViewSets avec DRF
    router = DefaultRouter()
    router.register(r'users', CustomUserViewSet, basename='user')
    router.register(r'connections', ConnectionViewSet, basename='connection')
    router.register(r'posts', PostViewSet, basename='post')
    router.register(r'comments', CommentViewSet, basename='comment')
    router.register(r'messages', MessageViewSet, basename='message')
    router.register(r'notifications', NotificationViewSet, basename='notification')

    urlpatterns = [
        path('', include(router.urls)),
    ]
else:
    # Utiliser les vues JSON simples
    urlpatterns = [
        path('users/', api_user_list, name='api_user_list'),
        path('users/<int:pk>/', api_user_detail, name='api_user_detail'),
        # Ajouter d'autres endpoints si nécessaire
    ]

