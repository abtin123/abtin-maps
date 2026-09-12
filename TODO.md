# TODO — نقشه راه پروژه «آبتین: سامانه مدیریت پخش و توزیع»

> استک: **React 18 + Vite** (فرانت) · **Django 5 + DRF + PostgreSQL** (بک‌اند) · JWT Auth · Celery/Redis

## ✅ فاز ۱ — طراحی UI/UX کامل (انجام شد)
- [x] دیزاین‌سیستم (توکن‌های رنگ/تایپوگرافی/فاصله، تم تیره، RTL، فونت وزیرمتن)
- [x] صفحه ورود با انتخاب نقش (پیش‌نمایش ۱۴ نقش)
- [x] پوسته اپلیکیشن: سایدبار Permission-Based، تاپ‌بار (جستجوی سراسری، اعلان، پروفایل)، نوار موبایل
- [x] داشبورد مدیر کل (کامل: KPI، نمودارها، نقشه زنده، آخرین فاکتورها، فعالیت‌ها)
- [x] داشبورد اختصاصی هر ۱۴ نقش
- [x] صفحات ماژول: فاکتورها (+ State Machine History + رزرو)، کالاها، مشتریان، موجودی/رزرو، مسیرها، حسابداری، چک‌ها، کارکنان، گزارشات، تنظیمات، اعلان‌ها، نقشه زنده، کاربران و ماتریس دسترسی، تأییدها، Audit Log
- [x] ویزارد ثبت سفارش بازاریاب (کم‌کلیک: مشتری → موجودی → کالا → تخفیف → رزرو)
- [x] صفحه تحویل مامور پخش (امضا، عکس، پرداخت ترکیبی، دلایل عدم تحویل)
- [x] صفحه همگام‌سازی آفلاین (صف ارسال)
- [x] اسکلت بک‌اند جنگو (settings لایه‌ای، DRF، JWT، Throttling، Swagger)
- [x] سند ERD و قوانین تراکنشی
- [x] حالت‌های UI: Skeleton / Empty / Error / Success (کلاس‌های آماده در theme)

## ✅ فاز ۲ — احراز هویت و کاربران (Backend) — انجام شد
- [x] مدل User سفارشی + Role + Permission (RBAC/Permission-Based) — apps/accounts
- [x] JWT Login/Refresh + OTP موبایل (بازاریاب/مامور) — OTPCode با انقضا ۲ دقیقه، ۵ تلاش، Throttle اختصاصی
- [x] API پروفایل و سوییچ نقش — /api/auth/me/ و /api/auth/switch-role/ (فقط مدیر کل)
- [x] اتصال Login فرانت به API واقعی — سه حالت: رمز عبور / OTP موبایل / پیش‌نمایش نقش‌ها
- [x] Seed داده اولیه: ۵۸ مجوز + ۱۴ نقش + ۱۴ کاربر نمونه (python manage.py seed_accounts)

### Endpoints فاز ۲
| متد | مسیر | توضیح |
|---|---|---|
| POST | /api/auth/login/ | ورود با نام کاربری + رمز → JWT |
| POST | /api/auth/refresh/ | تمدید access token (با چرخش refresh) |
| POST | /api/auth/logout/ | خروج و blacklist refresh token |
| POST | /api/auth/otp/request/ | ارسال OTP موبایل (در dev کد برمی‌گردد) |
| POST | /api/auth/otp/verify/ | تأیید OTP → JWT |
| GET | /api/auth/me/ | پروفایل + نقش + همه مجوزها |
| POST | /api/auth/switch-role/ | سوییچ نقش (فقط مدیر کل) |
| GET | /api/auth/roles/ | لیست نقش‌ها و مجوزها (ماتریس دسترسی) |
| GET | /api/auth/permissions/ | همه مجوزها (فقط مدیر کل) |

