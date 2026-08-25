#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_manifest.py — ساخت manifest.json و تکه‌کردن فایل برای ریلیز گیت‌هاب.

اجرا:
  python3 make_manifest.py out/IR.abm --code IR --name-fa ایران --name-en Iran \
      --out-dir out --release-tag maps-v1
"""
import argparse
import hashlib
import json
import os
import struct
import time

PART_LIMIT = 1_900_000_000  # سقف ~۱.۹GB برای هر asset ریلیز گیت‌هاب


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_bbox(path):
    with open(path, "rb") as f:
        h = f.read(128)
    if h[:8] != b"ABTINMAP":
        raise SystemExit("فایل ABTINMAP نیست")
    base_zoom = h[12]
    mn_lon, mn_lat, mx_lon, mx_lat = struct.unpack_from("<iiii", h, 20)
    return base_zoom, [mn_lon / 1e7, mn_lat / 1e7, mx_lon / 1e7, mx_lat / 1e7]


def split(path, out_dir, code):
    size = os.path.getsize(path)
    parts = []
    if size <= PART_LIMIT:
        parts.append(os.path.basename(path))
        return parts
    with open(path, "rb") as f:
        i = 0
        while True:
            name = f"{code}.abm.part{i}"
            written = 0
            with open(os.path.join(out_dir, name), "wb") as o:
                while written < PART_LIMIT:
                    chunk = f.read(min(1 << 22, PART_LIMIT - written))
                    if not chunk:
                        break
                    o.write(chunk)
                    written += len(chunk)
            if written == 0:
                os.remove(os.path.join(out_dir, name))
                break
            parts.append(name)
            i += 1
            if written < PART_LIMIT:
                break
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("abm")
    ap.add_argument("--code", default="IR")
    ap.add_argument("--name-fa", default="ایران")
    ap.add_argument("--name-en", default="Iran")
    ap.add_argument("--country-code", default=None,
                    help="کد کشور مادر برای بستهٔ منطقه‌ای، مانند US")
    ap.add_argument("--country-name-fa", default=None)
    ap.add_argument("--country-name-en", default=None)
    ap.add_argument("--region-name-fa", default=None)
    ap.add_argument("--region-name-en", default=None)
    ap.add_argument("--group-order", type=int, default=0)
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--release-tag", default="maps-v1")
    ap.add_argument("--repo", default="abtin123/abtin-maps")
    ap.add_argument("--merge-into", default=None,
                    help="manifest.json موجود، برای افزودن کشور جدید")
    ap.add_argument("--patch-json", default=None,
                    help="خروجیِ patch-{code}.json از abtinmap_diff.py — اگر "
                         "داده شود، ارجاعِ پچِ افزایشی به entry اضافه می‌شود.")
    ap.add_argument("--rendered-meta", default=None,
                    help="metadata خروجی rendered_tile_builder.py برای بستهٔ رندرشده")
    ap.add_argument("--source-url", default="",
                    help="URL رسمی PBF استفاده‌شده در ساخت این بسته")
    ap.add_argument("--source-provider", default="Geofabrik / OpenStreetMap")
    ap.add_argument("--source-attribution", default="Map data from OpenStreetMap, ODbL 1.0")
    ap.add_argument("--source-license-url", default="https://opendatacommons.org/licenses/odbl/1.0/")
    ap.add_argument("--source-copyright-url", default="https://www.openstreetmap.org/copyright")
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    base_zoom, bbox = read_bbox(a.abm)
    full_sha = sha256_file(a.abm)
    total = os.path.getsize(a.abm)
    parts = split(a.abm, a.out_dir, a.code)

    files = []
    for name in parts:
        p = os.path.join(a.out_dir, name)
        if not os.path.exists(p):
            p = a.abm
        files.append({"name": name, "size": os.path.getsize(p),
                      "sha256": sha256_file(p)})

    entry = {
        "code": a.code,
        "name_fa": a.name_fa,
        "name_en": a.name_en,
        "country_code": a.country_code or a.code[:2],
        "country_name_fa": a.country_name_fa or a.name_fa,
        "country_name_en": a.country_name_en or a.name_en,
        "region_name_fa": a.region_name_fa or a.name_fa,
        "region_name_en": a.region_name_en or a.name_en,
        "group_order": a.group_order,
        "enabled": True,
        "format": "ABTINMAP/1",
        "base_zoom": base_zoom,
        "bbox": bbox,
        "files": files,
        "total_size": total,
        "sha256": full_sha,
        "download_base":
            f"https://github.com/{a.repo}/releases/download/{a.release_tag}/",
        "source": {
            "provider": a.source_provider,
            "url": a.source_url,
            "attribution": a.source_attribution,
            "license_url": a.source_license_url,
            "copyright_url": a.source_copyright_url,
        },
    }

    # اگر پچِ افزایشی برای این کشور ساخته شده (abtinmap_diff.py)، ارجاعش را
    # به entry اضافه کن — اپ اول این را چک می‌کند و فقط اگر نسخه‌ی محلی‌اش
    # دقیقاً با base_sha256 یکی بود، پچِ کوچک را به‌جای فایلِ کامل می‌گیرد.
    if a.patch_json and os.path.exists(a.patch_json):
        with open(a.patch_json, encoding="utf-8") as f:
            patch = json.load(f)
        bin_name = f"{a.code}.abmpatch"
        manifest_name = f"patch-{a.code}.json"
        bin_src = os.path.join(os.path.dirname(a.patch_json), bin_name)
        entry["patch"] = {
            "base_sha256": patch["base_sha256"],
            "manifest_file": manifest_name,
            "bin_file": bin_name,
            "size": patch.get("patch_size", os.path.getsize(bin_src)
                              if os.path.exists(bin_src) else 0),
            "sha256": patch.get("patch_sha256", ""),
        }

    if a.rendered_meta and os.path.exists(a.rendered_meta):
        with open(a.rendered_meta, encoding="utf-8") as f:
            rendered = json.load(f)
        entry["rendered"] = rendered

    # خروجی این اجرا: manifest تک‌کشوره (برای هر job در ماتریس CI)،
    # جدا از manifest.json نهایی که در job ادغام ساخته می‌شود.
    single_out = os.path.join(a.out_dir, f"manifest-{a.code}.json")
    with open(single_out, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)

    # اگر merge-into داده شده (اجرای محلی/دستی)، manifest کلی را هم به‌روزرسانی کن.
    if a.merge_into:
        manifest = {"schema": 1,
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "release_tag": a.release_tag,
                    "countries": []}
        if os.path.exists(a.merge_into):
            with open(a.merge_into, encoding="utf-8") as f:
                old = json.load(f)
            manifest["countries"] = [c for c in old.get("countries", [])
                                     if c.get("code") != a.code]
        manifest["countries"].append(entry)
        with open(a.merge_into, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"manifest -> {a.merge_into}")

    out = single_out
    print(f"manifest تکی -> {out}")
    print(f"{a.code}: {total/1e6:.1f} MB در {len(files)} فایل")
    for fl in files:
        print(f"  {fl['name']}  {fl['size']/1e6:.1f} MB  {fl['sha256'][:16]}…")


if __name__ == "__main__":
    main()
