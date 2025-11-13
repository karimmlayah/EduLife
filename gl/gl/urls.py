"""
URL configuration for gl project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings 
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from django.shortcuts import redirect
from gl.ReservationApp.views import mes_reservations_passager
# IMPORTS DES VIEWS
from gl.CovoiturageApp import views as covoiturage_views
from gl.gl import views as gl_views

# IMPORTS DES RÉSERVATIONS (IMPORTANT : AVANT urlpatterns)
from gl.gl.views import (
    mes_reservations,
    reservation_accept,
    reservation_reject,
    approver_offre,
    rejeter_offre,
)


def redirect_to_dashboard(request):
    return redirect('dashboard')


urlpatterns = [
    # --- ADMIN REDIRIGÉ VERS DASHBOARD ---
    path('admin/', redirect_to_dashboard),

    # --- DASHBOARD INTERNE ---
    path('dashboard/covoiturage/', gl_views.dashboard, name='dashboard'),
    path('reservation_dashboard/', gl_views.reservation_dashboard, name='reservation_dashboard'),
    
    # --- APPROBATION DES OFFRES ---
    path('offres/covoiturage/approver/<int:id>/', approver_offre, name='approver_offre'),
    path('offres/covoiturage/rejeter/<int:id>/', rejeter_offre, name='rejeter_offre'),

    # --- PAGE ACCUEIL FRONT ---
    path('', covoiturage_views.covoiturage_home, name='root'),

    # --- MODULE COVOITURAGE ---
    path('offres/covoiturage/', covoiturage_views.offre_list, name='offres_list'),
    path('offres/covoiturage/add/', covoiturage_views.offre_create, name='offre_create'),
    path('offres/covoiturage/edit/<int:id>/', covoiturage_views.offre_update, name='offre_update'),
    path('offres/covoiturage/delete/<int:id>/', covoiturage_views.offre_delete, name='offre_delete'),
    path('mes_offres/', covoiturage_views.mes_offres, name='mes_offres'),
    path('covoiturage/', include('gl.CovoiturageApp.urls')),

    # --- MODULE RÉSERVATIONS ---
    path('reservation/', include('gl.ReservationApp.urls')),

    # Gestion des demandes pour le conducteur
    path('mes_reservations/', mes_reservations, name='mes_reservations'),
    path('reservations/accept/<int:id>/', reservation_accept, name='res_accept'),
    path('reservations/reject/<int:id>/', reservation_reject, name='res_reject'),
    path('mes_reservations_passager/', mes_reservations_passager, name='mes_reservations_passager'),
    
    # --- AUTHENTIFICATION PERSONNALISÉE ---
    path('accounts/login/', gl_views.CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', gl_views.CustomLogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),

]
