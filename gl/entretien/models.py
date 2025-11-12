from django.db import models
from django.core.exceptions import ValidationError


class Entretien(models.Model):
    STATUT_CHOICES = [
        ('planifie', 'Planifié'),
        ('effectue', 'Effectué'),
        ('annule', 'Annulé'),
    ]
    
    id_entretien = models.AutoField(primary_key=True)
    
    # Relation avec Postulation (OneToOne pour garantir 0 ou 1 entretien par postulation)
    postulation = models.OneToOneField(
        'postulation.Postulation',
        on_delete=models.CASCADE,
        related_name='entretien',
        verbose_name="Postulation"
    )
    
    # Date et heure de l'entretien
    date_entretien = models.DateTimeField(verbose_name="Date et heure de l'entretien")
    
    # Lien de visioconférence (Zoom, Teams, Google Meet, etc.)
    lien_meet = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Lien de visioconférence",
        help_text="Lien Zoom, Teams, Google Meet, etc."
    )
    
    # Commentaire ou notes sur l'entretien
    commentaire = models.TextField(
        null=True,
        blank=True,
        verbose_name="Commentaire",
        help_text="Notes ou commentaires sur l'entretien"
    )
    
    # Statut de l'entretien
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='planifie',
        verbose_name="Statut"
    )
    
    # Date de création
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    class Meta:
        verbose_name = "Entretien"
        verbose_name_plural = "Entretiens"
        ordering = ['-date_entretien']
    
    def clean(self):
        """Valide que l'entretien ne peut être créé que pour une postulation acceptée"""
        if self.postulation and hasattr(self.postulation, 'statut') and self.postulation.statut != 'acceptee':
            raise ValidationError({
                'postulation': 'Un entretien ne peut être planifié que pour une postulation acceptée.'
            })
        super().clean()
    
    def save(self, *args, **kwargs):
        """Valide avant la sauvegarde"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Entretien pour {self.postulation} - {self.date_entretien.strftime('%d/%m/%Y %H:%M')}"

