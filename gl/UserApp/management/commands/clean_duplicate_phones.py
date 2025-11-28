"""
Commande Django pour nettoyer les doublons de numéros de téléphone
Usage: python manage.py clean_duplicate_phones
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from UserApp.models import CustomUser


class Command(BaseCommand):
    help = 'Supprime les doublons de numéros de téléphone en gardant le premier utilisateur (le plus ancien)'

    def handle(self, *args, **options):
        self.stdout.write('Recherche des doublons de numéros de téléphone...')
        
        # Trouver tous les numéros de téléphone en double
        duplicates = CustomUser.objects.values('phone').annotate(
            count=Count('phone')
        ).filter(count__gt=1, phone__isnull=False).exclude(phone='')
        
        total_duplicates = duplicates.count()
        
        if total_duplicates == 0:
            self.stdout.write(self.style.SUCCESS('Aucun doublon trouvé. La base de données est propre.'))
            return
        
        self.stdout.write(f'Nombre de numéros en double trouvés: {total_duplicates}')
        
        total_cleaned = 0
        for duplicate in duplicates:
            phone = duplicate['phone']
            # Récupérer tous les utilisateurs avec ce numéro, triés par date de création
            users = CustomUser.objects.filter(phone=phone).order_by('date_joined')
            
            # Garder le premier (le plus ancien) et vider le phone pour les autres
            if users.count() > 1:
                first_user = users.first()
                self.stdout.write(f'\nNuméro {phone}:')
                self.stdout.write(f'  - Conservé pour: {first_user.username} (ID: {first_user.id}, créé le: {first_user.date_joined})')
                
                for user in users[1:]:
                    user.phone = None
                    user.save()
                    total_cleaned += 1
                    self.stdout.write(f'  - Supprimé pour: {user.username} (ID: {user.id}, créé le: {user.date_joined})')
        
        self.stdout.write(self.style.SUCCESS(f'\nNettoyage terminé! {total_cleaned} utilisateur(s) ont eu leur numéro de téléphone supprimé.'))

