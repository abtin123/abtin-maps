from celery import shared_task
from .services import expire_stale_reservations

@shared_task
def expire_stale_reservations_task():
    return expire_stale_reservations()
