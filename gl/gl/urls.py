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

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from LogementApp.views import dashboard, argon_page, tables

urlpatterns = [
    path('admin/', dashboard, name='admin_dashboard'),
    path('admin/tables/', tables, name='admin_tables'),
    path('admin/<str:page>/', argon_page, name='admin_page'),
    path('dj-admin/', admin.site.urls),
    path('Logement/', include('LogementApp.urls')),
    path('api/', include('UserApp.api_urls')),
    path('', include('UserApp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
