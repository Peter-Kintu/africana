# learnflow_ai/django_backend/africana/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings
# from django.conf.urls.static import static # REMOVED: No longer needed with WhiteNoise

# Only import teacher_dashboard_view if it's used directly here
from api.views import teacher_dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('teacher-dashboard/', teacher_dashboard_view, name='teacher-dashboard'),
]

# IMPORTANT: DO NOT serve static files directly in production via Django/Gunicorn
# when using WhiteNoise. WhiteNoiseMiddleware handles this.
# if not settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
