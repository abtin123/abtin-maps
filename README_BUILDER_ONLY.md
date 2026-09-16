# Abtin Maps — Map/ABM Builder (Standalone)

این آرشیو فقط اسکریپت و زنجیره ساخت نقشه‌های ABM است و هیچ کد Flutter/MapLibre اپلیکیشن داخل آن نیست.

اجزای اصلی:
- `build_abm.py`
- `abm_builder/`
- `extractors/`
- `routing/`
- `search/`
- `packaging/`
- `regions/` و `sample/`
- تست‌های Builder

اجرای پایه:
```bash
pip install -r requirements.txt
python build_abm.py path/to/country.osm.pbf --country IR --output dist/IR.abm
```

این نسخه شامل اصلاحات Build برای دیتاست‌های سنگین مثل ایران است.
