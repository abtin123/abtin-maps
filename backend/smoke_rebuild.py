import json
import os
import time
from urllib.request import Request, urlopen

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from apps.accounts.models import User
from apps.sales.models import Customer
from apps.inventory.models import Product
from apps.delivery.models import Visit
from apps.organization.models import Warehouse

BASE = 'http://127.0.0.1:8000'
def api(username, password, method, path, body=None):
    auth_body = json.dumps({'username': username, 'password': password}).encode()
    token = json.loads(urlopen(Request(BASE + '/api/auth/login/', data=auth_body, headers={'Content-Type': 'application/json'})).read())['tokens']['access']
    data = json.dumps(body).encode() if body is not None else None
    try:
        response = urlopen(Request(BASE + path, data=data, method=method, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}))
    except Exception as exc:
        if hasattr(exc, 'read'):
            print('API_ERROR', path, exc.read().decode(errors='replace'))
        raise
    return json.loads(response.read())

for user in ('admin', 'sales.rep', 'driver'):
    assert User.objects.filter(username=user, is_active=True).exists(), user
    api(user, 'Demo-Strong-Password-2026!', 'GET', '/api/auth/me/')
assert Customer.objects.exists() and Product.objects.exists() and Visit.objects.exists()
customer = api('sales.rep', 'Demo-Strong-Password-2026!', 'GET', '/api/sales/customers/')['results'][0]
product = api('sales.rep', 'Demo-Strong-Password-2026!', 'GET', '/api/inventory/products/')['results'][0]
warehouse = Warehouse.objects.order_by('id').first()
assert warehouse is not None
created = api('sales.rep', 'Demo-Strong-Password-2026!', 'POST', '/api/sales/invoices/', {'number': f"REBUILD-SMOKE-{int(time.time())}", 'customer': customer['id'], 'warehouse': warehouse.id, 'items': [{'product': product['id'], 'qty': 1}]})
assert created['status'] == 'draft'
visits = api('sales.rep', 'Demo-Strong-Password-2026!', 'GET', '/api/delivery/visits/')['results']
visit = next((v for v in visits if v['status'] == 'planned'), None)
if visit:
    checkin = api('sales.rep', 'Demo-Strong-Password-2026!', 'POST', f"/api/delivery/visits/{visit['id']}/check-in/", {'latitude': '35.721900', 'longitude': '51.334700'})
else:
    checkin = next(v for v in visits if v['status'] == 'in_progress')
assert checkin['status'] == 'in_progress'
routes = api('sales.rep', 'Demo-Strong-Password-2026!', 'GET', '/api/delivery/routes/')['results']
stops = api('driver', 'Demo-Strong-Password-2026!', 'GET', '/api/delivery/delivery-stops/')['results']
assert routes and stops
print('AUTH: OK')
print('CUSTOMERS_PRODUCTS: OK')
print('ORDER_CREATE: OK', created['number'], created['total'])
print('VISIT_GPS_CHECKIN: OK', checkin['status'])
print('ROUTES: OK', len(routes))
print('DRIVER_DELIVERY_STOPS: OK', len(stops))
