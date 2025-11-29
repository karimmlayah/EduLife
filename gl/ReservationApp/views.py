from django.shortcuts import render, redirect, get_object_or_404
from .models import Reservation, Avis
from CovoiturageApp.models import Offre
from django.conf import settings
from django.contrib.auth import get_user_model  # Ajoutez cet import
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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

def reservation_list(request):
    reservations = Reservation.objects.all()
    return render(request, 'ReservationApp/reservation_list.html', {'reservations': reservations})

@csrf_exempt
def reservation_create(request):
    if request.method == 'POST':
        try:
            offre_id = request.POST.get('offre_id')
            nombre_places = int(request.POST.get('nombre_places', 1))
            
            if not offre_id:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'ID de l\'offre manquant'
                    }, status=400)
                return redirect('covoiturage_home')
            
            offre = get_object_or_404(Offre, id=offre_id)
            
            # Vérifier les places disponibles
            from .models import Reservation as ReservationModel
            places_disponibles = ReservationModel.get_places_disponibles(offre)
            
            if nombre_places > places_disponibles:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Il ne reste que {places_disponibles} place(s) disponible(s)'
                    }, status=400)
                return redirect('covoiturage_home')
            
            # Utiliser l'utilisateur connecté ou l'utilisateur statique
            if request.user.is_authenticated:
                passager = request.user
                # Utiliser les informations de l'utilisateur connecté
                nom_passager = request.POST.get('nom_passager', '') or f"{passager.first_name} {passager.last_name}".strip() or passager.username
                telephone_passager = request.POST.get('telephone_passager', '') or (passager.phone if hasattr(passager, 'phone') else '')
            else:
                passager = get_static_user()
                nom_passager = request.POST.get('nom_passager', '') or passager.username
                telephone_passager = request.POST.get('telephone_passager', '') or (passager.phone if hasattr(passager, 'phone') else '')
            
            # Vérifier que les champs requis sont présents
            if not nom_passager:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Le nom du passager est requis'
                    }, status=400)
                return redirect('covoiturage_home')
            
            if not telephone_passager:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Le téléphone du passager est requis'
                    }, status=400)
                return redirect('covoiturage_home')
            
            # Créer la réservation avec les informations de l'utilisateur connecté
            reservation = Reservation.objects.create(
                offre=offre,
                passager=passager,
                nom_passager=nom_passager,
                telephone_passager=telephone_passager,
                nombre_places_reservees=nombre_places
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Réservation effectuée avec succès ! {nombre_places} place(s) réservée(s).',
                    'reservation_id': reservation.id,
                    'places_disponibles': ReservationModel.get_places_disponibles(offre)
                })
            
            return redirect('reservation_list')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Erreur: {str(e)}'
                }, status=400)
            return redirect('covoiturage_home')

    offres = Offre.objects.all()
    users = User.objects.all()
    return render(request, 'reservation_form.html', {'offres': offres, 'users': users})

def reservation_delete(request, id):
    reservation = get_object_or_404(Reservation, id=id)
    reservation.delete()
    return redirect('reservation_list')

def reservation_home(request):
    return render(request, 'reservation_list.html')
# ==========================
#   GESTION PAR CONDUCTEUR
# ==========================

def mes_reservations(request):
    # Afficher toutes les demandes pour le conducteur
    demandes = Reservation.objects.all()
    return render(request, "covoiturage/Backoffice/pages/mes_reservations.html", {"demandes": demandes})


def reservation_accept(request, id):
    r = get_object_or_404(Reservation, id=id)
    r.statut = "accepted"
    r.save()
    return redirect("mes_reservations")


def reservation_reject(request, id):
    r = get_object_or_404(Reservation, id=id)
    r.statut = "rejected"
    r.save()
    return redirect("mes_reservations")

def mes_reservations_passager(request):
    """Le passager voit ses propres réservations."""
    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()
    
    # Filtrer uniquement les réservations du passager, triées par date (plus récentes en premier)
    mes_res = Reservation.objects.filter(passager=user).order_by('-date_reservation')

    return render(request, "covoiturage/Fontoffice/mes_reservations_passager.html", {
        "mes_res": mes_res
    })


def reservation_cancel(request, id):
    from django.contrib import messages
    
    r = get_object_or_404(Reservation, id=id)

    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()

    if r.passager != user:
        messages.error(request, "Vous n'avez pas le droit d'annuler cette réservation.")
        return redirect("mes_reservations_passager")

    r.statut = "cancelled"
    r.save()
    messages.success(request, "Votre réservation a été annulée avec succès.")
    return redirect("mes_reservations_passager")


