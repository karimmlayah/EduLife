from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Startup(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('funded', 'Funded'),
        ('failed', 'Failed'),
        ('closed', 'Closed'),
    ]

    id_startup = models.AutoField(primary_key=True)
    nom_startup = models.CharField(max_length=100)
    date_creation = models.DateField()
    description = models.TextField()
    fond_desire = models.FloatField()
    fond_actuel = models.FloatField(default=0)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    category = models.CharField(max_length=100, null=True, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    founder = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.nom_startup

    class Meta:
        db_table = 'Startup'