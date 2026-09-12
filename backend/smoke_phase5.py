import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.core.management import call_command
from apps.accounts.models import User
from apps.organization.models import Branch, Zone
from apps.sales.models import Customer, Invoice
from apps.inventory.models import Product, Inventory
from apps.sales.services import create_invoice, transition_invoice, reserve_invoice
from apps.delivery.models import Route, RouteStop, Visit, Vehicle, DeliveryTrip, DeliveryStop, DeliveryAttempt
from apps.delivery.services import start_visit, finish_visit, start_trip, record_delivery

call_command('seed_accounts', verbosity=0); call_command('seed_inventory', verbosity=0)
user = User.objects.get(username='admin'); branch = Branch.objects.first(); zone = Zone.objects.first(); customer = Customer.objects.filter(code='SMOKE-001').first()
if not customer: customer = Customer.objects.create(code='SMOKE-001', name='مشتری تست', credit_limit=10**12)
route = Route.objects.create(code='SMOKE-R1', name='مسیر تست', branch=branch, zone=zone, sales_rep=user)
route.route_plan = {'points': [{'id': 'stop-1', 'lat': 35.70, 'lng': 51.40}], 'track': [[35.70, 51.40]], 'distance': 0, 'duration': 0, 'optimized': False, 'steps': []}
route.save(update_fields=['route_plan'])
assert route.refresh_from_db() is None and route.route_plan['points'][0]['lat'] == 35.70
stop = RouteStop.objects.create(route=route, customer=customer, sequence=1)
visit = Visit.objects.create(route_stop=stop, user=user)
start_visit(visit, latitude='35.70', longitude='51.40'); finish_visit(visit, latitude='35.71', longitude='51.41')
product = Product.objects.first(); inventory = Inventory.objects.filter(product=product).first()
invoice = create_invoice(data={'number': 'SMOKE-5001', 'customer': customer, 'warehouse': inventory.warehouse, 'items': [{'product': product, 'qty': 1}]}, user=user)
transition_invoice(invoice, Invoice.STATUS_PENDING_APPROVAL, user); transition_invoice(invoice, Invoice.STATUS_APPROVED, user); reserve_invoice(invoice, user)
vehicle = Vehicle.objects.create(code='SMOKE-V1', plate_number='TEST-01', title='خودروی تست')
trip = DeliveryTrip.objects.create(number='SMOKE-T1', route=route, vehicle=vehicle, driver=user)
dstop = DeliveryStop.objects.create(trip=trip, invoice=invoice, sequence=1)
start_trip(trip)
attempt = record_delivery(dstop, status=DeliveryAttempt.STATUS_DELIVERED, user=user, received_amount=0, latitude='35.71', longitude='51.41')
assert attempt.status == DeliveryAttempt.STATUS_DELIVERED and dstop.invoice.status == Invoice.STATUS_DELIVERED
print('phase5 smoke test: OK')
