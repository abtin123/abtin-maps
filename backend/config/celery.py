import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
app = Celery('abtin')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.beat_schedule = {
    'expire-stale-reservations-every-15-minutes': {
        'task': 'apps.inventory.tasks.expire_stale_reservations_task',
        'schedule': 900.0,
    },
}
