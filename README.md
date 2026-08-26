# آبتین مپس (Abtin Maps) — ساخت و انتشار نقشه‌های آفلاین

این مخزن سامانهٔ ساخت، انتشار و به‌روزرسانی نقشه‌های آفلاین **ABTINMAP** است. خروجی هر کشور به‌صورت یک فایل `ABM` در Release نهایی `maps-v3` منتشر می‌شود و اپ آبتین مپس آن را از همان Release دریافت می‌کند. طراحی workflowها برای ساخت تدریجی همهٔ کشورها، ادامه‌دادن پس از توقف runner و دریافت patch کوچک در تغییرات بعدی است.

> **قاعدهٔ اصلی:** برای ساخت همهٔ کشورها، `ALL` را در workflow `Build Abtin Map` وارد نکنید. این مقدار عمداً رد می‌شود. تنها workflow درست برای شروع سراسری، `Queue global OSM map updates` در حالت `initial` است.

| موضوع | مقدار یا رفتار صحیح |
|---|---|
| Release نهایی اپ | `maps-v3` |
| workflow شروع سراسری | `Queue global OSM map updates` با حالت `initial` |
| به‌روزرسانی خودکار | هر یک‌شنبه ساعت `03:17 UTC` با حالت `weekly` |
| اندازهٔ هر batch | حداکثر ۱۵ کشور |
| checkpoint هر کشور | ۱۶ مرحله، در Release مستقل `map-checkpoints-v2-<CODE>` |
| منبع داده | [Geofabrik / OpenStreetMap][1] با مجوز ODbL |
| انتشار کشور جدید | آپدیت همان `maps-v3`؛ Release نهایی جدید ساخته نمی‌شود |

## ۱. پیش‌نیاز حیاتی: source کامل باید در مخزن باشد

workflow فقط با فایل YAML کار نمی‌کند. YAMLها ابزارهای Python، catalog کشورها، dependencyهای renderer و stateهای صف را صدا می‌زنند. اگر فقط `.github/workflows` را upload کرده باشید، اجرای workflow پیش از شروع ساخت با خطای `No such file or directory` متوقف می‌شود.

ساختار حداقلی صحیح ریشهٔ مخزن چنین است:

```text
abtin-maps/
├── .github/
│   └── workflows/
│       ├── build-abtin-map.yml
│       └── queue-global-osm-map-updates.yml
├── tools/
│   ├── countries.json
│   ├── sync_geofabrik_catalog.py
│   ├── plan_osm_updates.py
│   ├── map_build_queue.py
│   ├── checkpoint_render.py
│   ├── build_country_package.py
│   ├── abtinmap_diff.py
│   ├── make_manifest.py
│   ├── merge_manifests.py
│   ├── extract_manifest_countries.py
│   └── update_osm_source_state.py
├── requirements-renderer.txt
└── README.md
```

> فایل‌های `tools/osm_source_state.json` و `tools/map_build_queue.json` در اولین اجرای صف، در صورت نبودن، به‌صورت خودکار ساخته و commit می‌شوند. آن‌ها را با فایل خالی یا نسخهٔ دستی جایگزین نکنید.

### بازیابی پس از خطای «فایل پیدا نشد»

اگر در log یکی از پیام‌های زیر دیده شد، مشکل از `ALL`، Release یا حجم نقشه نیست؛ sourceهای لازم از شاخهٔ `main` حذف شده‌اند.

| پیام خطا | فایل یا مجموعهٔ لازم |
|---|---|
| `tools/countries.json: No such file or directory` | `tools/countries.json` و همهٔ ابزارهای `tools/` |
| `can't open file ... sync_geofabrik_catalog.py` | `tools/sync_geofabrik_catalog.py` |
| خطای بعدی در `checkpoint_render.py` یا `build_country_package.py` | ابزارهای اصلی renderer و assembler در `tools/` |
| `No such file ... requirements-renderer.txt` | فایل `requirements-renderer.txt` در ریشهٔ مخزن |

