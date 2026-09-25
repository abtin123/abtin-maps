

AbtinMaps_REGIONS_ALL_COUNTRIES_AND_LOGFIX_2026-09-25.zip
Zip Archive
کوتاه: آره، منطق کلی درسته و یه معماری شناخته‌شده و منطقیه، ولی چند‌تا نقطه‌ضعف واقعی داره که باید بدونی:

چیزهایی که درست و منطقی‌ان
یک map.sqlite مستقل به‌ازای هر استان — درسته، چون هدف دانلود مجزا و سبک هر استانه.
آیدی: اول ISO-3166-2، بعد هش دترمینیستیک از اسم — درسته و استاندارده، چون هش پایدار می‌مونه بین بیلدهای مختلف (idempotent).
جلوگیری از کد تکراری با seen_codes — درسته، فِیل‌سیف خوبیه.
گراف مسیریابی با overlap corridor و «هیچ way بریده نمی‌شه» — این تکنیک درستیه برای این‌که جاده‌ای که از وسط مرز رد می‌شه، نصفه قطع نشه.
جاهایی که ایراد داره یا واقعاً باید نگرانش باشی
۱. کلیپ کردن بر اساس bbox مستطیلی، نه پلیگان واقعی مرز استان

این بزرگ‌ترین ایراده. استان‌ها معمولاً مستطیلی نیستن (فارس، گیلان، خیلی‌ها شکل نامنظم دارن). وقتی با bbox کلیپ می‌کنی:

فیچرهایی که واقعاً توی استان همسایه‌ان ولی داخل مستطیل تو افتادن، وارد فایل تو هم می‌شن → POI/جاده تکراری بین دو استان همسایه.
برعکس، گوشه‌های واقعی استان که خارج از یک مستطیل ساده نمی‌گنجن (اگه شکل L باشه مثلاً) می‌تونن جا بیفتن یا اشتباه دسته‌بندی بشن.
اگه دقت جغرافیایی مهمه، باید کلیپ با پلیگان واقعی Admin-1 انجام بشه نه فقط bbox.

۲. overlap corridor یه محدودیت پنهان داره

اگه مقصد کاربر بیرون از routing_overlap_degrees (مثلاً ۰.۲۵–۰.۳ درجه ≈ ۲۵-۳۰ کیلومتر) باشه، مسیریابی از وسط یه استان به نقطه‌ای دورتر از مرز همسایه fail می‌شه یا مسیر رو گم می‌کنه — چون داده‌ی اون طرف اصلاً دانلود نشده. این تصمیم طراحیه، ولی باید مطمئن بشی اپ به کاربر می‌گه «برای مسیر بین‌استانی، استان مقصد رو هم دانلود کن»، وگرنه رفتار عجیب می‌بینه.

۳. dedup key در map_db.py بر اساس نام+دسته+lat/lon گرد‌شده (۵ رقم اعشار ≈ ~1 متر)

اگه دو POI واقعاً مجزا (مثلاً دو تا شعبه‌ی یک فروشگاه با یک اسم) خیلی نزدیک هم باشن (کمتر از ۱ متر، بعیده ولی توی نقشه‌های چندطبقه یا پارکینگ ممکنه)، یکی حذف می‌شه. ریسک کمه ولی صفر نیست.

۴. ADM1_<hash> fallback فقط از نام (casefold شده) میاد، بدون کد کشور توش

چون تولید هش داخل generate_regions_from_admin1.py per-country انجام می‌شه (فقط رکوردهای همون iso3 رو فیلتر می‌کنه)، تصادم بین کشورها اتفاق نمی‌افته. ولی اگه یه‌روز بخوای همه‌ی هش‌ها رو تو یه namespace مشترک (بدون country prefix) استفاده کنی، ریسک تصادم هست. الان که هست مشکلی نداره، فقط شکننده‌ست اگه ساختار عوض بشه.

نتیجه: منطق تقسیم استانی + آیدی‌دهی + مسیریابی overlap، درست و قابل‌دفاعه، اما نقطه‌ضعف واقعی همون کلیپ bbox‌محور به‌جای پلیگان واقعی هست که باعث overlap/duplicate داده بین استان‌های همسایه می‌شه. اگه بخوای، می‌تونم نشونت بدم چطور با یه polygon clip واقعی (با geopandas/shapely) این مشکل رو حل کنی.

