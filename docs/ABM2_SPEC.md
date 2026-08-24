# قرارداد ABM2 — بستهٔ نقشهٔ برداری آفلاین آبتین‌مپ

> **وضعیت:** طرح پیشنهادی برای تأیید پیش از پیاده‌سازی. ABM2 یک فرمت مستقل آبتین‌مپ است و از فایل، کد یا دادهٔ اختصاصی برنامه‌های دیگر استفاده نمی‌کند.

## 1. هدف

ABM2 جایگزین اطلس WebP می‌شود. سرور، دادهٔ خام OpenStreetMap را فقط یک‌بار به chunkهای برداری آماده تبدیل می‌کند؛ اپ نه PBF را پردازش می‌کند و نه نقشهٔ کامل کشور را می‌سازد. اپ فقط برای مربع‌های داخل viewport، یک lookup باینری در index انجام می‌دهد، chunk فشرده را seek می‌کند و بایت برداری آماده را به MapLibre می‌دهد. MapLibre همان دادهٔ آماده را با GPU رسم می‌کند.

این روش با «ساخت آمادهٔ نقشه روی سرور» سازگار است: کارهای سنگین شامل استخراج OSM، طبقه‌بندی، ساده‌سازی geometry، ساخت LOD، تولید graph، ساخت index و فشرده‌سازی روی سرور انجام می‌شود. draw نهاییِ GPU در گوشی فقط بخش اجتناب‌ناپذیر نمایش یک نقشهٔ برداری است.

## 2. فایل‌های یک کشور

| فایل | وظیفه | دانلود اولیه |
|---|---|---|
| `IR.abm2` | container اصلیِ tileهای برداری، index، رشته‌ها، search و graph | بله |
| `IR.abp2` | patch کوچک برای جایگزینی chunkهای تغییرکرده | فقط هنگام update |
| `catalog.json` | نسخه، SHA-256، حجم، محدوده، URL، قابلیت‌ها و patchها | بسیار کوچک |
| `IR.routes.abm2` | اختیاری؛ فقط برای کشورهایی که graph بزرگ دارند | در زمان فعال‌کردن مسیریابی آفلاین |

کشورهای کوچک در یک `*.abm2` نگه داشته می‌شوند. کشورهایی که از بودجهٔ دانلود عبور کنند در catalog به regionهای رسمی مانند `US-West` و `US-East` تقسیم می‌شوند؛ هر region یک فایل مستقل، پرچم یکسان و مرز دانلود روشن دارد.

## 3. Layout کلی فایل `*.abm2`

