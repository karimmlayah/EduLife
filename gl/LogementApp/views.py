from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from UserApp.models import CustomUser, Post, Comment, Connection, Message, AdminMessage
from .models import Logement, LogementImage
from .forms import LogementForm

# Décorateur pour vérifier si l'utilisateur est superuser ou admin
def is_superuser_or_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'ADMIN'))

# Create your views here.
def logement_home(request):
    """Page d'accueil des logements - Liste tous les logements approuvés avec filtres"""
    logements = Logement.objects.filter(available=True, approved=True, rejected=False)
    
    # Filtres
    city_filter = request.GET.get('city', '')
    type_filter = request.GET.get('type', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    surface_min = request.GET.get('surface_min', '')
    surface_max = request.GET.get('surface_max', '')
    rooms_min = request.GET.get('rooms_min', '')
    rooms_max = request.GET.get('rooms_max', '')
    bathrooms_min = request.GET.get('bathrooms_min', '')
    wifi_filter = request.GET.get('wifi', '')
    search_query = request.GET.get('search', '')
    
    # Appliquer les filtres
    if city_filter:
        logements = logements.filter(city__icontains=city_filter)
    
    if type_filter:
        logements = logements.filter(type_logement=type_filter)
    
    if price_min:
        try:
            logements = logements.filter(price__gte=float(price_min))
        except ValueError:
            pass
    
    if price_max:
        try:
            logements = logements.filter(price__lte=float(price_max))
        except ValueError:
            pass
    
    if surface_min:
        try:
            logements = logements.filter(surface__gte=float(surface_min))
        except ValueError:
            pass
    
    if surface_max:
        try:
            logements = logements.filter(surface__lte=float(surface_max))
        except ValueError:
            pass
    
    if rooms_min:
        try:
            logements = logements.filter(rooms__gte=int(rooms_min))
        except ValueError:
            pass
    
    if rooms_max:
        try:
            logements = logements.filter(rooms__lte=int(rooms_max))
        except ValueError:
            pass
    
    if bathrooms_min:
        try:
            logements = logements.filter(bathrooms__gte=int(bathrooms_min))
        except ValueError:
            pass
    
    if wifi_filter == 'true':
        logements = logements.filter(wifi=True)
    
    if search_query:
        logements = logements.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(address__icontains=search_query) |
            Q(city__icontains=search_query)
        )
    
    # Trier par date de création (plus récent en premier)
    logements = logements.order_by('-created_at')
    
    # Récupérer toutes les villes uniques pour le filtre
    all_cities = Logement.objects.filter(available=True, approved=True, rejected=False).values_list('city', flat=True).distinct().order_by('city')
    
    # Pour marketplace, pas besoin de vérifier les connexions - contact direct
    logements_with_connection = [{'logement': logement, 'is_connected': False} for logement in logements]
    
    return render(request, 'User/LogementApp/logements.html', {
        'logements_with_connection': logements_with_connection,
        'all_cities': all_cities,
        'filters': {
            'city': city_filter,
            'type': type_filter,
            'price_min': price_min,
            'price_max': price_max,
            'surface_min': surface_min,
            'surface_max': surface_max,
            'rooms_min': rooms_min,
            'rooms_max': rooms_max,
            'bathrooms_min': bathrooms_min,
            'wifi': wifi_filter,
            'search': search_query,
        }
    })


@login_required
def my_logements(request):
    """Afficher les logements de l'utilisateur connecté"""
    logements = Logement.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'User/LogementApp/my_logements.html', {
        'logements': logements
    })


@login_required
def logement_add(request):
    """Ajouter un nouveau logement"""
    if request.method == 'POST':
        form = LogementForm(request.POST, request.FILES)
        if form.is_valid():
            logement = form.save(commit=False)
            logement.owner = request.user
            logement.approved = False  # Par défaut, non approuvé
            logement.save()
            
            # Traiter les images multiples
            images = request.FILES.getlist('images')
            for image in images:
                LogementImage.objects.create(logement=logement, image=image)
            
            messages.success(request, 'Logement ajouté avec succès! Il sera visible après approbation par un administrateur.')
            return redirect('my_logements')
    else:
        form = LogementForm()
    
    return render(request, 'User/LogementApp/logement_add.html', {
        'form': form
    })


