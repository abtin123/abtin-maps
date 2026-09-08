# Abtin Maps — Offline Map Builder

این repository سازندهٔ واقعی فایل‌های آفلاین `ABTINMAP v4` برای Abtin Maps است.

اپ فعلی از Release زیر می‌خواند:

```text
https://github.com/abtin123/abtin-maps/releases/download/maps-v4/
```

بنابراین **tag باید `maps-v4` باشد** مگر اینکه عمداً آن را در workflow تغییر دهید.

## ساخت مپ

Workflow اصلی:

```text
.github/workflows/build-offline-map-v4.yml
```

به‌صورت پیش‌فرض فقط ایران ساخته می‌شود:

```text
COUNTRY_SELECTOR=IR
RELEASE_TAG=maps-v4
```

از GitHub بروید به:

```text
Actions → Build offline maps v4 → Run workflow
```

و اجرا کنید.

### ساخت همه کشورها

در `Run workflow` مقدار زیر را بدهید:

```text
country_selector = ALL
```

یا برای حذف چند کشور:

```text
ALL/IR/AZ/TR
```

برای چند کشور مشخص هم می‌توانید کدهایشان را با `/` بدهید.

## فرآیند ساخت

```text
Geofabrik OSM PBF
        ↓
Planetiler
        ↓
vector.pmtiles
        ↓
build_abm_graph.py
        ↓
routing graph
        ↓
build_search_index.py
        ↓
search.sqlite
        ↓
pack_abm_container.py
        ↓
XX.abm
        ↓
verify_abm_container.py
        ↓
GitHub Release: maps-v4
```

فایل نهایی کشور، مثلاً `IR.abm`، یک فایل داده‌ای واحد است و شامل PMTiles برداری، routing graph و search database است. style/glyph/sprite در اپ قرار دارند و داخل هر کشور تکرار نمی‌شوند.

## آپدیت هفتگی

Workflow هر دوشنبه اجرا می‌شود و source signature مربوط به extractهای Geofabrik را بررسی می‌کند.

اگر source signature یک کشور تغییر نکرده باشد، آن کشور دوباره ساخته نمی‌شود. اگر تغییر کرده باشد، فقط همان extract دوباره ساخته می‌شود.

برای ABM تغییرکرده، workflow در صورت کوچک‌تر بودن patch نسبت به فایل کامل، `ABTINMAP-CHUNK-PATCH/1` می‌سازد و patch را کنار Release منتشر می‌کند.

## Release

Release شامل موارد زیر است:

```text
IR.abm
manifest.json
build-report.json
IR.patch.json       # فقط اگر patch مفید باشد
IR.patch.bin        # فقط اگر patch مفید باشد
```

برای ABMهای بزرگ‌تر از سقف asset گیت‌هاب، `split_abm.py` فایل را به قسمت‌های زیر 2GiB تقسیم می‌کند:

```text
XX.abm.part0
XX.abm.part1
...
```

manifest hash مربوط به فایل کامل و concatenated است.

## وابستگی‌ها

Runner اوبونتو به این موارد نیاز دارد:

- Docker برای Planetiler
- `osmium-tool` برای extractهای دارای bbox
- PMTiles CLI
- Python 3.13
- `osmium`, `zstandard`, `brotli`

Python dependencyها در `requirements.txt` هستند.

## اجرای دستی محلی

در root repository:

```bash
chmod +x tool/maps/build_country_abm.sh
python3 -m pip install -r requirements.txt
./tool/maps/build_country_abm.sh IR \
  https://download.geofabrik.de/asia/iran-latest.osm.pbf \
  dist
```

خروجی:

```text
dist/IR.abm
dist/IR.abm.zip
```

## نکته مهم

فایل‌های بزرگ `.abm` را داخل Git commit نکنید. خروجی واقعی نقشه باید فقط در **GitHub Release** منتشر شود و اپ از `maps-v4` دانلود کند.

منبع داده: © OpenStreetMap contributors، با دادهٔ extract شده از Geofabrik.
