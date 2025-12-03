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
from django.conf import settings
from django.core.files.storage import default_storage
import json
import base64
import json as json_lib
import requests
import re

from .forms import SignUpForm, LoginForm
from .models import CustomUser, Post, Comment, Like, Connection, Message, PasswordResetCode
from django.core.mail import send_mail
from datetime import timedelta
import re

# Fonction pour envoyer un SMS avec le code de vérification
def send_sms_code(phone_number, code, user):
    """
    Envoie un SMS avec le code de vérification via Twilio
    """
    twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    twilio_phone_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
    
    if not all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
        # Si Twilio n'est pas configuré, on peut utiliser un service alternatif ou simuler
        # Pour le développement, on peut juste logger le code
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'SMS Code for {phone_number}: {code}')
        # En production, vous devriez configurer Twilio ou un autre service SMS
        raise Exception('Service SMS non configuré. Veuillez configurer Twilio dans settings.py')
    
    try:
        from twilio.rest import Client
        
        # Debug: Logger les informations (à retirer en production)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'Envoi SMS - Numéro destination: {phone_number}, Numéro Twilio: {twilio_phone_number}')
        
        # Nettoyer le numéro de téléphone
        original_phone = phone_number
        phone_number = re.sub(r'[^\d+]', '', phone_number)
        
        # Normaliser le numéro Twilio pour comparaison
        twilio_normalized = re.sub(r'[^\d+]', '', twilio_phone_number)
        
        # Si le numéro ne commence pas par +, essayer de détecter le pays
        if not phone_number.startswith('+'):
            # Si le numéro commence par 0, on le retire
            if phone_number.startswith('0'):
                phone_number = phone_number[1:]
            
            # Détecter le préfixe basé sur le numéro Twilio (exemple: +216 pour la Tunisie)
            # Extraire le code pays du numéro Twilio
            if twilio_normalized.startswith('+'):
                # Extraire le code pays (ex: +216 -> 216, +33 -> 33)
                country_code = ''
                i = 1
                while i < len(twilio_normalized) and twilio_normalized[i].isdigit():
                    country_code += twilio_normalized[i]
                    i += 1
                    # Les codes pays font généralement 1-3 chiffres
                    if len(country_code) >= 3:
                        break
                
                if country_code:
                    phone_number = '+' + country_code + phone_number
                else:
                    phone_number = '+33' + phone_number  # Par défaut
            else:
                phone_number = '+33' + phone_number  # Par défaut
        
        # Normaliser pour comparaison
        phone_normalized = re.sub(r'[^\d+]', '', phone_number)
        
        # Vérifier que le numéro de destination n'est pas le même que le numéro Twilio
        if phone_normalized == twilio_normalized:
            raise Exception('Le numéro de téléphone ne peut pas être le même que le numéro Twilio. Veuillez utiliser un autre numéro.')
        
        client = Client(twilio_account_sid, twilio_auth_token)
        
        message_body = f'''Bonjour {user.get_full_name() or user.username},

Votre code de vérification EduLife est : {code}

Ce code est valide pendant 15 minutes.

Si vous n'avez pas demandé cette réinitialisation, ignorez ce message.'''
        
        try:
            message = client.messages.create(
                body=message_body,
                from_=twilio_phone_number,
                to=phone_number
            )
            logger.info(f'SMS envoyé avec succès. SID: {message.sid}, To: {phone_number}, From: {twilio_phone_number}')
            return message.sid
        except Exception as twilio_error:
            # Logger l'erreur complète pour le débogage
            error_str = str(twilio_error)
            logger.error(f'Erreur Twilio lors de l\'envoi: {error_str}')
            logger.error(f'Détails - To: {phone_number}, From: {twilio_phone_number}')
            # Relancer l'erreur pour qu'elle soit traitée par le bloc except externe
            raise twilio_error
    except ImportError:
        raise Exception('Twilio n\'est pas installé. Installez-le avec: pip install twilio')
    except Exception as e:
        # Masquer les détails techniques de l'erreur pour l'utilisateur
        error_msg = str(e)
        
        # Vérifier si c'est notre exception personnalisée
        if 'ne peut pas être le même' in error_msg or 'récupération par email' in error_msg:
            raise
        
        # Gérer les erreurs spécifiques de Twilio
        if 'To' in error_msg and 'From' in error_msg and 'cannot be the same' in error_msg:
            raise Exception('Le numéro de téléphone enregistré est le même que le numéro du service. Veuillez utiliser la récupération par email.')
        
        if 'HTTP Error' in error_msg or 'Twilio returned' in error_msg:
            # Extraire le message d'erreur principal de Twilio
            if 'Unable to create record:' in error_msg:
                error_start = error_msg.find('Unable to create record:')
                error_end = error_msg.find('More information', error_start)
                if error_end > error_start:
                    clean_error = error_msg[error_start:error_end].replace('Unable to create record:', '').strip()
                    # Masquer les numéros de téléphone dans l'erreur
                    clean_error = re.sub(r'\+?\d{8,}', 'XXXX', clean_error)
                    raise Exception(f'Erreur Twilio: {clean_error}. Veuillez utiliser la récupération par email.')
            
            # Autres erreurs HTTP communes
            if '21266' in error_msg:  # Numéro identique
                raise Exception('Le numéro de téléphone ne peut pas être le même que le numéro du service. Veuillez utiliser la récupération par email.')
            if '21211' in error_msg:  # Numéro invalide
                raise Exception('Le numéro de téléphone est invalide. Veuillez vérifier le format (ex: +21612345678).')
            if '21608' in error_msg:  # Numéro non vérifié (trial account)
                raise Exception('Le numéro de téléphone n\'est pas vérifié. Pour les comptes Twilio d\'essai, vous devez vérifier le numéro de destination dans votre console Twilio.')
            if '20003' in error_msg:  # Authentification échouée
                raise Exception('Erreur d\'authentification Twilio. Veuillez contacter l\'administrateur.')
            if '20001' in error_msg:  # Compte suspendu
                raise Exception('Le service SMS est temporairement indisponible. Veuillez utiliser la récupération par email.')
        
        # Logger l'erreur complète pour le débogage (en développement)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Erreur SMS non gérée: {error_msg}')
        
        # Message générique pour l'utilisateur
        raise Exception('Erreur lors de l\'envoi du SMS. Veuillez utiliser la récupération par email ou contacter l\'administrateur.')

