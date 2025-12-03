from django.db import models
from django.utils import timezone
from django.conf import settings

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


class Favori(models.Model):
    """Modèle pour sauvegarder les offres favorites des utilisateurs"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favoris',
        verbose_name="Utilisateur"
    )
    offre = models.ForeignKey(
        OffreStage,
        on_delete=models.CASCADE,
        related_name='favoris',
        verbose_name="Offre"
    )
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")
    
    class Meta:
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        unique_together = ('user', 'offre')  # Un utilisateur ne peut ajouter une offre qu'une seule fois
        ordering = ['-date_ajout']
    
    def __str__(self):
        return f"{self.user.email} - {self.offre.titre}"


class CVData(models.Model):
    """Modèle pour stocker les données CV d'un utilisateur"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cv_data',
        verbose_name="Utilisateur"
    )
    
    # Informations personnelles
    full_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nom complet")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Adresse")
    linkedin = models.URLField(blank=True, null=True, verbose_name="LinkedIn")
    github = models.URLField(blank=True, null=True, verbose_name="GitHub")
    website = models.URLField(blank=True, null=True, verbose_name="Site web")
    
    # Profil professionnel
    professional_summary = models.TextField(blank=True, null=True, verbose_name="Résumé professionnel")
    
    # Compétences (stockées en JSON)
    skills = models.JSONField(default=list, blank=True, verbose_name="Compétences")
    
    # Formations (stockées en JSON: [{"degree": "...", "school": "...", "year": "...", "description": "..."}])
    education = models.JSONField(default=list, blank=True, verbose_name="Formations")
    
    # Expériences (stockées en JSON: [{"title": "...", "company": "...", "start_date": "...", "end_date": "...", "description": "..."}])
    experience = models.JSONField(default=list, blank=True, verbose_name="Expériences")
    
    # Projets (optionnel)
    projects = models.JSONField(default=list, blank=True, verbose_name="Projets")
    
    # Langues (optionnel)
    languages = models.JSONField(default=list, blank=True, verbose_name="Langues")
    
    # Certifications (optionnel)
    certifications = models.JSONField(default=list, blank=True, verbose_name="Certifications")
    
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")
    
    class Meta:
        verbose_name = "Données CV"
        verbose_name_plural = "Données CV"
        ordering = ['-date_updated']
    
    def __str__(self):
        return f"CV de {self.user.email}"
