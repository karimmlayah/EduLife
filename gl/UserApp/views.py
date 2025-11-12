from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
import json

from .forms import SignUpForm, LoginForm
from .models import CustomUser, Post, Comment, Connection, Message, PasswordResetCode
from django.core.mail import send_mail
from datetime import timedelta

# Create your views here.
def index_view(request):
    # Rediriger les superusers et admins vers le dashboard
    if request.user.is_authenticated and (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'ADMIN')):
        return redirect('/admin/')
    return render(request, 'User/evently/index.html')

def login_view(request):
    """
    Vue pour la page de login/signup
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    login_form = LoginForm()
    signup_form = SignUpForm()
    
    # VÃ©rifier dans la session si on vient d'une inscription rÃ©ussie
    show_login = request.session.get('show_login_after_signup', False)
    # Supprimer le flag de session aprÃ¨s utilisation
    if show_login:
        del request.session['show_login_after_signup']
        request.session.modified = True
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'login':
            # Récupérer les données du formulaire AVANT la validation
            identifier = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            
            # Vérifier si l'utilisateur existe et est banni AVANT la validation du formulaire
            if identifier and password:
                try:
                    user_obj = CustomUser.objects.get(Q(email=identifier) | Q(username=identifier))
                    
                    # Vérifier si l'utilisateur est banni
                    if not user_obj.is_active:
                        # Vérifier si le mot de passe est correct
                        if user_obj.check_password(password):
                            # L'utilisateur est banni et le mot de passe est correct
                            ban_message = 'Votre compte a été banni.'
                            if hasattr(user_obj, 'ban_reason') and user_obj.ban_reason:
                                ban_message += f' Raison : {user_obj.ban_reason}'
                            messages.error(request, ban_message)
                            # Créer un nouveau formulaire pour réafficher la page
                            login_form = LoginForm(request)
                            return render(request, 'User/FrontOffice/Login/login.html', {
                                'login_form': login_form,
                                'signup_form': signup_form,
                                'show_login': show_login,
                            })
                except CustomUser.DoesNotExist:
                    pass  # L'utilisateur n'existe pas, laisser le formulaire gérer l'erreur
            
            # Continuer avec la validation normale du formulaire
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                identifier = login_form.cleaned_data.get('username')
                password = login_form.cleaned_data.get('password')

                # RÃ©soudre l'identifiant (username ou email) vers l'email, car USERNAME_FIELD = 'email'
                try:
                    user_obj = CustomUser.objects.get(Q(email=identifier) | Q(username=identifier))
                    auth_identifier = user_obj.email
                except CustomUser.DoesNotExist:
                    auth_identifier = identifier  # si l'utilisateur a dÃ©jÃ  saisi un email

                user = authenticate(request, username=auth_identifier, password=password)
                
                if user is not None:
                    if user.is_active:
                        # CrÃ©er la session utilisateur
                        login(request, user)
                        # Sauvegarder dans la session que l'utilisateur est connectÃ©
                        request.session['user_id'] = user.id
                        request.session['username'] = user.username
                        messages.success(request, f'Bienvenue {user.username}!')
                        # Rediriger les superusers et admins vers le dashboard
                        if user.is_superuser or (hasattr(user, 'role') and user.role == 'ADMIN'):
                            return redirect('/admin/')
                        return redirect('index')
        
        elif form_type == 'signup':
            signup_form = SignUpForm(request.POST)
            if signup_form.is_valid():
                try:
                    user = signup_form.save()
                    # Ne pas connecter automatiquement
                    # Sauvegarder dans la session pour afficher le formulaire de login
                    request.session['show_login_after_signup'] = True
                    messages.success(request, f'Compte crÃ©Ã© avec succÃ¨s! Vous pouvez maintenant vous connecter avec votre nom d\'utilisateur et mot de passe.')
                    # Rediriger vers la page de login
                    return redirect('login')
                except Exception as e:
                    messages.error(request, f'Erreur lors de la crÃ©ation du compte: {str(e)}')
            else:
                # Afficher les erreurs de validation
                for field, errors in signup_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
    
    return render(request, 'User/FrontOffice/Login/login.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'show_login': show_login,
    })


def forgot_password_view(request):
    """
    Vue pour afficher le formulaire de mot de passe oublié
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    return render(request, 'User/FrontOffice/Login/forgot_password.html')


