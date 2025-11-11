from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.shortcuts import get_object_or_404
from django.db.models import Q
import json

from .forms import SignUpForm, LoginForm
from .models import CustomUser, Post, Comment

# Create your views here.
def index_view(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('/admin/')
    return render(request, 'evently/index.html')

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
                        if user.is_superuser:
                            return redirect('/admin/')
                        return redirect('index')
                    else:
                        messages.error(request, 'Votre compte est dÃ©sactivÃ©.')
                else:
                    messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
        
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
    
    return render(request, 'FrontOffice/Login/login.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'show_login': show_login,
    })


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
    return render(request, 'FrontOffice/profile.html', {
        'user_obj': request.user,
    })


@login_required
def profile_view(request):
    """Public-facing profile header page (hero style)."""
    # Récupérer les posts de l'utilisateur
    posts = Post.objects.filter(author=request.user).order_by('-created_at')[:10]
    return render(request, 'FrontOffice/profile_public.html', {
        'user_obj': request.user,
        'posts': posts,
    })


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
    if 'cover_photo' in request.FILES:
        user.cover_photo = request.FILES['cover_photo']
    
    try:
        user.save()
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
    return render(request, 'evently/index.html')

def evently_template(request, page: str):
    allowed = {
        'about', 'schedule', 'speakers', 'speaker-details',
        'venue', 'tickets', 'buy-tickets', 'gallery',
        'terms', 'privacy', 'contact', 'sponsors', 'starter-page'
    }
    if page in allowed:
        return render(request, f'evently/{page}.html')
    return render(request, 'evently/404.html', status=404)

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


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def ban_user_view(request, user_id: int):
    target = get_object_or_404(CustomUser, pk=user_id)
    reason = request.POST.get('reason', '').strip()
    target.is_active = False
    target.ban_reason = reason or 'Banni par un administrateur.'
    from django.utils import timezone
    target.banned_at = timezone.now()
    target.save()
    messages.warning(request, f"{target.username} a été banni.")
    return redirect(request.META.get('HTTP_REFERER', 'manage_users'))


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def unban_user_view(request, user_id: int):
    target = get_object_or_404(CustomUser, pk=user_id)
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
