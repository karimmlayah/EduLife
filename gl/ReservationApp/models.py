from django.db import models
from django.contrib.auth.models import User
from gl.CovoiturageApp.models import Offre
from django.core.validators import MinValueValidator, MaxValueValidator

class Reservation(models.Model):

    STATUT = [
        ("pending", "En attente"),
        ("accepted", "Acceptée"),
        ("rejected", "Rejetée"),
        ("cancelled", "Annulée par le passager"),
    ]

    offre = models.ForeignKey(Offre, on_delete=models.CASCADE, related_name="reservations")
    passager = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reservations")

    # 🔥 NOUVEAUX CHAMPS
    nom_passager = models.CharField(max_length=100)
    telephone_passager = models.CharField(max_length=20)

    date_reservation = models.DateTimeField(auto_now_add=True)
    nombre_places_reservees = models.IntegerField(default=1)
    statut = models.CharField(max_length=20, choices=STATUT, default="pending")

    def __str__(self):
        return f"{self.nom_passager} ({self.passager.username}) - {self.offre} - {self.statut}"

    @staticmethod
    def get_places_disponibles(offre):
        reservations_valides = Reservation.objects.filter(
            offre=offre,
            statut__in=["pending", "accepted"]
        )
        total_reserve = sum(r.nombre_places_reservees for r in reservations_valides)
        return offre.nombre_places - total_reserve


class Avis(models.Model):
    """Modèle pour les avis et commentaires sur les trajets"""
    
    reservation = models.OneToOneField(
        Reservation, 
        on_delete=models.CASCADE, 
        related_name="avis",
        verbose_name="Réservation"
    )
    note = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Note (étoiles)",
        help_text="Note de 1 à 5 étoiles"
    )
    commentaire = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name="Commentaire"
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Avis de {self.reservation.passager.username} - {self.note}/5 étoiles"
    
    def get_etoiles_pleines(self):
        """Retourne le nombre d'étoiles pleines"""
        return self.note
    
    def get_etoiles_vides(self):
        """Retourne le nombre d'étoiles vides"""
        return 5 - self.note