@require_POST
def forgot_password_submit_view(request):
    """
    Vue pour traiter la demande de réinitialisation de mot de passe
    Vérifie si l'email existe et envoie un code de vérification
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    email = request.POST.get('email', '').strip()
    
    if not email:
        messages.error(request, 'Veuillez entrer votre adresse email.')
        return redirect('forgot_password')
    
    # Vérifier si l'email existe
    try:
        user = CustomUser.objects.get(email=email)
        
        # Générer un code de 6 chiffres
        code = PasswordResetCode.generate_code()
        
        # Marquer les anciens codes comme utilisés
        PasswordResetCode.objects.filter(user=user, used=False).update(used=True)
        
        # Créer un nouveau code avec expiration de 15 minutes
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Envoyer l'email avec le code
        try:
            send_mail(
                subject='Code de réinitialisation de mot de passe - EduLife',
                message=f'''Bonjour {user.get_full_name() or user.username},

Vous avez demandé à réinitialiser votre mot de passe sur EduLife.

Votre code de vérification est : {code}

Ce code est valide pendant 15 minutes.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

Cordialement,
L'équipe EduLife''',
                from_email=None,  # Utilise DEFAULT_FROM_EMAIL
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, f'Un code de vérification a été envoyé à {email}. Veuillez vérifier votre boîte de réception.')
            # Rediriger vers la page de vérification du code
            request.session['reset_email'] = email
            return redirect('verify_reset_code')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'envoi de l\'email: {str(e)}. Veuillez réessayer plus tard.')
            return redirect('forgot_password')
            
    except CustomUser.DoesNotExist:
        messages.error(request, 'Aucun compte n\'est associé à cette adresse email.')
        return redirect('forgot_password')


def verify_reset_code_view(request):
    """
    Vue pour afficher le formulaire de vérification du code
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    # Vérifier si l'email est en session
    if 'reset_email' not in request.session:
        messages.error(request, 'Session expirée. Veuillez recommencer.')
        return redirect('forgot_password')
    
    return render(request, 'User/FrontOffice/Login/verify_reset_code.html', {
        'email': request.session.get('reset_email', '')
    })


@require_POST
def verify_reset_code_submit_view(request):
    """
    Vue pour vérifier le code de réinitialisation
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Session expirée. Veuillez recommencer.')
        return redirect('forgot_password')
    
    # Récupérer le code depuis les 6 champs ou le champ complet
    code = request.POST.get('code', '').strip()
    
    # Si le code n'est pas dans le champ complet, le construire depuis les 6 champs
    if not code or len(code) != 6:
        code = ''.join([
            request.POST.get('code1', '').strip(),
            request.POST.get('code2', '').strip(),
            request.POST.get('code3', '').strip(),
            request.POST.get('code4', '').strip(),
            request.POST.get('code5', '').strip(),
            request.POST.get('code6', '').strip(),
        ])
    
    if not code or len(code) != 6:
        messages.error(request, 'Veuillez entrer un code de 6 chiffres.')
        return redirect('verify_reset_code')
    
    try:
        user = CustomUser.objects.get(email=email)
        reset_code = PasswordResetCode.objects.filter(
            user=user,
            code=code,
            used=False
        ).order_by('-created_at').first()
        
        if reset_code and reset_code.is_valid():
            # Code valide - marquer comme utilisé et rediriger vers la réinitialisation
            reset_code.used = True
            reset_code.save()
            request.session['reset_code_verified'] = True
            request.session['reset_user_id'] = user.id
            return redirect('reset_password')
        else:
            messages.error(request, 'Code invalide ou expiré. Veuillez réessayer.')
            return redirect('verify_reset_code')
    except CustomUser.DoesNotExist:
        messages.error(request, 'Erreur: utilisateur introuvable.')
        return redirect('forgot_password')


def reset_password_view(request):
    """
    Vue pour afficher le formulaire de réinitialisation du mot de passe
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    # Vérifier si le code a été vérifié
    if not request.session.get('reset_code_verified') or not request.session.get('reset_user_id'):
        messages.error(request, 'Veuillez d\'abord vérifier votre code.')
        return redirect('forgot_password')
    
    return render(request, 'User/FrontOffice/Login/reset_password.html')


