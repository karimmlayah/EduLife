from django.apps import AppConfig


class OffrestageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'offreStage'
    
    def ready(self):
        import offreStage.signals  # Import des signals pour les activer