from django.db import models
from django.contrib.auth.models import User
from gl.CovoiturageApp.models import Offre

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
