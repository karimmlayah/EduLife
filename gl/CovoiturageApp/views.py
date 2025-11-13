from django.shortcuts import render, redirect, get_object_or_404
from .models import Offre
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime

# 🌍 PAGE D'ACCUEIL (alias pour compatibilité avec urls.py)
def covoiturage_home(request):
    from gl.ReservationApp.models import Reservation
    offres = Offre.objects.all()[:6]  # Afficher les 6 dernières offres
    
    # Calculer les places disponibles pour chaque offre
    offres_avec_places = []
    for offre in offres:
        places_disponibles = Reservation.get_places_disponibles(offre)
        offres_avec_places.append({
            'offre': offre,
            'places_disponibles': places_disponibles
        })
    
    return render(request, 'Fontoffice/contact.html', {'offres_avec_places': offres_avec_places})


# 🌍 PAGE CONTACT (facultative)
def contact(request):
    return render(request, 'Fontoffice/2.html')  # page de contact avec Google Map


# 🔹 LISTE DES OFFRES (front + dashboard)
def offre_list(request):
    offres = Offre.objects.all()
    return render(request, 'backoffice/pages/offre_list.html', {'offres': offres})


# 🔹 CRÉER UNE OFFRE
def offre_create(request):
    if request.method == 'POST':
        try:
            # S'assurer qu'un utilisateur avec ID 1 existe
            # Créer un utilisateur admin s'il n'existe pas
            try:
                conducteur = User.objects.get(id=1)
            except User.DoesNotExist:
                # Créer un utilisateur admin par défaut
                conducteur = User.objects.create_user(
                    username='admin',
                    email='admin@example.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='User'
                )
                # Si l'ID n'est pas 1, utiliser le premier utilisateur disponible
                if conducteur.id != 1:
                    conducteur = User.objects.first()
                    if not conducteur:
                        raise Exception("Aucun utilisateur disponible. Veuillez créer un utilisateur admin.")
            
            depart = request.POST.get('depart')
            destination = request.POST.get('destination')
            prix = request.POST.get('prix')
            nombre_places = request.POST.get('nombre_places')
            telephone = request.POST.get('telephone')
            date_covoiturage_str = request.POST.get('date_covoiturage')
            modele_voiture = request.POST.get('modele_voiture', '')
            climatisation = request.POST.get('climatisation') == 'on'
            
            # Convertir la date si elle est fournie
            date_covoiturage = None
            if date_covoiturage_str:
                try:
                    date_covoiturage = datetime.strptime(date_covoiturage_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass

            # Utiliser conducteur_id=1 de manière fixe pour le moment
            # Si l'utilisateur avec ID 1 existe, l'utiliser, sinon utiliser le premier disponible
            conducteur_id = 1
            try:
                User.objects.get(id=1)
            except User.DoesNotExist:
                conducteur_id = conducteur.id
            
            offre = Offre.objects.create(
                conducteur_id=conducteur_id,  # Fixe à 1 si possible, sinon premier utilisateur
                depart=depart,
                destination=destination,
                prix=prix,
                nombre_places=nombre_places,
                telephone=telephone,
                date_covoiturage=date_covoiturage,
                modele_voiture=modele_voiture,
                climatisation=climatisation
            )
            
            # Si c'est une requête AJAX, retourner JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Offre publiée avec succès !',
                    'offre_id': offre.id
                })
            
            return redirect('home')  # Rediriger vers la page d'accueil du covoiturage
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Erreur: {str(e)}'
                }, status=400)
            return redirect('home')

    return render(request, 'offres/offre_form.html')


# 🔹 MODIFIER UNE OFFRE
def offre_update(request, id):
    offre = get_object_or_404(Offre, id=id)
    if request.method == 'POST':
        offre.depart = request.POST.get('depart')
        offre.destination = request.POST.get('destination')
        offre.prix = request.POST.get('prix')
        offre.save()
        return redirect('offre_list')

    return render(request, 'offres/offre_form.html', {'offre': offre})


# 🔹 SUPPRIMER UNE OFFRE
def offre_delete(request, id):
    offre = get_object_or_404(Offre, id=id)

    # Si l'utilisateur est ADMIN ou STAFF → SUPPRIMER DIRECT
    if request.user.is_staff or request.user.is_superuser:
        offre.delete()
        return redirect('dashboard')

    # Sinon, vérifier que c'est le conducteur propriétaire
    if offre.conducteur != request.user:
        return HttpResponseForbidden("Vous n'avez pas le droit de supprimer cette offre.")

    offre.delete()
    return redirect('dashboard')


# 🧭 (optionnel) PAGE DE RECHERCHE DE TRAJET
def recherche_trajet(request):
    query = request.GET.get('q')
    offres = Offre.objects.filter(destination__icontains=query) if query else Offre.objects.all()
    return render(request, 'offres/recherche.html', {'offres': offres})

def index(request):
    return render(request, 'evently/index.html')
