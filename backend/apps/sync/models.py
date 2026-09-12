from django.conf import settings
from django.db import models
from django.utils import timezone

class SyncOperation(models.Model):
    PENDING = 'pending'; APPLIED = 'applied'; CONFLICT = 'conflict'; FAILED = 'failed'
    STATUSES = [(PENDING, 'در انتظار'), (APPLIED, 'اعمال‌شده'), (CONFLICT, 'تعارض'), (FAILED, 'ناموفق')]
    client_id = models.CharField(max_length=80, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sync_operations')
    entity = models.CharField(max_length=80)
    operation = models.CharField(max_length=16)
    payload = models.JSONField(default=dict)
    client_updated_at = models.DateTimeField(null=True, blank=True)
    server_updated_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=12, choices=STATUSES, default=PENDING)
    error = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['server_updated_at']
