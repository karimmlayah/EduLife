from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Connection, Post, Comment, Message, Notification

# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'phone', 'role', 'face_id_enabled', 'is_active', 'is_verified', 'date_joined')
    list_filter = ('is_active', 'is_verified', 'face_id_enabled', 'role', 'date_joined')
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('phone', 'role', 'face_id_enabled', 'face_id_credential_id', 'face_id_public_key', 'is_verified')
        }),
        ('Profil', {
            'fields': ('avatar', 'headline', 'bio', 'location', 'date_of_birth', 'skills', 'education', 'experience')
        }),
        ('Adresse', {
            'fields': ('address', 'city', 'country')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('email', 'phone')
        }),
    )


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_user__username', 'from_user__email', 'to_user__username', 'to_user__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'content_preview', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('author__username', 'author__email', 'content')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Contenu'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'text_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('author__username', 'text', 'post__content')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Texte'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'text_preview', 'sent_at', 'read')
    list_filter = ('read', 'sent_at')
    search_fields = ('sender__username', 'receiver__username', 'text')
    readonly_fields = ('sent_at',)
    ordering = ('-sent_at',)
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Message'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'verb', 'read', 'created_at')
    list_filter = ('read', 'created_at')
    search_fields = ('user__username', 'user__email', 'verb')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

# Personnalisation Admin
from django.contrib import admin as _admin_site
_admin_site.site_header = 'Learner Administration'
_admin_site.site_title = 'Learner Admin'
_admin_site.index_title = 'Tableau de bord'

