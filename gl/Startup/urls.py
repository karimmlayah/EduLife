from django.urls import path
from . import views

urlpatterns = [
    path('startup_list/', views.courses, name='startup_list'),
    path('create_startup/', views.create_startup, name='create_startup'),
    path('my_startups/', views.my_startups, name='my_startups'),
    path('delete_startup/<int:id>/', views.delete_startup, name='delete_startup'),
    path('edit_startup/<int:id>/', views.edit_startup, name='edit_startup'),

    # AI logo generator
    path('generate-logo/', views.generate_logo, name='generate_logo'),

    # Chatbot endpoint
    path('chatbot/', views.startup_chatbot, name='startup_chatbot'),

    # BACKOFFICE
    path('dashboard_startup/', views.dashboard_startup, name='dashboard_startup'),
    path('startupList/', views.startupList, name='startupList'),

    # Startup actions
    path("startupList/approve/<int:id>/", views.approve_startup, name="approve_startup"),
    path("startupList/reject/<int:id>/", views.reject_startup, name="reject_startup"),

    # Investments
    path('investmentList/', views.investmentList, name='investmentList'),
    path('investmentList/approve/<int:invest_id>/', views.approve_investment, name='approve_investment'),
    path('investmentList/reject/<int:invest_id>/', views.reject_investment, name='reject_investment'),
]

