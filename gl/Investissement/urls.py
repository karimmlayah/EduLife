from django.urls import path

from . import views

urlpatterns = [
    path('create/<int:startup_id>/', views.create_investissement, name='create_investissement'),
    path('mine/', views.my_investissements, name='my_investissements'),
    path('edit/<int:invest_id>/', views.edit_investissement, name='edit_investissement'),
    path('delete/<int:invest_id>/', views.delete_investissement, name='delete_investissement'),
]