# 🔹 MODIFIER UNE RÉSERVATION (changer le nombre de places)
def reservation_update(request, id):
    from django.contrib import messages
    
    reservation = get_object_or_404(Reservation, id=id)
    
    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()
    
    # Vérifier que c'est bien le passager de cette réservation
    if reservation.passager != user:
        messages.error(request, "Vous n'avez pas le droit de modifier cette réservation.")
        return redirect("mes_reservations_passager")
    
    # Vérifier que la réservation peut être modifiée (pending ou accepted)
    if reservation.statut not in ['pending', 'accepted']:
        messages.error(request, "Cette réservation ne peut plus être modifiée.")
        return redirect("mes_reservations_passager")
    
    if request.method == 'POST':
        try:
            nouveau_nombre_places = int(request.POST.get('nombre_places', 1))
            
            # Vérifier que le nouveau nombre de places est valide
            if nouveau_nombre_places < 1:
                messages.error(request, "Le nombre de places doit être au moins 1.")
                return redirect("mes_reservations_passager")
            
            # Calculer les places disponibles (en excluant la réservation actuelle)
            from ReservationApp.models import Reservation as ReservationModel
            reservations_valides = ReservationModel.objects.filter(
                offre=reservation.offre,
                statut__in=["pending", "accepted"]
            ).exclude(id=reservation.id)
            
            total_reserve = sum(r.nombre_places_reservees for r in reservations_valides)
            places_disponibles = reservation.offre.nombre_places - total_reserve
            
            if nouveau_nombre_places > places_disponibles + reservation.nombre_places_reservees:
                messages.error(request, f"Pas assez de places disponibles. Maximum: {places_disponibles + reservation.nombre_places_reservees}")
                return redirect("mes_reservations_passager")
            
            # Mettre à jour le nombre de places
            reservation.nombre_places_reservees = nouveau_nombre_places
            reservation.save()
            
            messages.success(request, f"Votre réservation a été modifiée. Nombre de places: {nouveau_nombre_places}")
            return redirect("mes_reservations_passager")
        except ValueError:
            messages.error(request, "Nombre de places invalide.")
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification: {str(e)}")
    
    # Calculer les places disponibles pour l'affichage
    from ReservationApp.models import Reservation as ReservationModel
    reservations_valides = ReservationModel.objects.filter(
        offre=reservation.offre,
        statut__in=["pending", "accepted"]
    ).exclude(id=reservation.id)
    
    total_reserve = sum(r.nombre_places_reservees for r in reservations_valides)
    places_disponibles = reservation.offre.nombre_places - total_reserve
    
    return render(request, "covoiturage/Fontoffice/modifier_reservation.html", {
        "reservation": reservation,
        "places_disponibles": places_disponibles
    })


# ==========================
#   GESTION DES AVIS
# ==========================

@login_required
def creer_avis(request, reservation_id):
    """Permet au passager de créer un avis pour une réservation acceptée"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifier que c'est bien le passager de cette réservation
    if reservation.passager != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à noter cette réservation.")
        return redirect("mes_reservations_passager")
    
    # Vérifier que la réservation est acceptée
    if reservation.statut != "accepted":
        messages.error(request, "Vous ne pouvez noter que les réservations acceptées.")
        return redirect("mes_reservations_passager")
    
    # Vérifier qu'un avis n'existe pas déjà
    if hasattr(reservation, 'avis'):
        messages.info(request, "Vous avez déjà laissé un avis pour cette réservation.")
        return redirect("mes_reservations_passager")
    
    if request.method == 'POST':
        note = request.POST.get('note')
        commentaire = request.POST.get('commentaire', '').strip()
        
        if not note:
            messages.error(request, "Veuillez sélectionner une note.")
            return render(request, "covoiturage/Fontoffice/creer_avis.html", {
                "reservation": reservation
            })
        
        try:
            note = int(note)
            if note < 1 or note > 5:
                raise ValueError("Note invalide")
        except (ValueError, TypeError):
            messages.error(request, "La note doit être entre 1 et 5 étoiles.")
            return render(request, "covoiturage/Fontoffice/creer_avis.html", {
                "reservation": reservation
            })
        
        # Créer l'avis
        avis = Avis.objects.create(
            reservation=reservation,
            note=note,
            commentaire=commentaire if commentaire else None
        )
        
        messages.success(request, "Votre avis a été enregistré avec succès. Merci !")
        return redirect("mes_reservations_passager")
    
    return render(request, "covoiturage/Fontoffice/creer_avis.html", {
        "reservation": reservation
    })


@login_required
def modifier_avis(request, reservation_id):
    """Permet au passager de modifier son avis"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifier que c'est bien le passager de cette réservation
    if reservation.passager != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à modifier cet avis.")
        return redirect("mes_reservations_passager")
    
    # Vérifier qu'un avis existe
    if not hasattr(reservation, 'avis'):
        messages.error(request, "Aucun avis trouvé pour cette réservation.")
        return redirect("mes_reservations_passager")
    
    avis = reservation.avis
    
    if request.method == 'POST':
        note = request.POST.get('note')
        commentaire = request.POST.get('commentaire', '').strip()
        
        if not note:
            messages.error(request, "Veuillez sélectionner une note.")
            return render(request, "covoiturage/Fontoffice/modifier_avis.html", {
                "reservation": reservation,
                "avis": avis
            })
        
        try:
            note = int(note)
            if note < 1 or note > 5:
                raise ValueError("Note invalide")
        except (ValueError, TypeError):
            messages.error(request, "La note doit être entre 1 et 5 étoiles.")
            return render(request, "covoiturage/Fontoffice/modifier_avis.html", {
                "reservation": reservation,
                "avis": avis
            })
        
        # Modifier l'avis
        avis.note = note
        avis.commentaire = commentaire if commentaire else None
        avis.save()
        
        messages.success(request, "Votre avis a été modifié avec succès.")
        return redirect("mes_reservations_passager")
    
    return render(request, "covoiturage/Fontoffice/modifier_avis.html", {
        "reservation": reservation,
        "avis": avis
    })