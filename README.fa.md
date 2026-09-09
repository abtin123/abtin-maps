# سازنده‌ی ABM نقشه‌های آبتین (بدون تایل)

آرشیوهای کشوری `.abm` رو برای موتور نقشه‌ی برداری آفلاین آبتین می‌سازه.
یک فایل `.abm` صرفاً یک zip ساده است که **فقط** شامل این‌ها می‌شه:

```
metadata.json
vector/{roads,buildings,landuse,water,boundaries,places,terrain}.bin
poi/poi.sqlite
search/search.sqlite
routing/graph.bin
```

هیچ تایلی، هیچ PMTiles/MBTiles‌ای، و هیچ داده‌ی استایل/رنگی توش نیست.
`metadata.json` مقادیر `"tiles": false`، `"style": "external"` و یک `bbox`
رو با خودش حمل می‌کنه — `create_abm.py` از بسته‌بندی چیزی که این شرایط رو
نداشته باشه خودداری می‌کنه (و `verify_abm.py` هم آن را نمی‌پذیرد)، تا یک
build هیچ‌وقت بی‌سروصدا به عقب برنگرده و دوباره یک container تایل تحویل نده.

## ساخت پایه

```
pip install -r requirements.txt
python build_abm.py path/to/country.osm.pbf --country IR --output dist/IR.abm
```

برای تست محلی بدون نیاز به `osmium`، از یک فیکسچر `.jsonl` استفاده کنید
(برای شکل رکوردها به `sample/mini_country.jsonl` نگاه کنید):

```
python build_abm.py sample/mini_country.jsonl --country IR --output /tmp/IR.abm
```

## کشورهای بزرگ: مناطق جغرافیایی واقعی

کشورهایی که برای یک آرشیو (یا یک asset انتشار) خیلی بزرگ‌اند، بر اساس
**bbox تقسیم می‌شن، نه بر اساس بایت** — گزینه‌ی `--regions` دیتاست OSM رو
*پیش از* ساخت extraction/routing/search به مناطق نام‌گذاری‌شده کلیپ می‌کنه،
پس `US-NE.abm` و `US-SW.abm` واقعاً دو نقشه‌ی مستقل و قابل‌دانلود جداگانه
از بخش‌های متفاوت کشورند، نه دو نیمه‌ی دلبخواهی از یک فایل واحد.

```
python build_abm.py us.osm.pbf --country US --regions regions/US.json --output dist/
```

برای فرمت تنظیمات به `sample/regions/US.json` نگاه کنید: یک نام کشور به‌همراه
لیستی از مناطق با ساختار `{code, name_fa, name_en, bbox}`. انتظار می‌ره
bboxهای مناطق مجاور در لبه‌ها کمی هم‌پوشانی داشته باشند — یک جاده یا ساختمان
که روی مرز قرار می‌گیرد، به‌جای این‌که نصف بشه، در هر دو آرشیو همسایه حفظ می‌شه.

این موضوع ربطی به `packaging/split_abm.py` نداره؛ آن اسکریپت فقط برای این
وجود دارد که یک `.abm` *از‌قبل‌ساخته‌شده* را وقتی هنوز از سقف حجم هاستینگ
(مثلاً محدودیت حدود ۲ گیگابایتی asset در GitHub Release) بیشتر باشد، به
تکه‌های `.partNNN` بایتی خرد کند — هیچ آگاهی جغرافیایی ندارد و صرفاً یک
راه‌حل آخر است، نه جایگزینی برای `--regions`.

## به‌روزرسانی هفتگی → همه‌ی کشورها، پچ‌های دلتا

`.github/workflows/weekly-build.yml` هر دوشنبه اجرا می‌شه و **همه‌ی
کشورهای فهرست‌شده در `countries.json`** (نام، آدرس PBF مربوط به Geofabrik،
و یک `regions_config` اختیاری برای کشورهای بزرگ) را بازسازی می‌کند — نه
فقط یک پیش‌فرضِ ثابت. این یک pipeline سه‌مرحله‌ای است:

۱. مرحله‌ی `discover`، فایل `countries.json` را می‌خواند و آن را به یک
   matrix ساخت تبدیل می‌کند (یک job موازی برای هر کشور؛ با
   `workflow_dispatch` و ورودی `country` می‌توان این کار را به یک کد
   خاص برای بازسازی سریع دستی محدود کرد).
