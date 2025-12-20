from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from functools import wraps
import logging
import json
import requests
from UserApp.models import CustomUser, Post, Comment, Connection, Message, AdminMessage
from .models import Logement, LogementImage, TemporaryImage
from .forms import LogementForm
from .ml_service import predict_price

from .recommendation import RecommendationEngine

logger = logging.getLogger(__name__)

# Décorateur pour vérifier si l'utilisateur est superuser ou admin
def is_superuser_or_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'ADMIN'))

# Décorateur personnalisé pour les pages admin qui ne déconnecte pas
def admin_required(view_func):
    """
    Décorateur qui vérifie que l'utilisateur est admin/superuser.
    Si connecté mais pas admin → redirige vers index (pas login)
    Si pas connecté → redirige vers login
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('index')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

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
    
    # Pagination
    paginator = Paginator(logements, 9) # 9 logements par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get recommendations for logged-in users
    recommendations = []
    if request.user.is_authenticated:
        try:
            engine = RecommendationEngine()
            recommendations = engine.get_recommendations(request.user, limit=3)
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}", exc_info=True)
    
    context = {
        'page_obj': page_obj,
        'all_cities': all_cities, # Keep all_cities in context
        'filters': { # Keep filters in context
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
        },
        'recommendations': recommendations,
    }
    
    return render(request, 'User/LogementApp/logements.html', context)


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
            try:
                logement = form.save(commit=False)
                logement.owner = request.user
                logement.approved = False  # Par défaut, non approuvé
                logement.save()
                
                # Traiter les images multiples
                images = request.FILES.getlist('images')
                for image in images:
                    LogementImage.objects.create(logement=logement, image=image)
                
                messages.success(request, '✅ Logement ajouté avec succès! ⏳ Votre logement est maintenant en attente d\'approbation par un administrateur. Il sera visible une fois approuvé.')
                return redirect('my_logements')
            except Exception as e:
                error_msg = str(e)
                messages.error(request, f'Une erreur est survenue lors de l\'ajout du logement: {error_msg}')
                # Log l'erreur pour le débogage
                logger.error(f'Erreur lors de l\'ajout du logement: {error_msg}', exc_info=True)
        else:
            # Afficher les erreurs du formulaire
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = form.fields[field].label if field in form.fields else field
                    error_messages.append(f"{field_label}: {error}")
            if error_messages:
                messages.error(request, 'Veuillez corriger les erreurs suivantes: ' + ' | '.join(error_messages[:5]))  # Limiter à 5 erreurs pour éviter un message trop long
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
@admin_required
def dashboard(request):
    """Dashboard principal avec statistiques sur les utilisateurs"""
    
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
@admin_required
def admin_edubot(request):
    """
    Page complète pour le chatbot EduBot dans le backoffice.
    """
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    return render(request, 'User/Backoffice/edubot.html')


@login_required
@admin_required
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
@admin_required
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
@admin_required
def tables(request):
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('index')
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'User/Backoffice/tables.html', { 'users': users })


@login_required
@admin_required
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
@admin_required
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
    initial_message = f"Bonjour, je suis intéressé(e) par votre recherche de binôme pour {binome_request.city}. Budget: {binome_request.budget_max} DT."
    
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
@admin_required
def approve_logement(request, logement_id):
    """Approuver un logement"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
        return redirect('admin_dashboard')
    
    logement = get_object_or_404(Logement, id=logement_id)
    logement.approved = True
    logement.rejected = False  # Enlever le statut rejeté si on approuve
    logement.save()
    messages.success(request, f'✅ Le logement "{logement.title}" a été approuvé avec succès!')
    # Rediriger vers la page d'origine ou le dashboard logements
    referer = request.META.get('HTTP_REFERER', '')
    if 'dashboard' in referer or 'manage' in referer:
        return redirect(referer)
    return redirect('dashboard_logements')


@login_required
@admin_required
def reject_logement(request, logement_id):
    """Rejeter un logement"""
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
        return redirect('admin_dashboard')
    
    logement = get_object_or_404(Logement, id=logement_id)
    logement.rejected = True
    logement.approved = False  # S'assurer qu'il n'est pas approuvé
    logement.save()
    messages.success(request, f'❌ Le logement "{logement.title}" a été rejeté.')
    # Rediriger vers la page d'origine ou le dashboard logements
    referer = request.META.get('HTTP_REFERER', '')
    if 'dashboard' in referer or 'manage' in referer:
        return redirect(referer)
    return redirect('dashboard_logements')

