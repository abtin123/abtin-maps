# یافته‌های عمومی برای معماری نقشهٔ آفلاین

> این یادداشت فقط بر منابع عمومی و نمونهٔ قانونی Mapsforge تکیه دارد و شامل استخراج یا استفاده از فایل/کد اختصاصی Magic Earth نیست.

## Magic Earth

صفحات رسمی Magic Earth بیان می‌کنند که دادهٔ نقشهٔ آفلاین بر پایهٔ OpenStreetMap است، نقشه‌ها برای ۲۳۳ کشور و منطقه به‌صورت انتخابی دانلود می‌شوند و داده/صحنه‌های سه‌بعدی برای استفادهٔ آفلاین در اختیار کاربر قرار می‌گیرند. این منابع فرمت داخلی فایل‌ها، codec، layout index یا موتور رندر اختصاصی را منتشر نمی‌کنند؛ بنابراین نباید دربارهٔ جزئیات داخلی آن فرض‌سازی شود.

منابع:

- https://www.magicearth.com/offline-maps
- https://www.magicearth.com/maps
- https://www.magicearth.com/faq/en

## نمونهٔ قانونی Mapsforge

از نمونهٔ عمومیِ نقشهٔ ایرانِ Vector.city فقط ۱۸ مگابایت ابتدایی دریافت شد. هدر فایل با امضای `mapsforge binary OSM` آغاز می‌شود و متن header شامل `Mercator` و `mapsforge-map-writer` است. مشخصات رسمی Mapsforge می‌گوید فایل برای دستگاه‌های کم‌منبع طراحی شده، دادهٔ جغرافیایی را به‌شکل برداری ذخیره می‌کند، برای بازه‌های زوم sub-file دارد و با index ثابت tile به دادهٔ همان tile seek می‌کند.

منابع:

- https://vector.city/coinloads/asia-iran/
- https://github.com/mapsforge/mapsforge/blob/master/docs/Specification-Binary-Map-File.md

## نتیجه برای آبتین‌مپ

رندر صدها هزار WebP پیش از اعمال بودجهٔ حجم، علت گلوگاه ساخت اطلس فعلی است. الگوی قابل استفاده برای فرمت مستقل ABM2 عبارت است از: catalog سبک، فایل مستقل هر کشور، chunkهای زوم‌محور، index ثابت/seekable، جدول tag مشترک و کدگذاری delta/varint هندسه. این الگو از Mapsforge الهام معماری می‌گیرد، اما فرمت و پیاده‌سازی آبتین‌مپ مستقل باقی می‌ماند.

## Karta GPS

صفحهٔ App Store Karta بیان می‌کند که نقشه‌های آفلاین از OpenStreetMap فراهم و توسط Karta Software Technologies بهبود داده می‌شوند. صفحهٔ عمومی OpenStreetMap نیز «Map data: vector» را برای Karta GPS ثبت کرده و بر اجرای آفلاین جست‌وجو، محاسبهٔ مسیر و دستورهای turn-by-turn تأکید می‌کند. هیچ‌یک از این منابع فرمت داخلی فایل، codec یا layout index Karta را منتشر نمی‌کنند.

منابع:

- https://apps.apple.com/us/app/karta-offline-gps-maps-nav/id1072400876
- https://wiki.openstreetmap.org/wiki/Karta_GPS

### جمع‌بندی مقایسه

هر دو نمونهٔ Magic Earth و Karta GPS از دادهٔ OpenStreetMap، بسته‌های نقشهٔ آفلاین منطقه‌ای و رندر/دسترسی سریع برای نقشه استفاده می‌کنند. جزئیات فرمت‌های اختصاصی آن‌ها عمومی نیست. بنابراین انتخاب مستقل ABM2 باید بر اصول قابل تأیید تکیه کند: بستهٔ منطقه‌ای، chunkهای index‌شده، دادهٔ برداری فشرده و قابلیت patch در سطح shard؛ نه تقلید از فرمت نامعلوم برنامه‌های دیگر.
