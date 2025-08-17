# africana/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views
from api.views import home 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-token-auth/', views.obtain_auth_token),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', home, name='home'),
    path('api/', include('api.urls')),
]