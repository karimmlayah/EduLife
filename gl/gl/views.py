from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from django.conf import settings
from CovoiturageApp.models import Offre
from ReservationApp.models import Reservation


# ============================================
# FONCTION HELPER POUR UTILISATEUR STATIQUE
# ============================================
def get_static_user():
    """
    Retourne l'utilisateur statique configuré dans settings.STATIC_USER_ID
    Si l'utilisateur n'existe pas, retourne le premier utilisateur disponible
    """
    static_user_id = getattr(settings, 'STATIC_USER_ID', 1)
    try:
        return User.objects.get(id=static_user_id)
    except User.DoesNotExist:
        # Si l'utilisateur avec cet ID n'existe pas, retourner le premier disponible
        user = User.objects.first()
        if not user:
            # Créer un utilisateur par défaut si aucun n'existe
            user = User.objects.create_user(
                username='static_user',
                email='static@example.com',
                password='static123'
            )
        return user


# --- DASHBOARD PRINCIPAL ---
def dashboard(request):
    from django.db.models import Count, Sum, Avg
    from django.utils import timezone
    from datetime import timedelta
    
    offres = Offre.objects.all()
    reservations = Reservation.objects.all()
    
    # Statistiques générales
    total_offres = offres.count()
    total_reservations = reservations.count()
    reservations_acceptees = reservations.filter(statut='accepted').count()
    reservations_en_attente = reservations.filter(statut='pending').count()
    
    # Calculer le revenu total (somme des prix des offres avec réservations acceptées)
    revenu_total = 0
    for reservation in reservations.filter(statut='accepted'):
        revenu_total += float(reservation.offre.prix) * reservation.nombre_places_reservees
    
    # Offres récentes (7 derniers jours)
    date_limite = timezone.now() - timedelta(days=7)
    offres_recentes = offres.filter(date_covoiturage__gte=date_limite).count()
    
    # Statistiques par statut
    reservations_acceptees_pct = (reservations_acceptees / total_reservations * 100) if total_reservations > 0 else 0
    
    # Top 5 offres les plus réservées
    from django.db.models import Q
    top_offres = offres.annotate(
        nb_reservations=Count('reservations', filter=Q(reservations__statut__in=['pending', 'accepted']))
    ).order_by('-nb_reservations')[:5]
    
    # Offres en attente d'approbation
    offres_en_attente = offres.filter(approuve=False).order_by('-id')[:10]
    
    # Réservations par jour (7 derniers jours)
    reservations_par_jour = []
    for i in range(6, -1, -1):
        date = timezone.now() - timedelta(days=i)
        count = reservations.filter(date_reservation__date=date.date()).count()
        reservations_par_jour.append({
            'date': date.strftime('%d/%m'),
            'count': count
        })
    
    context = {
        "offres": offres,
        "total_offres": total_offres,
        "total_reservations": total_reservations,
        "reservations_acceptees": reservations_acceptees,
        "reservations_en_attente": reservations_en_attente,
        "revenu_total": round(revenu_total, 2),
        "offres_recentes": offres_recentes,
        "reservations_acceptees_pct": round(reservations_acceptees_pct, 1),
        "top_offres": top_offres,
        "reservations_par_jour": reservations_par_jour,
        "offres_en_attente": offres_en_attente,
    }
    
    return render(request, "covoiturage/Backoffice/pages/dashboard.html", context)


# --- DASHBOARD DES RÉSERVATIONS ---
def reservation_dashboard(request):
    return render(request, "covoiturage/Backoffice/pages/reservation_dashboard.html")


# --- MES RÉSERVATIONS (POUR LE CONDUCTEUR) ---
def mes_reservations(request):
    """
    Le conducteur voit toutes les réservations faites sur ses trajets.
    Filtre uniquement les réservations sur les offres du conducteur connecté.
    Utilise l'utilisateur statique si non authentifié.
    """
    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()
    
    # Filtrer uniquement les réservations sur les offres du conducteur
    # Trier par date de réservation (plus récentes en premier)
    demandes = Reservation.objects.filter(
        offre__conducteur=user
    ).order_by('-date_reservation')
    
    return render(request, "covoiturage/Fontoffice/mes_reservations.html", {
        "demandes": demandes
    })


# --- ACCEPTER UNE RÉSERVATION ---
def reservation_accept(request, id):
    reservation = get_object_or_404(Reservation, id=id)

    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()

    # Sécurité : vérifier le propriétaire du trajet
    if reservation.offre.conducteur != user:
        return HttpResponseForbidden("Tu n'es pas le conducteur de ce trajet.")

    reservation.statut = "accepted"
    reservation.save()

    return redirect('mes_reservations')