۲. مرحله‌ی `build` (به‌صورت matrix، با `fail-fast: false` تا خرابیِ دانلود
   PBF یک کشور باعث لغو بقیه‌ی بیش از ۳۰ کشور نشود) فایل `.abm` هر کشور را
   می‌سازد، در صورت عبور از سقف حجم انتشار آن را به قطعات بایتی تقسیم
   می‌کند، و در صورت وجود انتشار قبلی، یک پچ دلتا نسبت به آن می‌سازد.
۳. مرحله‌ی `manifest` artifact هر کشور را دانلود می‌کند، همه را در یک
   پوشه‌ی `dist/` ادغام می‌کند، و یک‌بار `build_release_manifest.py` را
   اجرا می‌کند تا `manifest.json` نهایی که همه‌ی کشورها را پوشش می‌دهد
   ساخته شود.
۴. مرحله‌ی `publish` (فقط در اجرای زمان‌بندی‌شده، یا وقتی به‌صورت دستی با
   `publish: true` اجرا شود) همه‌چیز را در انتشار `maps-v4` گیت‌هاب
   آپلود می‌کند.

`packaging/create_patch.py` هر آرشیو جدید را نسبت به انتشار قبلی در
تکه‌های ۴ مگابایتی مقایسه می‌کند و فقط تکه‌هایی را که تغییر کرده‌اند
منتشر می‌کند، به‌همراه یک manifest کوچک JSON که آن‌ها را توصیف می‌کند.
اپلیکیشن فقط زمانی یک پچ را اعمال می‌کند که SHA-256 آرشیو نصب‌شده‌ی
فعلی با پایه‌ی اعلام‌شده‌ی پچ مطابقت داشته باشد — در غیر این صورت باید
به دانلود کامل بازگردد.

## Manifest انتشار

`packaging/build_release_manifest.py` مرحله‌ای است که همه‌چیز را به هم
گره می‌زند و یک `manifest.json` واحد می‌سازد که اپلیکیشن واقعاً آن را
دانلود و پارس می‌کند (`MapCatalogService` / `MapRegion.fromJson`). آن را
آخرین قدم، بعد از ساخت و (در صورت نیاز) تقسیم/پچ‌کردنِ هر کشور برای
انتشار، اجرا کنید:

```
python packaging/build_release_manifest.py dist \
    --release-tag maps-v4 --names countries.json --output dist/manifest.json
```

این اسکریپت مقدار `bbox` را از `metadata.json` خودِ هر `dist/CC.abm`
می‌خواند و (برای یک منطقه) اطلاعات کشور مادرش را هم می‌خواند، در صورت
وجود `dist/CC-parts/manifest.json` و `dist/CC-patch/patch-descriptor.json`
را در خودش ادغام می‌کند، و برای کشورهای عادی (غیرمنطقه‌ای) نام‌های
نمایشی را از `countries.json` پیدا می‌کند.

## Pipeline

```
build_abm.py
  └─ extractors/loader.py     OSM (.pbf از طریق osmium، یا .jsonl برای تست‌ها) → Dataset
       └─ clip_dataset()      کلیپ bbox برای --regions (تقسیم جغرافیایی)
  └─ extractors/*.py          Dataset → رکوردهای Road/Building/Landuse/Water/Boundary/Place
  └─ search/create_search_db.py   ساخت search.sqlite با FTS5 + RTree، نرمال‌سازی آگاه از فارسی
  └─ routing/graph_builder.py     routing/graph.bin (گره‌ها، یال‌ها، محدودیت‌های گردش)
  └─ packaging/create_abm.py      همه را zip می‌کند، metadata.json (شامل bbox) را می‌نویسد، اعتبارسنجی می‌کند
  └─ packaging/split_abm.py       (فقط اگر از سقف حجم هاستینگ بیشتر باشد) تقسیم بایتی به قطعات
  └─ packaging/create_patch.py    (فقط اگر انتشار قبلی وجود داشته باشد) پچ دلتا
  └─ packaging/build_release_manifest.py   ساخت dist/manifest.json برای اپلیکیشن
```

## تست‌ها

نیازی به شبکه نیست؛ `tests/test_pipeline.py` از فیکسچرهای `.jsonl` زیر
پوشه‌ی `sample/` استفاده می‌کند. با `pytest` اجرایش کنید، یا اگر `pytest`
در محیط شما نصب نیست، مستقیماً توابع pipeline را اجرا کنید.