## ✅ فاز ۳ — سازمان و انبار — انجام شد
- [x] CRUD شرکت/شعبه/انبار/منطقه/شهر — apps/organization با روابط companies 1—n branches 1—n warehouses و branches 1—n zones 1—n cities؛ انبار دارای نوع (اصلی/ترانزیت/مرجوعی/ضایعات) و فلگ allow_negative
- [x] مدل کالا (SKU، بارکد، برند، دسته، واحد، انقضا، نقطه سفارش) — apps/inventory: Brand / Category (درختی) / UnitOfMeasure / Product + جستجوی by-barcode برای بارکدخوان
- [x] موجودی لحظه‌ای + کاردکس + گردش کالا — Inventory (physical/reserved/in_transit، available = physical − reserved) + InventoryTransaction با balance_after و مرجع سند + endpoint هشدار low_stock (نقطه سفارش)
- [x] **موتور رزرو موجودی**: سرویس Transactional با قفل `SELECT FOR UPDATE`، ضد Race Condition — reserve / release / convert / expire (انقضای ۲۴ ساعته + تابع expire_stale_reservations برای Celery)
- [x] ورود/خروج/انتقال/انبارگردانی + سند انبار — StockDocument + StockDocumentItem با وضعیت DRAFT → POSTED؛ ثبت نهایی موجودی را در یک تراکنش اتمیک به‌روز می‌کند و کاردکس می‌سازد
- [x] بارکدخوان در فرم‌ها — فیلد barcode یکتا + API جستجوی سریع `GET /api/inventory/products/by-barcode/<code>/` (اسکنر سخت‌افزاری به‌عنوان صفحه‌کلید متصل می‌شود؛ اسکن دوربین در فاز ۵ همراه اپ موبایل)
- [x] Seed فاز ۳: شرکت آبتین + ۲ شعبه + ۳ انبار + ۳ منطقه/شهر + ۴ برند + ۴ دسته + ۳ واحد + ۶ کالای نمونه + موجودی اولیه (python manage.py seed_inventory)

### Endpoints فاز ۳
| متد | مسیر | توضیح |
|---|---|---|
| CRUD | /api/org/companies/ · branches/ · warehouses/ · zones/ · cities/ | سازمان (view: settings.view / edit: settings.manage) |
| CRUD | /api/inventory/products/ · brands/ · categories/ · units/ | کالا و طبقه‌بندی (گارد products.*) |
| GET | /api/inventory/products/by-barcode/{code}/ | جستجوی بارکد |
| GET | /api/inventory/stocks/ | موجودی لحظه‌ای (+ available_qty محاسبه‌ای) |
| GET | /api/inventory/stocks/low_stock/ | هشدار نقطه سفارش |
| GET | /api/inventory/transactions/ | کاردکس/گردش کالا (read-only) |
| POST | /api/inventory/reserve/ | رزرو تراکنشی (SELECT FOR UPDATE) |
| GET | /api/inventory/reservations/ | لیست رزروها |
| POST | /api/inventory/reservations/{id}/release/ | آزادسازی رزرو |
| POST | /api/inventory/reservations/{id}/convert/ | تبدیل رزرو به خروج فیزیکی |
| CRUD | /api/inventory/documents/ | اسناد انبار (ورود/خروج/انتقال/انبارگردانی) |
| POST | /api/inventory/documents/{id}/post/ | ثبت نهایی سند → اعمال روی موجودی + کاردکس |

## ✅ فاز ۴ — فروش و فاکتور (انجام شد)
- [x] اپ `apps/sales` با مدل‌های Customer، PriceLevel، ProductPrice، Campaign، Invoice، InvoiceItem، Payment و ApprovalRequest
- [x] State Machine فاکتور با گذرهای کنترل‌شده، History کامل و گارد Permission مستقل روی هر action
- [x] Location Snapshot (آدرس، مختصات و نام مشتری) داخل فاکتور؛ تغییرات بعدی مشتری تاریخچه فاکتور را تغییر نمی‌دهد
- [x] قیمت‌گذاری چندسطحی، تخفیف درصدی/مبلغی، مالیات کالا و کمپین؛ محاسبات نهایی فقط در Service Layer
- [x] سقف اعتبار مشتری و ایجاد Approval Workflow برای اعتبار/تخفیف
- [x] صدور فاکتور از API و اتصال رزرو به FK واقعی `InventoryReservation.invoice`
- [x] پرداخت چندرکوردی/ترکیبی و محاسبه لحظه‌ای مانده فاکتور
- [x] تبدیل رزرو به خروج در تأیید نهایی، آزادسازی در لغو و ثبت کاردکس با مرجع فاکتور

### Endpoints فاز ۴
| متد | مسیر | توضیح |
|---|---|---|
| CRUD | `/api/sales/customers/` | مدیریت مشتری و سقف اعتبار |
| CRUD | `/api/sales/price-levels/` و `/api/sales/product-prices/` | قیمت‌گذاری چندسطحی |
| CRUD | `/api/sales/campaigns/` | کمپین‌های فعال فروش |
| CRUD | `/api/sales/invoices/` | فاکتور و اقلام با snapshot مشتری |
| POST | `/api/sales/invoices/{id}/submit/` | ارسال برای تأیید و ساخت درخواست اعتبار/تخفیف |
| POST | `/api/sales/invoices/{id}/approve/` | تأیید فاکتور |
| POST | `/api/sales/invoices/{id}/reserve/` | رزرو تراکنشی اقلام |
| POST | `/api/sales/invoices/{id}/confirm/` | خروج واقعی موجودی و تأیید نهایی |
| POST | `/api/sales/invoices/{id}/cancel/` | لغو و آزادسازی رزرو |
| GET | `/api/sales/invoice-history/` | تاریخچه تغییر وضعیت |
| POST | `/api/sales/approvals/{id}/decide/` | تصمیم‌گیری گردش تأیید |
| POST | `/api/sales/payments/receive/` | ثبت دریافت؛ چند پرداخت برای پرداخت ترکیبی |

