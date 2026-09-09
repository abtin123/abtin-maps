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


# Abtin Maps ABM builder (tile-free)

Builds `.abm` country archives for the Abtin Maps offline vector map engine.
An `.abm` file is a plain zip containing **only**:

```
metadata.json
vector/{roads,buildings,landuse,water,boundaries,places,terrain}.bin
poi/poi.sqlite
search/search.sqlite
routing/graph.bin
```

No tiles, no PMTiles/MBTiles, no style/color data. `metadata.json` carries
`"tiles": false`, `"style": "external"` and a `bbox` — `create_abm.py`
refuses to package (and `verify_abm.py` refuses to accept) anything that
doesn't hold, so a build can't silently regress into shipping a tile
container again.

## Basic build

```
pip install -r requirements.txt
python build_abm.py path/to/country.osm.pbf --country IR --output dist/IR.abm
```

Test locally without `osmium` using a `.jsonl` fixture (see
`sample/mini_country.jsonl` for the record shape):

```
python build_abm.py sample/mini_country.jsonl --country IR --output /tmp/IR.abm
```

## Large countries: real geographic regions

Countries too big for one archive (or one release asset) are split by
**bbox, not by bytes** — `--regions` clips the OSM dataset into named
regions *before* extraction/routing/search are built, so `US-NE.abm` and
`US-SW.abm` are genuinely separate, independently downloadable maps of
different parts of the country, not two arbitrary halves of the same file.

```
python build_abm.py us.osm.pbf --country US --regions regions/US.json --output dist/
```

See `sample/regions/US.json` for the config format: a country name plus a
list of `{code, name_fa, name_en, bbox}` regions. Adjacent regions'
bboxes are expected to overlap slightly at the edges — a road or building
that straddles the line is kept in both neighboring archives rather than
being cut in half.

This is unrelated to `packaging/split_abm.py`, which only exists to chop
an *already-built* single `.abm` into `.partNNN` byte chunks when it is
still over a hosting size cap (e.g. GitHub Release's ~2 GiB asset limit) —
it has no geography awareness at all and is a fallback of last resort, not
a substitute for `--regions`.

## Weekly updates → every country, delta patches

`.github/workflows/weekly-build.yml` runs every Monday and rebuilds **every
country listed in `countries.json`** (name, Geofabrik PBF URL, and an
optional `regions_config` for large countries) — not just one hardcoded
default. It's a 3-stage pipeline:

1. `discover` reads `countries.json` and expands it into a build matrix
   (one parallel job per country; `workflow_dispatch` with a `country`
   input can restrict this to a single code for a quick manual rebuild).
2. `build` (matrix, `fail-fast: false` so one broken country's PBF download
   doesn't cancel the other 30+) builds each country's `.abm`, splits it
   into byte parts if it's over the release size cap, and creates a delta
   patch against the previous `maps-v4` release when one exists.
3. `manifest` downloads every country's artifact, merges them into one
   `dist/`, and runs `build_release_manifest.py` once to produce the final
   `manifest.json` covering all of them.
4. `publish` (only on the scheduled run, or when triggered manually with
   `publish: true`) uploads everything to the `maps-v4` GitHub Release.

`packaging/create_patch.py` diffs each new archive against the previous
release in 4 MiB chunks and publishes only the chunks that changed, plus a
small JSON manifest describing them. The app only applies a patch when the
currently-installed archive's SHA-256 matches the patch's declared base —
otherwise it must fall back to a full re-download.

## Release manifest

`packaging/build_release_manifest.py` is the step that ties everything
together into the single `manifest.json` the app actually downloads and
parses (`MapCatalogService` / `MapRegion.fromJson`). Run it last, after
building and (if needed) splitting/patching every country for the release:

```
python packaging/build_release_manifest.py dist \
    --release-tag maps-v4 --names countries.json --output dist/manifest.json
```

It reads each `dist/CC.abm`'s own `metadata.json` for `bbox` and (for a
region) its parent country info, folds in `dist/CC-parts/manifest.json`
and `dist/CC-patch/patch-descriptor.json` when present, and looks up
display names for ordinary (non-region) countries from `countries.json`.

## Pipeline

```
build_abm.py
  └─ extractors/loader.py     OSM (.pbf via osmium, or .jsonl for tests) → Dataset
       └─ clip_dataset()      bbox clip for --regions (geographic split)
  └─ extractors/*.py          Dataset → Road/Building/Landuse/Water/Boundary/Place records
  └─ search/create_search_db.py   FTS5 + RTree search.sqlite, Persian-aware normalization
  └─ routing/graph_builder.py     routing/graph.bin (nodes, edges, turn restrictions)
  └─ packaging/create_abm.py      zips it all up, writes metadata.json (incl. bbox), verifies
  └─ packaging/split_abm.py       (only if over hosting size cap) byte-split into parts
  └─ packaging/create_patch.py    (only if a previous release exists) delta patch
  └─ packaging/build_release_manifest.py   assembles dist/manifest.json for the app
```

## Tests

No network is required; `tests/test_pipeline.py` uses the `.jsonl` fixtures
under `sample/`. Run with `pytest`, or execute the pipeline functions
directly if `pytest` isn't installed in your environment.
