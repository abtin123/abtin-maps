import os
from datetime import date
from decimal import Decimal
from uuid import uuid4
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.core.management import call_command
from apps.accounts.models import User
from apps.finance.models import Account, JournalEntry, JournalLine, Receipt, Cheque
from apps.hr.models import Employee, Attendance, LeaveRequest

call_command('seed_accounts', verbosity=0)
user = User.objects.get(username='admin')
run_id = uuid4().hex[:8]
asset, _ = Account.objects.get_or_create(code='SMOKE-1100', defaults={'name': 'صندوق تست', 'type': Account.ASSET})
revenue, _ = Account.objects.get_or_create(code='SMOKE-4100', defaults={'name': 'فروش تست', 'type': Account.REVENUE})
entry = JournalEntry.objects.create(number=f'SMOKE-JE-{run_id}', created_by=user, description='سند تست فاز ۶')
JournalLine.objects.create(entry=entry, account=asset, debit=Decimal('1000000'))
JournalLine.objects.create(entry=entry, account=revenue, credit=Decimal('1000000'))
assert sum((line.debit for line in entry.lines.all()), Decimal('0')) == sum((line.credit for line in entry.lines.all()), Decimal('0'))
entry.status = JournalEntry.POSTED; entry.save(update_fields=['status'])
receipt = Receipt.objects.create(number=f'SMOKE-REC-{run_id}', amount=Decimal('1000000'), method=Receipt.CASH, received_by=user)
cheque = Cheque.objects.create(number=f'SMOKE-CHQ-{run_id}', direction=Cheque.RECEIVED, bank='بانک تست', owner='مشتری تست', amount=Decimal('2000000'), due_date=date.today(), receipt=receipt)
employee = Employee.objects.create(code=f'SMOKE-EMP-{run_id}', full_name='کارمند تست', base_salary=Decimal('50000000'))
attendance = Attendance.objects.create(employee=employee, work_date=date.today())
leave = LeaveRequest.objects.create(employee=employee, leave_type=LeaveRequest.ANNUAL, start_date=date.today(), end_date=date.today())
assert cheque.receipt_id == receipt.id and attendance.employee_id == employee.id and leave.status == LeaveRequest.PENDING
print('phase6 smoke test: OK')
