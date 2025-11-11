from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
from django.utils import timezone

# Create your models here.
class CustomUser(AbstractUser):
    """
    Modèle utilisateur personnalisé avec support Face ID
    """
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        verbose_name="Email"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Téléphone"
    )
    
    # Face ID / Biometric data
    face_id_enabled = models.BooleanField(
        default=False,
        verbose_name="Face ID activé"
    )
    face_id_credential_id = models.TextField(
        blank=True,
        null=True,
        verbose_name="ID du credential Face ID"
    )
    face_id_public_key = models.TextField(
        blank=True,
        null=True,
        verbose_name="Clé publique Face ID"
    )
    
    # Dates
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Date d'inscription")
    last_login = models.DateTimeField(auto_now=True, verbose_name="Dernière connexion")
    
    # Statut
    is_active = models.BooleanField(default=True, verbose_name="Compte actif")
    is_verified = models.BooleanField(default=False, verbose_name="Email vérifié")
    
    class Roles(models.TextChoices):
        UTILISATEUR = 'UTILISATEUR', 'Utilisateur'
        ADMIN = 'ADMIN', 'Administrateur'
    role = models.CharField(
        max_length=32,
        choices=Roles.choices,
        default=Roles.UTILISATEUR,
        verbose_name="Rôle"
    )
    # Contact & profile info
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ville")
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Pays")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Avatar')
    cover_photo = models.ImageField(upload_to='covers/', blank=True, null=True, verbose_name='Photo de couverture')
    
    # Nouveaux champs de profil
    headline = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Titre professionnel"
    )
    bio = models.TextField(
        blank=True,
        null=True,
        verbose_name="Biographie"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Localisation"
    )
    skills = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Compétences"
    )
    education = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Formation"
    )
    experience = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Expérience"
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de naissance"
    )
    
    # Moderation / Ban
    ban_reason = models.TextField(blank=True, null=True, verbose_name="Raison du bannissement")
    banned_at = models.DateTimeField(blank=True, null=True, verbose_name="Date de bannissement")
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-date_joined']

    def __str__(self):
        return self.email


# Modèles pour les fonctionnalités sociales
class Connection(models.Model):
    """
    Modèle pour les connexions/relations entre utilisateurs
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        ACCEPTED = 'accepted', 'Acceptée'
        REJECTED = 'rejected', 'Refusée'
        BLOCKED = 'blocked', 'Bloquée'
    
    from_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_connections',
        verbose_name="Expéditeur"
    )
    to_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_connections',
        verbose_name="Destinataire"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    
    class Meta:
        verbose_name = "Connexion"
        verbose_name_plural = "Connexions"
        unique_together = ['from_user', 'to_user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"


class Post(models.Model):
    """
    Modèle pour les publications/posts
    """
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name="Auteur"
    )
    content = models.TextField(
        verbose_name="Contenu"
    )
    media = models.FileField(
        upload_to='posts/media/',
        blank=True,
        null=True,
        verbose_name="Média"
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
        verbose_name = "Publication"
        verbose_name_plural = "Publications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Post by {self.author} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Comment(models.Model):
    """
    Modèle pour les commentaires sur les posts
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Publication"
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Auteur"
    )
    text = models.TextField(
        verbose_name="Texte"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    
    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.author} on post {self.post.id}"


class Message(models.Model):
    """
    Modèle pour les messages privés entre utilisateurs
    """
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name="Expéditeur"
    )
    receiver = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_messages',
        verbose_name="Destinataire"
    )
    text = models.TextField(
        verbose_name="Message"
    )
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'envoi"
    )
    read = models.BooleanField(
        default=False,
        verbose_name="Lu"
    )
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"


class Notification(models.Model):
    """
    Modèle pour les notifications utilisateur
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Utilisateur"
    )
    verb = models.CharField(
        max_length=255,
        verbose_name="Action"
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Données supplémentaires"
    )
    read = models.BooleanField(
        default=False,
        verbose_name="Lu"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user}: {self.verb}"