همه مشکلاتشو‌حل کن و اسکریپت کامل رو بده

باشه، همه‌چیز رو بررسی کردم (loader.py, core.py, packaging/create_abm.py, تست‌ها). حالا میرم سراغ پیاده‌سازی. این کار روی خود ریپازیتوری آپلودشده انجام می‌شه (نه یه اسکریپت جدا)، چون مشکلات در چند فایل به‌هم‌وابسته‌ان. رفع می‌کنم:

کلیپ کردن بر اساس پلیگان واقعی استان (نه فقط bbox مستطیلی) → حذف POI/فیچر تکراری در مرز استان‌های همسایه
آیدی هش fallback رو country-scoped می‌کنم
دقت‌گرد‌کردن dedup در map_db.py رو تنگ‌تر می‌کنم (۵→۶ رقم اعشار)
متادیتای صریح برای محدودیت corridor مسیریابی (max_offroute_corridor_km) اضافه می‌کنم تا اپ بتونه به کاربر هشدار بده
ابنجوری درستش


بله. روی ریپازیتوری آپلودشده اعمالش کردم و تست‌ها هم اجرا شدند.

تغییرات اصلی:

کلیپ منطقه‌ای با Polygon واقعی Admin-1 به‌جای bbox

routing corridor هم polygon-based شد، نه bbox-based

هیچ OSM way بریده نمی‌شود؛ کل way در صورت تقاطع نگه داشته می‌شود

fallback ID به شکل country-scoped deterministic hash

dedup مختصات از ۵ به ۶ رقم اعشار

اضافه شدن max_offroute_corridor_km به metadata برای اطلاع‌رسانی به اپ

اعتبارسنجی ABM برای اطمینان از polygon-based بودن region

پشتیبانی از GeoJSON خارجی با --boundaries

generator مناطق، هندسه واقعی Admin-1 را داخل config تولید می‌کند

وابستگی shapely>=2,<3

تست جدید برای false-positiveهای bbox و crossing way

تست نهایی:

28 passed, 1 skipped
فایل کامل پروژه اصلاح‌شده:

دانلود نسخه اصلاح‌شده AbtinMaps

نکته مهم: کانفیگ‌های regional قدیمی که فقط bbox دارند دیگر عمداً به‌عنوان مرز واقعی پذیرفته نمی‌شوند؛ باید GeoJSON Admin-1 واقعی را با --boundaries بدهند، یا config را با generate_regions_from_admin1.py تولید کنند. این کار جلوی برگشت تصادفی به معماری bbox-based را می‌گیرد.


ی redme.mdفارسی و انگلیسی بده

حتماً. این README دو زبانه را برای نسخه اصلاح‌شده آماده کردم؛ می‌توانی مستقیماً به‌عنوان README.md داخل ریشه پروژه قرار بدهی.

AbtinMaps — Regional Map Builder
سازنده نقشه‌های منطقه‌ای AbtinMaps
Version / نسخه: 2.x
Status / وضعیت: Production-oriented / آماده برای استفاده در محیط واقعی

🇬🇧 English
Overview
AbtinMaps is a regional offline-map build system designed to generate independent map databases for administrative regions such as provinces, states, or first-level administrative divisions.

Each region can be packaged as an independent map.sqlite / ABM map package while still supporting routing across administrative boundaries.

The regional architecture is designed around four principles:

Real administrative polygons instead of rectangular bounding boxes

Deterministic and country-scoped region IDs

Safe deduplication of nearby map features

Routing corridors that preserve complete OSM ways

Key Features
1. Polygon-based regional clipping
Regional data is clipped using the actual Admin-1 boundary polygon.

A simple bounding box is not considered a valid regional boundary.

This prevents problems such as:

POIs from neighboring regions appearing in the wrong region

duplicated roads and features along administrative borders

large empty areas being incorrectly included

irregular regions being treated as rectangles

The actual polygon is used for spatial membership and clipping decisions.

2. Routing corridor
Routing requires special handling near administrative borders.

A road may cross from one region into another. To prevent broken routing graphs, the builder supports a configurable routing corridor.

A way that intersects the routing corridor is retained as a complete OSM way instead of being geometrically cut at the regional boundary.

This prevents:

broken road segments

disconnected routing graphs

artificial dead ends at borders

The regional metadata also exposes:

{
  "max_offroute_corridor_km": 30.0
}
The application can use this value to determine when another regional map may be required.