@require_POST
def reset_password_submit_view(request):
    """
    Vue pour réinitialiser le mot de passe
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    # Vérifier si le code a été vérifié
    if not request.session.get('reset_code_verified') or not request.session.get('reset_user_id'):
        messages.error(request, 'Session expirée. Veuillez recommencer.')
        return redirect('forgot_password')
    
    user_id = request.session.get('reset_user_id')
    password = request.POST.get('password', '').strip()
    password_confirm = request.POST.get('password_confirm', '').strip()
    
    if not password or len(password) < 8:
        messages.error(request, 'Le mot de passe doit contenir au moins 8 caractères.')
        return redirect('reset_password')
    
    if password != password_confirm:
        messages.error(request, 'Les mots de passe ne correspondent pas.')
        return redirect('reset_password')
    
    try:
        user = CustomUser.objects.get(id=user_id)
        user.set_password(password)
        user.save()
        
        # Nettoyer la session
        del request.session['reset_email']
        del request.session['reset_code_verified']
        del request.session['reset_user_id']
        
        messages.success(request, 'Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.')
        return redirect('login')
    except CustomUser.DoesNotExist:
        messages.error(request, 'Erreur: utilisateur introuvable.')
        return redirect('forgot_password')


@login_required
def logout_view(request):
    """
    Vue pour dÃ©connexion
    """
    logout(request)
    messages.info(request, 'Vous avez Ã©tÃ© dÃ©connectÃ©.')
    return redirect('login')


@login_required
def account_settings_view(request):
    """Account settings page (edit profile, password, etc.)."""
    return render(request, 'User/FrontOffice/profile.html', {
        'user_obj': request.user,
    })


@login_required
def profile_view(request):
    """Public-facing profile header page (hero style)."""
    from .models import Comment
    
    # Récupérer les posts de l'utilisateur
    posts = Post.objects.filter(author=request.user).order_by('-created_at')[:10]
    
    # Calculer les statistiques
    connections_count = Connection.objects.filter(
        Q(from_user=request.user, status='accepted') | Q(to_user=request.user, status='accepted')
    ).count()
    posts_count = Post.objects.filter(author=request.user).count()
    comments_count = Comment.objects.filter(author=request.user).count()
    
    return render(request, 'User/FrontOffice/profile_public.html', {
        'user_obj': request.user,
        'posts': posts,
        'connections_count': connections_count,
        'posts_count': posts_count,
        'comments_count': comments_count,
    })


def schedule_view(request):
    """Page pour voir tous les posts (style LinkedIn) - Accessible aux utilisateurs non connectés"""
    # Récupérer tous les posts de tous les utilisateurs, triés par date
    posts = Post.objects.select_related('author').prefetch_related('comments').order_by('-created_at')
    
    # Récupérer les connexions de l'utilisateur pour afficher le statut (seulement si connecté)
    user_connections = {}
    if request.user.is_authenticated:
        connections = Connection.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user),
            status='accepted'
        )
        for conn in connections:
            other_user = conn.to_user if conn.from_user == request.user else conn.from_user
            user_connections[other_user.id] = True
    
    return render(request, 'User/evently/schedule.html', {
        'posts': posts,
        'user_connections': user_connections,
    })


@login_required
def user_profile_view(request, user_id):
    """Voir le profil d'un autre utilisateur"""
    profile_user = get_object_or_404(CustomUser, id=user_id)
    
    # Ne pas permettre de voir son propre profil via cette vue
    if profile_user == request.user:
        return redirect('profile')
    
    # Récupérer les posts de l'utilisateur
    posts = Post.objects.filter(author=profile_user).order_by('-created_at')[:10]
    
    # Vérifier le statut de connexion
    connection_status = None
    connection = Connection.objects.filter(
        Q(from_user=request.user, to_user=profile_user) |
        Q(from_user=profile_user, to_user=request.user)
    ).first()
    
    if connection:
        connection_status = connection.status
    elif request.user == profile_user:
        connection_status = 'self'
    
    # Vérifier si connectés
    is_connected = connection and connection.status == 'accepted'
    
    # Déterminer qui a envoyé la demande (pour afficher le bon message)
    is_request_sender = connection and connection.from_user == request.user if connection else False
    
    # Calculer les statistiques
    from .models import Comment
    connections_count = Connection.objects.filter(
        Q(from_user=profile_user, status='accepted') | Q(to_user=profile_user, status='accepted')
    ).count()
    posts_count = Post.objects.filter(author=profile_user).count()
    comments_count = Comment.objects.filter(author=profile_user).count()
    
    return render(request, 'User/FrontOffice/user_profile.html', {
        'user_obj': request.user,
        'profile_user': profile_user,
        'posts': posts,
        'connection_status': connection_status,
        'is_connected': is_connected,
        'is_request_sender': is_request_sender,
        'connections_count': connections_count,
        'posts_count': posts_count,
        'comments_count': comments_count,
    })