## ✅ فاز ۵ — پخش و مسیریابی (Backend انجام شد)
- [x] Route/RouteStop با تخصیص بازاریاب، شعبه و منطقه
- [x] Visit با ورود/خروج و مختصات GPS + GPSTrack برای مسیر طی‌شده
- [x] Delivery Trip، خودرو، راننده و توقف‌های تحویل
- [x] تحویل کامل/ناقص/عدم تحویل/برگشت با دلیل، اقلام تحویل‌شده، امضا، عکس و موقعیت
- [x] کلاینت API فرانت (`frontend/src/api/delivery.js`) با JWT، مدیریت خطا و fallback پیش‌نمایش
- [x] اتصال صفحه مسیر امروز به routes/visits، ثبت موقعیت GPS، check-in و check-out
- [x] اتصال صفحه لیست تحویل به delivery-stops، مسیریابی مقصد Snapshot و ثبت نتیجه تحویل
- [x] پرامپت مرجع محصول در `docs/MASTER_PROMPT_FA.txt` نگهداری شد
- [x] نقشهٔ تعاملی Leaflet با Tile، marker رنگی، popup، fit bounds و polyline مسیر
- [x] ارائه مختصات مشتری در Visit API برای نمایش نقاط واقعی بازاریاب
- [x] اتصال OSRM برای route واقعی، فاصله و زمان تقریبی سفر
- [x] محاسبهٔ ماتریس زمان با Table API و بهینه‌سازی greedy ترتیب توقف‌ها
- [x] ناوبری turn-by-turn با steps واقعی OSRM و نمایش مرحله‌ای در صفحه مسیر
- [x] ذخیرهٔ برنامهٔ مسیر، polyline، فاصله، زمان و steps در `Route.route_plan`

### Endpoints فاز ۵
| متد | مسیر | توضیح |
|---|---|---|
| CRUD | `/api/delivery/routes/` و `/api/delivery/route-stops/` | مسیر و ترتیب مشتری‌ها |
| CRUD | `/api/delivery/visits/` | برنامه ویزیت |
| POST | `/api/delivery/visits/{id}/check-in/` | شروع ویزیت با GPS |
| POST | `/api/delivery/visits/{id}/check-out/` | پایان ویزیت با GPS |
| CRUD | `/api/delivery/gps-tracks/` | ثبت نقاط مسیر واقعی |
| CRUD | `/api/delivery/vehicles/` | خودروهای پخش |
| CRUD | `/api/delivery/trips/` | سفر پخش و تخصیص راننده |
| POST | `/api/delivery/trips/{id}/start/` | شروع سفر |
| POST | `/api/delivery/routes/{id}/save-plan/` | ذخیره برنامه مسیر و گام‌های ناوبری |
| CRUD | `/api/delivery/delivery-stops/` | توقف‌های متصل به فاکتور |
| POST | `/api/delivery/delivery-stops/{id}/deliver/` | ثبت نتیجه تحویل |
| GET | `/api/delivery/delivery-attempts/` | تاریخچه تحویل و عدم تحویل |

## فاز ۶ — مالی و HR
- [x] هسته سرفصل حساب‌ها، سند روزنامه متوازن، خطوط بدهکار/بستانکار و ثبت نهایی
- [x] دریافت، روش‌های پرداخت و چک‌های دریافتی/پرداختی با سررسید و وضعیت
- [x] مدل کارکنان، حضور و غیاب با GPS و درخواست مرخصی با گردش تصمیم‌گیری
- [x] کنترل غیرقابل‌ویرایش بودن سند ثبت‌شده، اعتبارسنجی خط‌های بدهکار/بستانکار و ابطال سند
- [x] سند خودکار درآمد/هزینه با ثبت اتمیک در دفتر روزنامه
- [x] API چک‌های نزدیک سررسید (`/api/finance/cheques/due/`)
- [x] مدل حقوق و دستمزد با محاسبه خالص، پورسانت و تارگت فروش با درصد تحقق
- [x] حضور و غیاب عملیاتی با check-in/check-out و GPS و جلوگیری از ثبت تکراری
- [x] اتصال صفحات حسابداری، چک‌ها و کارکنان به API واقعی با fallback حالت Preview
- [x] گزارش خلاصه مالی، خروجی CSV دفتر روزنامه و خروجی چاپی PDF مرورگر

