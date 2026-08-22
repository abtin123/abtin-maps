# ممیزی pipeline چندکشوری آبتین‌مپ

**تاریخ:** ۲۲ اوت ۲۰۲۶  
**دامنه:** تولید و انتشار نقشهٔ کاملاً آفلاین از دادهٔ آزاد OpenStreetMap؛ این سند هیچ فرمت، داده یا asset اختصاصیِ نمونه‌های ارسالی را استفاده نمی‌کند.

## نتیجهٔ اجرایی

pipeline فعلی برای ساخت یک کشور یا یک منطقهٔ بزرگ، پایه‌های درست را دارد: `abtinmap_build.py` دادهٔ ورودی PBF را فقط در زمان ساخت به ABM تبدیل می‌کند، `rendered_tile_builder.py` اطلس WebP/SQLite از پیش‌رندرشده می‌سازد و `embed_rendered_atlas.py` آن را در همان ABM قرار می‌دهد. اپ Flutter پس از نصب، ABM محلی را باز می‌کند و map payload خام OSM یا سرویس نقشهٔ آنلاین در runtime ندارد.

اما هنوز یک فرمانِ production واحد برای «از index قانونی استخراج را پیدا کن، PBF را با قابلیت resume بگیر، ABM و atlas بساز، artifactها را hash کن، manifest کلی بساز و آن را برای انتشار آماده کن» وجود ندارد. `countries.json` نیز یک فهرست دستی و محدود است؛ برای پوشش همهٔ extractهای قابل عرضه باید از index ماشینی رسمی منبع استفاده شود و فهرست قابل انتشار از آن ساخته شود.

| موضوع | وضعیت فعلی | شکاف موردنیاز |
|---|---|---|
| ورودی قانونی | لینک‌های PBF در `countries.json` وجود دارند | همگام‌سازی خودکار از index رسمی و ثبت URL/نسخهٔ ورودی برای هر build |
| ساخت ABM | `abtinmap_build.py` از `--region`، overview zoom، POI و راست/چپ‌رانی پشتیبانی می‌کند | فرمان country-profile و کنترل منابع/اندازه برای هر extract |
| اطلس آماده | atlas سروری SQLite/WebP در footer `ABTATLS2` embed می‌شود | اجرای زنجیره به‌صورت یک فرمان و سیاست budget متناسب با region |
| کشور بزرگ | `MapRegion`، `files` و region group در Flutter پشتیبانی می‌شوند | پروفایل shard‌محور، شناسهٔ پایدار و نصب یکپارچهٔ همهٔ regionهای انتخاب‌شده |
| دانلود | `downloadRegion` پارت‌ها را با resume، hash و نصب اتمیک مدیریت می‌کند | انتشار واقعی manifest کشورها و بهبود fallback catalog برای کشورهای هنوز منتشرنشده |
| به‌روزرسانی | patch اختیاری ABM موجود است | تولید پایدار state/patch برای هر region و policy انتشار نسخه |
| انتساب | منبع در provenance اراک ثبت شده است | metadata و UI ثابت «Map data from OpenStreetMap, ODbL 1.0» برای همهٔ بسته‌ها |

## منبع قانونی و کاتالوگ قابل تولید

Geofabrik یک index ماشینی پایدار با `id`، parent، نام، کدهای ISO، URL رسمی PBF و URL updates منتشر می‌کند. این index منبع profileهای ساخت می‌شود؛ تنها entryهایی که URL عمومی `pbf` دارند و در policy انتشار آبتین‌مپ تأیید شده‌اند وارد manifest می‌شوند. این کار هم نیاز به نگهداری دستی لینک صدها کشور را حذف می‌کند و هم برای کشورهایی که در منبع به regionهای مستقل تقسیم شده‌اند، regionها را با کشور مادر درست گروه‌بندی می‌کند.[1]

هر خروجی باید منبع PBF، زمان build، کد ISO یا شناسهٔ extract، نسخهٔ سازنده، hash نهایی، اندازه، محدوده و اطلاعات انتساب را در manifest خود ثبت کند. داده‌های OpenStreetMap و extractهای Geofabrik تحت ODbL هستند؛ نمایش نقشه، جست‌وجو و مسیریابی باید اعتبار OpenStreetMap و پیوند مجوز را در جای قابل دسترس نشان دهند.[2] [3]

## قرارداد پیشنهادی انتشار

هر job دقیقاً یک `profile` می‌سازد و هیچ کشور دیگری را در runtime نمی‌خواند. خروجی job شامل ABM دارای atlas embedded، preview اختیاری، `manifest-<id>.json` و provenance است. سپس یک job ادغام، artifactهای موفق را به `manifest.json` نسخه‌دار تبدیل می‌کند. اگر کشور بسیار بزرگ از چند extract رسمی تشکیل شده باشد، هر extract یک `MapRegion` مستقل با `country_code` مشترک دارد؛ اپ آن‌ها را زیر سربرگ و پرچم همان کشور نمایش می‌دهد. اگر یک فایل از سقف انتشار بزرگ‌تر باشد، `make_manifest.py` آن را به partهای hash‌شده تقسیم می‌کند و installer فعلی Flutter آن‌ها را resumable دانلود و اتمیک ادغام می‌کند.

> «همهٔ کشورها» به معنی catalog قابل ساخت و قابل انتشار است، نه اینکه همهٔ PBFهای جهان هم‌زمان download یا build شوند. ساخت باید صف‌محور و انتخابی باشد تا منابع build، ظرفیت انتشار و کنترل کیفیت هر کشور قابل مدیریت بماند.

## معیار پذیرش قبل از اعلام تکمیل

هر profile پیش از انتشار باید validate شود: ABM footer معتبر، hash، atlas قابل بازشدن، حداقل یک tile در سطح overview و street، گروه‌بندی region صحیح، manifest parse‌شونده در Flutter، نصب بدون اینترنت پس از دانلود و attribution قابل دسترس. سپس benchmark واقعی APK برای ایران و دست‌کم یک کشور region‌شده انجام می‌شود؛ تا آن benchmark، نمونهٔ اراک تنها اثبات مسیر فنی کوچک است، نه اثبات عملکرد کل ایران یا همهٔ کشورها.

## منابع

[1]: https://download.geofabrik.de/technical.html "Geofabrik — Data Extracts Technical Details"
[2]: https://www.geofabrik.de/data/download.html "Geofabrik — Downloads and ODbL terms"
[3]: https://www.openstreetmap.org/copyright "OpenStreetMap — Copyright and License"
