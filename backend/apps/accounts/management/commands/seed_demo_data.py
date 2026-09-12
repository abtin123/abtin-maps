from decimal import Decimal
from django.core.management import BaseCommand, call_command
from django.utils import timezone
from apps.accounts.models import User, Permission
from apps.organization.models import Branch, Zone
from apps.inventory.models import Product, Inventory
from apps.sales.models import Customer, Invoice
from apps.sales.services import create_invoice
from apps.delivery.models import Route, RouteStop, Visit, Vehicle, DeliveryTrip, DeliveryStop

class Command(BaseCommand):
    help = 'Create an explicit demo dataset for marketer and delivery testing.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='Demo-Strong-Password-2026!')

    def handle(self, *args, **options):
        password = options['password']
        call_command('seed_accounts', verbosity=0)
        call_command('seed_inventory', verbosity=0)
        for username in ('sales.rep', 'driver'):
            user = User.objects.get(username=username)
            user.set_password(password); user.is_active = True; user.save(update_fields=['password', 'is_active'])
        rep = User.objects.get(username='sales.rep'); driver = User.objects.get(username='driver')
        rep.extra_permissions.add(*Permission.objects.filter(code__in=['routes.view', 'visits.view', 'visits.create', 'customers.view', 'customers.create', 'products.view', 'invoices.view', 'invoices.create', 'inventory.view']))
        driver.extra_permissions.add(*Permission.objects.filter(code__in=['routes.view', 'visits.view', 'visits.create', 'delivery.view', 'delivery.manage', 'invoices.view']))
        branch = Branch.objects.first(); zone = Zone.objects.first(); warehouse = Inventory.objects.select_related('warehouse').first().warehouse
        customer, _ = Customer.objects.get_or_create(code='DEMO-C001', defaults={'name': 'فروشگاه نمونه آبتین', 'address': 'تهران، خیابان ولیعصر', 'latitude': Decimal('35.7219'), 'longitude': Decimal('51.3347'), 'credit_limit': Decimal('1000000000')})
        route, _ = Route.objects.get_or_create(code='DEMO-R01', defaults={'name': 'مسیر نمونه شمال تهران', 'branch': branch, 'zone': zone, 'sales_rep': rep, 'route_plan': {'points': [{'id': 'demo-customer', 'lat': 35.7219, 'lng': 51.3347, 'label': customer.name}], 'track': [], 'distance': 0, 'duration': 0, 'optimized': False, 'steps': []}})
        stop, _ = RouteStop.objects.get_or_create(route=route, customer=customer, sequence=1)
        Visit.objects.get_or_create(route_stop=stop, user=rep, visit_date=timezone.localdate())
        product = Product.objects.first()
        invoice = Invoice.objects.filter(number='DEMO-INV-001').first()
        if not invoice:
            invoice = create_invoice(data={'number': 'DEMO-INV-001', 'customer': customer, 'warehouse': warehouse, 'items': [{'product': product, 'qty': 1}]}, user=rep)
        vehicle, _ = Vehicle.objects.get_or_create(code='DEMO-V01', defaults={'plate_number': '11-د-123-ایران', 'title': 'خودروی نمونه', 'capacity': 1000})
        trip, _ = DeliveryTrip.objects.get_or_create(number='DEMO-TRIP-001', defaults={'route': route, 'vehicle': vehicle, 'driver': driver, 'date': timezone.localdate()})
        DeliveryStop.objects.get_or_create(trip=trip, invoice=invoice, sequence=1)
        self.stdout.write(self.style.SUCCESS('Demo data created.'))
        self.stdout.write('sales.rep / driver password: ' + password)
        self.stdout.write('Admin password remains unchanged.')
