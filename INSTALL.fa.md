# نصب patch اصلاح‌شدهٔ سازندهٔ نقشه

کل محتویات ZIP را در ریشهٔ سورس Flutter خود extract و فایل‌های هم‌نام را جایگزین کنید. سپس commit و push کنید.

در GitHub Actions، workflow **Build offline country map** را اجرا کنید. پیش‌فرض آن ایران (`IR`) و tag `maps-v3` است؛ app نیز از همین tag دانلود می‌کند. این نسخه خطای Docker مربوط به مسیر نسبی `dist/work-IR` را اصلاح می‌کند.

خروجی فقط `IR.abm` و `manifest.json` در GitHub Release است. هیچ نقشه، APK، PBF، cache یا کلید خصوصی در ZIP نیست.