@login_required
@require_POST
def send_connection_request(request, user_id):
    """Envoyer une demande de connexion"""
    from .models import Notification
    
    to_user = get_object_or_404(CustomUser, id=user_id)
    
    if to_user == request.user:
        messages.error(request, "Vous ne pouvez pas vous connecter à vous-même.")
        return redirect('user_profile', user_id=user_id)
    
    # Vérifier si une connexion existe déjà
    existing = Connection.objects.filter(
        Q(from_user=request.user, to_user=to_user) |
        Q(from_user=to_user, to_user=request.user)
    ).first()
    
    if existing:
        if existing.status == 'accepted':
            messages.info(request, f"Vous êtes déjà connecté avec {to_user.get_full_name() or to_user.username}.")
        elif existing.status == 'pending':
            messages.info(request, "Une demande de connexion est déjà en attente.")
        elif existing.status == 'rejected':
            # Permettre de réessayer en créant une nouvelle demande
            existing.status = 'pending'
            existing.save()
            # Créer une notification pour l'utilisateur qui reçoit la demande
            try:
                notification = Notification.objects.create(
                    user=to_user,
                    verb='connection_request',
                    data={
                        'connection_id': existing.id,
                        'from_user_id': request.user.id,
                        'from_user_name': request.user.get_full_name() or request.user.username,
                    }
                )
                print(f"DEBUG: Notification créée (réessai) - ID: {notification.id}, User: {to_user.id}, Verb: {notification.verb}")
                messages.success(request, f"Demande de connexion renvoyée à {to_user.get_full_name() or to_user.username}.")
            except Exception as e:
                print(f"DEBUG: Erreur lors de la création de la notification (réessai): {e}")
                messages.error(request, f"Erreur lors de l'envoi de la demande: {e}")
        elif existing.status == 'blocked':
            messages.error(request, "Cette connexion est bloquée.")
    else:
        connection = Connection.objects.create(
            from_user=request.user,
            to_user=to_user,
            status='pending'
        )
        # Créer une notification pour l'utilisateur qui reçoit la demande
        try:
            notification = Notification.objects.create(
                user=to_user,
                verb='connection_request',
                data={
                    'connection_id': connection.id,
                    'from_user_id': request.user.id,
                    'from_user_name': request.user.get_full_name() or request.user.username,
                }
            )
            print(f"DEBUG: Notification créée - ID: {notification.id}, User: {to_user.id}, Verb: {notification.verb}")
            messages.success(request, f"Demande de connexion envoyée à {to_user.get_full_name() or to_user.username}.")
        except Exception as e:
            print(f"DEBUG: Erreur lors de la création de la notification: {e}")
            messages.error(request, f"Erreur lors de l'envoi de la demande: {e}")
    
    return redirect('user_profile', user_id=user_id)


@login_required
@require_POST
def accept_connection_request(request, connection_id):
    """Accepter une demande de connexion"""
    from .models import Notification
    
    connection = get_object_or_404(Connection, id=connection_id, to_user=request.user)
    
    if connection.status == 'pending':
        connection.status = 'accepted'
        connection.save()
        # Marquer la notification comme lue
        Notification.objects.filter(
            user=request.user,
            verb='connection_request',
            data__connection_id=connection_id
        ).update(read=True)
        # Créer une notification pour l'utilisateur qui a envoyé la demande
        Notification.objects.create(
            user=connection.from_user,
            verb='connection_accepted',
            data={
                'connection_id': connection.id,
                'from_user_id': request.user.id,
                'from_user_name': request.user.get_full_name() or request.user.username,
            }
        )
        messages.success(request, f"Vous êtes maintenant connecté avec {connection.from_user.get_full_name() or connection.from_user.username}.")
    else:
        messages.error(request, "Cette demande de connexion n'est plus valide.")
    
    return redirect(request.META.get('HTTP_REFERER', 'notifications'))


@login_required
@require_POST
def reject_connection_request(request, connection_id):
    """Refuser une demande de connexion"""
    from .models import Notification
    
    connection = get_object_or_404(Connection, id=connection_id, to_user=request.user)
    
    if connection.status == 'pending':
        connection.status = 'rejected'
        connection.save()
        # Marquer la notification comme lue
        Notification.objects.filter(
            user=request.user,
            verb='connection_request',
            data__connection_id=connection_id
        ).update(read=True)
        messages.info(request, "Demande de connexion refusée.")
    else:
        messages.error(request, "Cette demande de connexion n'est plus valide.")
    
    return redirect('notifications')


