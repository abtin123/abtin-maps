from .base import *  # noqa
import os
from django.core.exceptions import ImproperlyConfigured

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set and at least 50 characters long.')

DEBUG = False
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', '').split(',') if host.strip()]
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must contain explicit production hostnames.')

CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if origin.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'