همهٔ عددهای fixed-width در ABM2 **little-endian** هستند. محتوای chunkها payload استاندارد برداری است و metadata داخلی ABM2 مستقل می‌ماند.

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Fixed Header — 256 bytes                                             │
├──────────────────────────────────────────────────────────────────────┤
│ String / style dictionaries (فشرده، append-only)                     │
├──────────────────────────────────────────────────────────────────────┤
│ Spatial index pages (IDX2، 4 KiB-aligned، بدون فشرده‌سازی)            │
├──────────────────────────────────────────────────────────────────────┤
│ Vector chunk blobs (VCH2؛ هر chunk جداگانه Zstd)                     │
├──────────────────────────────────────────────────────────────────────┤
│ Search index (SRH2؛ اختیاری)                                         │
├──────────────────────────────────────────────────────────────────────┤
│ Routing graph cells (RCH2؛ اختیاری یا فایل جدا)                      │
├──────────────────────────────────────────────────────────────────────┤
│ Footer / integrity manifest (FTR2)                                   │
└──────────────────────────────────────────────────────────────────────┘
```

## 4. Fixed Header — دقیقاً 256 بایت

| Offset | Size | نام | مقدار / کاربرد |
|---:|---:|---|---|
| `0x00` | 8 | `magic` | ASCII: `ABTIN2\0\0` |
| `0x08` | 2 | `major` | `2` |
| `0x0A` | 2 | `minor` | نسخهٔ سازگارِ کوچک؛ شروع از `0` |
| `0x0C` | 4 | `header_bytes` | همیشه `256` |
| `0x10` | 4 | `flags` | بیت‌های قابلیت: 3D، POI، search، graph، چپ‌رانی، patchable |
| `0x14` | 1 | `projection` | `1 = Web Mercator (EPSG:3857)` |
| `0x15` | 1 | `compression` | `1 = Zstd per chunk` |
| `0x16` | 1 | `min_zoom` | کمینهٔ دادهٔ نمایشی، معمولاً `3` |
| `0x17` | 1 | `max_zoom` | بیشینهٔ دادهٔ نمایشی، معمولاً `16` |
| `0x18` | 4 | `region_hash` | CRC32 کد region، مانند `IR` |
| `0x1C` | 16 | `package_uuid` | UUID ثابت همان build |
| `0x2C` | 16 | `base_uuid` | صفر برای full package؛ UUID پایه برای overlay/derived build |
| `0x3C` | 16 | `source_revision` | hash کوتاه PBF/style/config برای تشخیص تکرارپذیری build |
| `0x4C` | 16 | `bbox_e7` | `minLon, minLat, maxLon, maxLat`، هرکدام signed `int32` |
| `0x5C` | 8 | `created_unix_ms` | زمان ساخت |
| `0x64` | 8 | `index_offset` | شروع IDX2 |
| `0x6C` | 4 | `index_page_count` | تعداد صفحه‌های 4096‌بایتی index |
| `0x70` | 4 | `index_root_page` | شمارهٔ صفحهٔ root |
| `0x74` | 8 | `strings_offset` | شروع dictionary رشته‌ها |
| `0x7C` | 8 | `search_offset` | شروع SRH2؛ صفر یعنی وجود ندارد |
| `0x84` | 8 | `routing_offset` | شروع RCH2؛ صفر یعنی فایل جدا/وجود ندارد |
| `0x8C` | 8 | `footer_offset` | شروع FTR2 |
| `0x94` | 4 | `header_crc32` | CRC32 بایت‌های `0x00..0x93` |
| `0x98` | 104 | `reserved` | صفر؛ فقط برای توسعهٔ سازگار بعدی |

هر reader ابتدا magic، major، header size و CRC را کنترل می‌کند؛ ناسازگاری major باید خطای خوانا بدهد و هرگز با parser نسخهٔ قدیمی ادامه ندهد.

## 5. کلید spatial و مدل chunk

کلید هر chunk یک `uint64 tile_key` است:

```text
bits 63..58  = storage zoom (0..63)
bits 57..0   = Morton/Z-order interleave از x و y
```

برای هر zoom، `x` و `y` با Web Mercator محاسبه می‌شوند. Morton locality را حفظ می‌کند؛ بنابراین viewport با tileهای مجاور، seekهای نزدیک و cache مؤثر دارد.

chunkها تنها در zoomهای ذخیره‌ای ساخته می‌شوند:

| بازهٔ zoom نمایشی | zoom ذخیره‌ای | محتوای اصلی |
|---|---:|---|
| 3–6 | 5 | مرز کشور/استان، شهرهای اصلی، آب‌های بزرگ، motorway/trunk |
| 7–9 | 8 | شهرها، جاده‌های اصلی، راه‌آهن، landuse گسترده |
| 10–12 | 11 | جاده‌های شهری، POIهای منتخب، پارک‌ها |
| 13–14 | 13 | کوچه‌های لازم، POI کامل، ساختمان‌های مهم |
| 15–16 | 15 | ساختمان‌ها، آدرس/POI جزئی و geometry دقیق |

بازهٔ zoomهای view به نزدیک‌ترین storage zoom متصل می‌شود؛ بنابراین برای همهٔ ۱۷ سطح zoom کپی جداگانه تولید نمی‌شود. geometry در هر storage zoom یک‌بار با tolerance همان LOD ساده‌سازی می‌شود.

## 6. Index قابل seek — `IDX2`

صفحه‌های index همیشه 4096 بایت، aligned و بدون فشرده‌سازی هستند. reader برای هر viewport فقط root page و یک یا چند leaf page لازم را می‌خواند؛ قرار نیست کل index یا کل کشور در RAM بارگذاری شود.

### 6.1 صفحهٔ root

هر رکورد root، اولین `tile_key` موجود در یک leaf و شمارهٔ آن leaf را نگه می‌دارد. root با binary search، leaf مقصد را پیدا می‌کند.

```text
IDX2 root page
  4  magic = "IDX2"
  2  version = 1
  2  level = 1
  4  entry_count
  4  next_page = 0
  8  first_tile_key
  ... entries: { uint64 first_key, uint32 leaf_page, uint32 reserved }
