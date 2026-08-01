# پشتیبانی چند-کشوره‌ی Abtin Maps

## چه چیزی تغییر کرد

### ریپوی `abtin123/abtin-maps` (ساخت گراف‌ها در CI)
1. **`tools/countries.json`** — لیست کشورهای قابل‌ساخت (کد، نام فارسی/انگلیسی، آدرس pbf از Geofabrik).
   برای افزودن کشور جدید فقط یک آبجکت به این فایل اضافه کنید.
2. **`.github/workflows/build-abtin-map.yml`** — بازنویسی کامل با ۳ job:
   - `plan`: از ورودی `countries` (مثلاً `"IR,TR,IQ"` یا `all`) و `countries.json` یک ماتریس می‌سازد.
   - `build`: به‌ازای هر کشور یک job **موازی و مستقل** اجرا می‌شود (تا ۴ تا هم‌زمان) — دانلود pbf، ساخت `.abm`، اعتبارسنجی، ساخت `manifest-<CODE>.json`.
   - `release`: همه‌ی artifact ها را جمع می‌کند، manifest تک‌کشوره‌ها را در یک **`manifest.json` واحد** ادغام می‌کند و همه‌ی فایل‌های `.abm` را در **یک ریلیز مشترک** منتشر می‌کند.
3. **`tools/make_manifest.py`** — حالا هر اجرا یک `manifest-<CODE>.json` جدا می‌سازد (برای امنیت در برابر همزمانی موازی)، به‌علاوه‌ی رفتار قبلی `--merge-into` برای اجرای دستی محلی.
4. **`tools/merge_manifests.py`** (جدید) — همه‌ی `manifest-<CODE>.json` ها را در یک `manifest.json` نهایی ادغام می‌کند.

### آپدیت خودکار هفتگی
یک job جدید به نام `check-updates` هر **دوشنبه ساعت ۰۲:۰۰ UTC** به‌صورت خودکار اجرا می‌شود:
1. برای هر کشور در `countries.json` تاریخ آخرین آپدیت فایل pbf را در Geofabrik چک می‌کند (هدر `Last-Modified`).
2. آن را با `tools/build_state.json` (تاریخ آخرین ساخت موفق هر کشور، در ریپو نگه‌داری می‌شود) مقایسه می‌کند.
3. **فقط** کشورهایی که واقعاً داده‌ی تازه‌تر دارند دوباره ساخته می‌شوند — نه همه‌ی کشورها.
4. اگر هیچ کشوری آپدیت نشده باشد، هیچ build/release ای اجرا نمی‌شود (صرفه‌جویی در زمان/هزینه‌ی CI).
5. کشورهایی که تغییر نکرده‌اند در `manifest.json` نهایی دست‌نخورده باقی می‌مانند (manifest جدید با نسخه‌ی قبلی همان ریلیز ادغام می‌شود).

اگر ترجیح می‌دهید ماهانه به‌جای هفتگی چک شود، در `build-abtin-map.yml` خط `cron: "0 2 * * 1"` را کامنت و خط ماهانه‌ی زیرش را فعال کنید.

برای اجبار به بازسازی دستی صرف‌نظر از تاریخ (مثلاً بعد از تغییر تنظیمات build)، از `workflow_dispatch` با فیلد `force_rebuild: "IR,TR"` یا `force_rebuild: "all"` استفاده کنید.

### اجرا در Actions
`Actions → Build Abtin Map → Run workflow` و در فیلد `countries` مثلاً بنویسید:
```
IR,TR,IQ,AF,PK,AZ,AM,SY
```
یا خالی/`all` بگذارید تا همه‌ی کشورهای `countries.json` ساخته شوند.

### خروجی نهایی در ریلیز
```
manifest.json      ← لیست همه‌ی کشورها با bbox، حجم، sha256، آدرس دانلود
IR.abm
TR.abm
IQ.abm
...
```

آدرس manifest نهایی:
```
https://github.com/abtin123/abtin-maps/releases/download/<TAG>/manifest.json
```

---

## ریپوی اپ (Flutter)

فایل‌های آماده در `app_snippets/lib/features/countries/` قرار دارند:

- `country_models.dart` — مدل `CountryManifest` / `CountryMapEntry` که دقیقاً با ساختار JSON بالا مطابقت دارد.
- `country_providers.dart` — Riverpod providers:
  - `countryManifestProvider`: دریافت و پارس `manifest.json` (با fallback میرور `gh-proxy.com` مثل بقیه‌ی دانلودهای پروژه).
  - `countryDownloadProvider(entry)`: مدیریت دانلود/پیشرفت/لغو/نصب/حذف نقشه‌ی هر کشور به‌صورت جدا، با استریم به دیسک و اعتبارسنجی حجم.
- `countries_screen.dart` — صفحه‌ی RTL با کارت هر کشور (نام فارسی/انگلیسی، حجم، نوار پیشرفت، دکمه دانلود/لغو/حذف) — هماهنگ با استایل گلس‌مورفیسم پروژه.

### مراحل الحاق
1. کپی پوشه‌ی `lib/features/countries/` داخل پروژه‌ی اصلی Flutter.
2. مطمئن شوید `dio`, `flutter_riverpod`, `path_provider` در `pubspec.yaml` هستند (به احتمال زیاد از قبل هستند).
3. در `country_providers.dart` مقدار `_releaseTag` را با تگ واقعی ریلیزتان (همان ورودی `release_tag` در ورک‌فلو) هماهنگ کنید.
4. یک آیتم/دکمه در صفحه تنظیمات یا نقشه اضافه کنید که به `CountriesScreen()` ناوبری کند:
   ```dart
   Navigator.push(context, MaterialPageRoute(builder: (_) => const CountriesScreen()));
   ```
5. مسیر فایل نصب‌شده‌ی هر کشور از طریق `installedFilePath(code)` در دسترس است — همان جایی که موتور مسیریابی/رندر نقشه باید `.abm` را از آن بخواند.

### نکات هماهنگ با محدودیت‌های شبکه‌ی ایران
- هر دانلود ابتدا از GitHub امتحان می‌شود، در صورت شکست به `gh-proxy.com` سوییچ می‌کند (همان الگوی مصرف‌شده در دانلود گراف‌های GraphHopper).
- فایل‌های بزرگ‌تر از ۱.۹GB به‌صورت خودکار در CI به چند تکه (`part0`, `part1`, ...) شکسته می‌شوند؛ `downloadUrls` در مدل Dart همه‌ی تکه‌ها را به ترتیب برمی‌گرداند و کد دانلود آن‌ها را پشت‌سرهم می‌نویسد.
- دانلود به‌صورت استریم روی دیسک نوشته می‌شود (نه در حافظه) تا برای فایل‌های حجیم و اتصال کند مشکلی پیش نیاید.
