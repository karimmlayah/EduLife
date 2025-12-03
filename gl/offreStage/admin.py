from django.contrib import admin
from .models import OffreStage


@admin.register(OffreStage)
class OffreStageAdmin(admin.ModelAdmin):
    list_display = ('titre', 'domaine', 'lieu', 'etat', 'date_publication')
    list_filter = ('etat', 'domaine', 'date_publication')
    search_fields = ('titre', 'description', 'domaine')
    date_hierarchy = 'date_publication'
