from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import os
import uuid

User = get_user_model()


def video_upload_to(instance, filename):
    """
    Génère un nom de fichier court pour les vidéos (max 100 caractères)
    Format: logements/videos/{hash}.{ext}
    Le chemin complet sera: logements/videos/ + 8 caractères + . + extension (max 4) = ~25 caractères
    """
    # Obtenir l'extension du fichier (limiter à 4 caractères pour sécurité)
    ext = filename.split('.')[-1].lower()[:4] if '.' in filename else 'mp4'
    
    # Générer un nom de fichier unique et court avec UUID
    # Utiliser seulement les 8 premiers caractères pour garder le nom court
    hash_str = str(uuid.uuid4()).replace('-', '')[:16]
    
    # Format: logements/videos/{hash}.{ext}
    # Le chemin complet sera: logements/videos/ (20) + 16 (hash) + 1 (.) + 4 (ext) = 41 caractères max
    filename = f"{hash_str}.{ext}"
    
    return os.path.join('logements', 'videos', filename)

# Create your models here.
class Logement(models.Model):
    """
    Modèle pour les logements
    """
    TYPE_CHOICES = [
        ('APPARTEMENT', 'Appartement'),
        ('MAISON', 'Maison'),
        ('STUDIO', 'Studio'),
        ('VILLA', 'Villa'),
        ('AUTRE', 'Autre'),
    ]
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='logements',
        verbose_name="Propriétaire"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titre"
    )
    description = models.TextField(
        verbose_name="Description"
    )
    type_logement = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='APPARTEMENT',
        verbose_name="Type de logement"
    )
    address = models.CharField(
        max_length=255,
        verbose_name="Adresse"
    )
    city = models.CharField(
        max_length=100,
        verbose_name="Ville"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix"
    )
    surface = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Surface (m²)"
    )
    rooms = models.IntegerField(
        verbose_name="Nombre de pièces"
    )
    bathrooms = models.IntegerField(
        default=1,
        verbose_name="Nombre de salles de bain"
    )
    image = models.ImageField(
        upload_to='logements/',
        blank=True,
        null=True,
        verbose_name="Image principale"
    )
    model_3d = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Modèle 3D (URL optionnelle)",
        help_text="Lien vers un modèle 3D (ex: Sketchfab, etc.)"
    )
    wifi = models.BooleanField(
        default=False,
        verbose_name="WiFi disponible"
    )
    video = models.FileField(
        upload_to=video_upload_to,
        blank=True,
        null=True,
        max_length=100,
        verbose_name="Vidéo (fichier optionnel)",
        help_text="Fichier vidéo (MP4, WebM, OGG, etc.)"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Latitude",
        help_text="Coordonnée GPS (sera remplie automatiquement depuis la carte)"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Longitude",
        help_text="Coordonnée GPS (sera remplie automatiquement depuis la carte)"
    )
    available = models.BooleanField(
        default=True,
        verbose_name="Disponible"
    )
    approved = models.BooleanField(
        default=False,
        verbose_name="Approuvé"
    )
    rejected = models.BooleanField(
        default=False,
        verbose_name="Rejeté"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification"
    )
    
    class Meta:
        verbose_name = "Logement"
        verbose_name_plural = "Logements"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.city}"


class TemporaryImage(models.Model):
    """
    Modèle pour stocker temporairement les images pendant la création avec IA
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='temporary_images',
        verbose_name="Utilisateur"
    )
    image = models.ImageField(
        upload_to='logements/temp/',
        verbose_name="Image temporaire"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    
    class Meta:
        verbose_name = "Image temporaire"
        verbose_name_plural = "Images temporaires"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Image temporaire de {self.user.username}"


class LogementImage(models.Model):
    """
    Modèle pour gérer plusieurs images par logement
    """
    logement = models.ForeignKey(
        Logement,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Logement"
    )
    image = models.ImageField(
        upload_to='logements/images/',
        verbose_name="Image"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    
    class Meta:
        verbose_name = "Image de logement"
        verbose_name_plural = "Images de logement"
        ordering = ['created_at']
    
    def __str__(self):
        return f"Image pour {self.logement.title}"


class BinomeRequest(models.Model):
    """
    Modèle pour les demandes de recherche de binômes (colocataires)
    """
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('ACCEPTED', 'Accepté'),
        ('REJECTED', 'Rejeté'),
        ('COMPLETED', 'Complété'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='binome_requests',
        verbose_name="Utilisateur"
    )
    logement = models.ForeignKey(
        Logement,
        on_delete=models.CASCADE,
        related_name='binome_requests',
        verbose_name="Logement",
        blank=True,
        null=True,
        help_text="Logement spécifique (optionnel)"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titre de la recherche"
    )
    description = models.TextField(
        verbose_name="Description",
        help_text="Décrivez ce que vous cherchez (budget, préférences, etc.)"
    )
    city = models.CharField(
        max_length=100,
        verbose_name="Ville recherchée"
    )
    budget_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Budget maximum (DT)",
        help_text="Budget maximum par mois"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Statut"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification"
    )
    
    class Meta:
        verbose_name = "Demande de binôme"
        verbose_name_plural = "Demandes de binômes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recherche binôme - {self.user.username} - {self.city}"
