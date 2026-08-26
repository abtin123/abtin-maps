# ساخت خودکار همهٔ کشورها و به‌روزرسانی هفتگی OSM

## رفتار workflowها

| workflow | زمان/کار | نتیجه |
|---|---|---|
| `Queue global OSM map updates` با حالت `initial` | یک‌بار برای شروع | `manifest.json` ریلیز `maps-v3` را می‌خواند، فقط کشورهایی را که هنوز در آن نیستند پیدا می‌کند، آن‌ها را به batchهای حداکثر 15تایی تقسیم می‌کند و ساخت را خودکار شروع می‌کند. |
| `Queue global OSM map updates` با حالت `weekly` | هر یک‌شنبه 03:17 UTC | علاوه بر کشور نساخته، fingerprint منبع OSM (ETag یا Last-Modified) را بررسی می‌کند. فقط کشور تغییرکرده وارد صف می‌شود. |
| `Build Abtin Map` | خودکار، یک batch در هر نوبت | همان `maps-v3` را update می‌کند؛ کشورهای batchهای قبلی در manifest باقی می‌مانند. پس از هر batch، batch بعدی از صف شروع می‌شود. |

> `ALL` مستقیماً داخل renderer اجرا نمی‌شود، چون 100 کشور × 16 stage از سقف matrix می‌گذرد. workflow صف این کار را بدون واردکردن نام کشورها و با batchهای امن انجام می‌دهد.

## دانلود کاربر پس از به‌روزرسانی

برای کشور تغییرکرده، workflow ابتدا نسخهٔ قبلی `ABM` را از `maps-v3` می‌گیرد و `abtinmap_diff.py` پچ تولید می‌کند. `manifest.json` جدید reference پچ را دارد. اپ فقط وقتی نسخهٔ محلی کاربر با `base_sha256` منطبق باشد، پچ کوچک را به‌جای فایل کامل دانلود می‌کند؛ در غیر این صورت، فایل کامل همان کشور را می‌گیرد.

## stateهای نگه‌داری‌شده در repository

| فایل | نقش |
|---|---|
| `tools/osm_source_state.json` | fingerprint آخرین منبع OSM که پس از انتشار موفق ثبت شده است. |
| `tools/map_build_queue.json` | batch فعال و batchهای باقی‌مانده؛ برای ادامهٔ خودکار پس از هر build. |
| `tools/string_state/*.json` | state رشته‌های نقشه. |

## محدودیت‌ها

هر فایل Release باید کمتر از 2 GiB باشد و هر Release حداکثر 1000 asset دارد. checkpointها برای همین به Release جداگانهٔ هر کشور منتقل شده‌اند: `map-checkpoints-v2-<CODE>`.

## منابع

- GitHub Releases limits: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- GitHub Actions schedule syntax: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- Triggering `workflow_dispatch` from a workflow: https://docs.github.com/en/actions/using-workflows/triggering-a-workflow
