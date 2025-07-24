from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('your_app_name.urls')), # Assuming 'your_app_name' has API URLs
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'), # Assuming obtain_auth_token is imported
    path('accounts/', include('accounts.urls')), # Assuming 'accounts' has its own URLs
    path('teacher-dashboard/', your_app_name.views.teacher_dashboard, name='teacher-dashboard'), # Assuming this is a view
    path('media/<path:path>/', serve, {'document_root': settings.MEDIA_ROOT}), # Assuming serve and settings are imported
    path('static/<path:path>/', serve, {'document_root': settings.STATIC_ROOT}), # Assuming serve and settings are imported

    # Add this line to redirect the root URL
    path('', RedirectView.as_view(url='/api/', permanent=False)), # Redirects to /api/
    # Or redirect to the teacher-dashboard
    # path('', RedirectView.as_view(url='/teacher-dashboard/', permanent=False)),
]