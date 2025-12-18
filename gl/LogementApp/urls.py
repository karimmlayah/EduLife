from django.urls import path
from . import views

urlpatterns = [
    path('', views.logement_home, name='logement'),
    path('add/', views.logement_add, name='logement_add'),
    path('my/', views.my_logements, name='my_logements'),
    path('<int:logement_id>/', views.logement_detail, name='logement_detail'),
    path('<int:logement_id>/edit/', views.logement_edit, name='logement_edit'),
    path('<int:logement_id>/delete/', views.logement_delete, name='logement_delete'),
    path('<int:logement_id>/messages/', views.logement_messages, name='logement_messages'),
    path('<int:logement_id>/messages/send/', views.send_logement_message, name='send_logement_message'),
    path('marketplace/messages/', views.marketplace_messages, name='marketplace_messages'),
    path('binome/', views.binome_search, name='binome_search'),
    path('binome/add/', views.binome_add, name='binome_add'),
    path('binome/<int:request_id>/', views.binome_detail, name='binome_detail'),
    path('binome/<int:request_id>/edit/', views.binome_edit, name='binome_edit'),
    path('binome/<int:request_id>/delete/', views.binome_delete, name='binome_delete'),
    path('binome/<int:request_id>/contact/', views.binome_contact, name='binome_contact'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('predict-price/', views.predict_price_api, name='predict_price_api'),
    path('<int:logement_id>/summarize/', views.summarize_description, name='summarize_description'),
    path('generate-ai/', views.logement_generate_ai, name='logement_generate_ai'),
    path('upload-temp-image/', views.upload_temp_image, name='upload_temp_image'),
]
