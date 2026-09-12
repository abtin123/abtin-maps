# آبتین — سامانه هوشمند مدیریت پخش و توزیع

اپلیکیشن جامع، چندکاربره و نقش‌محور برای مدیریت کامل چرخه شرکت‌های پخش:
از ورود کالا به انبار تا فروش بازاریاب، رزرو موجودی، تأیید، آماده‌سازی، تحویل، دریافت وجه و حسابداری.

## استک
| لایه | تکنولوژی |
|---|---|
| Frontend | React 18 + Vite، RTL، فونت وزیرمتن، چارت SVG سبک (بدون وابستگی سنگین) |
| Backend | Django 5 + DRF + SimpleJWT + drf-spectacular |
| Database | PostgreSQL (در dev: SQLite) |
| Async | Celery + Redis (اعلان‌ها، سند خودکار) |

## اجرا (فاز ۵ — پخش و مسیریابی)

```bash
# فرانت‌اند
cd frontend
npm install
npm run dev        # http://localhost:3000

# بک‌اند
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_accounts      # Seed فاز ۲: ۵۸ مجوز + ۱۴ نقش + ۱۴ کاربر نمونه
python manage.py seed_inventory     # Seed فاز ۳: شرکت/شعبه/انبار + برند/دسته/واحد + ۶ کالا + موجودی
python manage.py runserver 8000     # مستندات API: /api/docs
```

### ورود
- **ورود با رمز عبور**: هنگام seed مقدار `SEED_DEFAULT_PASSWORD` را در محیط تنظیم کنید؛ اگر تنظیم نشود برای کاربران seed رمز تصادفی ساخته و در خروجی فرمان نمایش داده می‌شود.
- **ورود با موبایل (OTP)**: شماره‌های نمونه `09120000001` تا `09120000014` — در حالت dev کد تأیید در پاسخ API برمی‌گردد
- **پیش‌نمایش نقش‌ها**: حالت قدیمی UI بدون احراز هویت همچنان در دسترس است

## فاز ۴ — فروش و فاکتور (تازه)
- **apps/sales**: مشتری و snapshot آدرس/GPS، قیمت‌گذاری چندسطحی، کمپین، فاکتور، State Machine و History، گردش تأیید اعتبار/تخفیف، پرداخت ترکیبی و مانده لحظه‌ای.
- **اتصال رزرو به فروش**: `InventoryReservation.invoice` به فاکتور واقعی وصل است؛ تأیید نهایی رزرو را به خروج فیزیکی تبدیل و لغو آن را آزاد می‌کند.
- API فاز ۴ زیر مسیر `/api/sales/` در دسترس است و مستندات تعاملی آن در `/api/docs/` تولید می‌شود.

## فاز ۵ — پخش و مسیریابی
- **apps/delivery**: مسیر و توقف مسیر، تخصیص بازاریاب، ویزیت با check-in/check-out و GPS track، خودرو، سفر پخش، راننده و توقف‌های تحویل.
- **تحویل**: ثبت تحویل کامل/ناقص/عدم تحویل/برگشت همراه دلیل، مختصات، امضای مشتری، عکس رسید و مبلغ دریافتی؛ نتیجهٔ تحویل در تاریخچهٔ فاکتور نیز ثبت می‌شود.
- API فاز ۵ زیر مسیر `/api/delivery/` در دسترس است و صفحات `my-route` و `delivery-list` فرانت به آن متصل شده‌اند.
- کلاینت `frontend/src/api/delivery.js` عملیات GPS، check-in/check-out، شروع سفر و ثبت تحویل را با JWT انجام می‌دهد؛ در Preview fallback نمایشی فعال است.
- نقشهٔ تعاملی Leaflet با Tileهای OpenStreetMap، markerهای وضعیت‌محور، popup، fit bounds و polyline مسیر در `frontend/src/components/RealMap.jsx` اضافه شده است.
- Visit API اکنون مختصات مشتری را نیز برمی‌گرداند تا مسیر بازاریاب روی نقشهٔ واقعی نمایش داده شود؛ بهینه‌سازی ترتیب توقف‌ها با OSRM/Mapbox در گام بعدی است.
- کلاینت `frontend/src/api/routing.js` به OSRM عمومی متصل است: با Table API ترتیب توقف‌ها را greedy بهینه می‌کند و با Route API، polyline جاده‌ای، مسافت و زمان تقریبی را برمی‌گرداند؛ در خطای سرویس مسیر مستقیم باقی می‌ماند.
- steps واقعی OSRM به‌صورت راهنمای turn-by-turn در صفحه مسیر نمایش داده می‌شوند و برنامهٔ نهایی در فیلد `Route.route_plan` ذخیره می‌شود؛ endpoint ذخیره‌سازی `/api/delivery/routes/{id}/save-plan/` است.

## فاز ۶ — هسته مالی و منابع انسانی (تکمیل شد)
- **apps/finance**: سرفصل حساب‌ها، سند روزنامه با کنترل تراز بدهکار/بستانکار، دریافت وجه و چک‌های دریافتی/پرداختی.
- **apps/hr**: کارکنان، حضور و غیاب با مختصات GPS و درخواست مرخصی با تصمیم‌گیری تأیید/رد.
- درآمد/هزینه با ایجاد اتمیک سند حسابداری، حقوق و دستمزد، پورسانت، تارگت فروش و API چک‌های نزدیک سررسید اضافه شده‌اند.
- APIهای فاز ۶ زیر مسیرهای `/api/finance/` و `/api/hr/` در دسترس هستند و مجوزهای RBAC موجود (`accounting.*`، `checks.*`، `hr.*`، `sales.*`) را استفاده می‌کنند.
- ثبت نهایی سند فقط وقتی مجاز است که جمع بدهکار و بستانکار برابر و بزرگ‌تر از صفر باشد.
- سند ثبت‌شده قابل ویرایش نیست و برای تغییر وضعیت باید با عملیات ابطال کنترل‌شده مدیریت شود.
- صفحات حسابداری، چک‌ها و کارکنان در حالت احراز هویت از API واقعی داده می‌خوانند و در حالت Preview fallback نمایشی دارند؛ گزارش خلاصه مالی در `/api/finance/reports/summary/` و خروجی CSV دفتر روزنامه در `/api/finance/reports/csv/` در دسترس است.

