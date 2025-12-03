"""
Backend email personnalisé pour contourner les problèmes SSL en développement
"""
import smtplib
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
import ssl


class CustomEmailBackend(SMTPBackend):
    """
    Backend email personnalisé qui ignore les erreurs SSL en développement
    """
    def open(self):
        """
        Crée une connexion SMTP en ignorant les erreurs SSL
        """
        if self.connection:
            return False
        
        try:
            self.connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            if self.use_tls:
                # Créer un contexte SSL qui ignore les erreurs de certificat
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.connection.starttls(context=context)
            if self.username and self.password:
                # Essayer d'abord avec le mot de passe tel quel (avec espaces)
                try:
                    self.connection.login(self.username, self.password)
                except smtplib.SMTPAuthenticationError:
                    # Si échec, essayer sans espaces
                    password_sans_espaces = self.password.replace(' ', '')
                    self.connection.login(self.username, password_sans_espaces)
            return True
        except Exception as e:
            if not self.fail_silently:
                raise e

