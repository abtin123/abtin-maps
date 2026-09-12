"""End-to-end business workflow smoke test.
Run after migrate + seed_demo_data with a PostgreSQL database.
"""
import os
from decimal import Decimal
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.accounts.models import User
from apps.inventory.models import Inventory, InventoryReservation, Product
from apps.organization.models import Warehouse
from apps.sales.models import Invoice
from apps.sales.services import transition_invoice, reserve_invoice, confirm_invoice, record_payment
from apps.delivery.models import DeliveryTrip, DeliveryStop, DeliveryAttempt
from apps.delivery.services import record_delivery
from apps.finance.models import JournalEntry, Receipt

admin = User.objects.get(username='admin')
rep = User.objects.get(username='sales.rep')
driver = User.objects.get(username='driver')
invoice = Invoice.objects.get(number='DEMO-INV-001')
warehouse = invoice.warehouse

# Reset demo invoice to a clean draft if this script is re-run.
if invoice.status not in (Invoice.STATUS_DRAFT,):
    raise AssertionError(f'DEMO-INV-001 is already progressed: {invoice.status}; use a fresh database for CI')

transition_invoice(invoice, Invoice.STATUS_PENDING_APPROVAL, rep)
transition_invoice(invoice, Invoice.STATUS_APPROVED, admin)
reserve_invoice(invoice, admin)
assert invoice.status == Invoice.STATUS_RESERVED
inv = Inventory.objects.get(product=invoice.items.first().product, warehouse=warehouse)
assert inv.available_qty >= 0
confirm_invoice(invoice, admin)
invoice.refresh_from_db()
assert invoice.status == Invoice.STATUS_CONFIRMED
assert not InventoryReservation.objects.filter(invoice=invoice, status=InventoryReservation.STATUS_ACTIVE).exists()
transition_invoice(invoice, Invoice.STATUS_WAREHOUSE_PENDING, admin)
transition_invoice(invoice, Invoice.STATUS_PREPARING, admin)
transition_invoice(invoice, Invoice.STATUS_READY_FOR_DELIVERY, admin)
transition_invoice(invoice, Invoice.STATUS_OUT_FOR_DELIVERY, driver)

stop = DeliveryStop.objects.get(invoice=invoice)
attempt = record_delivery(stop, status=DeliveryAttempt.STATUS_DELIVERED, user=driver, delivered_qty={str(invoice.items.first().product_id): invoice.items.first().qty}, latitude=invoice.customer_latitude_snapshot, longitude=invoice.customer_longitude_snapshot)
invoice.refresh_from_db()
assert invoice.status == Invoice.STATUS_DELIVERED

payment = record_payment(invoice, method='cash', amount=invoice.total, reference='CI-E2E', user=driver)
invoice.refresh_from_db()
assert invoice.payment_status == Invoice.PAYMENT_PAID
assert invoice.balance == Decimal('0')
assert Receipt.objects.filter(invoice=invoice, amount=payment.amount).exists()
assert JournalEntry.objects.filter(reference__in=[invoice.number]).exists()
assert JournalEntry.objects.filter(reference__startswith='REC-').exists()

# Race-condition guard: available 10, first reservation 7, second reservation 5 must fail.
product = Product.objects.first()
inv_test, _ = Inventory.objects.update_or_create(product=product, warehouse=warehouse, defaults={'physical_qty': 10, 'reserved_qty': 0})
first = None
try:
    from apps.inventory.services import reserve_stock, InsufficientStock, release_reservation
    first = reserve_stock(product=product, warehouse=warehouse, qty=7, user=admin, invoice_ref='CI-RACE-1')
    try:
        reserve_stock(product=product, warehouse=warehouse, qty=5, user=admin, invoice_ref='CI-RACE-2')
    except InsufficientStock:
        pass
    else:
        raise AssertionError('race/oversell guard failed: second reservation was accepted')
finally:
    if first:
        release_reservation(first)
    Inventory.objects.filter(pk=inv_test.pk).update(physical_qty=0, reserved_qty=0)

print('E2E_WORKFLOW: PASS')
print('INVENTORY_RESERVATION_GUARD: PASS')
print('DELIVERY: PASS')
print('PAYMENT_RECEIPT_ACCOUNTING: PASS')
