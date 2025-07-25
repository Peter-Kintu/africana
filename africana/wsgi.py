# learnflow_ai/django_backend/africana/wsgi.py

import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise # REVERTED to simple WhiteNoise import
from django.conf import settings # Import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'africana.settings')

application = get_wsgi_application()

# Configure WhiteNoise to serve static files from STATIC_ROOT
# This line should be AFTER application = get_wsgi_application()
# and BEFORE any other middleware that might process requests.
# Only apply in production (when DEBUG is False)
if not settings.DEBUG:
    application = WhiteNoise(application, root=settings.STATIC_ROOT)

