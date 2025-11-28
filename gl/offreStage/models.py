from django.db import models
from django.utils import timezone

class OffreStage(models.Model):
    id_offre = models.AutoField(primary_key=True)
    titre = models.CharField(max_length=100)
    description = models.TextField()
    domaine = models.CharField(max_length=100)
    lieu = models.CharField(max_length=100)
    remuneration = models.DecimalField(max_digits=10, decimal_places=2)
    etat = models.CharField(max_length=50, default='disponible')
    duree = models.IntegerField(help_text="Durée en semaines ou en mois")
    visibilite = models.BooleanField(default=True)
    
    # 🖼️ Image du stage (nouvel attribut)
    image = models.ImageField(upload_to='offres_images/', null=True, blank=True)
    
    # 📅 Date de publication pour le filtrage par mois
    date_publication = models.DateField(default=timezone.now, verbose_name="Date de publication")

    def __str__(self):
        return self.titre