در این وضعیت، بستهٔ بازیابی کامل را با **حفظ دقیق مسیرها** در ریشهٔ مخزن جایگزین کنید و یک commit روی شاخهٔ `main` بسازید. سپس از ابتدا workflow صف را اجرا کنید. لازم نیست Release `maps-v3` یا checkpointهای قبلی را حذف کنید.

## ۲. اولین ساخت همهٔ کشورها

پس از کامل‌بودن source، این تنها کاری است که برای شروع ساخت همهٔ کشورها لازم است:

1. وارد تب **Actions** مخزن شوید.
2. workflow **Queue global OSM map updates** را باز کنید.
3. گزینهٔ **Run workflow** را بزنید.
4. Branch را `main`، حالت را `initial` و Release را `maps-v3` نگه دارید.
5. اجرا را تأیید کنید.

workflow ابتدا `manifest.json` داخل `maps-v3` را می‌خواند. هر کشوری که قبلاً در آن منتشر شده باشد، برای ساخت نخست دوباره وارد صف نمی‌شود. بنابراین ایران (`IR`) که اکنون در Release وجود دارد، بدون دلیل rebuild نخواهد شد. همهٔ کشورهای باقی‌مانده به batchهای حداکثر ۱۵تایی تقسیم می‌شوند؛ batch اول خودکار اجرا می‌شود و پس از انتشار موفق، batch بعدی شروع خواهد شد.

```text
Queue global OSM map updates (initial)
        │
        ├── manifest maps-v3 را می‌خواند
        ├── کشورهای منتشرشده را حذف می‌کند
        ├── کشورهای باقی‌مانده را به batchهای ≤۱۵تایی تقسیم می‌کند
        └── Build Abtin Map را برای batch اول شروع می‌کند
                    │
                    ├── ۱۶ checkpoint برای هر کشور
                    ├── assemble و ساخت ABM
                    ├── update assets و manifest در maps-v3
                    ├── ثبت وضعیت OSM و صف
                    └── شروع خودکار batch بعدی
```

### چرا `ALL` در Build Abtin Map خطا می‌دهد؟

هر کشور ۱۶ stage checkpoint دارد. ساخت هم‌زمان همهٔ کشورها از محدودیت matrix در GitHub Actions عبور می‌کند و هزینه/پایداری runner را تخریب می‌کند. به‌همین دلیل `Build Abtin Map` فقط برای یک batch کوچک طراحی شده و مقدار `ALL` را با پیام راهنما متوقف می‌کند. این **یک خطای عمدی و محافظتی** است، نه خرابی workflow.

## ۳. ساخت دستی یک کشور یا یک batch کوچک

`Build Abtin Map` برای تست یا ادامهٔ یک batch مشخص استفاده می‌شود؛ نه برای ساخت سراسری. در تب **Actions**، workflow **Build Abtin Map** را باز کنید و این مقادیر را وارد کنید:

| ورودی | مقدار صحیح |
|---|---|
| `countries` | یک تا ۱۵ کد دوحرفی، مانند `IQ` یا `TR,IQ,AF` |
| `release_tag` | `maps-v3` |
| `queue_id` | فقط اگر می‌خواهید batch فعال صف را دستی ادامه دهید؛ در غیر این صورت خالی بماند |

کدها باید از `tools/countries.json` باشند. مثال‌های معتبر شامل `IR`، `TR`، `IQ` و `AF` هستند. نام کشور، نام فارسی یا `ALL` ورودی معتبر برای این workflow نیست.

> اگر یک batch خودکار شکست خورد، ابتدا `tools/map_build_queue.json` را بخوانید. `active.countries` همان batchی است که باید دوباره اجرا شود و `queue_id` آن نیز باید در اجرای دستی حفظ شود؛ در غیر این صورت workflow پس از انتشار نمی‌تواند صف باقی‌مانده را درست جلو ببرد.

## ۴. checkpoint، توقف و ادامهٔ ساخت

ساخت کامل کشور بزرگ ممکن است زمان‌بر باشد؛ این workflow برای آن طراحی شده است. هر کشور به ۱۶ بخش checkpoint تقسیم می‌شود. checkpointهای کشور در Release جداگانهٔ زیر نگهداری می‌شوند:

```text
map-checkpoints-v2-IR
map-checkpoints-v2-TR
map-checkpoints-v2-IQ
...
```

