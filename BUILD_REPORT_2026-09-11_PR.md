# گزارش Build نهایی AbtinMaps_pr

## نتیجه

APK نسخه Release با موفقیت ساخته شد.

| مورد | مقدار |
|---|---|
| Application ID | `ir.abtin.abtin_maps` |
| Version | `0.1.1+2` |
| Flutter | `3.35.1` |
| Dart | `3.9.0` |
| Compile/Target SDK | Android API 36 |
| Min SDK | Android API 24 |
| Java | OpenJDK 21.0.12 |
| Gradle | 8.14 |
| حجم APK خام | `144,966,663 bytes` |

## امضا

APK با keystore موجود در `android/app/Key-abtin.p12` و تنظیمات `android/key.properties` ساخته شد. نوع keystore `PKCS12` و alias آن `key-abtin` است. اعتبارسنجی نهایی با `apksigner` انجام می‌شود.

## وابستگی‌ها

`flutter pub get` موفق شد و نسخه‌های دقیق وابستگی‌ها در `pubspec.lock` قرار دارند. ۸۳ پکیج نسخهٔ جدیدتری داشتند که با constraintهای پروژه سازگار نبودند؛ ارتقای خودکار انجام نشد.

## بسته‌بندی

ZIP پروژه شامل سورس، assets، تنظیمات، pubspec، lockfile و keystore است. برای کاهش حجم، فقط `build/`، `.dart_tool/`، `android/.gradle/` و `.flutter-plugins-dependencies` از ZIP پروژه حذف می‌شوند. APK به‌صورت ZIP جداگانه تحویل داده می‌شود.


## اصلاحات پس از گزارش 2026-09-11

- رندر آفلاین از خواندن مکرر کل لایه‌های کشور جلوگیری می‌کند و در صورت وجود `vector/index.json` فقط chunkهای متقاطع viewport را decode می‌کند.
- آستانه‌های zoom برای road/building/landuse/place با سبک برداری هماهنگ شدند؛ خیابان‌های محلی در نمای کشور دیگر همگی رندر نمی‌شوند.
- pan آفلاین به جهت استاندارد direct-manipulation اصلاح شد و pinch-zoom روی نقطهٔ لمس قفل می‌ماند.
- انتخاب آفلاین حتی هنگام تأخیر validation یک ABM نصب‌شده disabled نمی‌ماند و state نقشهٔ فعال در صورت stale بودن بازیابی می‌شود.
- کارت مسیریابی و آیکون میدان بازطراحی شد؛ همه خروجی‌های میدان کم‌رنگ و خروجی انتخاب‌شده پررنگ است.
- آب‌وهوا و ساعت/باتری کاملاً مستقل شدند؛ رنگ آیکون باتری و رنگ درصد داخل آن جداست و فونت هرکدام قابل انتخاب است.
- اندازه فونت کل اپ از طریق `MediaQuery.textScaler` اعمال می‌شود تا TextStyleهای صریح هم از تنظیم اندازه فونت پیروی کنند.

### وضعیت اعتبارسنجی این ویرایش

در محیط فعلی Flutter SDK نصب نیست و فایل `.abm` واقعیِ کشور نیز کنار سورس موجود نبود؛ بنابراین APK Release و runtime rendering روی دستگاه در این محیط قابل اجرا/تأیید نهایی نیست. این مورد عمداً به‌عنوان «تست‌شده» گزارش نشده است.