```

### 6.2 صفحهٔ leaf

هر leaf شامل entryهای مرتب‌شدهٔ `tile_key` است. entry دقیقاً 48 بایت دارد:

| Field | Size | توضیح |
|---|---:|---|
| `tile_key` | 8 | کلید spatial |
| `layer_mask` | 4 | `base`, `poi`, `building`, `camera`, `label`, `terrain` |
| `chunk_flags` | 2 | وجود label/3D/traffic، کامل یا overlay |
| `feature_count` | 2 | تعداد featureهای chunk برای telemetry و guard |
| `blob_offset` | 8 | offset مطلق VCH2 داخل فایل |
| `stored_bytes` | 4 | اندازهٔ Zstd blob |
| `raw_bytes` | 4 | اندازهٔ payload پس از decompress |
| `raw_crc32` | 4 | کنترل فساد chunk |
| `content_hash64` | 8 | hash پایدار محتوا برای patch |
| `revision` | 4 | شمارهٔ revision همان chunk |

برای lookup یک tile: `tile_key → root binary search → leaf binary search → blob_offset`. نبود entry به معنی tile خالی است، نه خطا.

## 7. Vector chunk — `VCH2`

هر tile blob به‌شکل مستقل Zstd فشرده می‌شود. پس از decompress، payload چنین است:

```text
VCH2 chunk header
  4  magic = "VCH2"
  1  version
  1  storage_zoom
  2  section_count
  8  tile_key
  4  layer_mask
  4  payload_crc32

Section table: section_count × 16 bytes
  1  section_type
  1  codec = 0 (raw section in decompressed chunk)
  2  flags
  4  offset from start of payload
  4  bytes
  4  crc32
```

| `section_type` | نام | کاربرد |
|---:|---|---|
| 1 | `BASE_MVT` | راه‌ها، آب، زمین، مرزها؛ tile برداری آمادهٔ MapLibre |
| 2 | `POI_MVT` | POI، دوربین، چراغ، سرعت‌گیر؛ با خاموش/روشن‌کردن لایه |
| 3 | `BUILDING_MVT` | footprint و `height` برای extrusion سه‌بعدی |
| 4 | `LABEL_MVT` | نام خیابان/شهر/مکان؛ جدا برای کنترل زبان و تراکم |
| 5 | `ROUTE_HINT` | انتخابی؛ lane/turn metadata نمایشی |
| 6 | `TERRAIN` | انتخابی؛ elevation mesh یا contour |

هر `*_MVT` یک vector-tile payload آماده است. ABM2 v1 برای سازگاری با افزونهٔ فعلی Flutter، یک **local vector-tile bridge** دارد: هنگام انتخاب نقشهٔ دانلودشده، اپ یک HTTP server فقط روی `127.0.0.1` و یک port تصادفی باز می‌کند. style MapLibre منبع‌های برداری را به آدرس‌هایی مانند `http://127.0.0.1:<port>/v1/<session-token>/IR/base/{z}/{x}/{y}.pbf` وصل می‌کند.

Bridge کلید tile را می‌سازد، index را lookup می‌کند، chunk Zstd را از فایل می‌خواند و فقط section درخواست‌شده را به‌عنوان `application/x-protobuf` برمی‌گرداند. نتیجه MVT آماده مستقیماً به MapLibre می‌رسد؛ Dart هیچ way را به GeoJSON تبدیل نمی‌کند و `setGeoJsonSource` در هر camera idle فراخوانی نمی‌شود. در نسخهٔ بعد، همین interface می‌تواند با source نیتیو memory-mapped جایگزین شود، بدون تغییر در فایل ABM2 یا style.

## 8. دادهٔ مسیر‌یابی — `RCH2`

