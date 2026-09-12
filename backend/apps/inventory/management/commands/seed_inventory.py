"""
Seed داده اولیه فاز ۳: سازمان + کالا + موجودی نمونه.
Idempotent — چند بار اجرا خطر ندارد.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inventory.models import (
    Brand,
    Category,
    Inventory,
    Product,
    UnitOfMeasure,
)
from apps.organization.models import Branch, City, Company, Warehouse, Zone

COMPANIES = [
    ('AB', 'شرکت پخش آبتین'),
]
BRANCHES = [
    ('AB', 'THR', 'شعبه تهران', 'رضا کریمی'),
    ('AB', 'ISF', 'شعبه اصفهان', 'مهدی نظری'),
]
WAREHOUSES = [
    ('AB', 'THR', 'W-MAIN', 'انبار اصلی تهران', 'main'),
    ('AB', 'THR', 'W-RET',  'انبار مرجوعی تهران', 'return'),
    ('AB', 'ISF', 'W-MAIN', 'انبار اصلی اصفهان', 'main'),
]
ZONES = [
    ('AB', 'THR', 'Z-N', 'شمال تهران'),
    ('AB', 'THR', 'Z-S', 'جنوب تهران'),
    ('AB', 'ISF', 'Z-C', 'مرکز اصفهان'),
]
CITIES = [
    ('AB', 'THR', 'Z-N', 'تهران', 'تهران', '19'),
    ('AB', 'THR', 'Z-S', 'ری', 'تهران', '18'),
    ('AB', 'ISF', 'Z-C', 'اصفهان', 'اصفهان', '81'),
]

BRANDS = [
    ('mihan', 'میهن'),
    ('mahram', 'مهرام'),
    ('kalleh', 'کاله'),
    ('domino', 'دومینو'),
]
CATEGORIES = [
    ('dairy', 'لبنیات'),
    ('sauce', 'سس و رب'),
    ('snack', 'اسنک'),
    ('ice_cream', 'بستنی'),
]
UNITS = [('unit', 'عدد'), ('carton', 'کارتن'), ('kg', 'کیلوگرم')]

# (sku, name, brand, category, unit, pack_size, price, reorder_point, barcode)
PRODUCTS = [
    ('SKU-1001', 'شیر پرچرب ۱ لیتری میهن', 'mihan', 'dairy', 'unit', 12, 68000, 40, '6260123400011'),
    ('SKU-1002', 'ماست چکیده ۹۰۰ گرمی کاله', 'kalleh', 'dairy', 'unit', 6, 145000, 30, '6260123400028'),
    ('SKU-2001', 'رب گوجه ۸۰۰ گرمی مهرام',  'mahram', 'sauce', 'unit', 12, 195000, 24, '6260123400035'),
    ('SKU-2002', 'سس مایونز ۴۵۰ گرمی مهرام', 'mahram', 'sauce', 'unit', 12, 125000, 24, '6260123400042'),
    ('SKU-3001', 'بستنی چوبی وانیلی دومینو', 'domino', 'ice_cream', 'unit', 24, 32000, 60, '6260123400059'),
    ('SKU-3002', 'بستنی لیوانی شکلاتی دومینو', 'domino', 'ice_cream', 'unit', 24, 45000, 60, '6260123400066'),
]

# موجودی نمونه: (sku, warehouse_code, physical, reserved)
INVENTORY = [
    ('SKU-1001', 'W-MAIN', 240, 12),
    ('SKU-1002', 'W-MAIN', 180, 0),
    ('SKU-2001', 'W-MAIN', 96, 8),
    ('SKU-2002', 'W-MAIN', 60, 0),
    ('SKU-3001', 'W-MAIN', 50, 0),
    ('SKU-3002', 'W-MAIN', 20, 0),   # زیر نقطه سفارش (۶۰) → هشدار low_stock
]


class Command(BaseCommand):
    help = 'Seed سازمان، کالا و موجودی نمونه (فاز ۳)'

    @transaction.atomic
    def handle(self, *args, **options):
        # شرکت
        companies = {}
        for code, name in COMPANIES:
            c, _ = Company.objects.update_or_create(code=code, defaults={'name': name})
            companies[code] = c

        # شعب
        branches = {}
        for ccode, bcode, name, mgr in BRANCHES:
            b, _ = Branch.objects.update_or_create(
                company=companies[ccode], code=bcode,
                defaults={'name': name, 'manager_name': mgr},
            )
            branches[(ccode, bcode)] = b

        # انبار
        warehouses = {}
        for ccode, bcode, wcode, name, wtype in WAREHOUSES:
            w, _ = Warehouse.objects.update_or_create(
                branch=branches[(ccode, bcode)], code=wcode,
                defaults={'name': name, 'type': wtype},
            )
            warehouses[(bcode, wcode)] = w

        # مناطق و شهرها
        zones = {}
        for ccode, bcode, zcode, zname in ZONES:
            z, _ = Zone.objects.update_or_create(
                branch=branches[(ccode, bcode)], code=zcode, defaults={'name': zname},
            )
            zones[(bcode, zcode)] = z
        for ccode, bcode, zcode, cname, prov, prefix in CITIES:
            City.objects.update_or_create(
                zone=zones[(bcode, zcode)], name=cname,
                defaults={'province': prov, 'postal_prefix': prefix},
            )

        # برند / دسته / واحد
        brands = {b: Brand.objects.update_or_create(code=b, defaults={'name': n})[0] for b, n in BRANDS}
        cats = {c: Category.objects.update_or_create(code=c, defaults={'name': n})[0] for c, n in CATEGORIES}
        units = {u: UnitOfMeasure.objects.update_or_create(code=u, defaults={'name': n})[0] for u, n in UNITS}

        # کالا
        products = {}
        for sku, name, brand, cat, unit, pack, price, rp, barcode in PRODUCTS:
            p, _ = Product.objects.update_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'brand': brands[brand],
                    'category': cats[cat],
                    'unit': units[unit],
                    'pack_size': pack,
                    'price': Decimal(price),
                    'reorder_point': rp,
                    'barcode': barcode,
                },
            )
            products[sku] = p

        # موجودی: فقط برای انبار W-MAIN همان شعبه‌ای که کالا در آن هست (شعبه تهران)
        wh = warehouses[('THR', 'W-MAIN')]
        for sku, wcode, phys, res in INVENTORY:
            inv, _ = Inventory.objects.update_or_create(
                product=products[sku], warehouse=warehouses[('THR', wcode)],
                defaults={'physical_qty': phys, 'reserved_qty': res},
            )

        self.stdout.write(self.style.SUCCESS(
            f'Seed فاز ۳ کامل شد: {len(companies)} شرکت / {len(branches)} شعبه / '
            f'{len(warehouses)} انبار / {len(products)} کالا / {len(INVENTORY)} ردیف موجودی'
        ))
