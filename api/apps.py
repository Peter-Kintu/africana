# Africana_m/africana/api/apps.p
from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Import signals here to ensure apps are loaded
        # This registers the signal handler when the 'api' app is ready
        import api.signals # This line will import your signals.py

