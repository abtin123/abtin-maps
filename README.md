# سازندهٔ نقشهٔ آبتین مپس

این بسته فقط workflow و ابزار ساخت archive آفلاین `.abm` است. سورس Flutter، APK، فایل امضای Android، PBF/OSM، PMTiles، ABM، cache و log در آن وجود ندارد.

محتوای ZIP را در **ریشهٔ repository پروژهٔ Flutter** extract کنید. بعد از extract باید این دو مسیر در همان repository وجود داشته باشند:

| مسیر | کاربرد |
|---|---|
| `.github/workflows/build-offline-map.yml` | workflow ساخت و انتشار هر کشور |
| `tool/maps/` | دانلود PBF، ساخت PMTiles و graph، pack و verify |

برای ساخت ایران، در GitHub به **Actions → Build Offline Map → Run workflow** بروید و مقدار `country_code` را `IR` انتخاب کنید. خروجی مجاز workflow، `IR.abm` است؛ PMTiles برداری، graph مسیریابی و styleهای روز/شب در همین یک فایل قرار دارند.

workflow پیش از publish، PMTiles، container، graph و styleها را verify می‌کند. فایل آزمایشی layout را هرگز با نام `IR.abm` منتشر نکنید.

> repository اپ می‌تواند private بماند؛ ولی URL دانلود `manifest.json` و فایل‌های `CC.abm` برای اپ کاربران باید عمومی باشد. release خصوصی GitHub از داخل اپِ کاربر بدون token دانلود نمی‌شود.
