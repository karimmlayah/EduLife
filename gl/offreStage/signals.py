from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import OffreStage
from postulation.models import Postulation
from UserApp.models import CustomUser


def envoyer_emails_aux_postulants():
    """
    Fonction utilitaire pour envoyer des emails à tous les étudiants qui ont postulé.
    Peut être appelée manuellement ou via une commande Django.
    """
    # Récupérer tous les emails uniques des étudiants qui ont postulé au moins une fois
    emails_postulants = Postulation.objects.values_list('email', flat=True).distinct()
    
    if not emails_postulants:
        print("Aucun étudiant n'a postulé jusqu'à présent.")
        return
    
    # Trouver les utilisateurs (étudiants) correspondants à ces emails
    etudiants = CustomUser.objects.filter(
        email__in=emails_postulants,
        is_active=True  # Seulement les comptes actifs
    )
    
    # Liste des emails qui ont un compte CustomUser
    emails_avec_compte = list(etudiants.values_list('email', flat=True))
    
    # Envoyer un email à chaque étudiant qui a un compte
    for etudiant in etudiants:
        try:
            # Utiliser le prénom ou le nom d'utilisateur comme nom
            nom_etudiant = etudiant.first_name or etudiant.username
            
            # Rendre le template HTML
            html_message = render_to_string('emails/nouvelle_offre_stage.html', {
                'nom_etudiant': nom_etudiant,
                'site_url': 'http://127.0.0.1:8000'  # URL du site (à modifier en production)
            })
            
            # Message texte simple pour les clients email qui ne supportent pas HTML
            message_texte = f'Bonjour {nom_etudiant},\n\n' \
                          f'De nouvelles offres de stage sont disponibles sur notre site.\n' \
                          f'Visitez le site pour découvrir les nouvelles opportunités.\n\n' \
                          f'Cordialement,\nL\'équipe EduLife'
            
            send_mail(
                subject='Nouvelles offres de stage disponibles - EduLife',
                message=message_texte,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[etudiant.email],
                fail_silently=False,
            )
            print(f"✅ Email envoyé avec succès à {etudiant.email}")
        except Exception as e:
            # Logger l'erreur si nécessaire
            print(f"❌ Erreur lors de l'envoi de l'email à {etudiant.email}: {e}")
    
    # Envoyer aussi aux emails qui ont postulé mais n'ont pas de compte CustomUser
    emails_sans_compte = [email for email in emails_postulants if email not in emails_avec_compte]
    
    for email in emails_sans_compte:
        try:
            # Extraire le nom de l'email (partie avant @)
            nom_etudiant = email.split('@')[0]
            
            # Rendre le template HTML
            html_message = render_to_string('emails/nouvelle_offre_stage.html', {
                'nom_etudiant': nom_etudiant,
                'site_url': 'http://127.0.0.1:8000'  # URL du site (à modifier en production)
            })
            
            # Message texte simple pour les clients email qui ne supportent pas HTML
            message_texte = f'Bonjour {nom_etudiant},\n\n' \
                          f'De nouvelles offres de stage sont disponibles sur notre site.\n' \
                          f'Visitez le site pour découvrir les nouvelles opportunités.\n\n' \
                          f'Cordialement,\nL\'équipe EduLife'
            
            send_mail(
                subject='Nouvelles offres de stage disponibles - EduLife',
                message=message_texte,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            print(f"✅ Email envoyé avec succès à {email} (sans compte)")
        except Exception as e:
            # Logger l'erreur si nécessaire
            print(f"❌ Erreur lors de l'envoi de l'email à {email}: {e}")


@receiver(post_save, sender=OffreStage)
def envoyer_email_nouvelle_offre(sender, instance, created, **kwargs):
    """
    Envoie un email aux étudiants qui ont déjà postulé au moins une fois
    quand une nouvelle offre de stage est créée par l'admin.
    """
    # Ne faire l'envoi que si c'est une nouvelle offre (created=True)
    if not created:
        return
    
    # Utiliser la fonction utilitaire pour envoyer les emails
    envoyer_emails_aux_postulants()

