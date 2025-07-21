# learnflow_ai/django_backend/django_backend/settings.py

import os
from pathlib import Path
# REMOVED: from django.db.models.signals import post_save
# REMOVED: from django.dispatch import receiver
# REMOVED: from rest_framework.authtoken.models import Token # This import caused AppRegistryNotReady

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# IMPORTANT: Replace this with a truly random and strong key in production!
SECRET_KEY = 'django-insecure-@e^$b!q#^1234567890abcdefghijklmnopqrstuvwxyz' 

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*'] # Allow all hosts for development, be specific in production!


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',  # Django REST Framework
    'rest_framework.authtoken', # For Token Authentication (this registers the Token model)
    'corsheaders',     # ADDED: CORS Headers
    'api',             # Your API app (contains all models for now)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ADDED: CorsMiddleware should be placed as high as possible,
    # preferably before any other middleware that might generate a response,
    # like CommonMiddleware or CsrfViewMiddleware.
    'corsheaders.middleware.CorsMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'africana.urls' # CORRECTED: Changed from 'django_backend.urls' to 'africana.urls'

WSGI_APPLICATION = 'africana.wsgi.application' # CORRECTED: Changed from 'django_backend.wsgi.application' to 'africana.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC' # Use UTC for consistency, convert on client-side for display

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# TEMPLATES configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication', # Good for browsable API
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated', # Require authentication by default
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

# Media files (for lesson content uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CORS Headers Configuration - ADDED FOR FLUTTER WEB COMMUNICATION
CORS_ALLOW_ALL_ORIGINS = True # For development, allows all origins.
# In production, you should use CORS_ALLOWED_ORIGINS = ['http://your-flutter-web-domain.com']
# Or CORS_ALLOWED_ORIGIN_REGEXES for more complex patterns.

# You might also need to allow specific methods and headers if you encounter issues
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Ensure these are False for HTTP development, True for HTTPS production
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# This prevents Django from sending X-Frame-Options header, which can interfere with iframes/embedding
# If you are not embedding your app, you can remove this.
X_FRAME_OPTIONS = 'SAMEORIGIN' # Or 'ALLOW-FROM http://localhost:YOUR_FLUTTER_PORT' if embedding
# For now, let's explicitly allow all for testing if it's the issue:
# X_FRAME_OPTIONS = 'ALLOWALL' # Use with caution, only for debugging if absolutely necessary
# Or simply remove the 'django.middleware.clickjacking.XFrameOptionsMiddleware' from MIDDLEWARE if it causes issues.