# Fonction pour valider le reCAPTCHA (obligatoire, même en développement)
def verify_recaptcha(recaptcha_response):
    """
    Vérifie la réponse du reCAPTCHA avec l'API Google.
    Retourne toujours False si :
      - la clé secrète n'est pas configurée
      - la réponse est vide
      - l'appel à l'API échoue
    """
    recaptcha_secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', None)
    recaptcha_verify_url = getattr(
        settings,
        'RECAPTCHA_VERIFY_URL',
        'https://www.google.com/recaptcha/api/siteverify'
    )

    # Si la clé n'est pas configurée ou pas de réponse, on refuse systématiquement
    if not recaptcha_secret or not recaptcha_response:
        return False

    data = {
        'secret': recaptcha_secret,
        'response': recaptcha_response
    }

    try:
        response = requests.post(recaptcha_verify_url, data=data, timeout=5)
        result = response.json()
        return result.get('success', False)
    except Exception:
        # En cas d'erreur réseau ou autre, on refuse aussi
        return False

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
    
    # Passer le Google Client ID et reCAPTCHA Site Key au template
    context = {
        'login_form': login_form,
        'signup_form': signup_form,
        'GOOGLE_OAUTH2_CLIENT_ID': getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID', ''),
        'RECAPTCHA_SITE_KEY': getattr(settings, 'RECAPTCHA_SITE_KEY', ''),
    }
    
    # VÃ©rifier dans la session si on vient d'une inscription rÃ©ussie
    show_login = request.session.get('show_login_after_signup', False)
    # Supprimer le flag de session aprÃ¨s utilisation
    if show_login:
        del request.session['show_login_after_signup']
        request.session.modified = True
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'login':
            # Vérifier le reCAPTCHA d'abord
            recaptcha_response = request.POST.get('g-recaptcha-response')
            if not verify_recaptcha(recaptcha_response):
                messages.error(request, 'Veuillez compléter la vérification reCAPTCHA.')
                login_form = LoginForm(request, data=request.POST)
                context['login_form'] = login_form
                context['show_login'] = show_login
                return render(request, 'User/FrontOffice/Login/login.html', context)
            
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
                            context['login_form'] = login_form
                            context['show_login'] = show_login
                            return render(request, 'User/FrontOffice/Login/login.html', context)
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
                    else:
                        # Si l'utilisateur n'est pas actif, afficher le formulaire avec erreur
                        login_form = LoginForm(request, data=request.POST)
                        login_form.add_error(None, 'Votre compte est désactivé. Contactez l\'administrateur.')
                        messages.error(request, 'Votre compte est désactivé. Contactez l\'administrateur.')
                        context['login_form'] = login_form
                        context['show_login'] = show_login
                        return render(request, 'User/FrontOffice/Login/login.html', context)
                else:
                    # Authentification échouée - identifiants incorrects
                    login_form = LoginForm(request, data=request.POST)
                    login_form.add_error(None, 'Nom d\'utilisateur ou mot de passe incorrect.')
                    messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect. Veuillez réessayer.')
                    context['login_form'] = login_form
                    context['show_login'] = show_login
                    return render(request, 'User/FrontOffice/Login/login.html', context)
            else:
                # Le formulaire n'est pas valide, les erreurs seront affichées automatiquement
                context['login_form'] = login_form
                context['show_login'] = show_login
                return render(request, 'User/FrontOffice/Login/login.html', context)
        
        elif form_type == 'signup':
            # Vérifier le reCAPTCHA d'abord
            recaptcha_response = request.POST.get('g-recaptcha-response')
            if not verify_recaptcha(recaptcha_response):
                messages.error(request, 'Veuillez compléter la vérification reCAPTCHA.')
                signup_form = SignUpForm(request.POST)
                context['signup_form'] = signup_form
                context['show_login'] = show_login
                return render(request, 'User/FrontOffice/Login/login.html', context)
            
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
    
    context['show_login'] = show_login
    return render(request, 'User/FrontOffice/Login/login.html', context)


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
    Vérifie si l'email ou le téléphone existe et envoie un code de vérification
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    recovery_method = request.POST.get('recovery_method', 'email').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    
    # Validation selon la méthode choisie
    if recovery_method == 'sms':
        if not phone:
            messages.error(request, 'Veuillez entrer votre numéro de téléphone.')
            return redirect('forgot_password')
        
        # Vérifier si le téléphone existe
        try:
            # Utiliser .first() pour éviter MultipleObjectsReturned en attendant la migration
            # Après la migration, on pourra utiliser .get() car le champ sera unique
            user = CustomUser.objects.filter(phone=phone).first()
            if not user:
                raise CustomUser.DoesNotExist
            
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
            
            # Envoyer le SMS avec le code
            try:
                send_sms_code(phone, code, user)
                messages.success(request, f'Un code de vérification a été envoyé par SMS au {phone}.')
                # Rediriger vers la page de vérification du code
                request.session['reset_phone'] = phone
                request.session['reset_method'] = 'sms'
                return redirect('verify_reset_code')
            except Exception as e:
                error_message = str(e)
                # Ne pas dupliquer le message d'erreur
                if 'Erreur lors de l\'envoi du SMS' not in error_message:
                    messages.error(request, f'Erreur lors de l\'envoi du SMS: {error_message}')
                else:
                    messages.error(request, error_message)
                return redirect('forgot_password')
                
        except CustomUser.DoesNotExist:
            messages.error(request, 'Aucun compte n\'est associé à ce numéro de téléphone.')
            return redirect('forgot_password')
    
    else:  # Méthode email (par défaut)
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
                request.session['reset_method'] = 'email'
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
    
    # Vérifier si l'email ou le téléphone est en session
    reset_method = request.session.get('reset_method', 'email')
    reset_email = request.session.get('reset_email', '')
    reset_phone = request.session.get('reset_phone', '')
    
    if not reset_email and not reset_phone:
        messages.error(request, 'Session expirée. Veuillez recommencer.')
        return redirect('forgot_password')
    
    return render(request, 'User/FrontOffice/Login/verify_reset_code.html', {
        'email': reset_email,
        'phone': reset_phone,
        'method': reset_method
    })


