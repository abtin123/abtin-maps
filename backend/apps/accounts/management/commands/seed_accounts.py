"""
Seed داده اولیه فاز ۲:
- مجوزهای سیستم (Permission)
- ۱۴ نقش + تخصیص مجوز به هر نقش
- کاربران نمونه متناظر هر نقش (رمز از `SEED_DEFAULT_PASSWORD` یا مقدار تصادفی ساخته می‌شود)
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import os

from apps.accounts.models import Permission, Role, User

import secrets
DEFAULT_PASSWORD = os.environ.get('SEED_DEFAULT_PASSWORD') or 'Demo-Strong-Password-2026!'

# مجوزها به تفکیک ماژول
PERMISSIONS = {
    'dashboard': ['view'],
    'invoices': ['view', 'create', 'confirm', 'cancel', 'discount_approve'],
    'products': ['view', 'create', 'edit', 'delete'],
    'customers': ['view', 'create', 'edit', 'credit_manage'],
    'inventory': ['view', 'entry', 'exit', 'transfer', 'count', 'reserve_manage'],
    'routes': ['view', 'manage'],
    'delivery': ['view', 'manage', 'confirm_delivery'],
    'accounting': ['view', 'entry', 'manage'],
    'checks': ['view', 'manage'],
    'hr': ['view', 'attendance', 'leave_manage', 'payroll'],
    'reports': ['view', 'export'],
    'users': ['view', 'create', 'edit', 'role_manage'],
    'settings': ['view', 'manage'],
    'approvals': ['view', 'decide'],
    'audit': ['view'],
    'notifications': ['view', 'send'],
    'sales': ['target_manage', 'commission', 'campaign'],
    'visits': ['view', 'create'],
    'orders': ['create', 'phone_create'],
    'payments': ['receive', 'confirm'],
    'system': ['backup', 'security'],
}

MODULE_LABELS = {
    'dashboard': 'داشبورد', 'invoices': 'فاکتورها', 'products': 'کالاها',
    'customers': 'مشتریان', 'inventory': 'موجودی و انبار', 'routes': 'مسیرها',
    'delivery': 'پخش و توزیع', 'accounting': 'حسابداری', 'checks': 'چک‌ها',
    'hr': 'منابع انسانی', 'reports': 'گزارشات', 'users': 'کاربران',
    'settings': 'تنظیمات', 'approvals': 'تأییدها', 'audit': 'لاگ سیستم',
    'notifications': 'اعلان‌ها', 'sales': 'فروش', 'visits': 'ویزیت‌ها',
    'orders': 'سفارش‌ها', 'payments': 'دریافت وجه', 'system': 'مدیریت فنی',
}

ALL = sorted(f'{m}.{a}' for m, acts in PERMISSIONS.items() for a in acts)

# ۱۴ نقش — (code, label, scope, is_mobile, [مجوزها])
ROLES = [
    ('super_admin', 'مدیر کل', 'دسترسی کامل به همه بخش‌ها', False, ALL),
    ('company_manager', 'مدیر شرکت', 'مدیریت شعبه و عملیات', False, [
        'dashboard.view', 'invoices.view', 'invoices.confirm', 'customers.view', 'customers.edit',
        'inventory.view', 'routes.view', 'routes.manage', 'delivery.view', 'hr.view',
        'reports.view', 'reports.export', 'approvals.view', 'approvals.decide',
    ]),
    ('sales_manager', 'مدیر فروش', 'فروش، بازاریاب‌ها، تارگت', False, [
        'dashboard.view', 'invoices.view', 'invoices.discount_approve', 'customers.view',
        'routes.view', 'routes.manage', 'reports.view', 'sales.target_manage',
        'sales.commission', 'sales.campaign', 'approvals.view', 'approvals.decide',
    ]),
    ('warehouse_manager', 'مدیر انبار', 'موجودی، ورود/خروج، انتقال', False, [
        'dashboard.view', 'inventory.view', 'inventory.entry', 'inventory.exit',
        'inventory.transfer', 'inventory.count', 'inventory.reserve_manage',
        'products.view', 'reports.view',
    ]),
    ('warehouse_keeper', 'انباردار', 'آماده‌سازی و شمارش', False, [
        'dashboard.view', 'inventory.view', 'inventory.entry', 'inventory.exit', 'inventory.count',
    ]),
    ('sales_rep', 'بازاریاب', 'مسیر، ویزیت، سفارش (موبایل)', True, [
        'dashboard.view', 'customers.view', 'products.view', 'inventory.view', 'routes.view',
        'orders.create', 'invoices.view', 'invoices.create', 'payments.receive',
        'visits.view', 'visits.create', 'reports.view',
    ]),
    ('rep_supervisor', 'سرپرست بازاریاب‌ها', 'نظارت بر تیم بازاریابی', False, [
        'dashboard.view', 'invoices.view', 'visits.view', 'sales.target_manage', 'reports.view',
    ]),
    ('driver', 'مامور پخش', 'تحویل، مسیریابی، دریافت (موبایل)', True, [
        'dashboard.view', 'routes.view', 'delivery.view', 'delivery.confirm_delivery', 'payments.receive',
    ]),
    ('accountant', 'حسابدار', 'اسناد، دریافت/پرداخت، چک', False, [
        'dashboard.view', 'accounting.view', 'accounting.entry', 'checks.view', 'checks.manage',
        'payments.receive', 'payments.confirm', 'reports.view',
    ]),
    ('finance_manager', 'مدیر مالی', 'نقدینگی، اعتبار، سود', False, [
        'dashboard.view', 'accounting.view', 'accounting.manage', 'checks.view', 'checks.manage',
        'customers.credit_manage', 'approvals.view', 'approvals.decide', 'reports.view', 'reports.export',
    ]),
    ('hr', 'منابع انسانی', 'کارکنان، حضور و غیاب، حقوق', False, [
        'dashboard.view', 'hr.view', 'hr.attendance', 'hr.leave_manage', 'hr.payroll', 'reports.view',
    ]),
    ('operator', 'اپراتور', 'ثبت سفارش تلفنی، پشتیبانی', False, [
        'dashboard.view', 'orders.phone_create', 'customers.view', 'customers.create',
        'invoices.view', 'notifications.view', 'notifications.send',
    ]),
    ('customer', 'مشتری / فروشگاه', 'سفارش، فاکتور، مانده حساب', True, [
        'dashboard.view', 'products.view', 'orders.create', 'invoices.view', 'settings.view',
    ]),
    ('system_admin', 'مدیر سیستم', 'امنیت، بکاپ، لاگ، سلامت سرویس', False, [
        'dashboard.view', 'users.view', 'users.create', 'users.edit', 'users.role_manage',
        'audit.view', 'system.backup', 'system.security', 'settings.view', 'settings.manage',
    ]),
]

# کاربران نمونه — (username, full_name, role, mobile)
USERS = [
    ('admin', 'علی محمدی', 'super_admin', '09120000001'),
    ('company.manager', 'رضا کریمی', 'company_manager', '09120000002'),
    ('sales.manager', 'سارا احمدی', 'sales_manager', '09120000003'),
    ('warehouse.manager', 'حسین رضایی', 'warehouse_manager', '09120000004'),
    ('warehouse.keeper', 'مهدی اکبری', 'warehouse_keeper', '09120000005'),
    ('sales.rep', 'امیر حسینی', 'sales_rep', '09120000006'),
    ('rep.supervisor', 'نگار موسوی', 'rep_supervisor', '09120000007'),
    ('driver', 'کامران صالحی', 'driver', '09120000008'),
    ('accountant', 'فرهاد نادری', 'accountant', '09120000009'),
    ('finance.manager', 'لیلا قاسمی', 'finance_manager', '09120000010'),
    ('hr', 'مریم توکلی', 'hr', '09120000011'),
    ('operator', 'پویا مرادی', 'operator', '09120000012'),
    ('customer.aria', 'فروشگاه آریا', 'customer', '09120000013'),
    ('system.admin', 'بهرام جلالی', 'system_admin', '09120000014'),
]


class Command(BaseCommand):
    help = 'Seed مجوزها، ۱۴ نقش و کاربران نمونه (idempotent)'

    @transaction.atomic
    def handle(self, *args, **options):
        # ۱) مجوزها
        perm_map = {}
        created = 0
        for module, actions in PERMISSIONS.items():
            for action in actions:
                code = f'{module}.{action}'
                p, was_created = Permission.objects.get_or_create(
                    code=code,
                    defaults={'label': f'{MODULE_LABELS[module]} — {action}', 'module': module},
                )
                created += was_created
                perm_map[code] = p
        self.stdout.write(f'Permissions: {created} جدید / {len(perm_map)} کل')

        # ۲) نقش‌ها + تخصیص مجوز
        for code, label, scope, is_mobile, perms in ROLES:
            role, _ = Role.objects.update_or_create(
                code=code,
                defaults={'label': label, 'scope': scope, 'is_mobile': is_mobile, 'is_system': True},
            )
            role.permissions.set([perm_map[c] for c in perms])
        self.stdout.write(f'Roles: {len(ROLES)} نقش به‌روز شد')

        # ۳) کاربران نمونه
        role_map = {r.code: r for r in Role.objects.all()}
        for username, full_name, role_code, mobile in USERS:
            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={'full_name': full_name, 'mobile': mobile, 'role': role_map[role_code]},
            )
            changed = False
            if user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if user.role_id != role_map[role_code].id:
                user.role = role_map[role_code]
                changed = True
            if was_created or not user.has_usable_password():
                user.set_password(DEFAULT_PASSWORD)
                changed = True
            if username == 'admin':
                user.is_staff = True
                user.is_superuser = True
                changed = True
            if changed:
                user.save()
        self.stdout.write(self.style.SUCCESS(
            f'Seed کامل شد: {len(USERS)} کاربر (رمز پیش‌فرض: {DEFAULT_PASSWORD})'
        ))
