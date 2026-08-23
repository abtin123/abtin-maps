# منبع دادهٔ نقشهٔ تست اراک

بستهٔ محلی `ARAK-TEST.abm` از دادهٔ عمومی OpenStreetMap برای یک محدودهٔ محدود از مرکز اراک ساخته شد. دادهٔ خام با درخواست read-only زیر دریافت شد:

`https://api.openstreetmap.org/api/0.6/map?bbox=49.695,34.075,49.715,34.095`

ترتیب bounding box در درخواست OSM برابر `minLon,minLat,maxLon,maxLat` است. خروجی دریافتی 2,983,987 بایت، شامل 2,243 راه و 11,168 گره بود. سپس با `abtinmap_build.py` و `rendered_tile_builder.py` به ABM v2 و اطلس آمادهٔ محلی تبدیل شد.

دادهٔ پایه تحت مجوز ODbL است؛ انتساب OpenStreetMap و مشارکت‌کنندگان باید در محصول/اسناد مربوط به نقشه حفظ شود.

## منبع عمومی

- [OpenStreetMap API 0.6 map endpoint](https://api.openstreetmap.org/api/0.6/map?bbox=49.695,34.075,49.715,34.095)
- [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright)
