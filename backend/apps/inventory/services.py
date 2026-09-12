"""
Business Logic لایه Service — هرگز در View یا Serializer محاسبه انجام نمی‌شود.

قوانین:
1) رزرو موجودی: transaction.atomic + select_for_update روی ردیف Inventory
2) ثبت سند ورود/خروج/انتقال → InventoryTransaction + به‌روزرسانی Inventory
3) تبدیل رزرو به خروج (فاز ۴ در تأیید فاکتور استفاده می‌شود)
4) ضدفروش منفی: مگر warehouse.allow_negative=True
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.organization.models import Warehouse

from .models import (
    Inventory,
    InventoryReservation,
    InventoryTransaction,
    Product,
    StockDocument,
    StockDocumentItem,
)

RESERVATION_TTL_HOURS = 24


class InsufficientStock(ValidationError):
    pass


def _get_or_create_inventory(product, warehouse, *, lock=False):
    qs = Inventory.objects.filter(product=product, warehouse=warehouse)
    if lock:
        qs = qs.select_for_update()
    inv = qs.first()
    if not inv:
        # اگر برای اولین بار قفل می‌خواهیم، رکورد را می‌سازیم بعد قفل می‌کنیم
        inv, _ = Inventory.objects.get_or_create(product=product, warehouse=warehouse)
        if lock:
            inv = Inventory.objects.select_for_update().get(pk=inv.pk)
    return inv


# --------------------- سند انبار ---------------------
@transaction.atomic
def post_stock_document(doc: StockDocument, user):
    """ثبت سند: کاردکس ایجاد و Inventory به‌روزرسانی می‌شود."""
    if doc.status != StockDocument.STATUS_DRAFT:
        raise ValidationError('این سند قبلاً ثبت یا باطل شده است.')

    if doc.type == StockDocument.DOC_TRANSFER and (
        not doc.source_warehouse or not doc.dest_warehouse
    ):
        raise ValidationError('انتقال به انبار مبدأ و مقصد نیاز دارد.')

    for item in doc.items.select_related('product').all():
        if doc.type == StockDocument.DOC_ENTRY:
            _apply_delta(doc.dest_warehouse or doc.source_warehouse, item, +item.qty,
                         InventoryTransaction.TYPE_IN, user, doc)
        elif doc.type == StockDocument.DOC_EXIT:
            _apply_delta(doc.source_warehouse or doc.dest_warehouse, item, -item.qty,
                         InventoryTransaction.TYPE_OUT, user, doc)
        elif doc.type == StockDocument.DOC_TRANSFER:
            _apply_delta(doc.source_warehouse, item, -item.qty,
                         InventoryTransaction.TYPE_TRANSFER_OUT, user, doc)
            _apply_delta(doc.dest_warehouse, item, +item.qty,
                         InventoryTransaction.TYPE_TRANSFER_IN, user, doc)
        elif doc.type in (StockDocument.DOC_ADJUST, StockDocument.DOC_COUNT):
            wh = doc.dest_warehouse or doc.source_warehouse
            _apply_delta(wh, item, item.qty,
                         InventoryTransaction.TYPE_ADJUST if doc.type == StockDocument.DOC_ADJUST
                         else InventoryTransaction.TYPE_COUNT, user, doc)

    doc.status = StockDocument.STATUS_POSTED
    doc.posted_by = user
    doc.posted_at = timezone.now()
    doc.save(update_fields=['status', 'posted_by', 'posted_at'])
    return doc


def _apply_delta(warehouse: Warehouse, item: StockDocumentItem, delta: int, txn_type, user, doc):
    inv = _get_or_create_inventory(item.product, warehouse, lock=True)
    new_physical = inv.physical_qty + delta
    if new_physical < 0 and not warehouse.allow_negative:
        raise InsufficientStock(
            f'موجودی کافی نیست: {item.product.sku} در {warehouse.code} '
            f'(موجود: {inv.physical_qty}، درخواست: {abs(delta)})'
        )
    inv.physical_qty = new_physical
    if delta > 0 and item.unit_cost:
        # میانگین موزون ساده
        total_qty = max(inv.physical_qty, 1)
        inv.avg_cost = (
            (inv.avg_cost * (total_qty - delta) + item.unit_cost * delta) / total_qty
        )
    inv.save(update_fields=['physical_qty', 'avg_cost', 'updated_at'])

    InventoryTransaction.objects.create(
        product=item.product,
        warehouse=warehouse,
        type=txn_type,
        qty=delta,
        balance_after=inv.physical_qty,
        unit_cost=item.unit_cost,
        reference=f'StockDoc#{doc.number}',
        note=item.note or doc.note,
        created_by=user,
    )


# --------------------- رزرو موجودی ---------------------
@transaction.atomic
def reserve_stock(*, product: Product, warehouse: Warehouse, qty: int, user, invoice_ref: str = ''):
    """
    رزرو ایمن در برابر Race Condition:
    - قفل ردیف Inventory با SELECT FOR UPDATE
    - چک available >= qty
    - افزایش reserved_qty + ایجاد InventoryReservation(status=ACTIVE)
    """
    if qty <= 0:
        raise ValidationError('تعداد باید بزرگ‌تر از صفر باشد.')

    inv = _get_or_create_inventory(product, warehouse, lock=True)
    if inv.available_qty < qty and not warehouse.allow_negative:
        raise InsufficientStock(
            f'موجودی قابل رزرو کافی نیست ({inv.available_qty} < {qty}) — {product.sku}'
        )

    inv.reserved_qty = inv.reserved_qty + qty
    inv.save(update_fields=['reserved_qty', 'updated_at'])

    return InventoryReservation.objects.create(
        product=product,
        warehouse=warehouse,
        qty=qty,
        invoice_ref=invoice_ref,
        status=InventoryReservation.STATUS_ACTIVE,
        expires_at=timezone.now() + timedelta(hours=RESERVATION_TTL_HOURS),
        created_by=user,
    )


@transaction.atomic
def release_reservation(reservation: InventoryReservation):
    """آزادسازی رزرو (لغو/رد فاکتور یا انقضا)."""
    if reservation.status != InventoryReservation.STATUS_ACTIVE:
        return reservation
    inv = _get_or_create_inventory(reservation.product, reservation.warehouse, lock=True)
    inv.reserved_qty = max(0, inv.reserved_qty - reservation.qty)
    inv.save(update_fields=['reserved_qty', 'updated_at'])
    reservation.status = InventoryReservation.STATUS_RELEASED
    reservation.released_at = timezone.now()
    reservation.save(update_fields=['status', 'released_at'])
    return reservation


@transaction.atomic
def convert_reservation_to_out(reservation: InventoryReservation, user, reference: str = ''):
    """تأیید فاکتور: تبدیل رزرو به خروج فیزیکی (کاهش physical و reserved)."""
    if reservation.status != InventoryReservation.STATUS_ACTIVE:
        raise ValidationError('این رزرو فعال نیست.')
    inv = _get_or_create_inventory(reservation.product, reservation.warehouse, lock=True)
    if inv.physical_qty < reservation.qty and not reservation.warehouse.allow_negative:
        raise InsufficientStock('موجودی فیزیکی برای تبدیل رزرو کافی نیست.')

    inv.physical_qty -= reservation.qty
    inv.reserved_qty = max(0, inv.reserved_qty - reservation.qty)
    inv.save(update_fields=['physical_qty', 'reserved_qty', 'updated_at'])

    InventoryTransaction.objects.create(
        product=reservation.product,
        warehouse=reservation.warehouse,
        type=InventoryTransaction.TYPE_OUT,
        qty=-reservation.qty,
        balance_after=inv.physical_qty,
        unit_cost=inv.avg_cost,
        reference=reference or f'Reservation#{reservation.id}',
        note='تبدیل رزرو به خروج',
        created_by=user,
    )
    reservation.status = InventoryReservation.STATUS_CONVERTED
    reservation.released_at = timezone.now()
    reservation.save(update_fields=['status', 'released_at'])
    return reservation


def expire_stale_reservations():
    """کاندید برای Celery beat: رزروهای منقضی → RELEASED."""
    stale = InventoryReservation.objects.filter(
        status=InventoryReservation.STATUS_ACTIVE,
        expires_at__lt=timezone.now(),
    )
    count = 0
    for r in stale:
        release_reservation(r)
        r.status = InventoryReservation.STATUS_EXPIRED
        r.save(update_fields=['status'])
        count += 1
    return count