اگر runner متوقف شود یا اجرای یک stage شکست بخورد، اجرای مجدد همان batch checkpointهای موجود را دانلود می‌کند و فقط stageهای ناقص را می‌سازد. بنابراین حذف checkpointها، حذف Release `maps-v3` یا ساخت Release جدید برای رفع توقف، روش درست نیست.

| وضعیت | اقدام درست |
|---|---|
| stage یا runner موقتاً شکست خورد | همان workflow یا همان batch را دوباره اجرا کنید؛ checkpointها باقی بمانند |
| اجرای صف هنوز `active` دارد | workflow صف جدید نسازید؛ batch فعال را ادامه دهید |
| Release `maps-v3` موجود است | آن را حذف نکنید؛ workflow فقط assetهای batch تازه و `manifest.json` را update می‌کند |
| queue خالی و ساخت اولیه پایان یافته | برای بررسی تغییرات، اجرای `weekly` را منتظر بمانید یا دستی همان workflow صف را در حالت `weekly` اجرا کنید |

## ۵. به‌روزرسانی هفتگی OSM

workflow `Queue global OSM map updates` هر یک‌شنبه ساعت `03:17 UTC` اجرا می‌شود. زمان‌بندی GitHub Actions فقط از workflow موجود در شاخهٔ پیش‌فرض مخزن اجرا می‌شود؛ بنابراین YAMLهای نهایی باید در `main` commit شده باشند.[2]

در اجرای هفتگی، workflow برای هر کشور fingerprint منبع Geofabrik را با `ETag` و در صورت نیاز `Last-Modified` بررسی می‌کند. نتیجه به این شکل است:

| وضعیت کشور | رفتار workflow |
|---|---|
| هنوز در manifest نیست | وارد صف ساخت می‌شود |
| در `maps-v3` هست و fingerprint تغییر نکرده | هیچ build یا دانلودی انجام نمی‌شود |
| در `maps-v3` هست و منبع OSM تغییر کرده | فقط همان کشور وارد صف می‌شود |
| پاسخ HEAD منبع موقتاً ناموفق است | برای کشور موجود rebuild کورکورانه انجام نمی‌شود |

پس از انتشار موفق کشور به‌روز‌شده، `tools/osm_source_state.json` commit می‌شود تا اجرای بعدی فرق واقعی را تشخیص دهد. این فایل را نگه دارید؛ حذف آن باعث از دست‌رفتن baseline می‌شود، هرچند workflow برای کشورهایی که در Release هستند، در اولین اجرای بعدی baseline جدید می‌سازد و بی‌جهت آن‌ها را rebuild نمی‌کند.

## ۶. خروجی Release `maps-v3`

برای هر کشور معمولاً این فایل‌ها در همان Release نهایی به‌روز می‌شوند:

| فایل | کاربرد |
|---|---|
| `XX.abm` | نقشهٔ کامل کشور، مانند `IR.abm` |
| `XX.abm.part0`, `XX.abm.part1`, ... | برای کشوری که فایلش باید به چند part تقسیم شود |
| `patch-XX.json` و `XX.update.abmpatch` | patch افزایشی اختیاری از نسخهٔ قبلی به نسخهٔ جدید |
| `manifest.json` | catalog نهایی شامل کشورها، فایل‌ها، hashها و reference patch |

Release `maps-v3` **ثابت** می‌ماند. workflow برای هر batch فقط assetهای کشور همان batch و `manifest.json` را با `--clobber` جایگزین می‌کند؛ سایر کشورها در manifest حفظ می‌شوند. محدودیت‌های GitHub Release، از جمله سقف حجم asset و تعداد asset، دلیل استفاده از checkpoint releaseهای مستقل هستند.[3]

در اپ آبتین‌مپ، اگر hash نقشهٔ نصب‌شده با `base_sha256` patch یکی باشد، patch کوچک دریافت می‌شود؛ در غیر این صورت، اپ فایل کامل همان کشور را می‌گیرد. این رفتار باعث می‌شود کاربر برای تغییر یک کشور، نقشهٔ کشورهای دیگر را دوباره دانلود نکند.

