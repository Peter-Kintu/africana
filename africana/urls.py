# africana/urls.py

from django.contrib import admin
from django.urls import path, include
from api.views import home 
from rest_framework.authtoken import views

urlpatterns = [
    path('', home, name='home'),  # This must be the first line
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api-token-auth/', views.obtain_auth_token),
    path('accounts/', include('django.contrib.auth.urls')),
]