3. Deterministic region IDs
Region IDs use the following priority:

ISO-3166-2 code
        ↓
country-scoped deterministic hash
Example:

IR-07
US-CA
DE-BY
If an official administrative code is unavailable, a deterministic fallback ID is generated from the country and normalized administrative name.

The fallback is therefore stable across builds.

4. Country-scoped fallback IDs
Fallback IDs are intentionally scoped to the country.

Conceptually:

ADM1_<country-scoped-hash>
This prevents accidental collisions when the same administrative name exists in different countries.

For example, identical or similar names in two countries do not share the same fallback namespace.

5. POI deduplication
Map features are deduplicated using:

name + category + rounded latitude + rounded longitude
The coordinate precision has been increased from five to six decimal places.

This reduces the chance of incorrectly merging very close but distinct POIs.

6. Complete-way routing
The builder does not split an OSM way merely because the way crosses an administrative boundary.

If a routing way intersects the configured corridor, the complete way is retained.

This is particularly important for:

highways

motorways

bridges

tunnels

long arterial roads

roads crossing provincial/state borders

Regional Data Model
A typical region contains:

Region
 ├── ID
 ├── Country
 ├── Name
 ├── ISO-3166-2 code
 ├── Admin-1 polygon
 ├── Bounding box (derived/auxiliary)
 ├── Routing corridor
 └── map.sqlite / ABM package
The bounding box may still be stored for fast indexing or download discovery, but it is not the authoritative regional boundary.

The polygon is authoritative.

Boundary Data
The preferred input is a GeoJSON dataset containing Admin-1 polygons.

Example:

python generate_regions_from_admin1.py \
    --boundaries boundaries.geojson \
    --countries countries.json
The generated region configuration should contain the actual polygon geometry or a reference to the corresponding geometry source.

Important
Old configurations containing only:

{
  "bbox": [...]
}
must not be treated as authoritative administrative boundaries.

They should be regenerated from real Admin-1 boundary data.

Requirements
Python 3.10+ is recommended.

Install dependencies:یلشو‌بده

pip install -r requirements.txt
The project requires Shapely 2.x:

shapely>=2,<3
Other dependencies are defined in requirements.txt.

Build
A typical regional build looks like:

python build_abm.py \
    --region IR-07 \
    --config regions.json
The exact arguments depend on the selected build workflow.

For a complete regional build, the process is conceptually:

Admin-1 boundaries
       ↓
Region generation
       ↓
OSM data acquisition
       ↓
Polygon filtering
       ↓
Routing corridor expansion
       ↓
POI / feature deduplication
       ↓
SQLite map database
       ↓
ABM packaging
Routing Behavior
Regional maps intentionally do not guarantee that every possible inter-region route exists inside a single regional package.


فایلشو‌بده

فایل README دو زبانه (فارسی + انگلیسی) آماده شد:

دانلود README.md 


README.md
Document


فایلی انتخاب نشده است
Library
/
README.md



AbtinMaps — Regional Map Builder
سازنده نقشه‌های منطقه‌ای AbtinMaps
Version / نسخه: 2.x

🇬🇧 English
Overview
AbtinMaps is a regional offline-map build system designed to generate independent map databases for administrative regions such as provinces, states, or first-level administrative divisions.

Each region can be packaged as an independent map.sqlite / ABM map package while still supporting routing across administrative boundaries.

The architecture is based on four principles:

Real administrative polygons instead of rectangular bounding boxes

Deterministic and country-scoped region IDs

Safe deduplication of nearby map features

Routing corridors that preserve complete OSM ways

Polygon-based regional clipping
Regional data is clipped using the actual Admin-1 boundary polygon.

A simple bounding box is not considered a valid regional boundary. The polygon prevents neighboring-region POIs and roads from being incorrectly included and avoids treating irregular administrative regions as rectangles.

The bounding box may still be stored for indexing or download discovery, but the polygon is authoritative.

Routing corridor
Roads can cross administrative boundaries. To avoid broken routing graphs, the builder supports a configurable routing corridor.

A way intersecting the corridor is retained as a complete OSM way instead of being cut at the administrative boundary.

This helps prevent broken road segments, disconnected routing graphs, and artificial dead ends.

Regional metadata can expose:

{
  "max_offroute_corridor_km": 30.0
}
The application can use this value to determine when another regional map may be required.