# ======================================================
# 🗺️ Mapping Ville → Région (ALIGNÉ AU MODÈLE ML)
# ======================================================

CITY_TO_REGION = {
    # Grand Tunis
    "Tunis": "Grand Tunis",
    "Ariana": "Grand Tunis",
    "Ben Arous": "Grand Tunis",
    "Manouba": "Grand Tunis",

    # Cap Bon
    "Nabeul": "Cap Bon",
    "Hammamet": "Cap Bon",
    "Kelibia": "Cap Bon",
    "Korba": "Cap Bon",

    # Centre Est
    "Sousse": "Centre Est",
    "Monastir": "Centre Est",
    "Mahdia": "Centre Est",
    "Sfax": "Centre Est",

    # Centre
    "Kairouan": "Centre",
    "Sidi Bouzid": "Centre",

    # Nord
    "Bizerte": "Nord",

    # Nord Ouest
    "Beja": "Nord Ouest",
    "Jendouba": "Nord Ouest",
    "Kef": "Nord Ouest",
    "Siliana": "Nord Ouest",

    # Sud Est
    "Gabes": "Sud Est",
    "Mednine": "Sud Est",
    "Tataouine": "Sud Est",

    # Sud Ouest
    "Gafsa": "Sud Ouest",
    "Tozeur": "Sud Ouest",
    "Kebili": "Sud Ouest"
}


