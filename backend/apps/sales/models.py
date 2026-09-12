from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Customer(models.Model):
    TYPE_STORE = 'store'
    TYPE_DISTRIBUTOR = 'distributor'
    TYPES = [(TYPE_STORE, 'فروشگاه'), (TYPE_DISTRIBUTOR, 'توزیع‌کننده')]
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=16, choices=TYPES, default=TYPE_STORE)
    mobile = models.CharField(max_length=20, blank=True, default='')
    national_id = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    credit_limit = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    current_balance = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    price_level = models.ForeignKey('PriceLevel', on_delete=models.PROTECT, null=True, blank=True, related_name='customers')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.code} — {self.name}'


class PriceLevel(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProductPrice(models.Model):
    price_level = models.ForeignKey(PriceLevel, on_delete=models.CASCADE, related_name='prices')
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(0)])
    min_qty = models.PositiveIntegerField(default=1)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('price_level', 'product', 'min_qty')


class Campaign(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    percent_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    fixed_discount = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    min_total = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    is_active = models.BooleanField(default=True)


class Invoice(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PENDING_APPROVAL = 'pending_approval'
    STATUS_APPROVED = 'approved'
    STATUS_RESERVED = 'reserved'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_WAREHOUSE_PENDING = 'warehouse_pending'
    STATUS_PREPARING = 'preparing'
    STATUS_READY_FOR_DELIVERY = 'ready_for_delivery'
    STATUS_OUT_FOR_DELIVERY = 'out_for_delivery'
    STATUS_DELIVERED = 'delivered'
    STATUS_PARTIALLY_DELIVERED = 'partially_delivered'
    STATUS_RECEIVED = 'received'
    STATUS_RETURNED = 'returned'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REJECTED = 'rejected'
    STATUSES = [
        (STATUS_DRAFT, 'پیش‌نویس'), (STATUS_PENDING_APPROVAL, 'در انتظار تأیید'),
        (STATUS_APPROVED, 'تأیید اعتبار'), (STATUS_RESERVED, 'رزرو شده'),
        (STATUS_CONFIRMED, 'تأیید نهایی'), (STATUS_CANCELLED, 'باطل'),
        (STATUS_REJECTED, 'رد شده'), (STATUS_WAREHOUSE_PENDING, 'در انتظار انبار'),
        (STATUS_PREPARING, 'در حال آماده‌سازی'), (STATUS_READY_FOR_DELIVERY, 'آماده ارسال'),
        (STATUS_OUT_FOR_DELIVERY, 'در مسیر تحویل'), (STATUS_DELIVERED, 'تحویل کامل'),
        (STATUS_PARTIALLY_DELIVERED, 'تحویل ناقص'), (STATUS_RECEIVED, 'رسید ثبت شد'),
        (STATUS_RETURNED, 'برگشت‌شده'),
    ]
    number = models.CharField(max_length=32, unique=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    warehouse = models.ForeignKey('organization.Warehouse', on_delete=models.PROTECT, related_name='sales_invoices')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_invoices')
    status = models.CharField(max_length=24, choices=STATUSES, default=STATUS_DRAFT, db_index=True)
    customer_name_snapshot = models.CharField(max_length=200)
    customer_address_snapshot = models.TextField(blank=True, default='')
    customer_latitude_snapshot = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    customer_longitude_snapshot = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    discount_total = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    tax_total = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    total = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    paid_total = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    PAYMENT_UNPAID = 'unpaid'
    PAYMENT_PARTIAL = 'partial'
    PAYMENT_PAID = 'paid'
    PAYMENT_STATUSES = [(PAYMENT_UNPAID, 'دریافت نشده'), (PAYMENT_PARTIAL, 'دریافت ناقص'), (PAYMENT_PAID, 'تسویه شده')]
    payment_status = models.CharField(max_length=12, choices=PAYMENT_STATUSES, default=PAYMENT_UNPAID, db_index=True)
    credit_approval_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def balance(self):
        return self.total - self.paid_total


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
    warehouse = models.ForeignKey('organization.Warehouse', on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=16, decimal_places=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    tax_amount = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    line_total = models.DecimalField(max_digits=16, decimal_places=0, default=0)


class InvoiceStatusHistory(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=24, blank=True, default='')
    to_status = models.CharField(max_length=24)
    note = models.TextField(blank=True, default='')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class ApprovalRequest(models.Model):
    TYPE_CREDIT = 'credit'
    TYPE_DISCOUNT = 'discount'
    TYPES = [(TYPE_CREDIT, 'اعتباری'), (TYPE_DISCOUNT, 'تخفیف')]
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='approval_requests')
    type = models.CharField(max_length=16, choices=TYPES)
    status = models.CharField(max_length=16, default=STATUS_PENDING)
    reason = models.TextField(blank=True, default='')
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class Payment(models.Model):
    METHOD_CASH = 'cash'
    METHOD_CARD = 'card'
    METHOD_TRANSFER = 'transfer'
    METHOD_CHEQUE = 'cheque'
    METHODS = [(METHOD_CASH, 'نقدی'), (METHOD_CARD, 'کارت'), (METHOD_TRANSFER, 'واریز'), (METHOD_CHEQUE, 'چک')]
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    method = models.CharField(max_length=16, choices=METHODS)
    amount = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(1)])
    reference = models.CharField(max_length=100, blank=True, default='')
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    received_at = models.DateTimeField(auto_now_add=True)
