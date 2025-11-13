from django.db import models

class Postulation(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'),
    ]
    
    id_postulation = models.AutoField(primary_key=True)
    date_postulation = models.DateField(auto_now_add=True)
    email = models.EmailField(verbose_name="Email")
    cv = models.FileField(upload_to='cv/', null=True, blank=True)
    lettre_motivation = models.TextField()
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="Statut"
    )

    # 🔗 Relation avec l'application offreStage (référence par chaîne)
    offre = models.ForeignKey(
        'offreStage.OffreStage',   # nom_app.NomClasse
        on_delete=models.CASCADE,
        related_name='postulations'
    )

    def save(self, *args, **kwargs):
        # Sauvegarder la postulation
        super().save(*args, **kwargs)
        
        # Vérifier le nombre de postulations pour cette offre
        nombre_postulations = Postulation.objects.filter(offre=self.offre).count()
        
        # Si le nombre de postulations atteint 3, changer l'état de l'offre à "indisponible"
        if nombre_postulations >= 3:
            self.offre.etat = 'indisponible'
            self.offre.save(update_fields=['etat'])
    
    def delete(self, *args, **kwargs):
        # Sauvegarder la référence à l'offre avant la suppression
        offre = self.offre
        
        # Supprimer la postulation
        super().delete(*args, **kwargs)
        
        # Vérifier le nombre de postulations restantes pour cette offre
        nombre_postulations = Postulation.objects.filter(offre=offre).count()
        
        # Si le nombre de postulations passe en dessous de 3, remettre l'état à "disponible"
        if nombre_postulations < 3:
            offre.etat = 'disponible'
            offre.save(update_fields=['etat'])
    
    def __str__(self):
        return f"Postulation #{self.id_postulation} pour {self.offre.titre}"