@require_POST
def verify_reset_code_submit_view(request):
    """
    Vue pour vérifier le code de réinitialisation
    """
    if request.user.is_authenticated:
        return redirect('index')
    
    reset_method = request.session.get('reset_method', 'email')
    email = request.session.get('reset_email')
    phone = request.session.get('reset_phone')
    
    if not email and not phone:
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
        # Récupérer l'utilisateur selon la méthode utilisée
        if reset_method == 'sms' and phone:
            # Utiliser .first() pour éviter MultipleObjectsReturned en attendant la migration
            user = CustomUser.objects.filter(phone=phone).first()
            if not user:
                raise CustomUser.DoesNotExist
        elif email:
            user = CustomUser.objects.get(email=email)
        else:
            messages.error(request, 'Session invalide. Veuillez recommencer.')
            return redirect('forgot_password')
        
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
        
        # Nettoyer la session (supprimer seulement les clés qui existent)
        request.session.pop('reset_email', None)
        request.session.pop('reset_phone', None)
        request.session.pop('reset_method', None)
        request.session.pop('reset_code_verified', None)
        request.session.pop('reset_user_id', None)
        
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
    # Vérifier si la table Like existe avant de prefetch
    from django.db import connection
    try:
        posts = Post.objects.select_related('author').prefetch_related('comments', 'likes').order_by('-created_at')
    except Exception:
        # Si la table Like n'existe pas encore, ne pas prefetch les likes
        posts = Post.objects.select_related('author').prefetch_related('comments').order_by('-created_at')
    
    # Récupérer les connexions de l'utilisateur pour afficher le statut (seulement si connecté)
    user_connections = {}
    # Récupérer les likes de l'utilisateur pour chaque post
    user_likes = {}
    if request.user.is_authenticated:
        connections = Connection.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user),
            status='accepted'
        )
        for conn in connections:
            other_user = conn.to_user if conn.from_user == request.user else conn.from_user
            user_connections[other_user.id] = True
        
        # Récupérer tous les likes de l'utilisateur pour les posts affichés
        # Vérifier si la table Like existe
        try:
            post_ids = [post.id for post in posts]
            likes = Like.objects.filter(post_id__in=post_ids, user=request.user)
            user_likes = {like.post_id: True for like in likes}
        except Exception:
            # Table Like n'existe pas encore
            user_likes = {}
    
    return render(request, 'User/evently/schedule.html', {
        'posts': posts,
        'user_connections': user_connections,
        'user_likes': user_likes,
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
    """Page de messagerie - Permet à n'importe qui de parler à n'importe qui"""
    if user_id:
        # Conversation avec un utilisateur spécifique
        other_user = get_object_or_404(CustomUser, id=user_id)
        if other_user == request.user:
            return redirect('messages')
        
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
            'is_connected': True,  # Toujours True maintenant, pas besoin de vérifier
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


def get_conversation_messages(request, user_id):
    """API pour récupérer les messages d'une conversation (JSON)"""
    from django.http import JsonResponse
    from django.utils import timezone
    import json
    
    print(f"[API] get_conversation_messages called for user_id={user_id}, authenticated={request.user.is_authenticated}")
    
    # Vérifier l'authentification manuellement pour retourner du JSON
    if not request.user.is_authenticated:
        print("[API] User not authenticated")
        return JsonResponse({'error': 'Authentication required', 'success': False}, status=401)
    
    try:
        other_user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found', 'success': False}, status=404)
    
    if other_user == request.user:
        return JsonResponse({'error': 'Cannot message yourself', 'success': False}, status=400)
    
    # Récupérer les messages - pas besoin de vérifier la connexion
    messages_list = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user),
        deleted=False,
        logement__isnull=True
    ).order_by('sent_at')
    
    # Marquer les messages comme lus
    Message.objects.filter(
        sender=other_user, 
        receiver=request.user, 
        read=False
    ).update(read=True)
    
    # Sérialiser les messages (convertir en liste pour itérer)
    messages_data = []
    messages_queryset = list(messages_list)  # Convertir en liste pour éviter les problèmes de requête
    
    for msg in messages_queryset:
        try:
            avatar_url = None
            if msg.sender.avatar:
                try:
                    avatar_url = str(msg.sender.avatar.url)
                except:
                    avatar_url = None
        except:
            avatar_url = None
        
        try:
            file_name = msg.get_file_name()
            file_name = str(file_name) if file_name else None
        except:
            file_name = None
            
        try:
            file_url = msg.get_file_url()
            file_url = str(file_url) if file_url else None
        except:
            file_url = None
        
        try:
            sent_at_str = msg.sent_at.isoformat() if hasattr(msg.sent_at, 'isoformat') else str(msg.sent_at)
        except:
            sent_at_str = str(msg.sent_at) if msg.sent_at else ''
            
        messages_data.append({
            'id': int(msg.id),
            'sender_id': int(msg.sender.id),
            'sender_name': str(msg.sender.get_full_name() or msg.sender.username),
            'sender_avatar': avatar_url,
            'text': str(msg.text) if msg.text else '',
            'file_name': file_name,
            'file_url': file_url,
            'sent_at': sent_at_str,
            'is_mine': bool(msg.sender == request.user),
        })
    
    try:
        user_avatar = None
        if other_user.avatar:
            user_avatar = other_user.avatar.url
    except:
        user_avatar = None
    
    # S'assurer que toutes les valeurs sont sérialisables en JSON
    try:
        # Construire l'objet user
        user_data = {
            'id': int(other_user.id),
            'name': str(other_user.get_full_name() or other_user.username),
            'avatar': str(user_avatar) if user_avatar else None,
        }
        
        response_data = {
            'user': user_data,
            'messages': messages_data,
            'count': int(len(messages_data)),
            'has_messages': bool(len(messages_data) > 0),
            'success': True
        }
        
        # Vérifier que les données sont sérialisables
        json_str = json.dumps(response_data)
        print(f"[API] Successfully serialized {len(messages_data)} messages for user {other_user.id}")
        print(f"[API] Response structure: user={bool(response_data.get('user'))}, messages={len(response_data.get('messages', []))}, success={response_data.get('success')}")
        
        response = JsonResponse(response_data, safe=True)
        response['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        import traceback
        error_msg = f"Error serializing response: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return JsonResponse({
            'error': 'Erreur lors de la sérialisation des données',
            'success': False,
            'messages': [],
            'count': 0
        }, status=500)


