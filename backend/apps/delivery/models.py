from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Route(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='routes')
    zone = models.ForeignKey('organization.Zone', on_delete=models.PROTECT, null=True, blank=True, related_name='routes')
    sales_rep = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='sales_routes')
    weekday = models.PositiveSmallIntegerField(null=True, blank=True, help_text='0=شنبه تا 6=جمعه')
    is_active = models.BooleanField(default=True)
    route_plan = models.JSONField(default=dict, blank=True, help_text='OSRM route plan: ordered stops, geometry, distance, duration and navigation steps')

    class Meta:
        ordering = ['code']


class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    customer = models.ForeignKey('sales.Customer', on_delete=models.PROTECT, related_name='route_stops')
    sequence = models.PositiveIntegerField(default=1)
    planned_minutes = models.PositiveIntegerField(default=15)
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        unique_together = ('route', 'sequence')
        ordering = ['route', 'sequence']


class Visit(models.Model):
    STATUS_PLANNED = 'planned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_SKIPPED = 'skipped'
    STATUSES = [(STATUS_PLANNED, 'برنامه‌ریزی‌شده'), (STATUS_IN_PROGRESS, 'در حال انجام'), (STATUS_COMPLETED, 'انجام‌شده'), (STATUS_SKIPPED, 'انجام‌نشده')]
    route_stop = models.ForeignKey(RouteStop, on_delete=models.PROTECT, related_name='visits')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='visits')
    visit_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=16, choices=STATUSES, default=STATUS_PLANNED)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    check_in_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_in_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_out_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_out_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.TextField(blank=True, default='')


class GPSTrack(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='gps_tracks')
    route = models.ForeignKey(Route, on_delete=models.PROTECT, null=True, blank=True, related_name='gps_tracks')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_meters = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)


class Vehicle(models.Model):
    code = models.CharField(max_length=32, unique=True)
    plate_number = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=128)
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)


class DeliveryTrip(models.Model):
    STATUS_PLANNED = 'planned'
    STATUS_LOADING = 'loading'
    STATUS_OUT = 'out_for_delivery'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUSES = [(STATUS_PLANNED, 'برنامه‌ریزی‌شده'), (STATUS_LOADING, 'در حال بارگیری'), (STATUS_OUT, 'در مسیر'), (STATUS_COMPLETED, 'تکمیل‌شده'), (STATUS_CANCELLED, 'لغوشده')]
    number = models.CharField(max_length=32, unique=True)
    date = models.DateField(default=timezone.localdate)
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name='trips', null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, null=True, blank=True, related_name='trips')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='delivery_trips')
    status = models.CharField(max_length=24, choices=STATUSES, default=STATUS_PLANNED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class DeliveryStop(models.Model):
    trip = models.ForeignKey(DeliveryTrip, on_delete=models.CASCADE, related_name='stops')
    invoice = models.OneToOneField('sales.Invoice', on_delete=models.PROTECT, related_name='delivery_stop')
    sequence = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=24, default='pending')
    arrived_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['trip', 'sequence']


class DeliveryAttempt(models.Model):
    STATUS_DELIVERED = 'delivered'
    STATUS_PARTIAL = 'partial'
    STATUS_FAILED = 'failed'
    STATUS_RETURNED = 'returned'
    STATUSES = [(STATUS_DELIVERED, 'تحویل کامل'), (STATUS_PARTIAL, 'تحویل ناقص'), (STATUS_FAILED, 'عدم تحویل'), (STATUS_RETURNED, 'برگشت')]
    REASONS = [('closed', 'مشتری بسته بود'), ('no_cash', 'عدم موجودی وجه'), ('mismatch', 'مغایرت سفارش'), ('refused', 'عدم پذیرش'), ('wrong_address', 'آدرس اشتباه'), ('absent', 'مشتری در محل نبود'), ('damaged', 'کالا آسیب دیده'), ('other', 'سایر')]
    stop = models.ForeignKey(DeliveryStop, on_delete=models.PROTECT, related_name='attempts')
    status = models.CharField(max_length=16, choices=STATUSES)
    reason = models.CharField(max_length=32, choices=REASONS, blank=True, default='')
    delivered_qty = models.JSONField(default=dict, blank=True)
    received_amount = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=16, blank=True, default='')
    customer_signature_url = models.URLField(blank=True, default='')
    receipt_photo_url = models.URLField(blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.TextField(blank=True, default='')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
