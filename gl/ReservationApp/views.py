from django.shortcuts import render, redirect, get_object_or_404
from .models import Reservation
from gl.CovoiturageApp.models import Offre
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

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
            
            # Utiliser l'utilisateur connecté ou un utilisateur par défaut
            if request.user.is_authenticated:
                passager = request.user
            else:
                # Utiliser l'utilisateur avec ID 1 ou le premier disponible
                try:
                    passager = User.objects.get(id=1)
                except User.DoesNotExist:
                    passager = User.objects.first()
                    if not passager:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False,
                                'message': 'Aucun utilisateur disponible. Veuillez vous connecter.'
                            }, status=400)
                        return redirect('covoiturage_home')
            
            # Créer la réservation
            reservation = Reservation.objects.create(
                offre=offre,
                passager=passager,
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
    return render(request, "backoffice/pages/mes_reservations.html", {"demandes": demandes})


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
@login_required
def mes_reservations_passager(request):
    """Le passager voit ses propres réservations."""
    mes_res = Reservation.objects.filter(passager=request.user)

    return render(request, "backoffice/pages/mes_reservations_passager.html", {
        "mes_res": mes_res
    })


@login_required
def reservation_cancel(request, id):
    r = get_object_or_404(Reservation, id=id)

    if r.passager != request.user:
        return HttpResponseForbidden("Ce n'est pas ta réservation !")

    r.statut = "cancelled"
    r.save()
    return redirect("mes_reservations_passager")