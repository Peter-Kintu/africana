# learnflow_ai/django_backend/africana/wsgi.py

import os
from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise # Use DjangoWhiteNoise for better integration
from django.conf import settings # Import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'africana.settings')

application = get_wsgi_application()

# Configure WhiteNoise to serve static files from STATIC_ROOT
# This line should be AFTER application = get_wsgi_application()
# and BEFORE any other middleware that might process requests.
if not settings.DEBUG: # Only apply in production
    application = DjangoWhiteNoise(application, root=settings.STATIC_ROOT)