def logement_detail(request, logement_id):
    """Détails d'un logement"""
    logement = get_object_or_404(Logement, id=logement_id)
    return render(request, 'User/LogementApp/logement_detail.html', {
        'logement': logement
    })


@login_required
def logement_edit(request, logement_id):
    """Modifier un logement (seulement le propriétaire)"""
    logement = get_object_or_404(Logement, id=logement_id)
    
    # Vérifier que l'utilisateur est le propriétaire
    if logement.owner != request.user:
        messages.error(request, 'Vous n\'avez pas la permission de modifier ce logement.')
        return redirect('logement')
    
    if request.method == 'POST':
        form = LogementForm(request.POST, request.FILES, instance=logement)
        if form.is_valid():
            form.save()
            
            # Traiter les images multiples supplémentaires
            images = request.FILES.getlist('images')
            for image in images:
                LogementImage.objects.create(logement=logement, image=image)
            
            messages.success(request, 'Logement modifié avec succès!')
            return redirect('logement_detail', logement_id=logement.id)
    else:
        form = LogementForm(instance=logement)
    
    return render(request, 'User/LogementApp/logement_edit.html', {
        'form': form,
        'logement': logement
    })


@login_required
def logement_delete(request, logement_id):
    """Supprimer un logement (seulement le propriétaire)"""
    logement = get_object_or_404(Logement, id=logement_id)
    
    # Vérifier que l'utilisateur est le propriétaire
    if logement.owner != request.user:
        messages.error(request, 'Vous n\'avez pas la permission de supprimer ce logement.')
        return redirect('logement')
    
    if request.method == 'POST':
        logement.delete()
        messages.success(request, 'Logement supprimé avec succès!')
        return redirect('logement')
    
    return render(request, 'User/LogementApp/logement_delete.html', {
        'logement': logement
    })


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def dashboard(request):
    """Dashboard principal avec statistiques sur les utilisateurs"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    
    all_users = CustomUser.objects.all()
    
    # Statistiques utilisateurs
    total_count = all_users.count()
    active_count = all_users.filter(is_active=True).count()
    superuser_count = all_users.filter(is_superuser=True).count()
    
    # Utilisateurs récents (7 derniers jours)
    from django.utils import timezone
    from datetime import timedelta
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_users = all_users.filter(date_joined__gte=seven_days_ago).count()
    
    # Utilisateurs récents
    latest_users = all_users.order_by('-date_joined')[:5]
    
    # Utilisateurs par mois (derniers 6 mois)
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    users_by_month = all_users.annotate(
        month=TruncMonth('date_joined')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('-month')[:6]
    
    # Utilisateurs actifs vs inactifs
    inactive_count = all_users.filter(is_active=False).count()
    
    # Comptes bannis (avec ban_reason ou banned_at)
    from django.db.models import Q
    banned_users = all_users.filter(
        is_active=False
    ).filter(
        Q(ban_reason__isnull=False) & ~Q(ban_reason='') | Q(banned_at__isnull=False)
    )
    banned_count = banned_users.count()
    recently_banned = banned_users.filter(banned_at__gte=seven_days_ago).count()
    
    # Statistiques Posts
    total_posts = Post.objects.count()
    posts_today = Post.objects.filter(created_at__date=timezone.now().date()).count()
    posts_this_week = Post.objects.filter(created_at__gte=seven_days_ago).count()
    
    # Statistiques Commentaires
    total_comments = Comment.objects.count()
    comments_today = Comment.objects.filter(created_at__date=timezone.now().date()).count()
    comments_this_week = Comment.objects.filter(created_at__gte=seven_days_ago).count()
    
    # Statistiques Connexions
    total_connections = Connection.objects.count()
    accepted_connections = Connection.objects.filter(status='accepted').count()
    pending_connections = Connection.objects.filter(status='pending').count()
    
    # Statistiques Messages
    total_messages = Message.objects.count()
    unread_messages = Message.objects.filter(read=False).count()
    messages_today = Message.objects.filter(sent_at__date=timezone.now().date()).count()
    
    # Posts récents
    recent_posts = Post.objects.select_related('author').order_by('-created_at')[:5]
    
    return render(request, 'User/argon/dashboard.html', {
        'total_count': total_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'banned_count': banned_count,
        'recently_banned': recently_banned,
        'superuser_count': superuser_count,
        'recent_users': recent_users,
        'latest_users': latest_users,
        'users_by_month': users_by_month,
        'total_posts': total_posts,
        'posts_today': posts_today,
        'posts_this_week': posts_this_week,
        'total_comments': total_comments,
        'comments_today': comments_today,
        'comments_this_week': comments_this_week,
        'total_connections': total_connections,
        'accepted_connections': accepted_connections,
        'pending_connections': pending_connections,
        'total_messages': total_messages,
        'unread_messages': unread_messages,
        'messages_today': messages_today,
        'recent_posts': recent_posts,
    })


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def admin_edubot(request):
    """
    Page complète pour le chatbot EduBot dans le backoffice.
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    return render(request, 'User/Backoffice/edubot.html')


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def admin_edubox(request):
    """
    Interface de messagerie entre administrateurs (EduBox)
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    
    # Récupérer tous les messages (chat de groupe)
    # D'abord filtrer, puis prendre le slice
    admin_messages_queryset = AdminMessage.objects.filter(deleted=False).select_related('sender').order_by('sent_at')
    
    # Marquer les messages non lus comme lus (avant le slice)
    unread_messages = admin_messages_queryset.exclude(read_by=request.user)
    for msg in unread_messages:
        msg.mark_as_read(request.user)
    
    # Maintenant prendre le slice pour l'affichage (les 100 derniers messages)
    # On prend les 100 derniers, puis on les inverse pour afficher du plus ancien au plus récent
    admin_messages_list = list(admin_messages_queryset[:100])
    admin_messages = admin_messages_list  # Garder l'ordre chronologique (du plus ancien au plus récent)
    
    # Récupérer tous les admins pour afficher dans la liste
    admins = CustomUser.objects.filter(
        Q(is_superuser=True) | Q(role='ADMIN')
    ).distinct()
    
    context = {
        'admin_messages': admin_messages,
        'admins': admins,
    }
    
    return render(request, 'User/Backoffice/edubox.html', context)


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def argon_page(request, page: str):
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    allowed = {
        'dashboard',
        'billing',
        'profile',
        'rtl',
        'sign-in',
        'sign-up',
        'tables',
        'virtual-reality',
    }
    if page not in allowed:
        raise Http404("Page not found")
    template_name = f"User/argon/{page}.html"
    return render(request, template_name)


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def tables(request):
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'User/Backoffice/tables.html', { 'users': users })


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def dashboard_logements(request):
    """Dashboard dédié aux logements avec statistiques"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('admin_dashboard')
    
    all_logements = Logement.objects.all()
    
    # Statistiques
    total_count = all_logements.count()
    pending_count = all_logements.filter(approved=False).count()
    approved_count = all_logements.filter(approved=True).count()
    available_count = all_logements.filter(available=True, approved=True).count()
    
    # Logements récents
    recent_logements = all_logements.order_by('-created_at')[:5]
    
    # Logements par type
    from django.db.models import Count
    logements_by_type = all_logements.values('type_logement').annotate(count=Count('id')).order_by('-count')
    
    # Logements par ville
    logements_by_city = all_logements.values('city').annotate(count=Count('id')).order_by('-count')[:5]
    
    return render(request, 'User/Backoffice/dashboard_logements.html', {
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'available_count': available_count,
        'recent_logements': recent_logements,
        'logements_by_type': logements_by_type,
        'logements_by_city': logements_by_city,
    })


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def manage_logements(request):
    """Gérer les logements dans le dashboard (approuver/rejeter)"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('admin_dashboard')
    
    all_logements = Logement.objects.all()
    
    # Filtrer par statut d'approbation si demandé
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'pending':
        # En attente = non approuvé ET non rejeté
        logements = all_logements.filter(approved=False, rejected=False).order_by('-created_at')
    elif status_filter == 'approved':
        logements = all_logements.filter(approved=True, rejected=False).order_by('-created_at')
    elif status_filter == 'rejected':
        logements = all_logements.filter(rejected=True).order_by('-created_at')
    else:
        logements = all_logements.order_by('-created_at')
    
    # Compteurs pour les filtres
    total_count = all_logements.count()
    pending_count = all_logements.filter(approved=False, rejected=False).count()
    approved_count = all_logements.filter(approved=True, rejected=False).count()
    rejected_count = all_logements.filter(rejected=True).count()
    
    return render(request, 'User/Backoffice/logements.html', {
        'logements': logements,
        'status_filter': status_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count
    })


@login_required
def logement_messages(request, logement_id):
    """Voir et envoyer des messages pour un logement (marketplace - pas besoin de connexion)"""
    logement = get_object_or_404(Logement, id=logement_id)
    
    # Déterminer l'autre utilisateur dans la conversation
    # Si un user_id est passé en paramètre (depuis la liste des conversations), l'utiliser
    user_id_param = request.GET.get('user_id')
    other_user = None
    
    if user_id_param:
        try:
            other_user = get_object_or_404(CustomUser, id=int(user_id_param))
            # Vérifier que cet utilisateur a bien des messages avec request.user (peu importe le logement)
            has_messages = Message.objects.filter(
                Q(sender=request.user, receiver=other_user) |
                Q(sender=other_user, receiver=request.user),
                deleted=False
            ).exists()
            if not has_messages:
                other_user = None
        except (ValueError, Http404):
            other_user = None
    
    # Si aucun user_id fourni ou invalide, déterminer l'autre utilisateur
    if not other_user:
        # Récupérer tous les messages entre request.user et d'autres utilisateurs
        all_user_messages = Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user),
            deleted=False
        ).order_by('-sent_at')
        
        # Trouver l'autre utilisateur le plus récent (peu importe le logement)
        for message in all_user_messages:
            if message.sender == request.user:
                potential_user = message.receiver
            else:
                potential_user = message.sender
            # S'assurer que l'autre utilisateur n'est pas request.user
            if potential_user != request.user:
                other_user = potential_user
                break
        
        # Si aucun autre utilisateur trouvé, utiliser le propriétaire du logement
        if not other_user:
            other_user = logement.owner
    
    # Récupérer TOUS les messages marketplace entre l'utilisateur actuel et l'autre utilisateur
    # Peu importe le logement - une seule conversation entre deux utilisateurs
    if other_user:
        messages_list = Message.objects.filter(
            Q(sender=request.user, receiver=other_user) |
            Q(sender=other_user, receiver=request.user),
            deleted=False
        ).order_by('sent_at')
        
        # Marquer tous les messages comme lus entre ces deux utilisateurs
        Message.objects.filter(
            sender=other_user,
            receiver=request.user, 
            read=False,
            deleted=False
        ).update(read=True)
    else:
        messages_list = Message.objects.none()
    
    return render(request, 'User/LogementApp/logement_messages.html', {
        'logement': logement,
        'messages_list': messages_list,
        'other_user': other_user if other_user else logement.owner
    })


@login_required
@require_POST
def send_logement_message(request, logement_id):
    """Envoyer un message au propriétaire d'un logement (marketplace - pas besoin de connexion)"""
    logement = get_object_or_404(Logement, id=logement_id)
    
    # Déterminer le destinataire : si user_id est fourni, l'utiliser, sinon utiliser le propriétaire
    user_id_param = request.POST.get('user_id') or request.GET.get('user_id')
    if user_id_param:
        try:
            receiver = get_object_or_404(CustomUser, id=int(user_id_param))
        except (ValueError, Http404):
            receiver = logement.owner
    else:
        receiver = logement.owner
    
    # Pas de vérification de connexion pour les messages de logements (marketplace)
    text = request.POST.get('text', '').strip()
    file = request.FILES.get('file', None)
    
    if not text and not file:
        messages.error(request, "Le message ne peut pas être vide.")
        if user_id_param:
            return redirect(f"{reverse('logement_messages', args=[logement_id])}?user_id={user_id_param}")
        return redirect('logement_messages', logement_id=logement_id)
    
    message = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        text=text if text else None,
        logement=logement  # Marquer comme message marketplace
    )
    
    if file:
        message.file = file
        message.save()
    
    messages.success(request, "Message envoyé.")
    # Rediriger avec user_id pour maintenir la conversation
    redirect_url = f"{reverse('logement_messages', args=[logement_id])}?user_id={receiver.id}"
    return redirect(redirect_url)


