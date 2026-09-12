from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Visit, GPSTrack, DeliveryTrip, DeliveryStop, DeliveryAttempt
from apps.sales.models import Invoice, InvoiceStatusHistory

@transaction.atomic
def start_visit(visit, *, latitude=None, longitude=None):
    if visit.status != Visit.STATUS_PLANNED:
        raise ValidationError('این ویزیت قبلاً شروع یا بسته شده است.')
    visit.status = Visit.STATUS_IN_PROGRESS
    visit.check_in_at = timezone.now()
    visit.check_in_latitude, visit.check_in_longitude = latitude, longitude
    visit.save(update_fields=['status', 'check_in_at', 'check_in_latitude', 'check_in_longitude'])
    return visit

@transaction.atomic
def finish_visit(visit, *, latitude=None, longitude=None, note=''):
    if visit.status != Visit.STATUS_IN_PROGRESS:
        raise ValidationError('فقط ویزیت در حال انجام قابل پایان است.')
    visit.status = Visit.STATUS_COMPLETED
    visit.check_out_at = timezone.now()
    visit.check_out_latitude, visit.check_out_longitude, visit.note = latitude, longitude, note
    visit.save(update_fields=['status', 'check_out_at', 'check_out_latitude', 'check_out_longitude', 'note'])
    return visit

@transaction.atomic
def start_trip(trip):
    if trip.status not in (DeliveryTrip.STATUS_PLANNED, DeliveryTrip.STATUS_LOADING):
        raise ValidationError('این سفر قابل شروع نیست.')
    trip.status, trip.started_at = DeliveryTrip.STATUS_OUT, timezone.now()
    trip.save(update_fields=['status', 'started_at'])
    return trip

@transaction.atomic
def record_delivery(stop, *, status, user, reason='', delivered_qty=None, received_amount=0, payment_method='', signature_url='', photo_url='', latitude=None, longitude=None, note=''):
    if status not in dict(DeliveryAttempt.STATUSES):
        raise ValidationError('وضعیت تحویل نامعتبر است.')
    if status == DeliveryAttempt.STATUS_FAILED and not reason:
        raise ValidationError('برای عدم تحویل، دلیل الزامی است.')
    attempt = DeliveryAttempt.objects.create(
        stop=stop, status=status, reason=reason, delivered_qty=delivered_qty or {},
        received_amount=received_amount, payment_method=payment_method,
        customer_signature_url=signature_url, receipt_photo_url=photo_url,
        latitude=latitude, longitude=longitude, note=note, recorded_by=user,
    )
    stop.status = status
    stop.delivered_at = timezone.now() if status in (DeliveryAttempt.STATUS_DELIVERED, DeliveryAttempt.STATUS_PARTIAL) else None
    stop.latitude, stop.longitude = latitude, longitude
    stop.save(update_fields=['status', 'delivered_at', 'latitude', 'longitude'])
    invoice = stop.invoice
    target = {
        DeliveryAttempt.STATUS_DELIVERED: Invoice.STATUS_DELIVERED,
        DeliveryAttempt.STATUS_PARTIAL: Invoice.STATUS_PARTIALLY_DELIVERED,
        DeliveryAttempt.STATUS_FAILED: Invoice.STATUS_OUT_FOR_DELIVERY,
        DeliveryAttempt.STATUS_RETURNED: Invoice.STATUS_RETURNED,
    }[status]
    if invoice.status not in (Invoice.STATUS_OUT_FOR_DELIVERY, target):
        raise ValidationError('فاکتور هنوز در وضعیت قابل تحویل نیست.')
    if invoice.status != target:
        old = invoice.status
        invoice.status = target
        invoice.save(update_fields=['status', 'updated_at'])
        InvoiceStatusHistory.objects.create(invoice=invoice, from_status=old, to_status=target, changed_by=user, note=f'تحویل: {status}')
    return attempt
