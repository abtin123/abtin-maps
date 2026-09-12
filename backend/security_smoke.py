import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.core.management import call_command
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.finance.models import Account

call_command('migrate', verbosity=0, interactive=False)
call_command('seed_accounts', verbosity=0)
admin = User.objects.get(username='admin')
rep = User.objects.get(username='sales.rep')
client = APIClient()
assert client.get('/api/finance/accounts/').status_code in (401, 403)
assert client.get('/api/sync/operations/pull/').status_code in (401, 403)
client.force_authenticate(user=rep)
assert client.get('/api/finance/accounts/').status_code == 403
assert client.get('/api/sales/customers/?search=%27%20OR%201%3D1').status_code == 200
client.force_authenticate(user=admin)
account = Account.objects.create(code='SEC-TEST-100', name='security test', type=Account.ASSET)
assert client.delete(f'/api/finance/accounts/{account.id}/').status_code == 405
assert client.post('/api/auth/login/', {'username': 'admin', 'password': 'wrong'}).status_code in (400, 429)
print('security smoke test: OK')
