# AbtinMaps ABM Map Builder

**English | فارسی**

---

## 🇬🇧 English

### Overview

**AbtinMaps ABM Map Builder** generates offline `.abm` map packages for AbtinMaps.

It processes OpenStreetMap `.osm.pbf` data, builds map and routing data, validates the result, and can publish ABM files through GitHub Actions.

### Features

- Country-level map generation
- First-level administrative region generation
- Separate ABM packages for regions
- Offline routing data
- Routing continuity across regional boundaries
- Incremental map updates
- Release manifests
- Automatic rebuild detection
- GitHub Actions publishing

### 🗺️ Map Architecture

When regional configuration is available, a country can be divided into first-level administrative regions.

Depending on the country, these can be states, provinces, departments, regions, governorates, or other first-level administrative divisions.

```text
Country
├── Region 1
│   └── Region1.abm
├── Region 2
│   └── Region2.abm
└── Region 3
    └── Region3.abm
```

Countries without regional configuration can still be generated as one country-level `.abm` file.

### 🧭 Routing Continuity

Regional maps are not created by simply cutting roads at administrative boundaries.

The routing builder keeps complete OSM ways that intersect a region, preserving road geometry across region boundaries.

Regional routing uses:

- OSM node IDs
- Complete OSM way geometry
- Expanded routing bounding boxes
- Configurable regional overlap

Default routing overlap:

```text
0.25°
```

Routing geometry policy:

```text
never_clip_osm_way
```

### 🌍 Country Configuration

Country definitions are stored in:

```text
countries.json
```

Example:

```json
{
  "pbf_url": "...",
  "iso3": "IRN"
}
```

A country can optionally define a regional configuration:

```json
{
  "pbf_url": "...",
  "iso3": "USA",
  "regions_config": "sample/regions/US.json"
}
```

### 🏛️ Automatic Region Generation

The builder includes:

```text
tools/generate_regions_from_admin1.py
```

It generates first-level administrative region configurations from the Admin-1 dataset.

Example output:

```json
{
  "country_code": "IR",
  "region_level": "admin1",
  "routing_overlap_degrees": 0.25,
  "regions": [
    {
      "code": "...",
      "name_fa": "...",
      "name_en": "...",
      "bbox": [0, 0, 0, 0],
      "routing_overlap_degrees": 0.25
    }
  ]
}
```

ISO-3166-2 is used when available; otherwise a deterministic region ID is generated.

### 📦 ABM Output

Final map format:

```text
.abm
```

Examples:

```text
IR.abm
IR_01.abm
IR_02.abm
IR_03.abm
```

Exact regional filenames are determined by the region configuration.

### 🔄 Incremental Builds

The GitHub Actions workflow checks whether the map source or builder inputs have changed.

If nothing relevant changed:

```text
No PBF download
No ABM rebuild
```

If a rebuild is required:

```text
Download PBF
    ↓
Build ABM
    ↓
Validate
    ↓
Create manifest
    ↓
Publish changed assets
```

### 🚀 GitHub Actions

Main workflow:

```text
.github/workflows/Build-and-publish-ABM-complete.yml
```

It supports manual and scheduled execution.

Example country selection:

```text
IR
AM
IR,AM
all
```

The country list comes from:

```text
countries.json
```

### 🔧 Build Commands

Country-level:

```bash
python3 build_abm.py source/input.osm.pbf   --country IR   --output dist/IR.abm
```

Regional:

```bash
python3 build_abm.py source/input.osm.pbf   --country IR   --regions regions.json   --output dist/
```

### 🧪 Testing

Run tests:

```bash
python3 -m pytest -q
```

Check Python syntax:

```bash
python3 -m compileall -q   build_abm.py   abm_builder   extractors   routing   packaging   tests
```

The workflow also validates ABM files, release manifests, asset sizes, regional metadata, routing metadata, and repository tests.

### 📋 Release Manifest

The release manifest lets the application discover:

- Available countries
- Available regions
- Map versions
- Map assets
- Updated assets
- Existing assets
- Release information

Unchanged assets do not need to be rebuilt.

### 📁 Project Structure

