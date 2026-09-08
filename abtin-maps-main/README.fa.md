# سازندهٔ مپ آفلاین Abtin Maps — نسخه v4

این repository اسکریپت کامل ساخت مپ و GitHub Actions انتشار مپ برای Abtin Maps است.

## Release مورد استفادهٔ اپ

```text
maps-v4
```

اپ از این Release می‌خواند:

```text
https://github.com/abtin123/abtin-maps/releases/download/maps-v4/
```

## ساخت ایران

از GitHub:

```text
Actions → Build offline maps v4 → Run workflow
```

مقادیر پیش‌فرض:

```text
release_tag: maps-v4
country_selector: IR
```

یعنی فقط مپ ایران ساخته و در Release منتشر می‌شود.

## ساخت همهٔ مپ‌ها

در `country_selector` بنویسید:

```text
ALL
```

یا مثلاً برای ساخت چند کشور مشخص، کدهای کشور را با `/` بدهید.

## ساخت واقعی

```text
OSM / Geofabrik PBF
        ↓
Planetiler
        ↓
PMTiles vector
        ↓
Routing Graph
        ↓
Offline Search DB
        ↓
ABTINMAP v4
        ↓
IR.abm
        ↓
GitHub Release maps-v4
```

## آپدیت هفتگی

Workflow هر دوشنبه اجرا می‌شود. اگر source یک کشور تغییر نکرده باشد، دوباره ساخته نمی‌شود. اگر تغییر کرده باشد، فقط همان مپ rebuild می‌شود.

برای نسخهٔ جدید، در صورت کوچک‌تر بودن patch از فایل کامل، patch سطح بلوکی هم ساخته می‌شود.

## نکته

فایل `.abm` را داخل repository commit نکنید؛ فقط در GitHub Release قرار بگیرد.
