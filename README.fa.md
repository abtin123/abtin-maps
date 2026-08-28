# اصلاح خطای glyph در ساخت ABM

## علت خطا

دریافت PBF ایران کامل شد، اما این دستور به مسیر asset موجود در repository وابسته بود:

`assets/glyphs/Vazirmatn/*.pbf`

در runner این پوشه وجود نداشت و wildcard با خطای `cannot stat` متوقف شد.

## اصلاح

`build_country_abm.sh` اکنون هر range را جدا بررسی می‌کند. اگر فایل محلی موجود باشد همان را استفاده می‌کند؛ اگر موجود نباشد، range معتبر را از font archive عمومی openmaptiles دریافت می‌کند. بنابراین نبود یا ناقص‌بودن پوشهٔ glyph دیگر باعث توقف build نمی‌شود. rangeهای عربی/فارسی، لاتین، اعداد و presentation forms پوشش داده شده‌اند.

Spriteهای POI همچنان عمداً اجباری هستند؛ چون حذف آن‌ها باعث می‌شود POI روی نقشه بدون آیکون ساخته شود. اگر در repository شما `assets/sprites/abtin.json`، `abtin.png`، `abtin@2x.json` و `abtin@2x.png` وجود دارند، مرحلهٔ بعد بدون مشکل از آن‌ها استفاده می‌کند.

## اجرا

فقط فایل موجود در patch را در همان مسیر root repository جایگزین کنید و workflow را دوباره برای `IR` اجرا کنید. نیازی به تغییر APK یا دانلود دستی glyph نیست.

اعتبارسنجی محلی: `bash -n` پاس شد؛ تمام URLهای fallback اصلی با HTTP 200 و فایل PBF غیرخالی بررسی شدند.
