from .models import Message, Notification

def unread_messages_count(request):
    """Context processor pour ajouter le nombre de messages non lus (personnels + marketplace)"""
    if request.user.is_authenticated:
        from django.db.models import Q
        # Compter les messages personnels (sans logement) ET les messages marketplace (avec logement)
        unread_count = Message.objects.filter(
            receiver=request.user, 
            read=False,
            deleted=False
        ).count()
        return {'unread_messages_count': unread_count}
    return {'unread_messages_count': 0}


def unread_notifications_count(request):
    """Context processor pour ajouter le nombre de notifications non lues"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, read=False).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}


def recent_conversations(request):
    """Context processor pour ajouter les conversations récentes pour le widget de messagerie"""
    if request.user.is_authenticated:
        from django.db.models import Q
        from django.utils import timezone
        
        # Récupérer tous les utilisateurs avec qui on a échangé des messages personnels (non supprimés, sans logement)
        sent_messages = Message.objects.filter(sender=request.user, deleted=False, logement__isnull=True).values_list('receiver', flat=True).distinct()
        received_messages = Message.objects.filter(receiver=request.user, deleted=False, logement__isnull=True).values_list('sender', flat=True).distinct()
        user_ids = set(list(sent_messages) + list(received_messages))
        
        conversations = []
        for uid in user_ids:
            try:
                from .models import CustomUser
                user = CustomUser.objects.get(id=uid)
                last_message = Message.objects.filter(
                    Q(sender=request.user, receiver=user) |
                    Q(sender=user, receiver=request.user),
                    deleted=False,
                    logement__isnull=True  # Seulement les messages personnels
                ).order_by('-sent_at').first()
                
                unread_count = Message.objects.filter(sender=user, receiver=request.user, read=False, deleted=False, logement__isnull=True).count()
                
                conversations.append({
                    'user': user,
                    'last_message': last_message,
                    'unread_count': unread_count,
                })
            except:
                continue
        
        # Trier par date du dernier message et prendre les 5 plus récents
        conversations.sort(key=lambda x: x['last_message'].sent_at if x['last_message'] else timezone.now(), reverse=True)
        conversations = conversations[:5]  # Limiter à 5 conversations récentes
        
        return {'recent_conversations': conversations}
    return {'recent_conversations': []}
