from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Employee(models.Model):
    code = models.CharField(max_length=32, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='employee_profile')
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, null=True, blank=True, related_name='employees')
    full_name = models.CharField(max_length=160)
    title = models.CharField(max_length=100, blank=True, default='')
    mobile = models.CharField(max_length=20, blank=True, default='')
    hire_date = models.DateField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['full_name']


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='attendances')
    work_date = models.DateField(default=timezone.localdate)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    check_in_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_in_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_out_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_out_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('employee', 'work_date')
        ordering = ['-work_date']


class LeaveRequest(models.Model):
    ANNUAL = 'annual'; SICK = 'sick'; UNPAID = 'unpaid'; OTHER = 'other'
    TYPES = [(ANNUAL, 'استحقاقی'), (SICK, 'استعلاجی'), (UNPAID, 'بدون حقوق'), (OTHER, 'سایر')]
    PENDING = 'pending'; APPROVED = 'approved'; REJECTED = 'rejected'
    STATUSES = [(PENDING, 'در انتظار'), (APPROVED, 'تأیید'), (REJECTED, 'رد')]
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='leave_requests')
    leave_type = models.CharField(max_length=16, choices=TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=12, choices=STATUSES, default=PENDING)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='leave_decisions')
    decided_at = models.DateTimeField(null=True, blank=True)
