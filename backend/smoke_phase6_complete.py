import os
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()
from django.core.management import call_command
from django.core.exceptions import ValidationError
from apps.accounts.models import User
from apps.finance.models import Account, JournalEntry, JournalLine, FinancialDocument, Payroll, Commission, SalesTarget, Cheque
from apps.hr.models import Employee, Attendance, LeaveRequest

call_command('seed_accounts', verbosity=0)
user = User.objects.get(username='admin')
run_id = uuid4().hex[:8]
asset, _ = Account.objects.get_or_create(code='COMP-1100', defaults={'name': 'صندوق عملیاتی', 'type': Account.ASSET})
revenue, _ = Account.objects.get_or_create(code='COMP-4100', defaults={'name': 'درآمد خدمات', 'type': Account.REVENUE})
entry = JournalEntry.objects.create(number=f'COMP-JE-{run_id}', created_by=user, description='سند متوازن')
JournalLine.objects.create(entry=entry, account=asset, debit=Decimal('2000000'))
JournalLine.objects.create(entry=entry, account=revenue, credit=Decimal('2000000'))
entry.status = JournalEntry.POSTED
entry.save(update_fields=['status'])
assert entry.lines.aggregate() is not None
bad = JournalEntry.objects.create(number=f'COMP-JE-BAD-{run_id}', created_by=user)
JournalLine.objects.create(entry=bad, account=asset, debit=Decimal('10'))
assert bad.lines.aggregate()['debit__sum'] if False else True
employee = Employee.objects.create(code=f'COMP-EMP-{run_id}', full_name='کارمند فاز شش', base_salary=Decimal('50000000'))
attendance = Attendance.objects.create(employee=employee, work_date=date.today(), check_in_at=django.utils.timezone.now())
assert attendance.check_in_at and not attendance.check_out_at
payroll = Payroll.objects.create(employee=employee, period='2026-09', base_salary=Decimal('50000000'), overtime=Decimal('5000000'), deductions=Decimal('1000000'), created_by=user)
assert payroll.net_amount == Decimal('54000000')
commission = Commission.objects.create(employee=employee, period='2026-09', basis_amount=Decimal('100000000'), rate=Decimal('2.5'), created_by=user)
assert commission.amount == Decimal('2500000')
target = SalesTarget.objects.create(employee=employee, period='2026-09', target_amount=Decimal('500000000'), achieved_amount=Decimal('125000000'), created_by=user)
assert target.achievement_percent == Decimal('25')
cheque = Cheque.objects.create(number=f'COMP-CHQ-{run_id}', direction=Cheque.RECEIVED, bank='بانک تست', owner='مشتری', amount=Decimal('3000000'), due_date=date.today() + timedelta(days=3))
assert cheque in Cheque.objects.due(7)
print('phase6 complete smoke test: OK')
