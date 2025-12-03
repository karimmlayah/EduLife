from django.urls import path

from . import views

urlpatterns = [
    path('create/<int:startup_id>/', views.create_investissement, name='create_investissement'),
    path('mine/', views.my_investissements, name='my_investissements'),
    path('edit/<int:invest_id>/', views.edit_investissement, name='edit_investissement'),
    path('delete/<int:invest_id>/', views.delete_investissement, name='delete_investissement'),
    path('convert/', views.convert_currency, name='convert_currency'),
    path('receipt/<int:id>/', views.generate_receipt, name='generate_receipt'),

    # Stripe checkout callbacks
    path('checkout/success/', views.invest_checkout_success, name='invest_checkout_success'),
    path('checkout/cancel/', views.invest_checkout_cancel, name='invest_checkout_cancel'),
]