@login_required
@require_POST
def send_message_view(request, user_id):
    """Envoyer un message - Permet à n'importe qui de parler à n'importe qui"""
    receiver = get_object_or_404(CustomUser, id=user_id)
    
    if receiver == request.user:
        messages.error(request, "Vous ne pouvez pas vous envoyer un message à vous-même.")
        return redirect('messages')
    
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
def toggle_like_view(request, post_id):
    """Like/Unlike un post"""
    from .models import Notification
    
    post = get_object_or_404(Post, id=post_id)
    
    # Vérifier si la table Like existe
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='UserApp_like'")
            table_exists = cursor.fetchone() is not None
    except Exception:
        table_exists = False
    
    if not table_exists:
        return JsonResponse({
            'success': False,
            'error': 'La table Like n\'existe pas encore. Veuillez exécuter la migration: python manage.py migrate UserApp'
        }, status=500)
    
    try:
        like, created = Like.objects.get_or_create(
            post=post,
            user=request.user
        )
        
        if not created:
            # Si le like existe déjà, on le supprime (unlike)
            like.delete()
            liked = False
        else:
            liked = True
            # Créer une notification pour l'auteur du post (seulement si ce n'est pas son propre post)
            if post.author != request.user:
                try:
                    Notification.objects.create(
                        user=post.author,
                        verb='post_liked',
                        data={
                            'post_id': post.id,
                            'post_content_preview': post.content[:100] if len(post.content) > 100 else post.content,
                            'liker_id': request.user.id,
                            'liker_name': request.user.get_full_name() or request.user.username,
                        }
                    )
                except Exception as e:
                    # Ne pas bloquer le like si la notification échoue
                    print(f"Erreur lors de la création de la notification de like: {e}")
        
        likes_count = post.likes.count()
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': likes_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors du like: {str(e)}'
        }, status=500)