@login_required
def marketplace_messages(request):
    """Liste des conversations marketplace (messages liés aux logements)"""
    from LogementApp.models import Logement
    
    # Récupérer tous les messages marketplace de l'utilisateur
    all_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
            deleted=False
        ).filter(
        Q(logement__isnull=False) | Q(logement__isnull=True)
    ).order_by('-sent_at')
    
    # Créer un dictionnaire pour regrouper les conversations par other_user uniquement
    # Clé: other_user_id - une seule conversation par utilisateur, peu importe le logement
    conversations_dict = {}
    
    # Traiter tous les messages pour regrouper par utilisateur
    for message in all_messages:
            # Déterminer l'autre utilisateur
        if message.sender == request.user:
            other_user = message.receiver
        else:
            other_user = message.sender
        
        # Ignorer les messages avec soi-même
        if other_user == request.user:
            continue
        
        # Clé unique: other_user_id seulement - une conversation par utilisateur
        conv_key = other_user.id
        
        # Si c'est une nouvelle conversation
        if conv_key not in conversations_dict:
            # Déterminer le logement à afficher (le plus récent ou le premier trouvé)
            logement = None
            if message.logement:
                logement = message.logement
            else:
                # Si pas de logement, chercher un logement du propriétaire
                user_logements = Logement.objects.filter(owner=other_user, approved=True).first()
                if user_logements:
                    logement = user_logements
            
            # Créer la conversation même si aucun logement n'est trouvé
            conversations_dict[conv_key] = {
                'logement': logement,
                'other_user': other_user,
                'last_message': message,
                'unread_count': 0,
            }
        else:
            # Mettre à jour la conversation existante
            existing = conversations_dict[conv_key]
            if message.sent_at > existing['last_message'].sent_at:
                existing['last_message'] = message
                # Mettre à jour le logement si le nouveau message a un logement plus récent
                if message.logement:
                    # Vérifier si ce logement est plus récent ou plus pertinent
                    existing_logement = existing['logement']
                    if not existing_logement or (message.logement.created_at > existing_logement.created_at):
                        existing['logement'] = message.logement
                # Si pas de logement dans le message mais qu'on n'en a pas encore, chercher un logement du propriétaire
                elif not existing['logement']:
                    user_logements = Logement.objects.filter(owner=other_user, approved=True).first()
                    if user_logements:
                        existing['logement'] = user_logements
    
    # Calculer les messages non lus pour chaque conversation
    for conv_key, conv in conversations_dict.items():
        other_user = conv['other_user']
        
        # Compter tous les messages non lus entre request.user et other_user (tous logements confondus)
        unread_count = Message.objects.filter(
            sender=other_user,
            receiver=request.user,
            read=False,
            deleted=False
        ).count()
        
        conv['unread_count'] = unread_count
    
    # Convertir le dictionnaire en liste et filtrer les conversations sans logement
    conversations = [conv for conv in conversations_dict.values() if conv['logement'] is not None]
    
    # Trier par date du dernier message
    conversations.sort(key=lambda x: x['last_message'].sent_at if x['last_message'] else timezone.now(), reverse=True)
    
    return render(request, 'User/LogementApp/marketplace_messages_list.html', {
        'conversations': conversations
    })