## فاز ۷ — زیرساخت (تکمیل شد)
- مرکز اعلان پایدار زیر مسیر `/api/notifications/notifications/`، با علامت‌گذاری تکی/جمعی و مدل Push-ready.
- Audit Log با `django-auditlog` برای عملیات حساس و API فقط‌خواندنی در `/api/audit/logs/`.
- همگام‌سازی آفلاین با IndexedDB در فرانت و endpointهای Push/Pull زیر `/api/sync/operations/`؛ عملیات با `client_id` idempotent هستند و تعارض‌ها جداگانه برگردانده می‌شوند.
- WebSocket داشبورد زنده در `/ws/live/` با Django Channels، Celery/Redis و اجرای دوره‌ای آزادسازی رزروهای منقضی.
- اجرای زیرساخت کامل با `docker compose up --build` و بررسی خودکار backend/frontend در `.github/workflows/ci.yml`.
- پشتیبان‌گیری و بازیابی: `python manage.py backup_data --output backup.json` و `python manage.py restore_data backup.json`.

## اجرای تست‌ها در GitHub

فایل `.github/workflows/ci.yml` با هر `push`، هر Pull Request و اجرای دستی، تست‌های Django، migration، smoke testهای فازهای ۴ تا ۷، تست‌های امنیتی API، Bandit، `pip-audit`، `npm audit` و build فرانت‌اند را اجرا می‌کند. برای استفاده، کل پوشهٔ پروژه را در یک repository جدید GitHub قرار دهید:

```bash
git init
git add .
git commit -m "Initial secure project"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

پس از push، از تب **Actions** اجرای `Abtin CI / Security` را باز کنید. در صورت سبز بودن همهٔ jobها، تست‌ها موفق هستند. خروجی build فرانت‌اند نیز به‌عنوان artifact با نام `abtin-frontend-dist` برای ۷ روز ذخیره می‌شود. برای اجرای دستی، در همان workflow گزینهٔ **Run workflow** را انتخاب کنید.

## پرامپت مرجع محصول
نسخهٔ کامل پرامپت ارسالی در `docs/MASTER_PROMPT_FA.txt` نگهداری می‌شود تا نیازمندی‌های محصول در پچ‌های بعدی مرجع ثابت داشته باشد.

## فاز ۳ — سازمان و انبار
- **apps/organization**: شرکت ← شعبه ← انبار (اصلی/ترانزیت/مرجوعی/ضایعات) و شعبه ← منطقه ← شهر
- **apps/inventory**: کالا (SKU/بارکد/برند/دسته/واحد/نقطه سفارش)، موجودی لحظه‌ای (`available = physical − reserved`)، کاردکس (`InventoryTransaction` با balance_after)، اسناد انبار (ورود/خروج/انتقال/انبارگردانی → `POST /api/inventory/documents/{id}/post/`)
- **موتور رزرو**: `reserve_stock` داخل `transaction.atomic` + `SELECT FOR UPDATE` (ضد Race Condition)، انقضای ۲۴ ساعته، release/convert/expire — آماده اتصال به فاکتور در فاز ۴
- **بارکدخوان**: `GET /api/inventory/products/by-barcode/<code>/` برای اسکنر سخت‌افزاری

مستندات تعاملی کامل در `http://localhost:8000/api/docs` (Swagger).

## ساختار

```
abtin-distribution/
├── frontend/
│   └── src/
│       ├── styles/          # دیزاین‌سیستم (theme.css توکن‌ها، app.css کامپوننت‌ها)
│       ├── components/      # Layout، Icon، Charts، کیت UI (Kpi/Card/Table/Badge/Map...)
│       ├── data/            # roles.js (ناوبری Permission-Based هر نقش) + mock.js (Preview)
│       └── pages/           # Login + داشبوردها + ماژول‌های مشترک + صفحات میدانی
├── backend/
│   ├── config/              # settings لایه‌ای (base/dev) + urls
│   ├── apps/accounts/       # فاز ۲: User سفارشی، Role/Permission، OTP، JWT
│   ├── apps/organization/   # فاز ۳: Company / Branch / Warehouse / Zone / City
│   └── apps/inventory/      # فاز ۳: Product / Inventory / Reservation / StockDocument + services
│   ├── apps/sales/          # فاز ۴: Customer / Invoice / Pricing / Payments / Approvals
│   └── apps/delivery/       # فاز ۵: Routes / Visits / GPS / Trips / Delivery
│   ├── apps/finance/        # فاز ۶: Accounts / Journal / Receipts / Cheques
│   └── apps/hr/             # فاز ۶: Employees / Attendance / Leave Requests
├── docs/ERD.md              # مدل داده و قوانین تراکنشی
└── TODO.md                  # نقشه راه فازها
```

## نکته
فازهای ۱ تا ۵ بک‌اند کامل هستند؛ داده‌های فرانت فعلاً Preview هستند و اتصال کامل صفحات پخش به API واقعی در کار بعدی فرانت‌اند انجام می‌شود.
