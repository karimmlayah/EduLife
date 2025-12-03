from django.core.management.base import BaseCommand
from offreStage.signals import envoyer_emails_aux_postulants


class Command(BaseCommand):
    help = 'Envoie des emails à tous les étudiants qui ont postulé au moins une fois'

    def handle(self, *args, **options):
        self.stdout.write('Envoi des emails aux étudiants qui ont postulé...')
        envoyer_emails_aux_postulants()
        self.stdout.write(self.style.SUCCESS('Envoi terminé !'))

