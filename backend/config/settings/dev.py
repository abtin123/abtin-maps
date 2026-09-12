from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']

# Lightweight sqlite for local scaffolding; switch to PostgreSQL in staging/prod
if os.environ.get('USE_SQLITE', '1') == '1':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