```text
.
├── build_abm.py
├── countries.json
├── requirements.txt
├── abm_builder/
├── extractors/
├── routing/
├── packaging/
│   ├── build_release_manifest.py
│   ├── check_source.py
│   ├── create_abm.py
│   └── prepare_release.py
├── tools/
│   └── generate_regions_from_admin1.py
├── sample/
│   └── regions/
│       └── US.json
├── tests/
└── .github/
    └── workflows/
        └── Build-and-publish-ABM-complete.yml
```

### 🌐 Administrative Region Data

Automatic Admin-1 generation uses the published Natural Earth Admin-1 dataset through its GeoJSON distribution.

Source:

https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/

Data distribution:

https://datahub.io/core/geo-ne-admin1

### ⚠️ Current Scope

Regional generation is automatic for countries configured in `countries.json` when usable Admin-1 data is available.

Countries without usable Admin-1 records fall back to country-level map generation.

### 📱 Application Compatibility

Generated `.abm` files are intended for the AbtinMaps Flutter application. The application can use the release manifest to discover available map packages and download the required map data.

---

# 🇮🇷 فارسی

## معرفی

**AbtinMaps ABM Map Builder** سیستم ساخت نقشه آفلاین پروژه AbtinMaps است.

این سیستم داده‌های OpenStreetMap با فرمت `.osm.pbf` را دریافت می‌کند، داده‌های نقشه و مسیریابی را پردازش می‌کند، فایل ABM تولیدشده را اعتبارسنجی می‌کند و در صورت استفاده از GitHub Actions آن را در Release منتشر می‌کند.

### قابلیت‌ها

- ساخت نقشه در سطح کشور
- ساخت نقشه بر اساس تقسیمات اداری سطح اول
- تولید فایل جداگانه برای مناطق
- داده مسیریابی آفلاین
- حفظ پیوستگی جاده‌ها بین مناطق
- به‌روزرسانی افزایشی نقشه
- Release Manifest
- تشخیص نیاز به بازسازی
- ساخت و انتشار خودکار با GitHub Actions

## 🗺️ ساختار نقشه

در صورت وجود تنظیمات منطقه‌ای، کشور به تقسیمات اداری سطح اول خودش تقسیم می‌شود.

بسته به کشور این تقسیمات می‌توانند شامل استان، ایالت، دپارتمان، منطقه، فرمانداری یا سایر تقسیمات اداری سطح اول باشند.

```text
کشور
├── منطقه ۱
│   └── Region1.abm
├── منطقه ۲
│   └── Region2.abm
└── منطقه ۳
    └── Region3.abm
```

کشورهایی که تنظیمات منطقه‌ای ندارند همچنان می‌توانند به‌صورت یک فایل `.abm` برای کل کشور ساخته شوند.

## 🧭 پیوستگی مسیریابی

نقشه‌های منطقه‌ای صرفاً با بریدن جاده‌ها در مرز مناطق ساخته نمی‌شوند.

اگر یک راه OSM از محدوده یک منطقه عبور کند، Builder هندسه کامل آن Way را حفظ می‌کند تا جاده در مرز مناطق قطع نشود.

سیستم از موارد زیر استفاده می‌کند:

- شناسه Node در OSM
- هندسه کامل Way
- Bounding Box توسعه‌یافته برای Routing
- Overlap قابل تنظیم بین مناطق

Overlap پیش‌فرض:

```text
0.25°
```

سیاست هندسه Routing:

```text
never_clip_osm_way
```

## 🌍 تنظیمات کشورها

تنظیمات کشورها در:

```text
countries.json
```

قرار دارد.

مثال:

```json
{
  "pbf_url": "...",
  "iso3": "IRN"
}
```

یک کشور می‌تواند تنظیمات مناطق خودش را نیز داشته باشد:

```json
{
  "pbf_url": "...",
  "iso3": "USA",
  "regions_config": "sample/regions/US.json"
}
```

## 🏛️ ساخت خودکار مناطق

ابزار:

```text
tools/generate_regions_from_admin1.py
```

برای تولید خودکار تنظیمات تقسیمات اداری سطح اول استفاده می‌شود.

نمونه خروجی:

```json
{
  "country_code": "IR",
  "region_level": "admin1",
  "routing_overlap_degrees": 0.25,
  "regions": [
    {
      "code": "...",
      "name_fa": "...",
      "name_en": "...",
      "bbox": [0, 0, 0, 0],
      "routing_overlap_degrees": 0.25
    }
  ]
}
```

