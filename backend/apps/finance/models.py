from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Account(models.Model):
    ASSET = 'asset'; LIABILITY = 'liability'; EQUITY = 'equity'; REVENUE = 'revenue'; EXPENSE = 'expense'
    TYPES = [(ASSET, 'دارایی'), (LIABILITY, 'بدهی'), (EQUITY, 'سرمایه'), (REVENUE, 'درآمد'), (EXPENSE, 'هزینه')]
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=160)
    type = models.CharField(max_length=16, choices=TYPES)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'


class JournalEntry(models.Model):
    DRAFT = 'draft'; POSTED = 'posted'; VOID = 'void'
    STATUSES = [(DRAFT, 'پیش‌نویس'), (POSTED, 'ثبت‌شده'), (VOID, 'باطل‌شده')]
    number = models.CharField(max_length=32, unique=True)
    entry_date = models.DateField(default=timezone.localdate)
    description = models.TextField(blank=True, default='')
    reference = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=12, choices=STATUSES, default=DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='journal_entries')
    posted_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.status == self.POSTED and self.pk:
            old = type(self).objects.filter(pk=self.pk).values_list('status', flat=True).first()
            if old == self.POSTED:
                raise ValidationError('سند ثبت‌شده قابل ویرایش نیست؛ از ابطال استفاده کنید.')


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_lines')
    description = models.CharField(max_length=255, blank=True, default='')
    debit = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    credit = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])

    def clean(self):
        if self.debit and self.credit:
            raise ValidationError('هر خط سند باید فقط بدهکار یا بستانکار باشد.')
        if not self.debit and not self.credit:
            raise ValidationError('مبلغ خط سند نمی‌تواند صفر باشد.')


class Receipt(models.Model):
    CASH = 'cash'; CARD = 'card'; TRANSFER = 'transfer'; CHEQUE = 'cheque'
    METHODS = [(CASH, 'نقدی'), (CARD, 'کارت'), (TRANSFER, 'واریز'), (CHEQUE, 'چک')]
    number = models.CharField(max_length=32, unique=True)
    invoice = models.ForeignKey('sales.Invoice', on_delete=models.PROTECT, null=True, blank=True, related_name='finance_receipts')
    customer = models.ForeignKey('sales.Customer', on_delete=models.PROTECT, null=True, blank=True, related_name='receipts')
    amount = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(1)])
    method = models.CharField(max_length=16, choices=METHODS)
    received_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=100, blank=True, default='')
    note = models.TextField(blank=True, default='')
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='receipts_received')


class ChequeQuerySet(models.QuerySet):
    def due(self, days=7):
        end = timezone.localdate() + timezone.timedelta(days=days)
        return self.filter(due_date__lte=end, status__in=['registered', 'deposited'])


class Cheque(models.Model):
    RECEIVED = 'received'; ISSUED = 'issued'
    DIRECTIONS = [(RECEIVED, 'دریافتی'), (ISSUED, 'پرداختی')]
    REGISTERED = 'registered'; DEPOSITED = 'deposited'; CLEARED = 'cleared'; BOUNCED = 'bounced'; CANCELLED = 'cancelled'
    STATUSES = [(REGISTERED, 'ثبت‌شده'), (DEPOSITED, 'در انتظار وصول'), (CLEARED, 'وصول‌شده'), (BOUNCED, 'برگشتی'), (CANCELLED, 'لغوشده')]
    number = models.CharField(max_length=64, unique=True)
    direction = models.CharField(max_length=12, choices=DIRECTIONS)
    bank = models.CharField(max_length=100)
    owner = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(1)])
    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    status = models.CharField(max_length=16, choices=STATUSES, default=REGISTERED)
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, null=True, blank=True, related_name='cheques')
    note = models.TextField(blank=True, default='')
    objects = ChequeQuerySet.as_manager()


class FinancialDocument(models.Model):
    INCOME = 'income'; EXPENSE = 'expense'
    TYPES = [(INCOME, 'درآمد'), (EXPENSE, 'هزینه')]
    number = models.CharField(max_length=32, unique=True)
    document_type = models.CharField(max_length=10, choices=TYPES)
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(1)])
    document_date = models.DateField(default=timezone.localdate)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='financial_documents')
    cash_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='cash_documents')
    description = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, null=True, blank=True, related_name='financial_document')
    is_void = models.BooleanField(default=False)


class Payroll(models.Model):
    employee = models.ForeignKey('hr.Employee', on_delete=models.PROTECT, related_name='payrolls')
    period = models.CharField(max_length=7, help_text='YYYY-MM')
    base_salary = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(0)])
    overtime = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    bonus = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    deductions = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    net_amount = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    status = models.CharField(max_length=12, choices=[('draft','پیش‌نویس'),('paid','پرداخت‌شده')], default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        self.net_amount = self.base_salary + self.overtime + self.bonus - self.deductions
        if self.net_amount < 0:
            raise ValidationError('خالص حقوق نمی‌تواند منفی باشد.')
        return super().save(*args, **kwargs)


class Commission(models.Model):
    employee = models.ForeignKey('hr.Employee', on_delete=models.PROTECT, related_name='commissions')
    period = models.CharField(max_length=7)
    basis_amount = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(0)])
    rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    amount = models.DecimalField(max_digits=16, decimal_places=0, default=0)
    status = models.CharField(max_length=12, choices=[('draft','پیش‌نویس'),('paid','پرداخت‌شده')], default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        self.amount = (self.basis_amount * self.rate / 100).quantize(Decimal('1'))
        return super().save(*args, **kwargs)


class SalesTarget(models.Model):
    employee = models.ForeignKey('hr.Employee', on_delete=models.PROTECT, null=True, blank=True, related_name='sales_targets')
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, null=True, blank=True, related_name='sales_targets')
    period = models.CharField(max_length=7)
    target_amount = models.DecimalField(max_digits=16, decimal_places=0, validators=[MinValueValidator(1)])
    achieved_amount = models.DecimalField(max_digits=16, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    @property
    def achievement_percent(self):
        return (self.achieved_amount * 100 / self.target_amount) if self.target_amount else 0

    def clean(self):
        if not self.employee_id and not self.branch_id:
            raise ValidationError('تارگت باید برای کارمند یا شعبه تعیین شود.')
        if self.employee_id and self.branch_id:
            raise ValidationError('تارگت همزمان برای کارمند و شعبه مجاز نیست.')

