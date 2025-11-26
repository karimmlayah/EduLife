from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, datetime
import uuid

class Event(models.Model):
    CATEGORY_CHOICES = [
        ('conference', 'Conférence'),
        ('workshop', 'Atelier'),
        ('concert', 'Concert'),
        ('festival', 'Festival'),
        ('autre', 'Autre'),
    ]

    name = models.CharField(max_length=200, verbose_name="Nom de l'événement")
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        verbose_name="Catégorie"
    )
    price = models.FloatField(
        verbose_name="Prix (en DT)"
    )
    description = models.TextField(verbose_name="Description", blank=True)
    date = models.DateField(verbose_name="Date de l'événement")
    location = models.CharField(max_length=200, verbose_name="Lieu")
    photo_url = models.CharField(max_length=10000, null=True, blank=True, verbose_name="Photo (URL ou Data URI)")

    total_seats = models.PositiveIntegerField(verbose_name="Places totales")
    reserved_seats = models.PositiveIntegerField(default=0, verbose_name="Places réservées")

    id_user = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    @property
    def formatted_date_for_countdown(self):
        """Retourne la date formatée pour le JavaScript du compte à rebours"""
        if self.date:
            return self.date.strftime('%Y/%m/%d 09:00:00')  # Vous pouvez ajuster l'heure
        return None

    # AJOUT: Vérifier si l'événement est à venir
    @property
    def formatted_date_for_countdown(self):
        """Retourne la date formatée pour le JavaScript du compte à rebours"""
        if self.date:
            # Combine la date avec une heure fixe (ex: 09:00:00)
            datetime_obj = datetime.combine(self.date, datetime.min.time().replace(hour=9))
            return datetime_obj.strftime('%Y/%m/%d %H:%M:%S')
        return None

    # AJOUT: Format de date simple pour l'affichage
    @property
    def formatted_date_display(self):
        """Retourne la date formatée pour l'affichage"""
        if self.date:
            return self.date.strftime('%d %B %Y')
        return "Date non définie"

    # AJOUT: Vérifier si l'événement est à venir
    @property
    def is_upcoming(self):
        return self.date >= date.today()

    def __str__(self):
        return f"{self.name} ({self.date.strftime('%d/%m/%Y')})"

    def clean(self):
        """Validation des données du modèle"""
        if self.date and self.date < date.today():
            raise ValidationError({"date": "La date de l'événement doit être dans le futur."})
        
        # Validation personnalisée pour photo_url
        if self.photo_url:
            # Accepter les URLs normales et les data URIs
            if (not self.photo_url.startswith('http://') and 
                not self.photo_url.startswith('https://') and 
                not self.photo_url.startswith('data:image/')):
                raise ValidationError({"photo_url": "L'URL doit être une URL valide (http://, https://) ou une image encodée (data:image/)."})
class Meta:
    ordering = ['date']  # AJOUT: Trier par date par défaut

class Seat(models.Model):

    class Status(models.TextChoices):
        AVAILABLE = "available", "Libre"
        RESERVED = "reserved", "Réservée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event = models.ForeignKey(
        'Event',
        on_delete=models.CASCADE,
        related_name='seats'
    )

    number = models.PositiveIntegerField()  # chaise 1, 2, 3...

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.AVAILABLE
    )
    id_user = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
    )
    def __str__(self):
        return f"Seat {self.number} — {self.get_status_display()}"