@login_required
def binome_search(request):
    """Page de recherche de binômes (colocataires)"""
    from .models import BinomeRequest
    
    # Récupérer toutes les demandes de binômes (sauf celles de l'utilisateur)
    binome_requests = BinomeRequest.objects.exclude(user=request.user).filter(status='PENDING').order_by('-created_at')
    
    # Récupérer les demandes de l'utilisateur
    my_requests = BinomeRequest.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'User/LogementApp/binome_search.html', {
        'binome_requests': binome_requests,
        'my_requests': my_requests
    })


@login_required
def binome_add(request):
    """Créer une demande de recherche de binôme"""
    from .models import BinomeRequest
    from .forms import BinomeRequestForm
    
    if request.method == 'POST':
        form = BinomeRequestForm(request.POST, user=request.user)
        if form.is_valid():
            binome_request = form.save(commit=False)
            binome_request.user = request.user
            binome_request.status = 'PENDING'
            binome_request.save()
            messages.success(request, 'Votre demande de recherche de binôme a été créée avec succès!')
            return redirect('binome_search')
    else:
        form = BinomeRequestForm(user=request.user)
    
    return render(request, 'User/LogementApp/binome_add.html', {
        'form': form
    })


@login_required
def binome_detail(request, request_id):
    """Détails d'une demande de binôme"""
    from .models import BinomeRequest
    binome_request = get_object_or_404(BinomeRequest, id=request_id)
    
    return render(request, 'User/LogementApp/binome_detail.html', {
        'binome_request': binome_request
    })