@login_required
def notifications_view(request):
    """Voir toutes les notifications"""
    from .models import Notification
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Marquer toutes les notifications non lues comme lues quand on visite la page
    unread_notifications = notifications.filter(read=False)
    if unread_notifications.exists():
        unread_notifications.update(read=True)
    
    return render(request, 'User/FrontOffice/notifications.html', {
        'notifications': notifications,
    })


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Marquer une notification comme lue"""
    from .models import Notification
    
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.read = True
    notification.save()
    
    return redirect('notifications')


@login_required
def messages_view(request, user_id=None):
    """Page de messagerie"""
    if user_id:
        # Conversation avec un utilisateur spécifique
        other_user = get_object_or_404(CustomUser, id=user_id)
        if other_user == request.user:
            return redirect('messages')
        
        # Vérifier le statut de la connexion
        connection = Connection.objects.filter(
            Q(from_user=request.user, to_user=other_user) |
            Q(from_user=other_user, to_user=request.user)
        ).first()
        
        # Vérifier si les utilisateurs sont connectés (status = 'accepted')
        is_connected = connection and connection.status == 'accepted'
        connection_status = connection.status if connection else None
        
        # Si pas connecté, rediriger vers le profil
        if not is_connected:
            if connection and connection.status == 'rejected':
                messages.error(request, "Votre demande de connexion a été refusée. Vous pouvez réessayer d'envoyer une demande depuis le profil.")
            elif connection and connection.status == 'pending':
                messages.info(request, "Votre demande de connexion est en attente. Vous devez attendre que la personne accepte avant de pouvoir voir la conversation.")
            else:
                messages.info(request, "Vous devez être connecté avec cette personne pour voir la conversation. Envoyez d'abord une demande de connexion.")
            return redirect('user_profile', user_id=user_id)
        
        # Récupérer les messages personnels entre les deux utilisateurs (non supprimés, sans logement)
        messages_list = Message.objects.filter(
            Q(sender=request.user, receiver=other_user) |
            Q(sender=other_user, receiver=request.user),
            deleted=False,
            logement__isnull=True  # Seulement les messages personnels
        ).order_by('sent_at')
        
        # Marquer les messages comme lus
        Message.objects.filter(
            sender=other_user, 
            receiver=request.user, 
            read=False
        ).update(read=True)
        
        return render(request, 'User/FrontOffice/messages.html', {
            'other_user': other_user,
            'messages_list': messages_list,
            'is_connected': is_connected,
        })
    else:
        # Liste des conversations
        # Récupérer tous les utilisateurs avec qui on a échangé des messages personnels (non supprimés, sans logement)
        sent_messages = Message.objects.filter(sender=request.user, deleted=False, logement__isnull=True).values_list('receiver', flat=True).distinct()
        received_messages = Message.objects.filter(receiver=request.user, deleted=False, logement__isnull=True).values_list('sender', flat=True).distinct()
        user_ids = set(list(sent_messages) + list(received_messages))
        
        conversations = []
        for uid in user_ids:
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
        
        conversations.sort(key=lambda x: x['last_message'].sent_at if x['last_message'] else timezone.now(), reverse=True)
        
        return render(request, 'User/FrontOffice/messages_list.html', {
            'conversations': conversations,
        })


@login_required
@require_POST
def send_message_view(request, user_id):
    """Envoyer un message - seulement si connecté"""
    receiver = get_object_or_404(CustomUser, id=user_id)
    
    if receiver == request.user:
        messages.error(request, "Vous ne pouvez pas vous envoyer un message à vous-même.")
        return redirect('messages')
    
    # Vérifier le statut de la connexion
    connection = Connection.objects.filter(
        Q(from_user=request.user, to_user=receiver) |
        Q(from_user=receiver, to_user=request.user)
    ).first()
    
    # Vérifier si les utilisateurs sont connectés (status = 'accepted')
    is_connected = connection and connection.status == 'accepted'
    
    # Si pas connecté ou connexion refusée, bloquer l'envoi
    if not is_connected:
        if connection and connection.status == 'rejected':
            messages.error(request, f"Votre demande de connexion a été refusée. Vous ne pouvez pas envoyer de message. Vous pouvez réessayer d'envoyer une demande de connexion depuis le profil.")
        elif connection and connection.status == 'pending':
            messages.error(request, "Votre demande de connexion est en attente. Vous devez attendre que la personne accepte avant de pouvoir envoyer des messages.")
        else:
            messages.error(request, "Vous devez être connecté avec cette personne pour lui envoyer un message. Envoyez d'abord une demande de connexion depuis son profil.")
        return redirect('user_profile', user_id=user_id)
    
    text = request.POST.get('text', '').strip()
    file = request.FILES.get('file', None)
    
    if not text and not file:
        messages.error(request, "Le message ne peut pas être vide.")
        return redirect('messages_conversation', user_id=user_id)
    
    message = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        text=text if text else None
    )
    
    if file:
        message.file = file
        message.save()
    
    messages.success(request, "Message envoyé.")
    return redirect('messages_conversation', user_id=user_id)


@login_required
@require_POST
def update_message_view(request, message_id):
    """Modifier un message"""
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    
    text = request.POST.get('text', '').strip()
    file = request.FILES.get('file', None)
    
    # Vérifier qu'il y a au moins du texte ou un fichier
    if not text and not file:
        # Si le message actuel n'a ni texte ni fichier, erreur
        if not message.text and not message.file:
            messages.error(request, "Le message ne peut pas être vide.")
            return redirect('messages_conversation', user_id=message.receiver.id)
        # Sinon, on garde l'ancien contenu
    
    try:
        if text:
            message.text = text
        elif not message.text:
            message.text = None
        
        if file:
            if message.file:
                message.file.delete()
            message.file = file
        
        message.save()
        messages.success(request, "Message modifié avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la modification du message: {e}")
    
    return redirect('messages_conversation', user_id=message.receiver.id)


@login_required
@require_POST
def delete_message_view(request, message_id):
    """Supprimer un message"""
    message = get_object_or_404(Message, id=message_id)
    
    # Seul l'expéditeur peut supprimer le message
    if message.sender != request.user:
        messages.error(request, "Vous n'avez pas la permission de supprimer ce message.")
        return redirect('messages_conversation', user_id=message.receiver.id if message.sender == request.user else message.sender.id)
    
    try:
        # Marquer comme supprimé au lieu de supprimer définitivement
        message.deleted = True
        message.save()
        messages.success(request, "Message supprimé avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression du message: {e}")
    
    return redirect('messages_conversation', user_id=message.receiver.id)


@login_required
@require_POST
def create_post_view(request):
    """Créer un nouveau post"""
    content = request.POST.get('content', '').strip()
    if not content:
        messages.error(request, 'Le contenu du post ne peut pas être vide.')
        return redirect('profile')
    
    try:
        post = Post.objects.create(
            author=request.user,
            content=content
        )
        # Gérer le fichier média si présent
        if 'media' in request.FILES:
            post.media = request.FILES['media']
            post.save()
        messages.success(request, 'Post créé avec succès.')
    except Exception as e:
        messages.error(request, f"Erreur lors de la création du post: {e}")
    return redirect('profile')


@login_required
@require_POST
def update_post_view(request, post_id):
    """Modifier un post existant"""
    try:
        post = Post.objects.get(id=post_id, author=request.user)
    except Post.DoesNotExist:
        messages.error(request, 'Post introuvable ou vous n\'avez pas la permission de le modifier.')
        return redirect('profile')
    
    content = request.POST.get('content', '').strip()
    if not content:
        messages.error(request, 'Le contenu du post ne peut pas être vide.')
        return redirect('profile')
    
    try:
        post.content = content
        # Gérer le fichier média si présent
        if 'media' in request.FILES:
            # Supprimer l'ancien média si existant
            if post.media:
                post.media.delete()
            post.media = request.FILES['media']
        post.save()
        messages.success(request, 'Post modifié avec succès.')
    except Exception as e:
        messages.error(request, f"Erreur lors de la modification du post: {e}")
    return redirect('profile')


@login_required
@require_POST
def delete_post_view(request, post_id):
    """Supprimer un post"""
    try:
        post = Post.objects.get(id=post_id, author=request.user)
        post.delete()
        messages.success(request, 'Post supprimé avec succès.')
    except Post.DoesNotExist:
        messages.error(request, 'Post introuvable ou vous n\'avez pas la permission de le supprimer.')
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression du post: {e}")
    return redirect('profile')


@login_required
@require_POST
def profile_update_view(request):
    """
    Met à jour les informations de base du profil (prénom, nom, téléphone).
    """
    user = request.user
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    address = request.POST.get('address', '').strip()
    city = request.POST.get('city', '').strip()
    country = request.POST.get('country', '').strip()

    # Appliquer les mises à jour
    user.first_name = first_name
    user.last_name = last_name
    if hasattr(user, 'phone'):
        setattr(user, 'phone', phone)
    if hasattr(user, 'address'):
        setattr(user, 'address', address)
    if hasattr(user, 'city'):
        setattr(user, 'city', city)
    if hasattr(user, 'country'):
        setattr(user, 'country', country)
    # Avatar upload
    if 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
    try:
        user.save()
        messages.success(request, 'Profil mis à jour avec succès.')
    except Exception as e:
        messages.error(request, f"Erreur lors de la mise à jour du profil: {e}")
    return redirect('profile')


@login_required
@require_POST
def profile_update_public_view(request):
    """
    Met à jour les informations publiques du profil (headline, bio, location, skills, education, experience).
    """
    import json
    user = request.user
    
    # Champs texte simples
    if 'headline' in request.POST:
        user.headline = request.POST.get('headline', '').strip() or None
    if 'bio' in request.POST:
        user.bio = request.POST.get('bio', '').strip() or None
    if 'location' in request.POST:
        user.location = request.POST.get('location', '').strip() or None
    
    # Champs JSON
    if 'skills' in request.POST:
        try:
            skills_data = request.POST.get('skills', '[]')
            user.skills = json.loads(skills_data) if skills_data else []
        except json.JSONDecodeError:
            messages.error(request, 'Format JSON invalide pour les compétences.')
            return redirect('profile')
    
    if 'education' in request.POST:
        try:
            education_data = request.POST.get('education', '[]')
            new_education = json.loads(education_data) if education_data else []
            # Si c'est un ajout (champs edu_* présents), ajouter à la liste existante
            if 'edu_degree' in request.POST:
                edu_item = {
                    'degree': request.POST.get('edu_degree', '').strip(),
                    'school': request.POST.get('edu_school', '').strip(),
                    'start_year': request.POST.get('edu_start', '').strip() or None,
                    'end_year': request.POST.get('edu_end', '').strip() or None,
                    'field': request.POST.get('edu_field', '').strip() or None
                }
                # Filtrer les valeurs vides
                edu_item = {k: v for k, v in edu_item.items() if v}
                existing_edu = user.education if user.education else []
                user.education = existing_edu + [edu_item]
            else:
                user.education = new_education
        except json.JSONDecodeError:
            messages.error(request, 'Format JSON invalide pour la formation.')
            return redirect('profile')
    
    if 'experience' in request.POST:
        try:
            experience_data = request.POST.get('experience', '[]')
            new_experience = json.loads(experience_data) if experience_data else []
            # Si c'est un ajout (champs exp_* présents), ajouter à la liste existante
            if 'exp_position' in request.POST:
                exp_item = {
                    'position': request.POST.get('exp_position', '').strip(),
                    'company': request.POST.get('exp_company', '').strip(),
                    'start_date': request.POST.get('exp_start', '').strip() or None,
                    'end_date': request.POST.get('exp_end', '').strip() or None,
                    'current': not request.POST.get('exp_end', '').strip(),
                    'description': request.POST.get('exp_description', '').strip() or None
                }
                # Filtrer les valeurs vides
                exp_item = {k: v for k, v in exp_item.items() if v}
                existing_exp = user.experience if user.experience else []
                user.experience = existing_exp + [exp_item]
            else:
                user.experience = new_experience
        except json.JSONDecodeError:
            messages.error(request, 'Format JSON invalide pour l\'expérience.')
            return redirect('profile')
    
    # Uploads de fichiers
    if 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
        messages.success(request, 'Avatar mis à jour avec succès.')
    if 'cover_photo' in request.FILES:
        user.cover_photo = request.FILES['cover_photo']
        messages.success(request, 'Photo de couverture mise à jour avec succès.')
    
    # Sauvegarder l'utilisateur
    try:
        user.save()
        # Si aucun message de succès n'a été ajouté (pas d'upload de fichier), ajouter un message générique
        if 'avatar' not in request.FILES and 'cover_photo' not in request.FILES:
            messages.success(request, 'Profil mis à jour avec succès.')
    except Exception as e:
        messages.error(request, f"Erreur lors de la mise à jour du profil: {e}")
    return redirect('profile')


@login_required
@require_POST
def profile_change_password_view(request):
    """
    Change le mot de passe de l'utilisateur après vérification de l'ancien.
    """
    user = request.user
    current_password = request.POST.get('current_password', '')
    new_password1 = request.POST.get('new_password1', '')
    new_password2 = request.POST.get('new_password2', '')

    if not user.check_password(current_password):
        messages.error(request, 'Ancien mot de passe incorrect.')
        return redirect('profile')

    if not new_password1 or new_password1 != new_password2:
        messages.error(request, 'Les nouveaux mots de passe ne correspondent pas.')
        return redirect('profile')

    try:
        user.set_password(new_password1)
        user.save()
        # Reconnecter l'utilisateur après le changement de mot de passe
        login(request, user)
        messages.success(request, 'Mot de passe changé avec succès.')
    except Exception as e:
        messages.error(request, f"Impossible de changer le mot de passe: {e}")
    return redirect('profile')

# --- Evently pages (squelettes) ---
def evently_index(request):
    """Page d'accueil"""
    return render(request, 'User/evently/index.html')