Deterministic region IDs
Region IDs use this priority:

ISO-3166-2 code
        ↓
country-scoped deterministic hash
If an official administrative code is unavailable, a deterministic fallback ID is generated from the country and normalized administrative name.

This keeps IDs stable between builds.

Country-scoped fallback IDs
Fallback IDs are scoped to the country:

ADM1_<country-scoped-hash>
This reduces collision risk when identical administrative names occur in different countries.

POI deduplication
Features are deduplicated using:

name + category + rounded latitude + rounded longitude
Coordinate precision is six decimal places instead of five, reducing the chance of incorrectly merging distinct nearby POIs.

Complete-way routing
An OSM way is not split merely because it crosses an administrative boundary.

If a routing way intersects the configured corridor, the complete way is retained.

This is important for highways, motorways, bridges, tunnels, and roads crossing provincial or state borders.

Regional data model
Region
 ├── ID
 ├── Country
 ├── Name
 ├── ISO-3166-2 code
 ├── Admin-1 polygon
 ├── Bounding box (derived/auxiliary)
 ├── Routing corridor
 └── map.sqlite / ABM package
Boundary data
The preferred input is a GeoJSON dataset containing Admin-1 polygons.

Example:

python generate_regions_from_admin1.py \
    --boundaries boundaries.geojson \
    --countries countries.json
Old configurations containing only:

{
  "bbox": [...]
}
must not be treated as authoritative administrative boundaries. Regenerate them from real Admin-1 boundary data.

Requirements
Python 3.10+ is recommended.

Install dependencies:

pip install -r requirements.txt
Required geometry dependency:

shapely>=2,<3
Build flow
Admin-1 boundaries
       ↓
Region generation
       ↓
OSM data acquisition
       ↓
Polygon filtering
       ↓
Routing corridor expansion
       ↓
POI / feature deduplication
       ↓
SQLite map database
       ↓
ABM packaging
Routing behavior
A regional package does not necessarily contain all data required for every inter-region route.

If the destination or required route is outside the configured corridor, the application should request or activate the corresponding neighboring regional map.

The metadata field:

max_offroute_corridor_km
exists specifically so the application can communicate this limitation clearly.

Validation
The build should validate:

Admin-1 polygon availability

valid region identifiers

country-scoped fallback IDs

polygon-based membership

routing corridor configuration

deduplication behavior

ABM package integrity

Testing
Run:

pytest -q
The test suite includes coverage for polygon clipping, boundary behavior, routing corridors, deterministic IDs, and deduplication.

🇮🇷 فارسی
معرفی
AbtinMaps یک سیستم ساخت نقشه آفلاین منطقه‌ای است که برای تولید دیتابیس مستقل برای استان‌ها، ایالت‌ها و سایر تقسیمات اداری سطح اول طراحی شده است.

هر منطقه می‌تواند یک map.sqlite یا بسته ABM مستقل داشته باشد و در عین حال مسیریابی در نزدیکی مرزهای اداری را پشتیبانی کند.

معماری بر چهار اصل اصلی استوار است:

استفاده از پلیگان واقعی مرز اداری به‌جای مستطیل Bounding Box

تولید ID قطعی و وابسته به کشور

Deduplication ایمن برای عوارض و POIهای نزدیک

حفظ کامل OSM Wayها در محدوده Routing Corridor

کلیپ واقعی با Polygon
مرز واقعی استان یا منطقه با پلیگان Admin-1 مشخص می‌شود.

Bounding Box فقط یک محدوده کمکی است و مرز واقعی منطقه محسوب نمی‌شود.

این روش از ورود اشتباه POIها و جاده‌های استان همسایه جلوگیری می‌کند و باعث می‌شود استان‌های با شکل نامنظم به‌درستی پردازش شوند.

Bounding Box همچنان می‌تواند برای Index یا پیدا کردن سریع داده استفاده شود، اما Polygon مرجع اصلی است.

Routing Corridor
بعضی جاده‌ها از مرز استان عبور می‌کنند. اگر چنین جاده‌ای دقیقاً در مرز قطع شود، گراف مسیریابی خراب خواهد شد.

به همین دلیل یک Routing Corridor قابل تنظیم وجود دارد.

اگر یک OSM Way با Corridor تداخل داشته باشد، Way به‌صورت کامل نگه داشته می‌شود و در مرز استان بریده نمی‌شود.

