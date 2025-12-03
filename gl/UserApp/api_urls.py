"""
URLs pour l'API UserApp
"""
from django.urls import path, include

# Vérifier si DRF est disponible
try:
    from rest_framework.routers import DefaultRouter
    from .api_views import (
        CustomUserViewSet, ConnectionViewSet, PostViewSet,
        CommentViewSet, MessageViewSet, NotificationViewSet,
        edubot_chat, edubot_public_chat, edubox_send_message, edubox_get_messages,
        edubox_update_message, edubox_delete_message, edubox_clear_all_messages,
        edubox_unread_count,
    )
    DRF_AVAILABLE = True
except ImportError:
    DRF_AVAILABLE = False
    from .api_views import (
        api_user_list, api_user_detail, edubot_chat, edubot_public_chat,
        edubox_send_message, edubox_get_messages, edubox_update_message, edubox_delete_message,
        edubox_clear_all_messages, edubox_unread_count
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
        path('edubot/chat/', edubot_chat, name='edubot_chat'),
        path('edubot/public-chat/', edubot_public_chat, name='edubot_public_chat'),
        path('edubox/send/', edubox_send_message, name='edubox_send_message'),
        path('edubox/messages/', edubox_get_messages, name='edubox_get_messages'),
        path('edubox/messages/<int:message_id>/update/', edubox_update_message, name='edubox_update_message'),
        path('edubox/messages/<int:message_id>/delete/', edubox_delete_message, name='edubox_delete_message'),
        path('edubox/clear-all/', edubox_clear_all_messages, name='edubox_clear_all_messages'),
        path('edubox/unread-count/', edubox_unread_count, name='edubox_unread_count'),
    ]
else:
    # Utiliser les vues JSON simples
    urlpatterns = [
        path('users/', api_user_list, name='api_user_list'),
        path('users/<int:pk>/', api_user_detail, name='api_user_detail'),
        path('edubot/chat/', edubot_chat, name='edubot_chat'),
        path('edubot/public-chat/', edubot_public_chat, name='edubot_public_chat'),
        path('edubox/send/', edubox_send_message, name='edubox_send_message'),
        path('edubox/messages/', edubox_get_messages, name='edubox_get_messages'),
        path('edubox/messages/<int:message_id>/update/', edubox_update_message, name='edubox_update_message'),
        path('edubox/messages/<int:message_id>/delete/', edubox_delete_message, name='edubox_delete_message'),
        path('edubox/clear-all/', edubox_clear_all_messages, name='edubox_clear_all_messages'),
        path('edubox/unread-count/', edubox_unread_count, name='edubox_unread_count'),
    ]

