from django.conf import settings
from django.db import models
from django.utils import timezone

class Notification(models.Model):
    INFO = 'info'; SUCCESS = 'success'; WARNING = 'warning'; ERROR = 'error'
    TYPES = [(INFO, 'اطلاع'), (SUCCESS, 'موفق'), (WARNING, 'هشدار'), (ERROR, 'خطا')]
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=180)
    message = models.TextField()
    notification_type = models.CharField(max_length=12, choices=TYPES, default=INFO)
    link = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read', '-created_at'])]