اگر کد ISO-3166-2 برای منطقه وجود داشته باشد از همان استفاده می‌شود؛ در غیر این صورت یک شناسه پایدار برای منطقه ساخته می‌شود.

## 📦 خروجی ABM

فرمت نهایی نقشه:

```text
.abm
```

مثال:

```text
IR.abm
IR_01.abm
IR_02.abm
IR_03.abm
```

نام دقیق فایل‌های مناطق از تنظیمات منطقه‌ای تعیین می‌شود.

## 🔄 ساخت افزایشی

GitHub Actions بررسی می‌کند که منبع نقشه یا ورودی‌های Builder تغییر کرده‌اند یا خیر.

اگر تغییری وجود نداشته باشد:

```text
PBF دوباره دانلود نمی‌شود
ABM دوباره ساخته نمی‌شود
```

اگر نیاز به ساخت مجدد باشد:

```text
دریافت PBF
    ↓
ساخت ABM
    ↓
اعتبارسنجی
    ↓
ساخت Manifest
    ↓
انتشار فایل‌های تغییرکرده
```

## 🚀 GitHub Actions

Workflow اصلی:

```text
.github/workflows/Build-and-publish-ABM-complete.yml
```

قابلیت اجرای دستی و زمان‌بندی‌شده دارد.

نمونه انتخاب کشور:

```text
IR
AM
IR,AM
all
```

لیست کشورها از:

```text
countries.json
```

خوانده می‌شود.

## 🔧 دستورات ساخت

ساخت نقشه یک کشور:

```bash
python3 build_abm.py source/input.osm.pbf   --country IR   --output dist/IR.abm
```

ساخت منطقه‌ای:

```bash
python3 build_abm.py source/input.osm.pbf   --country IR   --regions regions.json   --output dist/
```

## 🧪 تست

اجرای تست‌ها:

```bash
python3 -m pytest -q
```

بررسی Syntax:

```bash
python3 -m compileall -q   build_abm.py   abm_builder   extractors   routing   packaging   tests
```

Workflow نیز فایل‌های ABM، Manifest، حجم Assetها، Metadata مناطق، Metadata مربوط به Routing و تست‌های Builder را بررسی می‌کند.

## 📋 Release Manifest

Manifest اطلاعات زیر را در اختیار برنامه قرار می‌دهد:

- کشورهای موجود
- مناطق موجود
- نسخه نقشه
- فایل‌های نقشه
- فایل‌های به‌روزشده
- فایل‌های موجود
- اطلاعات Release

فایل‌های بدون تغییر نیاز به ساخت مجدد ندارند.

## 📁 ساختار پروژه

```text
.
├── build_abm.py
├── countries.json
├── requirements.txt
├── abm_builder/
├── extractors/
├── routing/
├── packaging/
│   ├── build_release_manifest.py
│   ├── check_source.py
│   ├── create_abm.py
│   └── prepare_release.py
├── tools/
│   └── generate_regions_from_admin1.py
├── sample/
│   └── regions/
│       └── US.json
├── tests/
└── .github/
    └── workflows/
        └── Build-and-publish-ABM-complete.yml
```

## 🌐 منبع تقسیمات اداری

برای ساخت خودکار مناطق Admin-1 از دیتاست منتشرشده Natural Earth استفاده می‌شود.

منبع:

https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/

توزیع GeoJSON:

https://datahub.io/core/geo-ne-admin1

## ⚠️ محدوده فعلی

ساخت منطقه‌ای برای کشورهایی که در `countries.json` تعریف شده‌اند و داده Admin-1 قابل استفاده دارند، به‌صورت خودکار انجام می‌شود.

اگر برای کشوری داده Admin-1 قابل استفاده وجود نداشته باشد، ساخت آن به حالت کشور کامل برمی‌گردد.

## 📱 سازگاری با برنامه

فایل‌های `.abm` تولیدشده برای استفاده توسط برنامه Flutter مربوط به AbtinMaps طراحی شده‌اند.

برنامه می‌تواند با استفاده از Release Manifest، نقشه‌ها و مناطق موجود را شناسایی کرده و داده موردنیاز را دانلود کند.
