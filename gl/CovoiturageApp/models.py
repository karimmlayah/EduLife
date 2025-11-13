from django.db import models
from django.contrib.auth.models import User

class Offre(models.Model):
    conducteur = models.ForeignKey(User, on_delete=models.CASCADE)
    depart = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    prix = models.DecimalField(max_digits=6, decimal_places=2)
    nombre_places = models.IntegerField(default=1)
    telephone = models.CharField(max_length=20, blank=True)
    date_covoiturage = models.DateTimeField(null=True, blank=True)
    modele_voiture = models.CharField(max_length=100, blank=True, verbose_name="Modèle de voiture")
    climatisation = models.BooleanField(default=False, verbose_name="Climatisation")
    conducteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trajets")


