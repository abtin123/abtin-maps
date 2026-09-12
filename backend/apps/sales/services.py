from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.inventory.services import reserve_stock, release_reservation, convert_reservation_to_out, InsufficientStock
from apps.inventory.models import InventoryReservation, Product
from apps.finance.models import Account, JournalEntry, JournalLine, Receipt
from .models import Invoice, InvoiceItem, InvoiceStatusHistory, ApprovalRequest, Payment

ALLOWED_TRANSITIONS = {
    Invoice.STATUS_DRAFT: {Invoice.STATUS_PENDING_APPROVAL, Invoice.STATUS_CANCELLED},
    Invoice.STATUS_PENDING_APPROVAL: {Invoice.STATUS_APPROVED, Invoice.STATUS_REJECTED, Invoice.STATUS_CANCELLED},
    Invoice.STATUS_APPROVED: {Invoice.STATUS_RESERVED, Invoice.STATUS_CANCELLED},
    Invoice.STATUS_RESERVED: {Invoice.STATUS_CONFIRMED, Invoice.STATUS_CANCELLED},
    Invoice.STATUS_CONFIRMED: {Invoice.STATUS_WAREHOUSE_PENDING, Invoice.STATUS_CANCELLED},
    Invoice.STATUS_WAREHOUSE_PENDING: {Invoice.STATUS_PREPARING, Invoice.STATUS_CANCELLED},
    Invoice.STATUS_PREPARING: {Invoice.STATUS_READY_FOR_DELIVERY, Invoice.STATUS_CANCELLED},
    Invoice.STATUS_READY_FOR_DELIVERY: {Invoice.STATUS_OUT_FOR_DELIVERY, Invoice.STATUS_CANCELLED},
    Invoice.STATUS_OUT_FOR_DELIVERY: {Invoice.STATUS_DELIVERED, Invoice.STATUS_PARTIALLY_DELIVERED, Invoice.STATUS_RETURNED},
    Invoice.STATUS_DELIVERED: {Invoice.STATUS_RECEIVED, Invoice.STATUS_RETURNED},
    Invoice.STATUS_PARTIALLY_DELIVERED: {Invoice.STATUS_RECEIVED, Invoice.STATUS_RETURNED},
    Invoice.STATUS_RECEIVED: set(),
    Invoice.STATUS_CANCELLED: set(), Invoice.STATUS_REJECTED: set(),
}


def _recalculate(invoice):
    subtotal = Decimal('0'); discount = Decimal('0'); tax = Decimal('0')
    for item in invoice.items.all():
        base = item.unit_price * item.qty
        item.discount_amount = (base * item.discount_percent / Decimal('100')).quantize(Decimal('1'))
        net = base - item.discount_amount
        item.tax_amount = (net * item.product.tax_rate / Decimal('100')).quantize(Decimal('1'))
        item.line_total = net + item.tax_amount
        item.save(update_fields=['discount_amount', 'tax_amount', 'line_total'])
        subtotal += base; discount += item.discount_amount; tax += item.tax_amount
    invoice.subtotal, invoice.discount_total, invoice.tax_total = subtotal, discount, tax
    invoice.total = subtotal - discount + tax
    invoice.credit_approval_required = invoice.total + invoice.customer.current_balance > invoice.customer.credit_limit
    invoice.save(update_fields=['subtotal', 'discount_total', 'tax_total', 'total', 'credit_approval_required', 'updated_at'])
    return invoice


@transaction.atomic
def create_invoice(*, data, user):
    customer = data['customer']; warehouse = data['warehouse']; items = data['items']
    invoice = Invoice.objects.create(
        number=data['number'], customer=customer, warehouse=warehouse, seller=user,
        customer_name_snapshot=customer.name, customer_address_snapshot=customer.address,
        customer_latitude_snapshot=customer.latitude, customer_longitude_snapshot=customer.longitude,
    )
    for raw in items:
        product = raw['product']
        if raw.get('unit_price') is None:
            price = product.price
            if customer.price_level:
                candidate = customer.price_level.prices.filter(product=product, min_qty__lte=raw['qty'], is_active=True).order_by('-min_qty').first()
                if candidate: price = candidate.price
        else: price = raw['unit_price']
        InvoiceItem.objects.create(invoice=invoice, product=product, warehouse=warehouse, qty=raw['qty'], unit_price=price, discount_percent=raw.get('discount_percent', 0))
    return _recalculate(invoice)


@transaction.atomic
def transition_invoice(invoice, to_status, user, note=''):
    if to_status not in ALLOWED_TRANSITIONS.get(invoice.status, set()):
        raise ValidationError(f'گذار وضعیت {invoice.status} به {to_status} مجاز نیست.')
    old = invoice.status
    invoice.status = to_status
    invoice.save(update_fields=['status', 'updated_at'])
    InvoiceStatusHistory.objects.create(invoice=invoice, from_status=old, to_status=to_status, changed_by=user, note=note)
    return invoice