graph هیچ‌وقت از MVT بازسازی نمی‌شود. سرور همزمان با ساخت tileها، graph آمادهٔ مسیریابی را در cellهای بزرگ‌تر (storage zoom 12) می‌نویسد.

هر cell RCH2 شامل این بخش‌هاست:

| بخش | محتوا |
|---|---|
| `NODE` | `global_node_id`، مختصات local، محدودیت‌های عبور |
| `EDGE` | node مبدأ/مقصد، distance، زمان پایه، speed، one-way، toll، surface، bridge/tunnel |
| `TURN` | restrictionهای OSM برای turnهای ممنوع یا زمان‌دار |
| `PORTAL` | اتصال پایدار به nodeهای cell مجاور |
| `SPATIAL` | R-tree کوچک برای nearest-road و map matching |

روی موبایل فقط cellهای اطراف مبدأ/مقصد و کریدور route بارگذاری می‌شوند. برای مسیرهای بین‌شهری، graph در سطح coarse ابتدا corridor را پیدا می‌کند و سپس cellهای detailed همان corridor باز می‌شوند.

## 9. Search و زبان

`SRH2` از یک FST/تری فشرده تشکیل می‌شود و کلیدهای normalised شامل فارسی، عربی، لاتین، transliteration و نام جایگزین را نگه می‌دارد. هر hit به `poi_id` یا `feature_id` اشاره می‌کند؛ ویژگی کامل از chunk spatial خوانده می‌شود. بنابراین سرچ آفلاین بدون اسکن فایل کشور انجام می‌شود.

رشته‌ها در dictionary `STR2` append-only نگه‌داری می‌شوند. `string_id`های قدیمی هرگز تغییر نمی‌کنند تا chunkهای بدون تغییر و patchها معتبر بمانند.

## 10. update و patch — `ABP2`

`ABP2` فایل overlay مستقل است؛ فایل اصلی ۵۰۰ مگابایتی را rewrite نمی‌کند.

```text
ABP2 header
  base_package_uuid
  target_revision
  catalog_revision
  patch_sha256

operations (مرتب بر tile_key)
  REPLACE_TILE: tile_key + entry metadata + VCH2 blob
  DELETE_TILE:  tile_key
  REPLACE_ROUTE_CELL: cell_key + RCH2 blob
  APPEND_STRINGS: از string_id مشخص به بعد
  REPLACE_SEARCH_PAGE: page_id + bytes
```

reader همیشه ابتدا overlayهای معتبر را lookup می‌کند و سپس فایل پایه را. عملیات patch پس از verify SHA-256، CRC هر chunk و تطبیق `base_package_uuid` اتمیک فعال می‌شود. در صورت وجود بیش از سه overlay، اپ هنگام شارژ و فضای کافی یک compact merge محلی انجام می‌دهد.

## 11. جریان ساخت روی سرور

```text
OSM PBF
  → فیلتر و طبقه‌بندی قانونی OSM
  → name normalization + tag/style dictionaries
  → simplify بر اساس پنج LOD
  → برش geometry روی مرز storage tile
  → تولید MVT section برای هر layer
  → ساخت graph cells + search FST
  → Zstd per chunk
  → نوشتن IDX2 مرتب و catalog.json
  → SHA-256 / manifest / انتشار
```

مرحلهٔ WebP atlas در این جریان وجود ندارد. کیفیت خط، رنگ و عرض جاده در style MapLibre کنترل می‌شود؛ تغییر style بدون ساخت دوبارهٔ کل نقشه ممکن است، مگر اینکه layer یا attribute تازه نیاز باشد.

## 12. سازگاری با ABM v2 فعلی

ABM2 جایگزین نسخهٔ فعلی نمی‌شود مگر با `major=2` reader مستقل. دانلودهای `.abm` فعلی همچنان توسط reader ABM v2 باز می‌شوند. catalog با `format: abm-v2 | abm2` reader درست را انتخاب می‌کند. این راه مهاجرت بدون شکستن نقشه‌های قبلی را ممکن می‌کند.

## 13. معیار پذیرش نسخهٔ اول