# --- REJETER UNE RÉSERVATION ---
def reservation_reject(request, id):
    reservation = get_object_or_404(Reservation, id=id)

    # Utiliser l'utilisateur connecté ou l'utilisateur statique
    if request.user.is_authenticated:
        user = request.user
    else:
        user = get_static_user()

    if reservation.offre.conducteur != user:
        return HttpResponseForbidden("Tu n'es pas le conducteur de ce trajet.")

    reservation.statut = "rejected"
    reservation.save()

    return redirect('mes_reservations')


# --- VUE DE CONNEXION PERSONNALISÉE ---
class CustomLoginView(LoginView):
    template_name = 'covoiturage/Fontoffice/login.html'
    redirect_authenticated_user = True
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Ajouter des attributs aux champs du formulaire
        form.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Entrez votre email ou nom d\'utilisateur',
            'autofocus': True
        })
        form.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Entrez votre mot de passe'
        })
        return form


# --- VUE DE DÉCONNEXION PERSONNALISÉE ---
class CustomLogoutView(LogoutView):
    next_page = '/'


# --- APPROUVER UNE OFFRE ---
def approver_offre(request, id):
    """
    Approuver une offre de covoiturage.
    Met approuve à True et redirige vers la page appropriée.
    """
    try:
        # Récupérer l'offre
        offre = get_object_or_404(Offre, id=id)
        
        # Mettre à jour le statut d'approbation
        offre.approuve = True
        offre.save(update_fields=['approuve'])
        
        # Message de succès
        messages.success(request, f"L'offre de {offre.depart} → {offre.destination} a été approuvée.")
        
        # Rediriger vers la page d'origine ou la liste des offres
        referer = request.META.get('HTTP_REFERER', '')
        if 'dashboard/covoiturage' in referer:
            return redirect('dashboard_covoiturage')
        elif 'offres/covoiturage' in referer or 'offres_list' in referer:
            return redirect('offres_list')
        # Par défaut, rediriger vers le dashboard covoiturage
        return redirect('dashboard_covoiturage')
        
    except Exception as e:
        # Gérer les erreurs
        messages.error(request, f"Une erreur s'est produite lors de l'approbation de l'offre : {str(e)}")
        # Rediriger vers le dashboard en cas d'erreur
        return redirect('dashboard_covoiturage')


# --- ANNULER L'APPROBATION D'UNE OFFRE ---
def annuler_approbation(request, id):
    """
    Annuler l'approbation d'une offre de covoiturage.
    Remet approuve à False et redirige vers la page appropriée.
    """
    try:
        # Récupérer l'offre
        offre = get_object_or_404(Offre, id=id)
        
        # Mettre à jour le statut d'approbation
        offre.approuve = False
        offre.save(update_fields=['approuve'])
        
        # Message de succès
        messages.warning(request, f"L'approbation de l'offre {offre.depart} → {offre.destination} a été annulée. L'offre est maintenant en attente.")
        
        # Rediriger vers la page d'origine ou la liste des offres
        referer = request.META.get('HTTP_REFERER', '')
        if 'dashboard/covoiturage' in referer:
            return redirect('dashboard_covoiturage')
        elif 'offres/covoiturage' in referer or 'offres_list' in referer:
            return redirect('offres_list')
        # Par défaut, rediriger vers la liste des offres
        return redirect('offres_list')
        
    except Exception as e:
        # Gérer les erreurs
        messages.error(request, f"Une erreur s'est produite lors de l'annulation de l'approbation : {str(e)}")
        # Rediriger vers la liste des offres en cas d'erreur
        return redirect('offres_list')


# --- REJETER UNE OFFRE ---
def rejeter_offre(request, id):
    """
    Rejeter et supprimer une offre de covoiturage.
    Supprime l'offre du tableau après rejet.
    """
    try:
        # Récupérer l'offre
        offre = get_object_or_404(Offre, id=id)
        
        # Sauvegarder les informations pour le message
        depart = offre.depart
        destination = offre.destination
        
        # Supprimer l'offre
        offre.delete()
        
        # Message de succès
        messages.success(request, f"L'offre de {depart} → {destination} a été rejetée et supprimée.")
        
        # Rediriger vers la page d'origine ou la liste des offres
        referer = request.META.get('HTTP_REFERER', '')
        if 'dashboard/covoiturage' in referer:
            return redirect('dashboard_covoiturage')
        elif 'offres/covoiturage' in referer or 'offres_list' in referer:
            return redirect('offres_list')
        # Par défaut, rediriger vers le dashboard covoiturage
        return redirect('dashboard_covoiturage')
        
    except Exception as e:
        # Gérer les erreurs
        messages.error(request, f"Une erreur s'est produite lors du rejet de l'offre : {str(e)}")
        # Rediriger vers le dashboard en cas d'erreur
        return redirect('dashboard_covoiturage')