@require_http_methods(["POST"])
@csrf_exempt
def predict_price_api(request):
    """
    API endpoint pour prédire le prix d'un logement

    JSON attendu :
    {
        "city": "Tunis",
        "surface": 95,
        "bathrooms": 2,
        "rooms": 3,
        "type": "Appartement"
    }
    """

    try:
        # ======================================================
        # 📥 PARSING
        # ======================================================
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        # 🔤 Normalisation ville
        city_raw = data.get("city", "")
        city = city_raw.strip().title()

        if not city:
            return JsonResponse(
                {"success": False, "error": "La ville est requise"},
                status=400
            )

        # 🗺️ Déduction région
        region = CITY_TO_REGION.get(city)
        if not region:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Ville '{city}' non reconnue par le modèle"
                },
                status=400
            )

        logement_type = (
    data.get("type") or
    data.get("type_logement") or
    ""
).strip()

        surface = data.get("surface")
        bathrooms = data.get("bathrooms")
        rooms = data.get("rooms")

        # ======================================================
        # ✅ VALIDATIONS
        # ======================================================
        if not logement_type:
            return JsonResponse(
                {"success": False, "error": "Le type de logement est requis"},
                status=400
            )

        try:
            surface = float(surface)
            if surface <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "error": "La surface doit être un nombre positif"},
                status=400
            )

        try:
            bathrooms = int(bathrooms)
            if bathrooms <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "error": "Le nombre de salles de bain doit être un entier positif"},
                status=400
            )

        try:
            rooms = int(rooms)
            if rooms <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "error": "Le nombre de pièces doit être un entier positif"},
                status=400
            )

        # ======================================================
        # 🔮 PRÉDICTION ML
        # ======================================================
        predicted_price = predict_price(
            city=city,
            region=region,
            surface=surface,
            bathrooms=bathrooms,
            rooms=rooms,
            logement_type=logement_type
        )

        # ======================================================
        # 📤 RÉPONSE
        # ======================================================
        return JsonResponse({
            "success": True,
            "predicted_price": predicted_price,
            "currency": "TND"
        })

    except Exception:
        logger.error("Erreur lors de la prédiction du prix", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": "Une erreur interne est survenue lors de la prédiction"
            },
            status=500
        )


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def logement_generate_ai(request):
    """
    Système de conversation interactive avec IA pour créer un logement.
    L'IA pose des questions pour compléter les champs manquants, puis crée le logement.
    """
    try:
        # Lire les données JSON
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])  # Historique de la conversation
        current_data = data.get('current_data', {})  # Données collectées jusqu'à présent
        
        if not user_message:
            return JsonResponse(
                {"success": False, "error": "Le message est requis"},
                status=400
            )
        
        # Récupérer la configuration Groq
        api_key = getattr(settings, "EDUBOT_API_KEY", "")
        api_base = getattr(settings, "EDUBOT_API_BASE", "https://api.groq.com/openai/v1")
        model = getattr(settings, "EDUBOT_MODEL", "llama-3.1-8b-instant")
        
        if not api_key:
            return JsonResponse(
                {"success": False, "error": "Clé API Groq non configurée"},
                status=500
            )
        
        # Construire le prompt système avec les données déjà collectées
        current_data_str = json.dumps(current_data, ensure_ascii=False) if current_data else "{}"
        
        # Définir l'ordre des questions
        field_order = [
            ("title", "Quel titre souhaitez-vous donner à votre annonce ?"),
            ("type_logement", "Quel est le type de logement (APPARTEMENT, MAISON, STUDIO, VILLA, ou AUTRE) ?"),
            ("description", "Décrivez votre logement en détail (caractéristiques, avantages, équipements, localisation, etc.)"),
            ("address", "Quelle est l'adresse complète du logement ?"),
            ("city", "Dans quelle ville se trouve le logement ?"),
            ("rooms", "Combien de pièces contient le logement ?"),
            ("bathrooms", "Combien de salles de bain y a-t-il ?"),
            ("wifi", "Le logement dispose-t-il d'un accès WiFi (oui/non) ?"),
            ("surface", "Quelle est la surface du logement en m² ?"),
            ("price", "Quel est le prix mensuel du logement en DT ? (Vous pouvez répondre 'prédire' pour que l'IA estime le prix)")
        ]
        
        # Trouver le prochain champ manquant dans l'ordre
        missing_fields = []
        for field, question in field_order:
            if field not in current_data or not current_data[field] or current_data[field] == "":
                missing_fields.append((field, question))
        
        next_question = missing_fields[0][1] if missing_fields else None
        next_field = missing_fields[0][0] if missing_fields else None
        
        # Si c'est le premier message, donner des instructions spéciales pour extraire tout
        is_first_message = len(conversation_history) == 0
        
        first_message_instruction = ""
        if is_first_message:
            first_message_instruction = """
⚠️ C'EST LE PREMIER MESSAGE - INSTRUCTIONS SPÉCIALES :
- L'utilisateur peut donner soit une description complète en un paragraphe, soit répondre à la première question (titre)
- Si l'utilisateur donne une description complète : EXTRAIS TOUTES les informations possibles :
  * Titre (génère-en un accrocheur si non mentionné)
  * Type de logement (APPARTEMENT, MAISON, STUDIO, VILLA, AUTRE)
  * Description complète
  * Adresse et ville (cherche les noms de villes tunisiennes)
  * Prix (cherche les montants en DT, DZD, ou "prix")
  * Surface (cherche "m²", "m2", "mètres carrés")
  * Nombre de pièces (cherche "pièces", "chambres", "chambre")
  * Nombre de salles de bain (cherche "salle de bain", "bain")
  * WiFi (cherche "wifi", "internet", "connexion")
  * Modèle 3D (cherche des URLs de modèles 3D si mentionné)
- Si l'utilisateur donne juste le titre : enregistre-le et pose la prochaine question
- Extrais le maximum d'informations avant de poser des questions
- Si l'utilisateur dit "prédire" ou "estimer" pour le prix, note-le comme "PREDICT_PRICE"
- Si beaucoup d'informations sont extraites, dis "J'ai extrait les informations suivantes : [liste]. Il me manque encore : [liste des champs manquants]"
"""
        
        system_prompt = f"""Tu es un assistant expert en immobilier qui aide à créer des annonces de logement.

{first_message_instruction}

DONNÉES DÉJÀ COLLECTÉES (ne pose JAMAIS de questions sur ces champs) :
{current_data_str}

PROCHAINE QUESTION À POSER (si nécessaire, dans cet ordre) :
{next_question if next_question else "Aucune - tous les champs sont remplis"}

TON RÔLE :
1. Si l'utilisateur donne une description complète en un paragraphe : EXTRAIS TOUTES les informations possibles (titre, type, description, adresse, ville, prix, surface, pièces, salles de bain, wifi, modèle 3D si mentionné)
2. Mettre à jour les données collectées avec les nouvelles informations extraites
3. Si tous les champs obligatoires sont remplis : dire "READY_TO_CREATE" et retourner le JSON complet
4. Si l'utilisateur dit "créer", "valider", "ok", "c'est bon", "c'est tout", "terminer", "finaliser" ou équivalent APRÈS avoir donné des informations : vérifie si tous les champs sont remplis, sinon demande les champs manquants, sinon déclenche "READY_TO_CREATE"
5. Si des champs manquent : répondre "DATA_UPDATE:" suivi du JSON mis à jour, puis poser UNIQUEMENT la prochaine question dans l'ordre
6. Les images sont gérées séparément via upload (ne pas demander dans les questions)
7. Le modèle 3D et la vidéo sont optionnels (ne demander que si l'utilisateur les mentionne)

CHAMPS OBLIGATOIRES (dans cet ordre) :
1. title (titre accrocheur, max 200 caractères)
2. type_logement (APPARTEMENT, MAISON, STUDIO, VILLA, ou AUTRE)
3. description (description détaillée)
4. address (adresse complète)
5. city (ville en Tunisie)
6. rooms (nombre de pièces, entier)
7. bathrooms (nombre de salles de bain, entier, défaut: 1)
8. wifi (true ou false, défaut: false)
9. surface (surface en m², nombre)
10. price (prix en nombre, en DT, ou "PREDICT_PRICE" si l'utilisateur veut une prédiction)

RÈGLES CRITIQUES :
- Extrais TOUTES les informations du message, même si plusieurs sont mentionnées
- NE pose JAMAIS de questions sur les champs déjà remplis dans current_data
- Pose UNIQUEMENT la prochaine question dans l'ordre défini ci-dessus
- Si l'utilisateur donne plusieurs informations, enregistre-les TOUTES dans DATA_UPDATE
- Si l'utilisateur dit "créer", "valider", "ok", "c'est bon", "c'est tout", "terminer", "finaliser", "je valide", "créer le logement" : vérifie tous les champs, si tout est rempli → "READY_TO_CREATE", sinon liste les champs manquants
- Pour "wifi", accepte: oui/oui/non/non/true/false/wifi
- Pour "type_logement", accepte uniquement: APPARTEMENT, MAISON, STUDIO, VILLA, AUTRE
- Pour "surface", cherche "m²" ou "m2" dans le texte
- Pour "rooms", cherche "pièces", "chambres", "chambre" dans le texte
- Pour "bathrooms", cherche "salle de bain", "salles de bain", "bain" dans le texte
- Pour "price", si l'utilisateur dit "prédire" ou "estimer", mets "PREDICT_PRICE"
- Si l'utilisateur donne une description complète en un paragraphe, extrais TOUT ce que tu peux

FORMAT DE RÉPONSE :
Si des champs manquent :
DATA_UPDATE: {{"field1": "value1", "field2": "value2", ...}}
[Prochaine question dans l'ordre - UNE SEULE question]

Si tout est rempli :
READY_TO_CREATE
{{"title": "...", "description": "...", "type_logement": "APPARTEMENT", "address": "...", "city": "...", "price": 500, "surface": 80, "rooms": 3, "bathrooms": 2, "wifi": true, "model_3d": "url_ou_vide"}}

NOTE IMPORTANTE :
- Si l'utilisateur donne une description complète en un paragraphe, extrais TOUTES les informations possibles
- Les images sont gérées séparément via upload (ne pas demander dans les questions)
- Le modèle 3D et la vidéo sont optionnels (ne pas demander si l'utilisateur ne les mentionne pas)
- Pour le prix, si l'utilisateur dit "prédire" ou "estimer", utilise "PREDICT_PRICE" """
        
        # Construire l'historique de conversation
        messages = [{"role": "system", "content": system_prompt}]
        
        # Ajouter l'historique
        for msg in conversation_history:
            messages.append(msg)
        
        # Ajouter le message actuel
        messages.append({"role": "user", "content": user_message})
        
        # Appel à l'API Groq avec retry en cas d'erreur 429
        max_retries = 3
        retry_delay = 2  # secondes
        ai_response = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 500
                    },
                    timeout=30
                )
                
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        import time
                        wait_time = retry_delay * (attempt + 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        return JsonResponse({
                            "success": False,
                            "error": "Trop de requêtes. Veuillez patienter 10-15 secondes avant de réessayer.",
                            "message": "L'API est temporairement surchargée. Veuillez patienter quelques secondes puis réessayez.",
                            "continue": True
                        }, status=429)
                
                response.raise_for_status()
                data_response = response.json()
                ai_response = data_response["choices"][0]["message"]["content"].strip()
                break  # Succès, sortir de la boucle
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        import time
                        wait_time = retry_delay * (attempt + 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        return JsonResponse({
                            "success": False,
                            "error": "Trop de requêtes. Veuillez patienter 10-15 secondes avant de réessayer.",
                            "message": "L'API est temporairement surchargée. Veuillez patienter quelques secondes puis réessayez.",
                            "continue": True
                        }, status=429)
                else:
                    raise
        
        # Si aucune réponse n'a été obtenue après tous les essais
        if ai_response is None:
            return JsonResponse({
                "success": False,
                "error": "Erreur lors de l'appel à l'API. Veuillez réessayer.",
                "message": "Une erreur s'est produite. Veuillez réessayer.",
                "continue": True
            }, status=500)
            
        # Vérifier si l'utilisateur veut créer le logement (mots-clés de validation)
        validation_keywords = ['créer', 'valider', 'ok', 'c\'est bon', 'c\'est tout', 'terminer', 'finaliser', 'je valide', 'créer le logement', 'c\'est parfait', 'parfait']
        user_wants_to_create = any(keyword in user_message.lower() for keyword in validation_keywords)
        
        # Si l'utilisateur veut créer et que tous les champs sont remplis, forcer READY_TO_CREATE
        if user_wants_to_create:
            required_fields = ['title', 'description', 'type_logement', 'address', 'city', 'price', 'surface', 'rooms', 'bathrooms']
            all_fields_present = all(
                field in current_data and current_data[field] and str(current_data[field]).strip() != ""
                for field in required_fields
            )
            if all_fields_present:
                # Forcer la création
                ai_response = "READY_TO_CREATE\n" + json.dumps(current_data, ensure_ascii=False)
        
        # Vérifier si l'IA a mis à jour les données
        updated_data = current_data.copy()
        if "DATA_UPDATE:" in ai_response:
                # Extraire le JSON mis à jour
                data_start = ai_response.find("DATA_UPDATE:") + len("DATA_UPDATE:")
                json_start = ai_response.find("{", data_start)
                json_end = ai_response.find("}", json_start) + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = ai_response[json_start:json_end].strip()
                    try:
                        new_data = json.loads(json_str)
                        # Nettoyer et valider les données
                        for key, value in new_data.items():
                            if value is not None and value != "":
                                # Conversion spéciale pour certains champs
                                if key == "wifi":
                                    if isinstance(value, str):
                                        updated_data[key] = value.lower() in ['true', '1', 'yes', 'oui', 'wifi', 'oui']
                                    else:
                                        updated_data[key] = bool(value)
                                elif key in ['price', 'surface']:
                                    try:
                                        updated_data[key] = float(value)
                                    except (ValueError, TypeError):
                                        pass
                                elif key in ['rooms', 'bathrooms']:
                                    try:
                                        updated_data[key] = int(float(value))
                                    except (ValueError, TypeError):
                                        pass
                                elif key == "type_logement":
                                    valid_types = ['APPARTEMENT', 'MAISON', 'STUDIO', 'VILLA', 'AUTRE']
                                    if value.upper() in valid_types:
                                        updated_data[key] = value.upper()
                                elif key == "model_3d":
                                    # Garder l'URL du modèle 3D si fournie
                                    if value and isinstance(value, str) and (value.startswith('http') or value.startswith('https')):
                                        updated_data[key] = value
                                else:
                                    updated_data[key] = str(value)
                        # Nettoyer la réponse pour ne garder que la question
                        ai_response = ai_response[json_end:].strip()
                        if ai_response.startswith("\n"):
                            ai_response = ai_response[1:].strip()
                    except json.JSONDecodeError as e:
                        logger.error(f"Erreur parsing DATA_UPDATE: {json_str}", exc_info=True)
        
        # Vérifier si l'IA dit que tout est prêt
        if "READY_TO_CREATE" in ai_response:
                # Extraire le JSON
                json_start = ai_response.find("{")
                json_end = ai_response.rfind("}") + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = ai_response[json_start:json_end]
                    try:
                        logement_data = json.loads(json_str)
                        
                        # Valider et nettoyer les données
                        valid_types = ['APPARTEMENT', 'MAISON', 'STUDIO', 'VILLA', 'AUTRE']
                        if logement_data.get('type_logement') not in valid_types:
                            logement_data['type_logement'] = 'AUTRE'
                        
                        # Convertir les valeurs numériques
                        for field in ['price', 'surface', 'rooms', 'bathrooms']:
                            if field in logement_data and logement_data[field] is not None:
                                try:
                                    if field in ['rooms', 'bathrooms']:
                                        logement_data[field] = int(float(logement_data[field]))
                                    else:
                                        logement_data[field] = float(logement_data[field])
                                except (ValueError, TypeError):
                                    return JsonResponse({
                                        "success": False,
                                        "error": f"Valeur invalide pour {field}",
                                        "message": "Veuillez fournir une valeur valide.",
                                        "continue": True
                                    })
                        
                        # Convertir wifi
                        if 'wifi' in logement_data:
                            wifi_val = logement_data['wifi']
                            if isinstance(wifi_val, str):
                                logement_data['wifi'] = wifi_val.lower() in ['true', '1', 'yes', 'oui', 'wifi']
                            else:
                                logement_data['wifi'] = bool(wifi_val)
                        else:
                            logement_data['wifi'] = False
                        
                        # Gérer la prédiction de prix si demandée
                        if logement_data.get('price') == 'PREDICT_PRICE' or (isinstance(logement_data.get('price'), str) and 'prédire' in logement_data.get('price', '').lower()):
                            # Utiliser le service de prédiction ML
                            try:
                                from .ml_service import predict_price
                                
                                city = logement_data.get('city', 'Tunis')
                                region = CITY_TO_REGION.get(city, 'Grand Tunis')
                                surface = float(logement_data.get('surface', 0))
                                bathrooms = int(logement_data.get('bathrooms', 1))
                                rooms = int(logement_data.get('rooms', 1))
                                logement_type = logement_data.get('type_logement', 'APPARTEMENT')
                                
                                predicted_price = predict_price(
                                    city=city,
                                    region=region,
                                    surface=surface,
                                    bathrooms=bathrooms,
                                    rooms=rooms,
                                    logement_type=logement_type
                                )
                                logement_data['price'] = float(predicted_price)
                            except Exception as e:
                                logger.error(f"Erreur lors de la prédiction du prix: {e}", exc_info=True)
                                return JsonResponse({
                                    "success": False,
                                    "error": "Impossible de prédire le prix. Veuillez fournir un prix manuellement.",
                                    "message": "Impossible de prédire le prix. Veuillez indiquer le prix mensuel en DT.",
                                    "continue": True
                                })
                        
                        # Vérifier que tous les champs obligatoires sont présents
                        required_fields = ['title', 'description', 'type_logement', 'address', 'city', 'price', 'surface', 'rooms', 'bathrooms']
                        missing_fields = [f for f in required_fields if not logement_data.get(f)]
                        
                        if missing_fields:
                            return JsonResponse({
                                "success": False,
                                "error": f"Champs manquants: {', '.join(missing_fields)}",
                                "message": f"Veuillez fournir: {', '.join(missing_fields)}",
                                "continue": True
                            })
                        
                        # Récupérer les images temporaires si elles existent
                        image_ids = data.get('image_ids', [])
                        
                        # Déterminer l'image principale (première image si disponible)
                        main_image = None
                        if image_ids:
                            try:
                                from .models import TemporaryImage
                                temp_img = TemporaryImage.objects.filter(id=image_ids[0], user=request.user).first()
                                if temp_img:
                                    main_image = temp_img.image
                            except Exception:
                                pass
                        
                        # Créer le logement directement dans la base de données
                        try:
                            logement = Logement.objects.create(
                                owner=request.user,
                                title=logement_data['title'],
                                description=logement_data['description'],
                                type_logement=logement_data['type_logement'],
                                address=logement_data['address'],
                                city=logement_data['city'],
                                price=logement_data['price'],
                                surface=logement_data['surface'],
                                rooms=logement_data['rooms'],
                                bathrooms=logement_data.get('bathrooms', 1),
                                wifi=logement_data.get('wifi', False),
                                image=main_image,  # Image principale
                                model_3d=logement_data.get('model_3d') or None,  # Modèle 3D optionnel
                                approved=False,  # En attente d'approbation par un administrateur
                                rejected=False,
                                available=True
                            )
                            
                            # Associer les images secondaires au logement (sauf la première qui est l'image principale)
                            if len(image_ids) > 1:
                                from .models import LogementImage, TemporaryImage
                                for img_id in image_ids[1:]:  # Sauter la première image (déjà utilisée comme principale)
                                    try:
                                        temp_img = TemporaryImage.objects.get(id=img_id, user=request.user)
                                        LogementImage.objects.create(
                                            logement=logement,
                                            image=temp_img.image
                                        )
                                        temp_img.delete()  # Supprimer l'image temporaire
                                    except TemporaryImage.DoesNotExist:
                                        pass
                            
                            # Supprimer aussi la première image temporaire si elle a été utilisée
                            if image_ids and main_image:
                                try:
                                    from .models import TemporaryImage
                                    temp_img = TemporaryImage.objects.filter(id=image_ids[0], user=request.user).first()
                                    if temp_img:
                                        temp_img.delete()
                                except Exception:
                                    pass
                            
                            return JsonResponse({
                                "success": True,
                                "created": True,
                                "logement_id": logement.id,
                                "message": "✅ Logement créé avec succès! Il est maintenant en attente d'approbation par un administrateur."
                            })
                        except Exception as e:
                            logger.error(f"Erreur lors de la création du logement: {e}", exc_info=True)
                            return JsonResponse({
                                "success": False,
                                "error": f"Erreur lors de la création: {str(e)}",
                                "continue": True
                            })
                    except json.JSONDecodeError as e:
                        logger.error(f"Erreur parsing JSON: {ai_response}", exc_info=True)
                        return JsonResponse({
                            "success": False,
                            "error": "Erreur lors de l'analyse de la réponse",
                            "message": "Veuillez réessayer.",
                            "continue": True
                        })
        
        # Si pas prêt, retourner la question de l'IA avec les données mises à jour
        return JsonResponse({
            "success": True,
            "created": False,
            "message": ai_response,
            "current_data": updated_data,
            "continue": True
        })
        
    except requests.RequestException as e:
            logger.error(f"Erreur API Groq: {e}", exc_info=True)
            error_msg = str(e)
            if "429" in error_msg or "Too Many Requests" in error_msg:
                return JsonResponse(
                    {"success": False, "error": "Trop de requêtes. Veuillez patienter quelques secondes avant de réessayer.", "continue": True},
                    status=429
                )
            return JsonResponse(
                {"success": False, "error": f"Erreur lors de l'appel à l'API: {error_msg}", "continue": True},
                status=500
            )
    except Exception as e:
        logger.error(f"Erreur lors de la génération: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": f"Erreur lors du traitement: {str(e)}"},
            status=500
        )
            
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "JSON invalide"},
            status=400
        )
    except Exception as e:
        logger.error(f"Erreur serveur: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": f"Erreur serveur : {str(e)}"},
            status=500
        )


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def upload_temp_image(request):
    """
    Upload une image temporaire pendant la création avec IA
    """
    try:
        if 'image' not in request.FILES:
            return JsonResponse(
                {"success": False, "error": "Aucune image fournie"},
                status=400
            )
        
        image_file = request.FILES['image']
        
        # Créer l'image temporaire
        temp_image = TemporaryImage.objects.create(
            user=request.user,
            image=image_file
        )
        
        return JsonResponse({
            "success": True,
            "image_id": temp_image.id,
            "image_url": temp_image.image.url
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'upload d'image temporaire: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": f"Erreur lors de l'upload: {str(e)}"},
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def summarize_description(request, logement_id):
    """
    Endpoint pour résumer la description d'un logement en utilisant Groq (LLM).
    """
    try:
        # Récupérer le logement
        logement = get_object_or_404(Logement, id=logement_id)
        
        # Vérifier que la description existe et n'est pas vide
        description = logement.description
        if not description or len(description.strip()) == 0:
            return JsonResponse(
                {"error": "La description est vide"},
                status=400
            )
        
        # Vérifier si la description est assez longue pour justifier un résumé
        # (optionnel, mais on peut définir un seuil, par exemple 200 caractères)
        if len(description) < 200:
            return JsonResponse(
                {"error": "La description est trop courte pour être résumée"},
                status=400
            )
        
        # Récupérer la configuration Groq depuis settings
        api_key = getattr(settings, "EDUBOT_API_KEY", "")
        api_base = getattr(settings, "EDUBOT_API_BASE", "https://api.groq.com/openai/v1")
        model = getattr(settings, "EDUBOT_MODEL", "llama-3.1-8b-instant")
        
        if not api_key:
            return JsonResponse(
                {"error": "Clé API Groq non configurée"},
                status=500
            )
        
        # Appel à l'API Groq pour résumer
        try:
            response = requests.post(
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
                            "content": (
                                "Tu es un expert en synthèse de descriptions immobilières. "
                                "Ton rôle est de créer un résumé ULTRA-CONCIS (maximum 2-3 phrases) qui capture uniquement l'essentiel. "
                                "Élimine les répétitions et les détails superflus. "
                                "Garde uniquement : type de logement, équipements principaux, localisation/avantages clés. "
                                "Réponds UNIQUEMENT avec le résumé, sans introduction ni formule comme 'Voici un résumé'."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Résume de manière ultra-concise cette description de logement (2-3 phrases maximum) :\n\n{description}"
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 150
                },
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            summary = data["choices"][0]["message"]["content"].strip()
            
            # Nettoyer le résumé : supprimer les phrases d'introduction communes
            phrases_intro = [
                "Voici un résumé",
                "Résumé :",
                "Résumé de la description",
                "Description résumée :",
                "Voici le résumé",
                "Résumé de cette description"
            ]
            
            for phrase in phrases_intro:
                if summary.startswith(phrase):
                    # Supprimer la phrase d'introduction et les deux-points/points qui suivent
                    summary = summary[len(phrase):].strip()
                    if summary.startswith(":"):
                        summary = summary[1:].strip()
                    if summary.startswith("."):
                        summary = summary[1:].strip()
                    break
            
            # S'assurer que le résumé commence par une majuscule
            if summary and len(summary) > 0:
                summary = summary[0].upper() + summary[1:] if len(summary) > 1 else summary.upper()
            
            return JsonResponse({
                "success": True,
                "summary": summary,
                "original_length": len(description)
            })
            
        except requests.RequestException as e:
            logger.error(f"Erreur API Groq lors du résumé: {e}", exc_info=True)
            return JsonResponse(
                {"error": f"Erreur lors de l'appel à l'API de résumé: {str(e)}"},
                status=500
            )
        except Exception as e:
            logger.error(f"Erreur lors du résumé: {e}", exc_info=True)
            return JsonResponse(
                {"error": f"Erreur lors du traitement: {str(e)}"},
                status=500
            )
            
    except Exception as e:
        logger.error(f"Erreur serveur lors du résumé: {e}", exc_info=True)
        return JsonResponse(
            {"error": f"Erreur serveur : {str(e)}"},
            status=500
        )

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def predict_price_api(request):
    """
    API pour prédire le prix d'un logement
    """
    try:
        data = json.loads(request.body)
        
        # Validation des champs requis
        required_fields = ['city', 'surface', 'rooms', 'type']
        for field in required_fields:
            if field not in data:
                return JsonResponse({"error": f"Champ manquant : {field}"}, status=400)
        
        # Prédiction
        price = predict_price(
            city=data['city'],
            region=data.get('region', data['city']), # Par défaut région = ville
            surface=float(data['surface']),
            bathrooms=int(data.get('bathrooms', 1)),
            rooms=int(data['rooms']),
            logement_type=data['type']
        )
        
        return JsonResponse({
            "success": True, 
            "price": price,
            "message": f"Estimation : {price} DT"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide"}, status=400)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Erreur prédiction: {e}", exc_info=True)
        return JsonResponse({"error": f"Erreur serveur : {str(e)}"}, status=500)