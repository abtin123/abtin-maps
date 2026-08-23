# نتیجهٔ prototype محدود ABM2

این benchmark با دادهٔ واقعی `monaco-latest.osm.pbf` از Geofabrik، نه دادهٔ مصنوعی، اجرا شد. هدف آن فقط اعتبارسنجی مسیر `PBF → MVT آماده → VCH2 Zstd → IDX2 seek` بود؛ این گزارش عملکرد نهایی APK یا مقایسهٔ مستقیم با ABM v2 نیست.

## ورودی و خروجی

| مورد | مقدار |
|---|---:|
| منبع داده | Monaco OpenStreetMap PBF، 689,759 بایت |
| tile تست | `z=13, x=4264, y=2987` |
| road feature واقعی | 2,297 |
| MVT آماده | 85,551 بایت |
| VCH2 raw | 85,591 بایت |
| VCH2 فشرده با Zstd | 45,584 بایت |
| container شامل header/index/chunk | 49,936 بایت |

## نتیجهٔ خواندن محلی sandbox

در 50 بار تکرار read + seek + Zstd decompress، `P50 = 0.051ms` و `P95 = 0.065ms` ثبت شد. این عدد فقط برای sandbox با دیسک و CPU سرور معتبر است و نباید به‌عنوان زمان Android اعلام شود.

## نتیجهٔ فنی

prototype تأیید می‌کند که chunk آمادهٔ برداری برای یک tile متراکم شهری به حدود 46KiB فشرده می‌شود و index ثابت به offset مشخص آن seek می‌کند. مرحلهٔ بعدی فقط پس از benchmark روی Android انجام می‌شود: local vector-tile bridge، cache 3×3 و اندازه‌گیری end-to-end تا نخستین frame در MapLibre.