@login_required
@require_POST
def add_comment_view(request, post_id):
    """Ajouter un commentaire à un post"""
    from .models import Notification
    
    post = get_object_or_404(Post, id=post_id)
    
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({
            'success': False,
            'error': 'Le commentaire ne peut pas être vide.'
        }, status=400)
    
    try:
        comment = Comment.objects.create(
            post=post,
            author=request.user,
            text=text
        )
        
        # Créer une notification pour l'auteur du post (seulement si ce n'est pas son propre post)
        if post.author != request.user:
            try:
                Notification.objects.create(
                    user=post.author,
                    verb='post_commented',
                    data={
                        'post_id': post.id,
                        'post_content_preview': post.content[:100] if len(post.content) > 100 else post.content,
                        'comment_id': comment.id,
                        'comment_text_preview': text[:100] if len(text) > 100 else text,
                        'commenter_id': request.user.id,
                        'commenter_name': request.user.get_full_name() or request.user.username,
                    }
                )
            except Exception as e:
                # Ne pas bloquer le commentaire si la notification échoue
                print(f"Erreur lors de la création de la notification de commentaire: {e}")
        
        comments_count = post.comments.count()
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'text': comment.text,
                'author': comment.author.get_full_name() or comment.author.username,
                'author_id': comment.author.id,
                'author_avatar': comment.author.avatar.url if comment.author.avatar else None,
                'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M')
            },
            'comments_count': comments_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def share_post_view(request, post_id):
    """Partager un post"""
    from .models import Notification
    
    post = get_object_or_404(Post, id=post_id)
    
    # Créer un nouveau post partagé
    try:
        shared_content = f"Partagé depuis {post.author.get_full_name() or post.author.username}:\n\n{post.content}"
        
        shared_post = Post.objects.create(
            author=request.user,
            content=shared_content
        )
        
        # Si le post original a un média, on peut le copier (optionnel)
        # Pour l'instant, on ne copie pas le média
        
        # Créer une notification pour l'auteur du post original (seulement si ce n'est pas son propre post)
        if post.author != request.user:
            try:
                Notification.objects.create(
                    user=post.author,
                    verb='post_shared',
                    data={
                        'post_id': post.id,
                        'post_content_preview': post.content[:100] if len(post.content) > 100 else post.content,
                        'shared_post_id': shared_post.id,
                        'sharer_id': request.user.id,
                        'sharer_name': request.user.get_full_name() or request.user.username,
                    }
                )
            except Exception as e:
                # Ne pas bloquer le partage si la notification échoue
                print(f"Erreur lors de la création de la notification de partage: {e}")
        
        messages.success(request, 'Post partagé avec succès.')
        return JsonResponse({
            'success': True,
            'message': 'Post partagé avec succès.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def update_comment_view(request, comment_id):
    """Modifier un commentaire"""
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({
            'success': False,
            'error': 'Le commentaire ne peut pas être vide.'
        }, status=400)
    
    try:
        comment.text = text
        comment.save()
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'text': comment.text,
                'author': comment.author.get_full_name() or comment.author.username,
                'author_id': comment.author.id,
                'author_avatar': comment.author.avatar.url if comment.author.avatar else None,
                'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M')
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def delete_comment_view(request, comment_id):
    """Supprimer un commentaire"""
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    
    try:
        post_id = comment.post.id
        comment.delete()
        
        post = Post.objects.get(id=post_id)
        comments_count = post.comments.count()
        
        return JsonResponse({
            'success': True,
            'comments_count': comments_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


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
    
    # Récupérer l'utilisateur depuis la base de données pour éviter les problèmes de cache
    try:
        user = CustomUser.objects.get(id=user.id)
    except CustomUser.DoesNotExist:
        messages.error(request, "Utilisateur introuvable.")
        return redirect('account_settings')
    
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    address = request.POST.get('address', '').strip()
    city = request.POST.get('city', '').strip()
    country = request.POST.get('country', '').strip()
    zip_code = request.POST.get('zip', '').strip()

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
    if hasattr(user, 'zip'):
        setattr(user, 'zip', zip_code)
    
    # Avatar upload
    if 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
    
    try:
        # Construire la liste des champs à mettre à jour
        update_fields = ['first_name', 'last_name']
        
        # Ajouter les champs optionnels s'ils existent dans le modèle
        if hasattr(user, 'phone'):
            update_fields.append('phone')
        if hasattr(user, 'address'):
            update_fields.append('address')
        if hasattr(user, 'city'):
            update_fields.append('city')
        if hasattr(user, 'country'):
            update_fields.append('country')
        if hasattr(user, 'zip'):
            update_fields.append('zip')
        if 'avatar' in request.FILES:
            update_fields.append('avatar')
        if hasattr(user, 'updated_at'):
            update_fields.append('updated_at')
        
        # Utiliser update_fields pour éviter de toucher aux champs uniques (username, email)
        user.save(update_fields=update_fields)
        messages.success(request, 'Profil mis à jour avec succès.')
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        messages.error(request, f"Erreur lors de la mise à jour du profil: {str(e)}")
        # Log l'erreur pour le débogage (en production, utiliser un logger)
        print(f"Erreur profile_update: {error_details}")
    
    return redirect('account_settings')


@login_required
@require_POST
def profile_update_public_view(request):
    """
    Met à jour les informations publiques du profil (headline, bio, location, skills, education, experience).
    """
    import json
    user = request.user
    action = request.POST.get('action', '').strip()
    
    # Gestion des actions de suppression / mise à jour ciblée (expérience / formation)
    # Ces actions retournent immédiatement après mise à jour.
    if action == 'delete_experience':
        try:
            index = int(request.POST.get('exp_index', '-1'))
            experiences = list(user.experience or [])
            if 0 <= index < len(experiences):
                experiences.pop(index)
                user.experience = experiences
                user.save(update_fields=['experience'])
                messages.success(request, 'Expérience supprimée avec succès.')
            else:
                messages.error(request, 'Indice d’expérience invalide.')
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression de l'expérience: {e}")
        return redirect('profile')

    if action == 'delete_education':
        try:
            index = int(request.POST.get('edu_index', '-1'))
            educations = list(user.education or [])
            if 0 <= index < len(educations):
                educations.pop(index)
                user.education = educations
                user.save(update_fields=['education'])
                messages.success(request, 'Formation supprimée avec succès.')
            else:
                messages.error(request, 'Indice de formation invalide.')
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression de la formation: {e}")
        return redirect('profile')

    if action == 'update_experience':
        try:
            index = int(request.POST.get('exp_index', '-1'))
            experiences = list(user.experience or [])
            if 0 <= index < len(experiences):
                exp_item = {
                    'position': request.POST.get('exp_position', '').strip(),
                    'company': request.POST.get('exp_company', '').strip(),
                    'start_date': request.POST.get('exp_start', '').strip() or None,
                    'end_date': request.POST.get('exp_end', '').strip() or None,
                    'current': not request.POST.get('exp_end', '').strip(),
                    'description': request.POST.get('exp_description', '').strip() or None
                }
                exp_item = {k: v for k, v in exp_item.items() if v is not None and v != ''}
                experiences[index] = exp_item
                user.experience = experiences
                user.save(update_fields=['experience'])
                messages.success(request, 'Expérience mise à jour avec succès.')
            else:
                messages.error(request, 'Indice d’expérience invalide.')
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour de l'expérience: {e}")
        return redirect('profile')

    if action == 'update_education':
        try:
            index = int(request.POST.get('edu_index', '-1'))
            educations = list(user.education or [])
            if 0 <= index < len(educations):
                current = educations[index] or {}
                image_url = current.get('image_url')

                img_file = request.FILES.get('edu_image_file')
                if img_file:
                    try:
                        path = default_storage.save(f'education/{img_file.name}', img_file)
                        image_url = settings.MEDIA_URL + path
                    except Exception:
                        pass

                edu_item = {
                    'degree': request.POST.get('edu_degree', '').strip(),
                    'school': request.POST.get('edu_school', '').strip(),
                    'start_year': request.POST.get('edu_start', '').strip() or None,
                    'end_year': request.POST.get('edu_end', '').strip() or None,
                    'field': request.POST.get('edu_field', '').strip() or None,
                }
                edu_item = {k: v for k, v in edu_item.items() if v is not None and v != ''}
                if image_url:
                    edu_item['image_url'] = image_url
                educations[index] = edu_item
                user.education = educations
                user.save(update_fields=['education'])
                messages.success(request, 'Formation mise à jour avec succès.')
            else:
                messages.error(request, 'Indice de formation invalide.')
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour de la formation: {e}")
        return redirect('profile')

    # --------- Cas général : mise à jour des informations publiques / ajout d'éléments ---------
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
    
    # ----- Education -----
    # Deux modes supportés :
    # 1) Envoi JSON complet via un champ "education"
    # 2) Ajout d'une formation via les champs edu_* (modal du profil)
    if 'education' in request.POST or 'edu_degree' in request.POST or 'edu_school' in request.POST:
        try:
            education_data = request.POST.get('education', '')
            # Mode 1: JSON complet reçu
            if education_data:
                new_education = json.loads(education_data) if education_data else []
                user.education = new_education
            # Mode 2: ajout d'un seul élément depuis le formulaire
            elif request.POST.get('edu_degree') or request.POST.get('edu_school'):
                image_url = None
                img_file = request.FILES.get('edu_image_file')
                if img_file:
                    try:
                        path = default_storage.save(f'education/{img_file.name}', img_file)
                        image_url = settings.MEDIA_URL + path
                    except Exception:
                        image_url = None

                edu_item = {
                    'degree': request.POST.get('edu_degree', '').strip(),
                    'school': request.POST.get('edu_school', '').strip(),
                    'start_year': request.POST.get('edu_start', '').strip() or None,
                    'end_year': request.POST.get('edu_end', '').strip() or None,
                    'field': request.POST.get('edu_field', '').strip() or None,
                }
                # Filtrer les valeurs vides
                edu_item = {k: v for k, v in edu_item.items() if v}
                if image_url:
                    edu_item['image_url'] = image_url
                existing_edu = user.education if user.education else []
                user.education = existing_edu + [edu_item]
        except json.JSONDecodeError:
            messages.error(request, 'Format JSON invalide pour la formation.')
            return redirect('profile')
    
    # ----- Experience -----
    # Deux modes supportés :
    # 1) Envoi JSON complet via un champ "experience"
    # 2) Ajout d'une expérience via les champs exp_* (modal du profil)
    if 'experience' in request.POST or 'exp_position' in request.POST or 'exp_company' in request.POST:
        try:
            experience_data = request.POST.get('experience', '')
            # Mode 1: JSON complet reçu
            if experience_data:
                new_experience = json.loads(experience_data) if experience_data else []
                user.experience = new_experience
            # Mode 2: ajout d'un seul élément depuis le formulaire
            elif request.POST.get('exp_position') or request.POST.get('exp_company'):
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
        'terms', 'privacy', 'contact', 'sponsors', 'starter-page', 'spline-test'
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

def face_id_register_page(request):
    """
    Page pour l'enregistrement Face ID avec caméra
    """
    return render(request, 'User/FrontOffice/Login/face_id_register.html')

@csrf_exempt
@require_http_methods(["POST"])
def face_id_register(request):
    """
    API pour enregistrer les credentials Face ID
    """
    # Permettre l'enregistrement sans être connecté (pour nouveau compte)
    # L'email sera utilisé pour créer ou trouver l'utilisateur
    
    try:
        data = json.loads(request.body)
        credential_id = data.get('credentialId')
        public_key = data.get('publicKey')
        email = data.get('email')
        
        if not credential_id or not public_key:
            return JsonResponse({'error': 'DonnÃ©es manquantes'}, status=400)
        
        # Si l'utilisateur est connecté, utiliser son compte
        if request.user.is_authenticated:
            user = request.user
        elif email:
            # Sinon, chercher ou créer un utilisateur avec cet email
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                # Créer un nouvel utilisateur temporaire (sera complété lors de l'inscription)
                # Pour l'instant, on retourne une erreur demandant de s'inscrire d'abord
                return JsonResponse({
                    'error': 'Compte non trouvé. Veuillez d\'abord créer un compte avec cet email.',
                    'requires_signup': True
                }, status=404)
        else:
            return JsonResponse({'error': 'Email requis pour l\'enregistrement'}, status=400)
        
        # Enregistrer Face ID
        user.face_id_enabled = True
        user.face_id_credential_id = credential_id
        user.face_id_public_key = public_key
        user.save()
        
        return JsonResponse({'success': True, 'message': 'Face ID enregistrÃ© avec succÃ¨s'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def google_login(request):
    """
    Redirige vers Google OAuth pour l'authentification
    """
    
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        "&client_id=" + settings.GOOGLE_OAUTH2_CLIENT_ID +
        "&redirect_uri=" + settings.GOOGLE_OAUTH2_REDIRECT_URI +
        "&scope=email profile"
        "&access_type=online"
        "&prompt=select_account"
    )
    return redirect(google_auth_url)

def google_callback(request):
    """
    Callback URL - Google renvoie ici après l'authentification
    """
    
    code = request.GET.get("code")
    
    if not code:
        messages.error(request, 'Erreur lors de l\'authentification Google. Code d\'autorisation manquant.')
        return redirect('login')
    
    try:
        # Échanger le code contre un token d'accès
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "code": code,
            "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_OAUTH2_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        
        token_response = requests.post(token_url, data=data)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            messages.error(request, 'Erreur lors de l\'obtention du token d\'accès Google.')
            return redirect('login')
        
        # Obtenir les informations utilisateur
        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        email = user_info.get("email")
        first_name = user_info.get("given_name", "")
        last_name = user_info.get("family_name", "")
        picture = user_info.get("picture", "")
        google_id = user_info.get("id", "")
        
        if not email:
            messages.error(request, 'Impossible de récupérer l\'email depuis Google.')
            return redirect('login')
        
        # Chercher ou créer l'utilisateur
        try:
            user = CustomUser.objects.get(email=email)
            user_created = False
        except CustomUser.DoesNotExist:
            # Créer un nouvel utilisateur
            username = email.split('@')[0]
            # S'assurer que le username est unique
            base_username = username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Générer un mot de passe aléatoire
            import secrets
            password = secrets.token_urlsafe(16)
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_verified=True  # Email Google est déjà vérifié
            )
            user_created = True
        
        # Connecter l'utilisateur
        login(request, user)
        
        # Sauvegarder dans la session
        request.session['user_id'] = user.id
        request.session['username'] = user.username
        
        # Message de succès
        if user_created:
            messages.success(request, f'Compte créé avec Google! Bienvenue {user.username}!')
        else:
            messages.success(request, f'Connexion Google réussie! Bienvenue {user.username}!')
        
        # Rediriger selon le rôle
        if user.is_superuser or (hasattr(user, 'role') and user.role == 'ADMIN'):
            return redirect('/admin/')
        
        return redirect('/')
        
    except requests.exceptions.RequestException as e:
        messages.error(request, f'Erreur lors de la communication avec Google: {str(e)}')
        return redirect('login')
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'authentification Google: {str(e)}')
        return redirect('login')

def google_auth_login(request):
    """
    Page de redirection pour l'authentification Google (ancienne méthode - conservée pour compatibilité)
    """
    return render(request, 'User/FrontOffice/Login/google_auth.html')

@csrf_exempt
@require_http_methods(["POST"])
def google_auth(request):
    """
    API pour authentifier avec Google
    Supporte deux méthodes :
    1. JWT token (recommandé) - depuis Google Sign-In API
    2. Données utilisateur directes - depuis OAuth 2.0 token
    """
    try:
        data = json.loads(request.body)
        credential = data.get('credential')  # JWT token depuis Google Sign-In
        email = data.get('email')
        name = data.get('name', '')
        picture = data.get('picture', '')
        google_id = data.get('google_id', '')
        
        # Si un credential JWT est fourni, le vérifier
        if credential:
            try:
                # Décoder le JWT (sans vérification de signature pour simplifier)
                # En production, vous devriez vérifier la signature avec la clé publique Google
                parts = credential.split('.')
                if len(parts) == 3:
                    # Décoder le payload (partie 2)
                    payload = parts[1]
                    # Ajouter le padding si nécessaire
                    padding = 4 - len(payload) % 4
                    if padding != 4:
                        payload += '=' * padding
                    decoded = base64.urlsafe_b64decode(payload)
                    jwt_data = json_lib.loads(decoded)
                    
                    email = jwt_data.get('email')
                    name = jwt_data.get('name', '')
                    picture = jwt_data.get('picture', '')
                    google_id = jwt_data.get('sub', '')
            except Exception as e:
                print(f"Erreur décodage JWT: {e}")
                # Continuer avec les données directes si le JWT échoue
        
        if not email:
            return JsonResponse({'error': 'Email requis'}, status=400)
        
        # Chercher ou créer l'utilisateur
        user_created = False
        try:
            user = CustomUser.objects.get(email=email)
            # Mettre à jour les informations Google si nécessaire
            if google_id and not hasattr(user, 'google_id'):
                # Vous pouvez ajouter un champ google_id au modèle si nécessaire
                pass
        except CustomUser.DoesNotExist:
            # Créer un nouvel utilisateur
            username = email.split('@')[0]
            # S'assurer que le username est unique
            base_username = username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Générer un mot de passe aléatoire (l'utilisateur pourra le changer)
            import secrets
            password = secrets.token_urlsafe(16)
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=name.split()[0] if name else '',
                last_name=' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
                is_verified=True  # Email Google est déjà vérifié
            )
            user_created = True
        
        # Connecter l'utilisateur
        login(request, user)
        
        # Sauvegarder dans la session
        request.session['user_id'] = user.id
        request.session['username'] = user.username
        
        # Rediriger selon le rôle
        redirect_url = '/'
        if user.is_superuser or (hasattr(user, 'role') and user.role == 'ADMIN'):
            redirect_url = '/admin/'
        
        return JsonResponse({
            'success': True,
            'message': 'Compte créé avec Google! Bienvenue!' if user_created else 'Connexion Google réussie!',
            'redirect': redirect_url,
            'user_created': user_created
        })
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