| معیار | هدف |
|---|---|
| ساخت ایران | بدون مرحلهٔ رندر WebP و قابل اجرا در runner عادی |
| شروع نقشه پس از دانلود | بازشدن index بدون اسکن کل فایل |
| حرکت و زوم | cache حداقل 3×3 storage tile اطراف viewport |
| POI | خاموش/روشن فقط با تغییر layer، بدون build دوباره |
| 3D | extrusion فقط از section ساختمان، در zoomهای مجاز |
| update | patch فقط tile/cell تغییرکرده را دریافت کند |
| سازگاری | ABM v2 و ABM2 همزمان قابل نصب باشند |

## 14. سیاست نمایش آنی، cache و prefetch

### 14.1 قانون غیرقابل‌مذاکره

در زمان اجرای اپ این کارها **ممنوع** هستند: parse کردن OSM PBF، ساده‌سازی geometry، ساخت atlas، تولید WebP، تبدیل مجموعهٔ کامل wayها به GeoJSON و بازنویسی کامل source در هر حرکت دوربین. تمام این کارها فقط در server builder انجام می‌شوند.

کار مجاز در زمان اجرا فقط این زنجیره است: `tile URL → IDX2 lookup → seek blob → Zstd decompress → پاسخ MVT آماده → draw GPU`. خود draw GPU برای نمایش پیکسل اجتناب‌ناپذیر است، اما data build یا map render مجدد محسوب نمی‌شود.

### 14.2 cacheهای سه‌لایه

| لایه | محتوا | سقف و سیاست |
|---|---|---|
| `IndexCache` | root و leaf pageهای 4KiB IDX2 | همیشه حافظه؛ کمتر از 1MiB برای یک کشور |
| `CompressedChunkCache` | blobهای Zstd خوانده‌شدهٔ اخیر | LRU، 12MiB پیش‌فرض؛ برای برگشت سریع pan |
| `DecodedTileCache` | پاسخ MVT آماده برای MapLibre | LRU، 24MiB پیش‌فرض؛ کلید شامل region/revision/layer/z/x/y |

### 14.3 prefetch

هنگام open نقشه، bridge بدون انتظار رویداد camera idle، 3×3 tileهای storage zoom اطراف آخرین موقعیت ذخیره‌شده را به‌ترتیب نزدیک‌به‌دور آماده می‌کند. اگر آخرین موقعیت در دسترس نباشد، 3×3 tile اطراف مرکز region آماده می‌شوند.

در pan، الگوریتم velocity-aware یک ring در جهت حرکت و یک ring کوچک در جهت مخالف prefetch می‌کند. در zoom، ابتدا tileهای parent موجود نمایش داده می‌شوند و هم‌زمان tileهای سطح تازه خوانده می‌شوند؛ بنابراین صفحه هرگز با پس‌زمینهٔ خالی جایگزین نمی‌شود.

### 14.4 بودجهٔ عملکرد و benchmark

اعداد زیر معیار پذیرش prototype هستند و تا اندازه‌گیری روی APK، **هدف طراحی** محسوب می‌شوند:

| سناریو | معیار هدف روی Android میان‌رده با حافظهٔ UFS معمولی |
|---|---|
| بازکردن فایل/اعتبارسنجی header | P95 ≤ 25ms |
| lookup index برای یک tile | P95 ≤ 2ms |
| seek + decompress chunk عادی | P95 ≤ 15ms |
| warm start، 3×3 tile آخرین viewport | اولین نقشهٔ قابل استفاده ≤ 350ms |
| cold start، 3×3 tile آخرین viewport | اولین نقشهٔ قابل استفاده ≤ 900ms |
| pan یک viewport به tileهای cache‌شده | P95 ≤ 80ms |
| pan به tileهای روی دیسک اما خارج cache | P95 ≤ 180ms |
| zoom با parent fallback | بدون flash خالی؛ tile باکیفیت P95 ≤ 250ms |
| نرخ فریم gesture | 55fps یا بیشتر روی دستگاه مرجع |

هر benchmark باید timestampهای زیر را log کند: `file_open`, `index_lookup`, `disk_read`, `decompress`, `http_response`, `maplibre_tile_ready`, `first_rendered_frame`. عبور از معیارها مانع جایگزینی ABM v2 می‌شود.
