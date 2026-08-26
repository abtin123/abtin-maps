# محدودیت‌ها و معماری انتشار نقشه‌های جهانی

## منابع رسمی GitHub

- GitHub Releases: حداکثر **1000 asset** در هر Release، حداکثر **2 GiB برای هر فایل asset**، و بدون سقف اعلام‌شده برای مجموع حجم یا پهنای باند یک Release. منبع: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- GitHub Actions: سقف اجرای job روی GitHub-hosted runner برابر **6 ساعت** است؛ سقف matrix هر workflow برابر **256 job** است. منبع: https://docs.github.com/en/actions/reference/limits
- Repository: فایل‌های تولیدی بزرگ نباید وارد Git شوند؛ single Git object بالای 100 MB پذیرفته نمی‌شود و حجم روی دیسک repo تا 10 GB توصیه شده است. منبع: https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits

## نتیجه برای آبتین‌مپ

فهرست فعلی 100 کشور دارد. هر کشور 16 checkpoint دارد؛ نگهداری آن‌ها در یک Release برابر 1600 asset می‌شود و از سقف 1000 asset بالاتر است. در workflow، checkpointها باید در Release جداگانه برای هر کشور با tag `map-checkpoints-v2-<CODE>` ذخیره شوند. Release نهایی `maps-v3` تنها برای assetهای قابل دانلود کاربران باقی می‌ماند و در اجرای بعدی update می‌شود.

ایران فعلی در `map-checkpoints-v1` نگهداری شده است؛ workflow جدید در نخستین اجرای ایران از آن fallback می‌گیرد و سپس checkpointهای همان کشور را در Release اختصاصی v2 وارد می‌کند.
