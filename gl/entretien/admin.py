from django.contrib import admin
from .models import Entretien

@admin.register(Entretien)
class EntretienAdmin(admin.ModelAdmin):
    list_display = ('id_entretien', 'postulation', 'date_entretien', 'statut', 'created_at')
    list_filter = ('statut', 'date_entretien')
    search_fields = ('postulation__id_postulation', 'commentaire')
    date_hierarchy = 'date_entretien'

