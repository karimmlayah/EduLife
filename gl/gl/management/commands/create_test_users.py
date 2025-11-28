from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Crée des utilisateurs de test (admin et covoitureur)'

    def handle(self, *args, **options):
        # Créer ou mettre à jour l'utilisateur admin
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utilisateur admin créé avec succès (username: admin, password: admin123)')
            )
        else:
            admin.set_password('admin123')
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utilisateur admin mis à jour (username: admin, password: admin123)')
            )

        # Créer ou mettre à jour l'utilisateur covoitureur
        covoitureur, created = User.objects.get_or_create(
            username='covoitureur',
            defaults={
                'email': 'covoitureur@example.com',
                'is_staff': False,
                'is_superuser': False,
            }
        )
        if created:
            covoitureur.set_password('covoitureur123')
            covoitureur.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utilisateur covoitureur créé avec succès (username: covoitureur, password: covoitureur123)')
            )
        else:
            covoitureur.set_password('covoitureur123')
            covoitureur.is_staff = False
            covoitureur.is_superuser = False
            covoitureur.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utilisateur covoitureur mis à jour (username: covoitureur, password: covoitureur123)')
            )

        # Créer ou mettre à jour un utilisateur passager pour tester
        passager, created = User.objects.get_or_create(
            username='passager',
            defaults={
                'email': 'passager@example.com',
                'is_staff': False,
                'is_superuser': False,
            }
        )
        if created:
            passager.set_password('passager123')
            passager.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utilisateur passager créé avec succès (username: passager, password: passager123)')
            )
        else:
            passager.set_password('passager123')
            passager.is_staff = False
            passager.is_superuser = False
            passager.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utilisateur passager mis à jour (username: passager, password: passager123)')
            )

        self.stdout.write(
            self.style.SUCCESS('\n' + '='*60)
        )
        self.stdout.write(
            self.style.SUCCESS('UTILISATEURS DE TEST CRÉÉS:')
        )
        self.stdout.write(
            self.style.SUCCESS('='*60)
        )
        self.stdout.write(
            self.style.SUCCESS('1. Admin:')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Username: admin')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Password: admin123')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Rôle: Administrateur (peut gérer toutes les offres)')
        )
        self.stdout.write(
            self.style.SUCCESS('\n2. Covoitureur:')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Username: covoitureur')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Password: covoitureur123')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Rôle: Conducteur (peut accepter les réservations sur ses offres)')
        )
        self.stdout.write(
            self.style.SUCCESS('\n3. Passager:')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Username: passager')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Password: passager123')
        )
        self.stdout.write(
            self.style.SUCCESS('   - Rôle: Passager (peut réserver des trajets)')
        )
        self.stdout.write(
            self.style.SUCCESS('='*60 + '\n')
        )

