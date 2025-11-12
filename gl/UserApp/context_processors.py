from .models import Message, Notification

def unread_messages_count(request):
    """Context processor pour ajouter le nombre de messages non lus"""
    if request.user.is_authenticated:
        unread_count = Message.objects.filter(receiver=request.user, read=False).count()
        return {'unread_messages_count': unread_count}
    return {'unread_messages_count': 0}


def unread_notifications_count(request):
    """Context processor pour ajouter le nombre de notifications non lues"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, read=False).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}