## ۷. مجوزها و تنظیمات مخزن

workflowها برای ساخت Release، آپلود asset، commit state و شروع batch بعدی به این مجوزها نیاز دارند:

```yaml
permissions:
  contents: write
  actions: write
```

`contents: write` برای Release و commit فایل‌های state لازم است. `actions: write` برای شروع `Build Abtin Map` از workflow صف لازم است. triggering یک workflow از طریق `workflow_dispatch` در GitHub به دسترسی و تنظیم صحیح workflow وابسته است.[4]

برای دریافت عمومی Geofabrik و انتشار public Release، secret سفارشی لازم نیست. `github.token` داخلی Actions برای عملیات داخل همان مخزن استفاده می‌شود؛ آن را چاپ یا در README ذخیره نکنید.

## ۸. عیب‌یابی سریع

| نشانه | علت محتمل | راه‌حل |
|---|---|---|
| `0 workflow runs` | هنوز workflow اجرا نشده یا صفحه روی workflow اشتباه باز است | `Queue global OSM map updates` را در حالت `initial` اجرا کنید |
| `countries.json` پیدا نشد | فقط YAMLها upload شده‌اند | source کامل `tools/` را بازیابی کنید |
| `sync_geofabrik_catalog.py` پیدا نشد | ابزار catalog حذف شده است | source کامل `tools/` را بازیابی کنید |
| `ALL مستقیماً ... اجرا نمی‌شود` | `ALL` در Build Abtin Map وارد شده | به جای آن Queue global را اجرا کنید |
| `کد ناشناخته` | کد کشور معتبر نیست | از کد دوحرفی `tools/countries.json` استفاده کنید |
| build بعد از چند ساعت متوقف شد | runner یا stage موقتاً شکست خورده | checkpointها را نگه دارید و همان batch را دوباره اجرا کنید |
| صف جدید شروع نمی‌شود | یک `active` در `map_build_queue.json` وجود دارد | همان batch فعال را ادامه دهید، صف جدید نسازید |
| کشور قبلی دوباره وارد initial شده | manifest یا state پاک/خراب شده است | `maps-v3/manifest.json` و state را بررسی کنید؛ Release را حذف نکنید |
| اپ نقشه را دانلود نمی‌کند | APK قدیمی هنوز release قبلی را دارد یا manifest ناقص است | APK جدید با پایهٔ `maps-v3` نصب و manifest Release را بررسی کنید |

## ۹. اعتبار منبع و مجوز داده

دادهٔ نقشه از Geofabrik و OpenStreetMap تهیه می‌شود. attribution و پیوند مجوز در `manifest.json` هر کشور ثبت می‌شود. هنگام نمایش، توزیع یا تغییر داده باید الزامات مجوز ODbL و attribution OpenStreetMap رعایت شود.[1]

## ۱۰. نگه‌داری امن مخزن

فایل‌های زیر بخش ضروری عملیات هستند و نباید برای «سبک‌کردن» مخزن حذف شوند:

```text
.github/workflows/build-abtin-map.yml
.github/workflows/queue-global-osm-map-updates.yml
tools/countries.json
tools/sync_geofabrik_catalog.py
tools/checkpoint_render.py
tools/build_country_package.py
requirements-renderer.txt
tools/osm_source_state.json        # پس از اولین اجرا
tools/map_build_queue.json         # پس از اولین اجرا
```

فایل‌های PBF خام، checkpoint tar و ABM نهایی را در Git معمولی commit نکنید. checkpointها در Releaseهای اختصاصی و خروجی کاربر در Release `maps-v3` نگهداری می‌شوند؛ این همان چیزی است که طراحی workflow بر پایهٔ آن انجام شده است.

## منابع

[1] [Geofabrik Download Server و داده‌های OpenStreetMap](https://download.geofabrik.de/)

[2] [Syntax و زمان‌بندی GitHub Actions](https://docs.github.com/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

[3] [محدودیت‌ها و مدیریت GitHub Releases](https://docs.github.com/repositories/releasing-projects-on-github/about-releases)

[4] [شروع workflow با `workflow_dispatch`](https://docs.github.com/actions/using-workflows/manually-running-a-workflow)