def evently_template(request, page: str):
    allowed = {
        'about', 'schedule', 'speakers', 'speaker-details',
        'venue', 'tickets', 'buy-tickets', 'gallery',
        'terms', 'privacy', 'contact', 'sponsors', 'starter-page'
    }
    if page in allowed:
        return render(request, f'User/evently/{page}.html')
    return render(request, 'User/evently/404.html', status=404)

@user_passes_test(lambda u: u.is_superuser)
def manage_users_view(request):
    """
    Gestion des utilisateurs (superuser uniquement): lister et changer les rÃ´les.
    """
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'manage_users.html', {
        'users': users,
    })

@user_passes_test(lambda u: u.is_superuser)
@require_POST
def set_user_role_view(request, user_id: int):
    """
    Met Ã  jour les rÃ´les d'un utilisateur (staff/superuser). Superuser only.
    """
    target = get_object_or_404(CustomUser, pk=user_id)
    action = request.POST.get('action')
    # Optional direct role update for non-superusers (new attribute)
    new_role = request.POST.get('role')

    if target.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas modifier votre propre rÃ´le.")
        return redirect(request.META.get('HTTP_REFERER', 'manage_users'))

    changed = False
    # If 'role' parameter is provided, set the user's role attribute
    try:
        valid_roles = {c[0] for c in CustomUser._meta.get_field('role').choices}
    except Exception:
        valid_roles = {'UTILISATEUR', 'ADMIN'}
    if new_role in valid_roles:
        if target.pk == request.user.pk:
            messages.error(request, "Vous ne pouvez pas modifier votre propre rôle.")
            return redirect(request.META.get('HTTP_REFERER', 'manage_users'))
        target.role = new_role
        target.save()
        messages.success(request, f"Rôle mis à jour pour {target.username}.")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect(request.META.get('HTTP_REFERER', 'manage_users'))
    if action == 'make_staff':
        if not target.is_staff:
            target.is_staff = True
            changed = True
    elif action == 'remove_staff':
        if target.is_staff:
            target.is_staff = False
            changed = True
    elif action == 'make_superuser':
        if not target.is_superuser:
            target.is_superuser = True
            target.is_staff = True
            changed = True
    elif action == 'remove_superuser':
        if target.is_superuser:
            target.is_superuser = False
            changed = True
    else:
        messages.error(request, 'Action invalide.')
        return redirect(request.META.get('HTTP_REFERER', 'manage_users'))

    if changed:
        target.save()
        messages.success(request, f"RÃ´le mis Ã  jour pour {target.username}.")
    else:
        messages.info(request, "Aucun changement nÃ©cessaire.")
    return redirect(request.META.get('HTTP_REFERER', 'manage_users'))

