# learnflow_ai/django_backend/django_backend/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken import views as drf_authtoken_views # ADDED: Import the views module

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Include your API app's URLs
    path('api-token-auth/', drf_authtoken_views.obtain_auth_token, name='api_token_auth'), # CORRECTED: Direct view reference
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
