"""
Organization domain — شرکت / شعبه / انبار / منطقه / شهر
بر اساس ERD: companies 1—n branches 1—n warehouses
          branches 1—n zones 1—n cities
جداسازی داده شعب از طریق ForeignKey branch روی همه رکوردهای عملیاتی.
"""
from django.db import models


class Company(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    national_id = models.CharField(max_length=16, blank=True, default='')
    economic_code = models.CharField(max_length=16, blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')
    address = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'شرکت'
        verbose_name_plural = 'شرکت‌ها'

    def __str__(self):
        return f'{self.code} — {self.name}'


class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='branches')
    code = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=128)
    manager_name = models.CharField(max_length=128, blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')
    address = models.CharField(max_length=255, blank=True, default='')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'code')
        ordering = ['company', 'code']
        verbose_name = 'شعبه'
        verbose_name_plural = 'شعبه‌ها'

    def __str__(self):
        return f'{self.company.code}/{self.code} — {self.name}'


class Warehouse(models.Model):
    TYPE_MAIN = 'main'
    TYPE_TRANSIT = 'transit'
    TYPE_RETURN = 'return'
    TYPE_DAMAGED = 'damaged'
    TYPE_CHOICES = [
        (TYPE_MAIN, 'اصلی'), (TYPE_TRANSIT, 'ترانزیت'),
        (TYPE_RETURN, 'مرجوعی'), (TYPE_DAMAGED, 'ضایعات'),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='warehouses')
    code = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_MAIN)
    address = models.CharField(max_length=255, blank=True, default='')
    keeper_name = models.CharField(max_length=128, blank=True, default='')
    is_active = models.BooleanField(default=True)
    allow_negative = models.BooleanField(default=False)  # ضدفروش منفی؛ فعلاً فقط انبار ضایعات ممکنه True باشه
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('branch', 'code')
        ordering = ['branch', 'code']
        verbose_name = 'انبار'
        verbose_name_plural = 'انبارها'

    def __str__(self):
        return f'{self.branch.code}/{self.code} — {self.name}'


class Zone(models.Model):
    """منطقه فروش/پخش داخل یک شعبه"""
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='zones')
    code = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('branch', 'code')
        ordering = ['branch', 'code']
        verbose_name = 'منطقه'
        verbose_name_plural = 'مناطق'

    def __str__(self):
        return f'{self.branch.code}/{self.code} — {self.name}'


class City(models.Model):
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='cities')
    name = models.CharField(max_length=128)
    province = models.CharField(max_length=64, blank=True, default='')
    postal_prefix = models.CharField(max_length=8, blank=True, default='')

    class Meta:
        unique_together = ('zone', 'name')
        ordering = ['zone', 'name']
        verbose_name = 'شهر'
        verbose_name_plural = 'شهرها'

    def __str__(self):
        return f'{self.name} ({self.zone.name})'
