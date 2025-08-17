# africana/urls.py

from django.contrib import admin
from django.urls import path, include
from api.views import home  # Make sure this import matches your file structure
from rest_framework.authtoken import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api-token-auth/', views.obtain_auth_token),
    path('accounts/', include('django.contrib.auth.urls')),
    path('teacher-dashboard/', include('api.urls')),
    path('', home, name='home'),  # This line will connect the root URL to your home view
]