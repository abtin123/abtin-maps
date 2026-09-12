import os
from uuid import uuid4
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.core.management import call_command
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.sync.models import SyncOperation

call_command('seed_accounts', verbosity=0)
user = User.objects.get(username='admin')
notification = Notification.objects.create(recipient=user, title='تست فاز ۷', message='اعلان تست')
assert Notification.objects.filter(recipient=user, is_read=False).exists()
client = APIClient(); client.force_authenticate(user=user)
response = client.post('/api/notifications/notifications/mark_all_read/')
assert response.status_code == 200 and response.data['updated'] >= 1
client_id = f'phase7-{uuid4().hex}'
push = client.post('/api/sync/operations/push/', {'operations': [{'client_id': client_id, 'entity': 'order', 'operation': 'create', 'payload': {'total': 100}}]}, format='json')
assert push.status_code == 200 and len(push.data['accepted']) == 1
repeat = client.post('/api/sync/operations/push/', {'operations': [{'client_id': client_id, 'entity': 'order', 'operation': 'create', 'payload': {'total': 100}}]}, format='json')
assert repeat.status_code == 200 and len(repeat.data['accepted']) == 1
pull = client.get('/api/sync/operations/pull/')
assert pull.status_code == 200 and any(item['client_id'] == client_id for item in pull.data)
print('phase7 smoke test: OK')
