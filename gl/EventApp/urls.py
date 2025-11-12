from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_home, name='event_home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('event/<int:event_id>/seats/', views.view_seats, name='view_seats'),
    path('event/<int:event_id>/reserve/', views.reserve_event, name='reserve_event'),
    path("create-checkout-session/", views.create_checkout_session, name="create_checkout_session"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path("payment/cancel/", views.payment_cancel, name="payment_cancel"),
    path('liberer_place/<uuid:seat_id>/', views.liberer_place, name='liberer_place'),

]