@csrf_exempt
@require_http_methods(["POST"])
def face_id_register(request):
    """
    API pour enregistrer les credentials Face ID
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Non authentifiÃ©'}, status=401)
    
    try:
        data = json.loads(request.body)
        credential_id = data.get('credentialId')
        public_key = data.get('publicKey')
        
        if credential_id and public_key:
            user = request.user
            user.face_id_enabled = True
            user.face_id_credential_id = credential_id
            user.face_id_public_key = public_key
            user.save()
            
            return JsonResponse({'success': True, 'message': 'Face ID enregistrÃ© avec succÃ¨s'})
        else:
            return JsonResponse({'error': 'DonnÃ©es manquantes'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def face_id_authenticate(request):
    """
    API pour authentifier avec Face ID
    """
    try:
        data = json.loads(request.body)
        credential_id = data.get('credentialId')
        username = data.get('username')
        
        try:
            # Trouver l'utilisateur par username ou email
            try:
                user = CustomUser.objects.get(email=username)
            except CustomUser.DoesNotExist:
                user = CustomUser.objects.get(username=username)
            
            # Si credential_id n'est pas fourni, retourner le credential_id de l'utilisateur
            if not credential_id:
                if user.face_id_enabled and user.face_id_credential_id:
                    return JsonResponse({
                        'credentialId': user.face_id_credential_id,
                        'challenge': 'challenge_string'  # En production, gÃ©nÃ©rer un vrai challenge
                    })
                else:
                    return JsonResponse({'error': 'Face ID non enregistrÃ© pour cet utilisateur'}, status=404)
            
            # VÃ©rifier si Face ID est activÃ© et correspond
            if user.face_id_enabled and user.face_id_credential_id == credential_id:
                # Authentifier l'utilisateur
                login(request, user)
                return JsonResponse({
                    'success': True, 
                    'message': 'Authentification Face ID rÃ©ussie',
                    'redirect': '/'
                })
            else:
                return JsonResponse({'error': 'Face ID non enregistrÃ© ou invalide'}, status=401)
        except CustomUser.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur non trouvÃ©'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Décorateur pour vérifier si l'utilisateur est superuser ou admin
def is_superuser_or_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'ADMIN'))

@user_passes_test(is_superuser_or_admin, login_url='/login/')
@require_POST
def ban_user_view(request, user_id: int):
    target = get_object_or_404(CustomUser, pk=user_id)
    # Les admins ne peuvent pas bannir les superusers
    if not request.user.is_superuser and target.is_superuser:
        messages.error(request, "Vous n'avez pas la permission de bannir un superuser.")
        return redirect(request.META.get('HTTP_REFERER', 'manage_users'))
    reason = request.POST.get('reason', '').strip()
    target.is_active = False
    target.ban_reason = reason or 'Banni par un administrateur.'
    from django.utils import timezone
    target.banned_at = timezone.now()
    target.save()
    messages.warning(request, f"{target.username} a été banni.")
    return redirect(request.META.get('HTTP_REFERER', 'manage_users'))


@user_passes_test(is_superuser_or_admin, login_url='/login/')
@require_POST
def unban_user_view(request, user_id: int):
    target = get_object_or_404(CustomUser, pk=user_id)
    # Les admins ne peuvent pas débannir les superusers
    if not request.user.is_superuser and target.is_superuser:
        messages.error(request, "Vous n'avez pas la permission de débannir un superuser.")
        return redirect(request.META.get('HTTP_REFERER', 'manage_users'))
    target.is_active = True
    target.ban_reason = ''
    target.banned_at = None
    target.save()
    messages.success(request, f"{target.username} a été débanni.")
    return redirect(request.META.get('HTTP_REFERER', 'manage_users'))


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_user_view(request, user_id: int):
    target = get_object_or_404(CustomUser, pk=user_id)
    if target.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect(request.META.get('HTTP_REFERER', 'manage_users'))
    username = target.username
    target.delete()
    messages.success(request, f"L'utilisateur {username} a été supprimé.")
    return redirect(request.META.get('HTTP_REFERER', 'manage_users'))