این موضوع برای:

آزادراه‌ها

بزرگراه‌ها

پل‌ها

تونل‌ها

جاده‌های اصلی

جاده‌های بین‌استانی

اهمیت زیادی دارد.

متادیتای منطقه می‌تواند شامل این مقدار باشد:

{
  "max_offroute_corridor_km": 30.0
}
اپلیکیشن می‌تواند از این مقدار برای تشخیص نیاز به دانلود نقشه منطقه دیگر استفاده کند.

سیستم ID مناطق
اولویت تولید ID به این شکل است:

ISO-3166-2
      ↓
هش قطعی وابسته به کشور
اگر کد رسمی ISO-3166-2 موجود نباشد، یک ID قطعی از کشور و نام نرمال‌شده منطقه ساخته می‌شود.

در نتیجه ID در Buildهای مختلف تغییر نمی‌کند.

Fallback ID وابسته به کشور
Fallback ID به کشور Scope می‌شود:

ADM1_<country-scoped-hash>
بنابراین اگر دو کشور منطقه‌ای با نام یکسان داشته باشند، احتمال Collision ناشی از نام یکسان کاهش پیدا می‌کند.

Deduplication
کلید Dedup به‌صورت مفهومی:

name + category + rounded latitude + rounded longitude
است.

دقت مختصات از ۵ رقم اعشار به ۶ رقم اعشار افزایش یافته است تا POIهای بسیار نزدیک ولی مستقل اشتباهاً یکی نشوند.

حفظ کامل Way
یک OSM Way صرفاً به‌خاطر عبور از مرز استان Split نمی‌شود.

اگر Way وارد Routing Corridor شود، کل Way نگه داشته می‌شود.

این رفتار برای جلوگیری از:

Road قطع‌شده

Dead End مصنوعی

گراف مسیریابی ناقص

قطع مسیرهای بین‌استانی

استفاده می‌شود.

ساختار منطقه
Region
 ├── ID
 ├── Country
 ├── Name
 ├── ISO-3166-2
 ├── Admin-1 Polygon
 ├── Bounding Box
 ├── Routing Corridor
 └── map.sqlite / ABM
داده مرزها
ورودی پیشنهادی، فایل GeoJSON شامل Polygonهای Admin-1 است.

نمونه:

python generate_regions_from_admin1.py \
    --boundaries boundaries.geojson \
    --countries countries.json
کانفیگ‌های قدیمی که فقط شامل:

{
  "bbox": [...]
}
هستند نباید به‌عنوان مرز واقعی استان استفاده شوند.

برای تولید صحیح منطقه‌ها باید از داده واقعی Admin-1 استفاده شود.

پیش‌نیازها
Python نسخه 3.10 یا بالاتر پیشنهاد می‌شود.

نصب وابستگی‌ها:

pip install -r requirements.txt
وابستگی اصلی هندسی:

shapely>=2,<3
روند Build
Admin-1 Polygon
       ↓
تولید Region
       ↓
دریافت OSM
       ↓
فیلتر Polygon
       ↓
اعمال Routing Corridor
       ↓
Deduplication
       ↓
ساخت map.sqlite
       ↓
ساخت بسته ABM
محدودیت مسیریابی
هر فایل منطقه‌ای الزاماً تمام داده موردنیاز برای هر مسیر بین‌استانی را ندارد.

اگر مقصد یا بخشی از مسیر خارج از Corridor باشد، اپلیکیشن باید نقشه منطقه مقصد یا منطقه موردنیاز را درخواست یا فعال کند.

فیلد:

max_offroute_corridor_km
برای همین منظور در Metadata قرار داده شده تا اپ بتواند محدودیت را به کاربر اعلام کند.

اعتبارسنجی
در Build باید موارد زیر بررسی شوند:

وجود Polygon واقعی Admin-1

معتبر بودن Region ID

وابسته بودن Fallback ID به کشور

استفاده از Polygon در Membership

معتبر بودن Routing Corridor

عملکرد Deduplication

صحت بسته ABM

اجرای تست‌ها
pytest -q
تست‌ها بخش‌های مهم شامل Polygon clipping، رفتار مرز، Routing Corridor، IDهای قطعی و Deduplication را پوشش می‌دهند.

License
See the repository license file.

مجوز
برای اطلاعات مجوز، فایل License موجود در ریشه پروژه را بررسی کنید.

