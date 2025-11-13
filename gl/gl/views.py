from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from gl.CovoiturageApp.models import Offre
from gl.ReservationApp.models import Reservation


# --- DASHBOARD PRINCIPAL ---
def dashboard(request):
    offres = Offre.objects.all()
    return render(request, "backoffice/pages/dashboard.html", {"offres": offres})


# --- DASHBOARD DES RÉSERVATIONS ---
def reservation_dashboard(request):
    return render(request, "backoffice/pages/reservation_dashboard.html")


# --- MES RÉSERVATIONS (POUR LE CONDUCTEUR) ---
def mes_reservations(request):
    """
    Le conducteur voit toutes les réservations faites sur ses trajets.
    """
    if not request.user.is_authenticated:
        return redirect("login")

    demandes = Reservation.objects.filter(offre__conducteur=request.user)
    
    return render(request, "backoffice/pages/mes_reservations.html", {
        "demandes": demandes
    })


# --- ACCEPTER UNE RÉSERVATION ---
def reservation_accept(request, id):
    reservation = get_object_or_404(Reservation, id=id)

    # Sécurité : vérifier le propriétaire du trajet
    if reservation.offre.conducteur != request.user:
        return HttpResponseForbidden("Tu n'es pas le conducteur de ce trajet.")

    reservation.statut = "Active"
    reservation.save()

    return redirect('mes_reservations')


# --- REJETER UNE RÉSERVATION ---
def reservation_reject(request, id):
    reservation = get_object_or_404(Reservation, id=id)

    if reservation.offre.conducteur != request.user:
        return HttpResponseForbidden("Tu n'es pas le conducteur de ce trajet.")

    reservation.statut = "Annulée"
    reservation.save()

    return redirect('mes_reservations')