@transaction.atomic
def reserve_invoice(invoice, user):
    if invoice.status != Invoice.STATUS_APPROVED:
        raise ValidationError('فاکتور برای رزرو آماده نیست.')
    _recalculate(invoice)
    if invoice.credit_approval_required:
        raise ValidationError('سقف اعتبار مشتری کافی نیست و تأیید اعتبار لازم است.')
    reservations = []
    for item in invoice.items.select_related('product'):
        reservation = reserve_stock(product=item.product, warehouse=invoice.warehouse, qty=item.qty, user=user, invoice_ref=invoice.number)
        reservation.invoice = invoice
        reservation.save(update_fields=['invoice'])
        reservations.append(reservation)
    transition_invoice(invoice, Invoice.STATUS_RESERVED, user, 'رزرو موجودی انجام شد')
    return invoice


@transaction.atomic
def confirm_invoice(invoice, user):
    if invoice.status != Invoice.STATUS_RESERVED:
        raise ValidationError('فقط فاکتور رزروشده قابل تأیید نهایی است.')
    for reservation in invoice.reservations.select_for_update().filter(status=InventoryReservation.STATUS_ACTIVE):
        convert_reservation_to_out(reservation, user, reference=f'Invoice#{invoice.number}')
    invoice = transition_invoice(invoice, Invoice.STATUS_CONFIRMED, user, 'تأیید نهایی و خروج موجودی')

    # ثبت خودکار سند فروش: بدهکار مشتری / بستانکار فروش
    receivable, _ = Account.objects.get_or_create(code='1100', defaults={'name': 'حساب دریافتنی مشتریان', 'type': Account.ASSET})
    sales_account, _ = Account.objects.get_or_create(code='4100', defaults={'name': 'فروش کالا', 'type': Account.REVENUE})
    entry = JournalEntry.objects.create(number=f'SALE-{invoice.number}', description=f'فروش فاکتور {invoice.number}', reference=invoice.number, created_by=user)
    JournalLine.objects.create(entry=entry, account=receivable, debit=invoice.total)
    JournalLine.objects.create(entry=entry, account=sales_account, credit=invoice.total)
    entry.status = JournalEntry.POSTED; entry.posted_at = timezone.now(); entry.save(update_fields=['status', 'posted_at'])
    return invoice


@transaction.atomic
def cancel_invoice(invoice, user, note='لغو فاکتور'):
    if invoice.status in (Invoice.STATUS_CONFIRMED, Invoice.STATUS_CANCELLED, Invoice.STATUS_REJECTED):
        raise ValidationError('این فاکتور قابل لغو نیست.')
    for reservation in invoice.reservations.select_for_update().filter(status=InventoryReservation.STATUS_ACTIVE):
        release_reservation(reservation)
    return transition_invoice(invoice, Invoice.STATUS_CANCELLED, user, note)


@transaction.atomic
def record_payment(invoice, *, method, amount, reference, user):
    amount = Decimal(amount)
    if invoice.status in (Invoice.STATUS_CANCELLED, Invoice.STATUS_REJECTED, Invoice.STATUS_RETURNED):
        raise ValidationError('برای فاکتور لغوشده، ردشده یا برگشتی دریافت وجه مجاز نیست.')
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if amount <= 0 or amount > invoice.balance:
        raise ValidationError('مبلغ پرداخت باید مثبت و حداکثر برابر مانده فاکتور باشد.')
    payment = Payment.objects.create(invoice=invoice, method=method, amount=amount, reference=reference, received_by=user)
    invoice.paid_total += amount
    invoice.payment_status = Invoice.PAYMENT_PAID if invoice.paid_total >= invoice.total else Invoice.PAYMENT_PARTIAL
    if invoice.paid_total >= invoice.total:
        invoice.paid_total = invoice.total
    invoice.save(update_fields=['paid_total', 'payment_status', 'updated_at'])

    # رسید و سند حسابداری دریافت وجه
    receipt = Receipt.objects.create(
        number=f'REC-{payment.id}-{invoice.number}', invoice=invoice, customer=invoice.customer,
        amount=amount, method=method, reference=reference, received_by=user,
    )
    cash_code = {'cash': '1000', 'card': '1010', 'transfer': '1020', 'cheque': '1030'}.get(method, '1000')
    cash_account, _ = Account.objects.get_or_create(code=cash_code, defaults={'name': f'دریافت {method}', 'type': Account.ASSET})
    receivable, _ = Account.objects.get_or_create(code='1100', defaults={'name': 'حساب دریافتنی مشتریان', 'type': Account.ASSET})
    entry = JournalEntry.objects.create(number=f'REC-{receipt.number}', description=f'دریافت فاکتور {invoice.number}', reference=receipt.number, created_by=user)
    JournalLine.objects.create(entry=entry, account=cash_account, debit=amount)
    JournalLine.objects.create(entry=entry, account=receivable, credit=amount)
    entry.status = JournalEntry.POSTED; entry.posted_at = timezone.now(); entry.save(update_fields=['status', 'posted_at'])
    return payment

