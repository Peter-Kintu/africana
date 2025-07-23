# learnflow_ai/django_backend/africana/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings # Import settings
from django.conf.urls.static import static # Import static
from api.views import teacher_dashboard_view # Import the view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Include your API app's URLs
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('accounts/', include('django.contrib.auth.urls')), # For Django's auth views
    path('teacher-dashboard/', teacher_dashboard_view, name='teacher-dashboard'), # ADDED: Teacher Dashboard URL
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