@login_required
def binome_contact(request, request_id):
    """Contacter un utilisateur pour une demande de binôme"""
    from .models import BinomeRequest
    from UserApp.models import Message, Connection
    from django.db.models import Q
    
    binome_request = get_object_or_404(BinomeRequest, id=request_id)
    
    if binome_request.user == request.user:
        messages.error(request, "Vous ne pouvez pas vous contacter vous-même.")
        return redirect('binome_search')
    
    # Vérifier si les utilisateurs sont connectés (pour messages personnels)
    connection = Connection.objects.filter(
        Q(from_user=request.user, to_user=binome_request.user) |
        Q(from_user=binome_request.user, to_user=request.user)
    ).first()
    
    is_connected = connection and connection.status == 'accepted'
    
    # Si pas connecté, créer une demande de connexion automatiquement
    if not is_connected:
        if not connection:
            Connection.objects.create(
                from_user=request.user,
                to_user=binome_request.user,
                status='pending'
            )
            messages.info(request, "Une demande de connexion a été envoyée. Vous pourrez envoyer un message une fois la connexion acceptée.")
        else:
            messages.info(request, "Votre demande de connexion est en attente. Vous pourrez envoyer un message une fois acceptée.")
        return redirect('user_profile', user_id=binome_request.user.id)
    
    # Si connecté, créer le message directement
    initial_message = f"Bonjour, je suis intéressé(e) par votre recherche de binôme pour {binome_request.city}. Budget: {binome_request.budget_max} DZD."
    
    message = Message.objects.create(
        sender=request.user,
        receiver=binome_request.user,
        text=initial_message,
        logement=None  # Message personnel, pas marketplace
    )
    
    messages.success(request, "Message envoyé! Vous pouvez continuer la conversation dans vos messages.")
    return redirect('messages_conversation', user_id=binome_request.user.id)


