from django.shortcuts import render, redirect, get_object_or_404
from .models import Offre
from django.conf import settings
from django.contrib.auth import get_user_model  # Ajout de cet import
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ReservationApp.models import Reservation
import json
from datetime import datetime

# Récupère le modèle utilisateur personnalisé
User = get_user_model()

# ============================================
# FONCTION HELPER POUR UTILISATEUR STATIQUE
# ============================================
def get_static_user():
    """
    Retourne l'utilisateur statique configuré dans settings.STATIC_USER_ID
    Si l'utilisateur n'existe pas, retourne le premier utilisateur disponible
    NE CRÉE PAS d'utilisateur pour éviter les erreurs UNIQUE constraint
    """
    static_user_id = getattr(settings, 'STATIC_USER_ID', 1)
    try:
        return User.objects.get(id=static_user_id)
    except User.DoesNotExist:
        # Si l'utilisateur avec cet ID n'existe pas, retourner le premier disponible
        user = User.objects.first()
        if not user:
            # Ne pas créer d'utilisateur, lever une exception
            raise Exception("Aucun utilisateur disponible. Veuillez vous connecter ou créer un utilisateur dans l'admin.")
        return user

# 🌍 PAGE D'ACCUEIL (alias pour compatibilité avec urls.py)
def covoiturage_home(request):
    from ReservationApp.models import Reservation, Avis
    from django.db.models import Avg, Count
    
    # Afficher uniquement les offres approuvées
    offres = Offre.objects.filter(approuve=True).order_by('-date_covoiturage')[:6]
    
    # Calculer les places disponibles et les avis pour chaque offre
    offres_avec_places = []
    for offre in offres:
        places_disponibles = Reservation.get_places_disponibles(offre)
        
        # Récupérer tous les avis pour cette offre (via les réservations acceptées)
        reservations_acceptees = Reservation.objects.filter(
            offre=offre,
            statut="accepted"
        )
        avis_list = Avis.objects.filter(reservation__in=reservations_acceptees)
        
        # Calculer la note moyenne
        note_moyenne = avis_list.aggregate(Avg('note'))['note__avg']
        nombre_avis = avis_list.count()
        
        offres_avec_places.append({
            'offre': offre,
            'places_disponibles': places_disponibles,
            'note_moyenne': round(note_moyenne, 1) if note_moyenne else None,
            'nombre_avis': nombre_avis,
            'avis_list': avis_list[:3]  # Afficher les 3 derniers avis
        })
    
    return render(request, 'covoiturage/Fontoffice/contact.html', {'offres_avec_places': offres_avec_places})


# 🌍 PAGE CONTACT (facultative)
def contact(request):
    return render(request, 'covoiturage/Fontoffice/2.html')  # page de contact avec Google Map


# 🔹 LISTE DES OFFRES (front + dashboard)
def offre_list(request):
    from django.db.models import Count, Sum
    from django.utils import timezone
    from datetime import timedelta
    
    offres = Offre.objects.all().order_by('-date_covoiturage')
    reservations = Reservation.objects.all()
    
    # Statistiques
    total_offres = offres.count()
    
    # Trajets futurs (date >= aujourd'hui)
    aujourdhui = timezone.now()
    trajets_futurs = offres.filter(date_covoiturage__gte=aujourdhui).count()
    
    # Places totales
    places_totales = sum(offre.nombre_places for offre in offres)
    
    # Places réservées (toutes les réservations acceptées ou en attente)
    places_reservees = sum(
        res.nombre_places_reservees 
        for res in reservations.filter(statut__in=['pending', 'accepted'])
    )
    
    # Places disponibles
    places_disponibles = places_totales - places_reservees
    
    # Revenu total estimé
    revenu_total = sum(
        float(res.offre.prix) * res.nombre_places_reservees 
        for res in reservations.filter(statut='accepted')
    )
    
    context = {
        'offres': offres,
        'total_offres': total_offres,
        'trajets_futurs': trajets_futurs,
        'places_totales': places_totales,
        'places_reservees': places_reservees,
        'places_disponibles': places_disponibles,
        'revenu_total': round(revenu_total, 2),
    }
    
    return render(request, 'covoiturage/Backoffice/pages/offre_list.html', context)


