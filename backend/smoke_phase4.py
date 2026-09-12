import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.core.management import call_command
from apps.accounts.models import User
from apps.organization.models import Warehouse
from apps.inventory.models import Product, Inventory, InventoryReservation
from apps.sales.models import Customer, Invoice
from apps.sales.services import create_invoice, transition_invoice, reserve_invoice, confirm_invoice, record_payment

call_command('seed_accounts', verbosity=0)
call_command('seed_inventory', verbosity=0)
user = User.objects.get(username='admin')
product = Product.objects.first()
inv = Inventory.objects.filter(product=product).first()
warehouse = inv.warehouse
initial = inv.physical_qty
initial_reserved = inv.reserved_qty
customer, _ = Customer.objects.get_or_create(code='SMOKE-001', defaults={'name': 'مشتری تست', 'credit_limit': 10**12})
invoice = create_invoice(data={'number': 'SMOKE-0001', 'customer': customer, 'warehouse': warehouse, 'items': [{'product': product, 'qty': 1}]}, user=user)
transition_invoice(invoice, Invoice.STATUS_PENDING_APPROVAL, user)
transition_invoice(invoice, Invoice.STATUS_APPROVED, user)
reserve_invoice(invoice, user)
inv.refresh_from_db()
print('after reserve', initial, inv.physical_qty, inv.reserved_qty, invoice.items.first().qty, list(InventoryReservation.objects.values_list('qty', 'status')))
assert inv.physical_qty == initial and inv.reserved_qty == initial_reserved + 1
confirm_invoice(invoice, user)
inv.refresh_from_db()
assert inv.physical_qty == initial - 1 and inv.reserved_qty == initial_reserved
record_payment(invoice, method='cash', amount=invoice.total, reference='SMOKE', user=user)
invoice.refresh_from_db()
assert invoice.balance == 0 and invoice.status == Invoice.STATUS_CONFIRMED
print('phase4 smoke test: OK')
