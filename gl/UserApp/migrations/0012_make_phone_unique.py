# Generated migration to make phone unique and remove duplicates

from django.db import migrations, models
from django.db.models import Count


def remove_duplicate_phones(apps, schema_editor):
    """
    Supprime les doublons de numéros de téléphone
    Garde le premier utilisateur (le plus ancien) et vide le champ phone pour les autres
    """
    CustomUser = apps.get_model('UserApp', 'CustomUser')
    
    # Trouver tous les numéros de téléphone en double
    duplicates = CustomUser.objects.values('phone').annotate(
        count=Count('phone')
    ).filter(count__gt=1, phone__isnull=False).exclude(phone='')
    
    for duplicate in duplicates:
        phone = duplicate['phone']
        # Récupérer tous les utilisateurs avec ce numéro, triés par date de création
        users = CustomUser.objects.filter(phone=phone).order_by('date_joined')
        
        # Garder le premier (le plus ancien) et vider le phone pour les autres
        if users.count() > 1:
            first_user = users.first()
            for user in users[1:]:
                user.phone = None
                user.save()
                print(f'Numéro de téléphone {phone} supprimé pour l\'utilisateur {user.username} (ID: {user.id})')


def reverse_remove_duplicates(apps, schema_editor):
    """
    Fonction de rollback - ne fait rien car on ne peut pas restaurer les doublons
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('UserApp', '0011_like'),  # Dernière migration
    ]

    operations = [
        # Étape 1: Supprimer les doublons
        migrations.RunPython(remove_duplicate_phones, reverse_remove_duplicates),
        
        # Étape 2: Ajouter la contrainte unique
        migrations.AlterField(
            model_name='customuser',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='Téléphone'),
        ),
    ]