@login_required
def binome_edit(request, request_id):
    """Modifier une demande de binôme"""
    from .models import BinomeRequest
    from .forms import BinomeRequestForm
    
    binome_request = get_object_or_404(BinomeRequest, id=request_id)
    
    # Vérifier que l'utilisateur est le propriétaire de la demande
    if binome_request.user != request.user:
        messages.error(request, "Vous n'avez pas la permission de modifier cette demande.")
        return redirect('binome_search')
    
    if request.method == 'POST':
        form = BinomeRequestForm(request.POST, instance=binome_request, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre demande de binôme a été modifiée avec succès!')
            return redirect('binome_search')
    else:
        form = BinomeRequestForm(instance=binome_request, user=request.user)
    
    return render(request, 'User/LogementApp/binome_edit.html', {
        'form': form,
        'binome_request': binome_request
    })


@login_required
def binome_delete(request, request_id):
    """Supprimer une demande de binôme"""
    from .models import BinomeRequest
    
    binome_request = get_object_or_404(BinomeRequest, id=request_id)
    
    # Vérifier que l'utilisateur est le propriétaire de la demande
    if binome_request.user != request.user:
        messages.error(request, "Vous n'avez pas la permission de supprimer cette demande.")
        return redirect('binome_search')
    
    if request.method == 'POST':
        binome_request.delete()
        messages.success(request, 'Votre demande de binôme a été supprimée avec succès!')
        return redirect('binome_search')
    
    return render(request, 'User/LogementApp/binome_delete.html', {
        'binome_request': binome_request
    })


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def approve_logement(request, logement_id):
    """Approuver un logement"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
        return redirect('admin_dashboard')
    
    logement = get_object_or_404(Logement, id=logement_id)
    logement.approved = True
    logement.rejected = False  # Enlever le statut rejeté si on approuve
    logement.save()
    messages.success(request, f'Le logement "{logement.title}" a été approuvé avec succès!')
    return redirect('manage_logements')


@login_required
@user_passes_test(is_superuser_or_admin, login_url='/login/')
def reject_logement(request, logement_id):
    """Rejeter un logement"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
        return redirect('admin_dashboard')
    
    logement = get_object_or_404(Logement, id=logement_id)
    logement.rejected = True
    logement.approved = False  # S'assurer qu'il n'est pas approuvé
    logement.save()
    messages.success(request, f'Le logement "{logement.title}" a été rejeté.')
    return redirect('manage_logements')
