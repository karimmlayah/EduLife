from django.urls import path
from . import views

urlpatterns = [
    path('', views.logement_home, name='logement'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