### Endpoints پایه فاز ۶
| متد | مسیر | توضیح |
|---|---|---|
| CRUD | `/api/finance/accounts/` | سرفصل حساب‌ها |
| CRUD | `/api/finance/journal-entries/` | اسناد روزنامه |
| POST | `/api/finance/journal-entries/{id}/post/` | کنترل تراز و ثبت نهایی سند |
| CRUD | `/api/finance/journal-lines/` | خطوط بدهکار/بستانکار |
| CRUD | `/api/finance/receipts/` | دریافت وجه |
| CRUD | `/api/finance/cheques/` | چک‌های دریافتی و پرداختی |
| CRUD | `/api/finance/financial-documents/` | درآمد و هزینه + ایجاد خودکار سند متوازن |
| GET | `/api/finance/cheques/due/` | چک‌های سررسیدشده/نزدیک سررسید؛ پارامتر `days` |
| CRUD | `/api/finance/payroll/` | حقوق و دستمزد و خالص پرداختی |
| CRUD | `/api/finance/commissions/` | پورسانت بر اساس مبلغ و نرخ |
| CRUD | `/api/finance/targets/` | تارگت کارمند/شعبه و درصد تحقق |
| CRUD | `/api/hr/employees/` | کارکنان |
| CRUD | `/api/hr/attendance/` | حضور و غیاب و GPS |
| CRUD | `/api/hr/leave-requests/` | درخواست مرخصی |
| POST | `/api/hr/leave-requests/{id}/decide/` | تأیید یا رد مرخصی |
| POST | `/api/hr/attendance/check_in/` | ثبت ورود امروز با GPS |
| POST | `/api/hr/attendance/check_out/` | ثبت خروج امروز با GPS |

## فاز ۷ — زیرساخت
- [x] Notification Center پایدار + endpointهای mark-read و mark-all-read
- [x] Audit Log کامل روی مدل‌های حساس با django-auditlog و API فقط‌خواندنی
- [x] Offline Sync بازاریاب: IndexedDB + صف + idempotency + Conflict Response
- [x] WebSocket پایه داشبورد زنده با Django Channels (`/ws/live/`)
- [x] خروجی CSV گزارش دفتر روزنامه و چاپ PDF گزارش‌ها
- [x] Backup/Restore داده با `backup_data` و `restore_data`
- [x] Smoke Test فاز ۷ برای اعلان و همگام‌سازی
- [x] Docker Compose (api, postgres, redis, celery, celery-beat) + CI
- [x] Celery beat برای expire_stale_reservations (هر ۱۵ دقیقه)

## ممیزی امنیتی نهایی
- [x] ارتقای وابستگی‌های آسیب‌پذیر Python و Node
- [x] Bandit بدون یافتهٔ Medium/High
- [x] pip-audit و npm audit بدون آسیب‌پذیری شناخته‌شده
- [x] تست ناشناس‌بودن API، RBAC، throttle، ورودی جست‌وجو و حذف مالی
- [x] تنظیمات production امن با HTTPS، HSTS، کوکی امن و secrets اجباری

## تصمیمات معماری ثابت‌شده
- موجودی: `physical` و `reserved` جدا؛ `available = physical − reserved` (بدون فروش منفی — فقط انبار ضایعات می‌تواند allow_negative داشته باشد)
- حذف مالی = Soft Delete / Void فقط
- هر تغییر وضعیت فاکتور → History + Audit
- Business Logic فقط در لایه Service بک‌اند؛ فرانت هیچ محاسبه مالی نهایی نمی‌کند

### پچ فاز ۵ فرانت‌اند — وضعیت و نحوهٔ تست
کلاینت جدید به‌صورت progressive enhancement پیاده شده است: در حالت احراز هویت، داده‌ها و عملیات از API واقعی خوانده می‌شوند؛ در حالت Preview یا قطع API، UI با دادهٔ نمایشی قابل مشاهده می‌ماند. برای تست، ابتدا backend را اجرا و با `admin / 12345678` وارد شوید، سپس صفحات `my-route` و `delivery-list` را باز کنید. دسترسی مرورگر به GPS برای ثبت موقعیت لازم است.