# 🔹 CRÉER UNE OFFRE
def offre_create(request):
    if request.method == 'POST':
        try:
            # Utiliser l'utilisateur connecté ou l'utilisateur statique
            if request.user.is_authenticated:
                conducteur = request.user
            else:
                # Si l'utilisateur n'est pas connecté, utiliser l'utilisateur statique
                conducteur = get_static_user()
            
            depart = request.POST.get('depart')
            destination = request.POST.get('destination')
            prix = request.POST.get('prix')
            nombre_places = request.POST.get('nombre_places')
            telephone = request.POST.get('telephone')
            date_covoiturage_str = request.POST.get('date_covoiturage')
            modele_voiture = request.POST.get('modele_voiture', '')
            climatisation = request.POST.get('climatisation') == 'on'
            preference_genre = request.POST.get('preference_genre', 'tous')
            
            # Convertir la date si elle est fournie
            date_covoiturage = None
            if date_covoiturage_str:
                try:
                    date_covoiturage = datetime.strptime(date_covoiturage_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass

            # Créer l'offre avec l'utilisateur connecté
            offre = Offre.objects.create(
                conducteur=conducteur,  # Utilise l'utilisateur connecté
                depart=depart,
                destination=destination,
                prix=prix,
                nombre_places=nombre_places,
                telephone=telephone,
                date_covoiturage=date_covoiturage,
                modele_voiture=modele_voiture,
                climatisation=climatisation,
                preference_genre=preference_genre
            )
            
            # Si c'est une requête AJAX, retourner JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Offre publiée avec succès !',
                    'offre_id': offre.id
                })
            
            # Rediriger selon la page d'origine
            referer = request.META.get('HTTP_REFERER', '')
            if 'dashboard' in referer:
                return redirect('dashboard')
            elif 'offres' in referer or 'offre_list' in referer:
                return redirect('offres_list')
            return redirect('home')  # Rediriger vers la page d'accueil du covoiturage
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Erreur: {str(e)}'
                }, status=400)
            return redirect('home')

    return render(request, 'offres/offre_form.html')


# 🔹 MES OFFRES (POUR LE COVOITUREUR)
def mes_offres(request):
    """
    Le conducteur voit toutes ses propres offres.
    Utilise l'utilisateur statique si non authentifié.
    """
    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()
    
    # Filtrer uniquement les offres du conducteur
    mes_offres = Offre.objects.filter(conducteur=user).order_by('-date_covoiturage')
    
    # Calculer les places disponibles pour chaque offre
    from ReservationApp.models import Reservation
    offres_avec_places = []
    for offre in mes_offres:
        places_disponibles = Reservation.get_places_disponibles(offre)
        offres_avec_places.append({
            'offre': offre,
            'places_disponibles': places_disponibles
        })
    
    return render(request, 'covoiturage/Fontoffice/mes_offres.html', {
        'offres_avec_places': offres_avec_places
    })


# 🔹 MODIFIER UNE OFFRE
def offre_update(request, id):
    from datetime import datetime
    from django.contrib import messages
    
    offre = get_object_or_404(Offre, id=id)
    
    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()
    
    # Vérifier que c'est le conducteur propriétaire
    if offre.conducteur != user:
        messages.error(request, "Vous n'avez pas le droit de modifier cette offre.")
        return redirect('mes_offres')
    
    if request.method == 'POST':
        try:
            offre.depart = request.POST.get('depart')
            offre.destination = request.POST.get('destination')
            offre.prix = request.POST.get('prix')
            offre.nombre_places = request.POST.get('nombre_places')
            offre.telephone = request.POST.get('telephone', '')
            offre.modele_voiture = request.POST.get('modele_voiture', '')
            offre.climatisation = request.POST.get('climatisation') == 'on'
            offre.preference_genre = request.POST.get('preference_genre', 'tous')
            
            # Gérer les coordonnées
            offre.depart_lat = request.POST.get('depart_lat') or None
            offre.depart_lng = request.POST.get('depart_lng') or None
            offre.destination_lat = request.POST.get('destination_lat') or None
            offre.destination_lng = request.POST.get('destination_lng') or None
            
            # Gérer la date
            date_covoiturage_str = request.POST.get('date_covoiturage')
            if date_covoiturage_str:
                try:
                    offre.date_covoiturage = datetime.strptime(date_covoiturage_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
            else:
                offre.date_covoiturage = None
            
            offre.save()
            messages.success(request, "L'offre a été modifiée avec succès.")
            
            # Rediriger selon la page d'origine
            referer = request.META.get('HTTP_REFERER', '')
            if 'mes_offres' in referer:
                return redirect('mes_offres')
            elif 'dashboard' in referer:
                return redirect('dashboard')
            return redirect('mes_offres')
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification: {str(e)}")
    
    return render(request, 'covoiturage/Fontoffice/modifier_offre.html', {'offre': offre})


# 🔹 SUPPRIMER UNE OFFRE
def offre_delete(request, id):
    from django.contrib import messages
    
    offre = get_object_or_404(Offre, id=id)
    
    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()

    # Si l'utilisateur est ADMIN ou STAFF → SUPPRIMER DIRECT
    if user.is_staff or user.is_superuser:
        offre.delete()
        messages.success(request, "L'offre a été supprimée avec succès.")
        return redirect('dashboard')

    # Sinon, vérifier que c'est le conducteur propriétaire
    if offre.conducteur != user:
        messages.error(request, "Vous n'avez pas le droit de supprimer cette offre.")
        return redirect('mes_offres')

    offre.delete()
    messages.success(request, "Votre offre a été supprimée avec succès.")
    
    # Rediriger selon la page d'origine
    referer = request.META.get('HTTP_REFERER', '')
    if 'mes_offres' in referer:
        return redirect('mes_offres')
    elif 'dashboard' in referer:
        return redirect('dashboard')
    return redirect('mes_offres')


# 🧭 (optionnel) PAGE DE RECHERCHE DE TRAJET
def recherche_trajet(request):
    query = request.GET.get('q')
    offres = Offre.objects.filter(destination__icontains=query) if query else Offre.objects.all()
    return render(request, 'offres/recherche.html', {'offres': offres})

def index(request):
    return render(request, 'evently/index.html')