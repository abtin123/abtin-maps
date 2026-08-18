# ABTINMAP v2

هدف: گوشی فقط نمایش، جستجو و مسیریابی.

ساخت:
OSM PBF -> CI Builder -> ABM Package

داخل بسته:
- tile آماده نمایش
- routing graph
- search index
- POI فشرده
- speed limit
- speed camera
- speed bump
- restrictions

آپدیت:
ABM base + ABMPATCH

Patch فقط:
- tile تغییرکرده
- graph تغییرکرده
- POI تغییرکرده
- index تغییرکرده

گوشی هیچ tile یا geometry جدیدی تولید نمی‌کند.
