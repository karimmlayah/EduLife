from django.db import models
from django.contrib.auth.models import User
from Startup.models import Startup
from django.conf import settings


class Investissement(models.Model):
    id_invest = models.AutoField(primary_key=True)

    startup = models.ForeignKey(
        Startup,
        on_delete=models.CASCADE,
        related_name='investissements'
    )

    investor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,null=True,blank=True)

    montant = models.FloatField()
    date = models.DateField()
    commentaire = models.CharField(max_length=255, blank=True, null=True)

    statut = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )

    class Meta:
        db_table = 'investissement'

    def __str__(self):
        return f"{self.startup.nom_startup} — {self.montant} DT"

    # ⭐ CORRECT save() implementation
    def save(self, *args, **kwargs):

        # Check old status before saving
        if self.pk:
            old_status = Investissement.objects.filter(pk=self.pk).values_list("statut", flat=True).first()
        else:
            old_status = None

        print("DEBUG | OLD STATUS:", old_status, "| NEW STATUS:", self.statut)

        super().save(*args, **kwargs)

        # Apply funds only when pending → accepted
        if old_status == "pending" and self.statut == "accepted":
            startup = self.startup
            print(f"DEBUG | Adding funds: {startup.fond_actuel} + {self.montant}")

            startup.fond_actuel = (startup.fond_actuel or 0) + self.montant
            startup.save(update_fields=['fond_actuel'])

            print("DEBUG | New startup funds:", startup.fond_actuel)
