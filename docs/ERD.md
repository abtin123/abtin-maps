# مدل داده (ERD) — سامانه مدیریت پخش آبتین

## موجودیت‌های اصلی و روابط کلیدی

### سازمان
- **companies** 1—n **branches** 1—n **warehouses**
- **branches** 1—n **zones** 1—n **cities**
- **users** n—1 **roles** (و n—n **permissions** از طریق role_permissions / user_permissions)
- **employees** 1—1 users (اختیاری) ، n—1 branches

### کالا و انبار
- **products** n—1 categories ، n—1 brands
- **inventory** (product_id, warehouse_id) → physical_qty, reserved_qty, in_transit_qty
  - `available_qty = physical_qty - reserved_qty` (محاسبه‌ای / Generated Column)
- **inventory_transactions** — هر تغییر موجودی (IN/OUT/TRANSFER/ADJUST) با مرجع سند
- **inventory_reservations** — رزرو هر آیتم فاکتور؛ وضعیت: ACTIVE / CONVERTED / RELEASED / EXPIRED

### فروش و فاکتور
- **customers** — شامل latitude/longitude, credit_limit, zone_id, route_id, rep_id
- **invoices** — State Machine: DRAFT → PENDING → RESERVED → CONFIRMED → WAREHOUSE_PENDING → PREPARING → READY_FOR_DELIVERY → OUT_FOR_DELIVERY → DELIVERED → PAID (+ شاخه‌های CANCELLED / REJECTED / RETURNED / PARTIAL)
  - **Location Snapshot**: lat, lng, address_text در خود فاکتور فریز می‌شود (عدم تغییر تاریخی)
- **invoice_items** — کالا، تعداد، فی، تخفیف، مالیات
- **invoice_status_history** — هر گذر وضعیت: old_status, new_status, by_user, at, note
- **payments** / **receipts** — پشتیبانی پرداخت ترکیبی (چند ردیف روش پرداخت برای یک فاکتور)

### پخش
- **vehicles** ، **delivery_trips** (راننده، خودرو، کیلومتر شروع/پایان)
- **delivery_orders** n—1 trips ، 1—1 invoices → وضعیت تحویل + دلایل عدم تحویل
- **routes** 1—n **route_stops** (ترتیب مشتریان، پنجره زمانی)
- **visits** — ورود/خروج بازاریاب به مشتری (GPS + Timestamp)
- **gps_tracks** — نقشه مسیر واقعی (user_id, lat, lng, recorded_at)

### مالی
- **accounting_accounts** (سرفصل درختی) ، **accounting_entries** + **accounting_entry_items** (سند خودکار از فروش/دریافت)
- **checks** — دریافتی/پرداختی + وضعیت و سررسید
- **expenses** / **revenues**

### HR
- **attendance** (ورود/خروج + GPS اختیاری) ، **leave_requests** ، **payroll** ، **commissions** ، **targets**

### زیرساخت
- **notifications** ، **audit_logs** (غیرقابل حذف) ، **attachments** (امضا، عکس رسید، اسناد)

## قوانین تراکنشی حیاتی
1. رزرو موجودی فقط داخل `transaction.atomic` + `SELECT ... FOR UPDATE` روی ردیف inventory
2. تأیید فاکتور → تبدیل reservation به inventory_transaction (OUT) و کاهش physical در همان تراکنش
3. لغو/رد/انقضا → آزادسازی reservation (status=RELEASED) بدون تغییر physical
4. حذف سوابق مالی ممنوع — فقط Soft Delete / Void
5. هر گذر وضعیت، سطر invoice_status_history + audit_logs تولید می‌کند
