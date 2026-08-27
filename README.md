# سازندهٔ نقشهٔ آفلاین آبتین

این پوشه **یک کشور را در یک فایل** می‌سازد. خروجی ایران دقیقاً `IR.abm` است؛ فایل جداگانه برای PMTiles یا graph منتشر نمی‌شود. پسوند فایل اختصاصی آبتین (`.abm`) است، اما ابتدای همان فایل یک PMTiles v3 استاندارد قرار دارد. در metadata همان PMTiles، offset بخش graph مسیریابی و styleهای روز/شب ثبت می‌شود. این طرح اجازه می‌دهد MapLibre دادهٔ برداری را با GPU بخواند و مسیریاب Flutter، graph خودش را از همان دانلود بخواند.

| بخش داخلی `IR.abm` | مصرف‌کننده | کاربرد |
|---|---|---|
| کاشی‌های برداری MVT در PMTiles | MapLibre Native | نقشهٔ آفلاین پیوسته، بدون Atlas raster و بزرگ‌کردن bitmap |
| `ABTINMAP v2` graph | `AbmRouter` | snap، مسیر میان‌شهری و گزینه‌های route |
| `styles/day.json` و `styles/night.json` | `VectorMapService` | رنگ‌بندی روز/شب بدون POI و بدون درخواست API |

> **هیچ فایل نقشه‌ای را در APK یا ZIP سورس نگذارید.** فایل‌های کشور باید فقط به‌عنوان asset یک GitHub Release نقشه منتشر شوند؛ app از manifest همان Release آن را دانلود و hash را کنترل می‌کند.

## فایل‌هایی که باید جایگزین/اضافه شوند

| مسیر در repository | وظیفه |
|---|---|
| `.github/workflows/build-offline-map.yml` | workflow دستی ساخت و انتشار مستقیم Release |
| `tool/maps/build_country_abm.sh` | orchestration دریافت PBF، تولید PMTiles، graph و container |
| `tool/maps/build_abm_graph.py` | ساخت graph واقعی ABTINMAP v2 از راه‌های خودرو در OSM PBF |
| `tool/maps/verify_abm_graph.py` | کنترل header، zstd، strings و index graph |
| `tool/maps/pack_abm_container.py` | قراردادن PMTiles، graph و style در یک `CC.abm` استاندارد |
| `tool/maps/update_map_manifest.py` | افزودن/جایگزینی کشور ساخته‌شده در `manifest.json` |
| `tool/maps/abtin_basemap.yml` | schema سبک Planetiler، بدون لایهٔ POI |
| `tool/maps/styles/day.json` و `tool/maps/styles/night.json` | styleهای محلی روز/شب |

## ساخت ایران از GitHub Actions

پس از commit این فایل‌ها در repository **خصوصی**، در تب **Actions** workflow با نام `Build offline country map` را باز کنید و **Run workflow** را بزنید. مقادیر پیش‌فرض برای ایران از قبل تنظیم شده‌اند. فقط `release_tag` باید با tag دانلود app یکی باشد؛ مقدار پیش‌فرض `maps-v3` است و با آدرس دانلود فعلی app یکی است.

| ورودی workflow | مقدار ایران |
|---|---|
| `country_code` | `IR` |
| `pbf_url` | `https://download.geofabrik.de/asia/iran-latest.osm.pbf` |
| `name_fa` | `ایران` |
| `name_en` | `Iran` |
| `bbox` | `44.0,25.0,64.5,40.5` |
| `release_tag` | `maps-v3` |

در پایان موفق، فقط این دو asset روی همان GitHub Release وجود خواهند داشت: `IR.abm` و `manifest.json`. بار بعدی که کشور دیگری می‌سازید، workflow manifest قبلی را دریافت می‌کند، همان کشور را با نسخه تازه جایگزین می‌کند و بقیهٔ entryها را حفظ می‌کند. اجرای هم‌زمان برای یک tag با `concurrency` صف می‌شود تا manifest خراب نشود. workflow هیچ artifact تکراری آپلود نمی‌کند.

## اجرای محلی

اجرای محلی به Docker، Python 3 و PMTiles CLI نیاز دارد. مسیر خروجی پیش از mount به Docker به مسیر مطلق تبدیل می‌شود؛ بنابراین خطای `invalid characters for a local volume name` که در اجرای قبلی رخ داد، دیگر نباید تکرار شود. Planetiler داخل Docker ساخته می‌شود تا Java/وابستگی‌های آن روی سیستم شما نصب نشود. برای ایران، فرمان زیر را در ریشهٔ repository اجرا کنید:

```bash
chmod +x tool/maps/build_country_abm.sh
tool/maps/build_country_abm.sh IR https://download.geofabrik.de/asia/iran-latest.osm.pbf dist
```

این فرمان `dist/IR.abm` را می‌سازد. پیش از موفقیت نهایی، script PMTiles payload و سپس فایل نهایی `.abm` را با `pmtiles verify` کنترل می‌کند و graph را با `verify_abm_graph.py` می‌سنجد. فایل نهایی از نظر ساختار PMTiles استاندارد است و با وجود پسوند `.abm` باید توسط verifier پذیرفته شود.

## محدودیت‌های مهم و واقعی

این script از **snapshot کامل** OSM PBF استفاده می‌کند. هر build کشور، نسخهٔ جدید همان PBF را دریافت می‌کند و کل `CC.abm` را دوباره تولید می‌کند؛ PMTiles برای patch درجا طراحی نشده است. بنابراین client فقط وقتی archive جدید را دانلود می‌کند که SHA-256 در manifest تغییر کرده باشد. «دانلود فقط تغییرهای OSM» با یک فایل archive تک‌فایلی ممکن نیست، مگر اینکه سمت سرور یک protocol patch جدا و client patcher امن طراحی شود؛ این workflow عمداً چنین ادعایی ندارد.[1]

برای کشورهایی که archive نهایی از سقف asset گیت‌هاب بزرگ‌تر شود، ساخت تک‌فایل قابل انتشار در GitHub Release نیست. در آن حالت باید zoom/building detail را کم کرد یا یک object storage مناسبِ فایل‌های بزرگ انتخاب کرد؛ graph و PMTiles همچنان داخل **یک فایل دانلودی `CC.abm`** می‌مانند. از شکستن graph و display به دو asset جدا استفاده نکنید.

نقشهٔ برداری schema حاضر POI سراسری ندارد، مطابق خواستهٔ پروژه. POIهای محلی بعداً باید فقط از دادهٔ واقعی ABM به‌صورت overlay MapLibre اضافه شوند. رنگ‌بندی پایه داخل دو style ثابت روز/شب آمده است و route overlay مستقل از style باقی می‌ماند.

## اعتبارسنجی انجام‌شده

این pipeline با extract واقعی Liechtenstein اجرا شد: Planetiler از PBF خروجی MVT PMTiles ساخت؛ graph شامل **55,955 segment جاده‌ای** و **1 tile** بود؛ سپس هر دو در یک `LI.abm` قرار گرفتند. `pmtiles verify LI.abm` با موفقیت انجام شد و reader Flutter نیز metadata داخلی، graph و هر دو style را باز کرد. این یک آزمون ساختار/دادهٔ کوچک است؛ آزمون تصویری MapLibre روی Android واقعی برای ایران هنوز لازم است.

## منابع

[1] [PMTiles CLI and archive operations](https://docs.protomaps.com/pmtiles/cli)

[2] [Planetiler custom map schema](https://github.com/onthegomap/planetiler/tree/main/planetiler-custommap)

[3] [OpenStreetMap copyright and attribution](https://www.openstreetmap.org/copyright)
