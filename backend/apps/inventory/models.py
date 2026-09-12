"""
Inventory domain — کالا، دسته، برند، واحد، موجودی، رزرو، اسناد انبار.

قوانین تراکنشی (طبق ERD):
- Inventory جدول واحدِ (product, warehouse) → physical_qty / reserved_qty / in_transit_qty
- available_qty = physical_qty - reserved_qty (property؛ در Postgres می‌شود Generated Column)
- رزرو فقط داخل transaction.atomic + SELECT FOR UPDATE (سرویس reserve_stock)
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Brand(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'برند'
        verbose_name_plural = 'برندها'

    def __str__(self):
        return self.name


class Category(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    parent = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True, related_name='children'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'دسته کالا'
        verbose_name_plural = 'دسته‌های کالا'

    def __str__(self):
        return self.name


class UnitOfMeasure(models.Model):
    code = models.SlugField(max_length=16, unique=True)
    name = models.CharField(max_length=32)  # عدد / کارتن / کیلوگرم / بسته

    class Meta:
        ordering = ['code']
        verbose_name = 'واحد شمارش'
        verbose_name_plural = 'واحدهای شمارش'

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=32, unique=True, db_index=True)
    barcode = models.CharField(max_length=32, unique=True, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='products')

    pack_size = models.PositiveIntegerField(default=1)  # تعداد در بسته
    weight_grams = models.PositiveIntegerField(default=0)

    price = models.DecimalField(max_digits=14, decimal_places=0, default=0)  # قیمت لیست (ریال)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # نقطه سفارش برای هر کالا — منطق هشدار در فاز ۷
    reorder_point = models.PositiveIntegerField(default=0)
    has_expiry = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sku']
        verbose_name = 'کالا'
        verbose_name_plural = 'کالاها'

    def __str__(self):
        return f'{self.sku} — {self.name}'


class Inventory(models.Model):
    """ردیف موجودی هر کالا در هر انبار — Physical / Reserved / In-Transit"""
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='inventory_rows')
    warehouse = models.ForeignKey(
        'organization.Warehouse', on_delete=models.PROTECT, related_name='inventory_rows'
    )

    physical_qty = models.IntegerField(default=0)
    reserved_qty = models.IntegerField(default=0)
    in_transit_qty = models.IntegerField(default=0)

    # مقدار میانگین بها (برای گزارش سود)؛ در فاز مالی به‌طور دقیق‌تر محاسبه می‌شود
    avg_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'warehouse')
        ordering = ['warehouse', 'product']
        verbose_name = 'موجودی'
        verbose_name_plural = 'موجودی‌ها'

    def __str__(self):
        return f'{self.product.sku}@{self.warehouse.code}'

    @property
    def available_qty(self):
        """موجودی قابل فروش = فیزیکی − رزرو"""
        return self.physical_qty - self.reserved_qty


class InventoryTransaction(models.Model):
    """کاردکس/گردش کالا — هر تغییر روی موجودی یک سند دارد."""
    TYPE_IN = 'in'
    TYPE_OUT = 'out'
    TYPE_TRANSFER_OUT = 'transfer_out'
    TYPE_TRANSFER_IN = 'transfer_in'
    TYPE_ADJUST = 'adjust'
    TYPE_COUNT = 'count'
    TYPES = [
        (TYPE_IN, 'ورود'), (TYPE_OUT, 'خروج'),
        (TYPE_TRANSFER_OUT, 'انتقال-خروج'), (TYPE_TRANSFER_IN, 'انتقال-ورود'),
        (TYPE_ADJUST, 'اصلاح'), (TYPE_COUNT, 'انبارگردانی'),
    ]

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='transactions')
    warehouse = models.ForeignKey('organization.Warehouse', on_delete=models.PROTECT)
    type = models.CharField(max_length=16, choices=TYPES)
    qty = models.IntegerField()  # مثبت برای ورود، منفی برای خروج
    balance_after = models.IntegerField()  # فیزیکی بعد از این تراکنش
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    reference = models.CharField(max_length=64, blank=True, default='')  # e.g. StockDoc#123, Invoice#456
    note = models.CharField(max_length=255, blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='inventory_txns'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'warehouse', '-created_at']),
            models.Index(fields=['type', '-created_at']),
        ]
        verbose_name = 'تراکنش موجودی'
        verbose_name_plural = 'تراکنش‌های موجودی'


class InventoryReservation(models.Model):
    """رزرو موجودی برای هر آیتم فاکتور — Race-Condition safe از طریق سرویس."""
    STATUS_ACTIVE = 'active'
    STATUS_CONVERTED = 'converted'
    STATUS_RELEASED = 'released'
    STATUS_EXPIRED = 'expired'
    STATUSES = [
        (STATUS_ACTIVE, 'فعال'), (STATUS_CONVERTED, 'تبدیل‌شده به خروج'),
        (STATUS_RELEASED, 'آزادشده'), (STATUS_EXPIRED, 'منقضی‌شده'),
    ]

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='reservations')
    warehouse = models.ForeignKey('organization.Warehouse', on_delete=models.PROTECT)
    qty = models.PositiveIntegerField()

    invoice = models.ForeignKey(
        'sales.Invoice', on_delete=models.PROTECT, null=True, blank=True,
        related_name='reservations',
    )
    invoice_ref = models.CharField(max_length=64, blank=True, default='')  # فاز ۴ به فاکتور واقعی FK می‌شود
    status = models.CharField(max_length=16, choices=STATUSES, default=STATUS_ACTIVE, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # پیش‌فرض: ۲۴ ساعت

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'warehouse', 'status']),
            models.Index(fields=['status', 'expires_at']),
        ]
        verbose_name = 'رزرو موجودی'
        verbose_name_plural = 'رزروهای موجودی'

    def release(self):
        if self.status == self.STATUS_ACTIVE:
            self.status = self.STATUS_RELEASED
            self.released_at = timezone.now()
            self.save(update_fields=['status', 'released_at'])


class StockDocument(models.Model):
    """سند انبار — ورود/خروج/انتقال/انبارگردانی. Header + Items."""
    DOC_ENTRY = 'entry'
    DOC_EXIT = 'exit'
    DOC_TRANSFER = 'transfer'
    DOC_COUNT = 'count'
    DOC_ADJUST = 'adjust'
    DOC_TYPES = [
        (DOC_ENTRY, 'ورود'), (DOC_EXIT, 'خروج'),
        (DOC_TRANSFER, 'انتقال'), (DOC_COUNT, 'انبارگردانی'),
        (DOC_ADJUST, 'اصلاح'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_POSTED = 'posted'
    STATUS_CANCELLED = 'cancelled'
    STATUSES = [
        (STATUS_DRAFT, 'پیش‌نویس'), (STATUS_POSTED, 'ثبت‌شده'),
        (STATUS_CANCELLED, 'باطل'),
    ]

    type = models.CharField(max_length=16, choices=DOC_TYPES)
    number = models.CharField(max_length=32, unique=True, db_index=True)
    source_warehouse = models.ForeignKey(
        'organization.Warehouse', on_delete=models.PROTECT,
        related_name='source_docs', null=True, blank=True,
    )
    dest_warehouse = models.ForeignKey(
        'organization.Warehouse', on_delete=models.PROTECT,
        related_name='dest_docs', null=True, blank=True,
    )
    date = models.DateField()
    status = models.CharField(max_length=16, choices=STATUSES, default=STATUS_DRAFT)
    note = models.CharField(max_length=255, blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='stock_docs'
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='posted_stock_docs', null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = 'سند انبار'
        verbose_name_plural = 'اسناد انبار'

    def __str__(self):
        return f'{self.get_type_display()} #{self.number}'


class StockDocumentItem(models.Model):
    document = models.ForeignKey(StockDocument, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    note = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'ردیف سند'
        verbose_name_plural = 'ردیف‌های سند'
