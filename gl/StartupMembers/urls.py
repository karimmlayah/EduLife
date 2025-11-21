# StartupMembers/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path("<int:startup_id>/", views.startup_members, name="startup_members"),
    path("<int:startup_id>/add/", views.add_member, name="add_member"),
    # NEW:
    path("<int:startup_id>/members/<int:member_id>/edit/", 
         views.edit_member, name="edit_member"),

    path("<int:startup_id>/members/<int:member_id>/delete/", 
         views.delete_member, name="delete_member"),
]
