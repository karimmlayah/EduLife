from django.contrib import admin
from .models import Logement, LogementImage, BinomeRequest


class LogementImageInline(admin.TabularInline):
    """Inline pour afficher les images dans l'admin du logement"""
    model = LogementImage
    extra = 1


@admin.register(Logement)
class LogementAdmin(admin.ModelAdmin):
    """Admin pour le modèle Logement"""
    list_display = ['title', 'city', 'price', 'owner', 'approved', 'available', 'created_at']
    list_filter = ['approved', 'available', 'type_logement', 'city', 'created_at']
    search_fields = ['title', 'description', 'address', 'city', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [LogementImageInline]
    fieldsets = (
        ('Informations générales', {
            'fields': ('owner', 'title', 'description', 'type_logement')
        }),
        ('Localisation', {
            'fields': ('address', 'city')
        }),
        ('Caractéristiques', {
            'fields': ('price', 'surface', 'rooms', 'bathrooms')
        }),
        ('Médias', {
            'fields': ('image', 'video', 'model_3d')
        }),
        ('Statut', {
            'fields': ('available', 'approved')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LogementImage)
class LogementImageAdmin(admin.ModelAdmin):
    """Admin pour le modèle LogementImage"""
    list_display = ['logement', 'image', 'created_at']
    list_filter = ['created_at']
    search_fields = ['logement__title']
    readonly_fields = ['created_at']


@admin.register(BinomeRequest)
class BinomeRequestAdmin(admin.ModelAdmin):
    """Admin pour le modèle BinomeRequest"""
    list_display = ['title', 'user', 'city', 'budget_max', 'status', 'created_at']
    list_filter = ['status', 'city', 'created_at']
    search_fields = ['title', 'description', 'city', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'title', 'description')
        }),
        ('Recherche', {
            'fields': ('city', 'budget_max', 'logement')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
