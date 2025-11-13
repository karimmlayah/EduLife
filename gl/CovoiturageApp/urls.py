from django.urls import path
from . import views

urlpatterns = [
    # 🏠 Page d'accueil du site (front principal avec la map ou autre)
    path('', views.covoiturage_home, name='home'),

    # 📍 Page contact (si tu veux une page distincte)
    path('contact/', views.contact, name='contact'),

    # 🚗 Gestion des offres
    path('offres/', views.offre_list, name='offre_list'),
    path('offres/add/', views.offre_create, name='offre_create'),
    path('offres/edit/<int:id>/', views.offre_update, name='offre_update'),
    path('offres/delete/<int:id>/', views.offre_delete, name='offre_delete'),
    path('', views.index, name='covoiturage_index'),
]
