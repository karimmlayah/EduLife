from django.apps import AppConfig


class EventappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "EventApp"
    def ready(self):
        import EventApp.signals
