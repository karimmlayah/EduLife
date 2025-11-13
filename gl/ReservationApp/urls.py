from django.urls import path
from . import views
from .views import (
    mes_reservations_passager,
    reservation_cancel,)
urlpatterns = [
    path('', views.reservation_list, name='reservation_list'),
    path('add/', views.reservation_create, name='reservation_create'),
    path('delete/<int:id>/', views.reservation_delete, name='reservation_delete'),
    path('', views.reservation_home, name='reservation_home'),
     path('mes_reservations_passager/', mes_reservations_passager, name='mes_reservations_passager'),
    path('cancel/<int:id>/', reservation_cancel, name='res_cancel'),
]
