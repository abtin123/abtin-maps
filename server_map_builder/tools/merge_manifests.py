#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_manifests.py — ادغام manifest-<CODE>.json های تولیدشده در job های
ماتریس CI (هر کشور یک job جدا) در یک manifest.json نهایی برای ریلیز.

اجرا:
  python3 merge_manifests.py --in-dir merged --out out/manifest.json --release-tag maps-v1
"""
import argparse
import glob
import json
import os
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True,
                     help="پوشه‌ای که همه‌ی manifest-<CODE>.json ها (از همه‌ی job های ماتریس) داخلش دانلود شده")
    ap.add_argument("--out", default="out/manifest.json")
    ap.add_argument("--release-tag", default="maps-v1")
    a = ap.parse_args()

    all_files = glob.glob(os.path.join(a.in_dir, "**", "manifest-*.json"), recursive=True)
    if not all_files:
        raise SystemExit(f"هیچ manifest-*.json در {a.in_dir} پیدا نشد")

    # اول manifest های نسخه‌ی قبلی (پوشه‌هایی که با prev- شروع می‌شوند) خوانده
    # می‌شوند، بعد manifest های تازه‌ساخته — تا کشورهای تازه همیشه جایگزین
    # نسخه‌ی قدیمی همان کشور شوند، نه برعکس.
    prev_files = sorted(f for f in all_files if os.path.basename(os.path.dirname(f)).startswith("prev-"))
    fresh_files = sorted(f for f in all_files if not os.path.basename(os.path.dirname(f)).startswith("prev-"))
    files = prev_files + fresh_files

    countries = {}
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            entry = json.load(f)
        code = entry.get("code")
        if not code:
            continue
        countries[code] = entry  # اگر تکراری بود، آخری (تازه‌ساخته) جای قبلی را می‌گیرد

    manifest = {
        "schema": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "release_tag": a.release_tag,
        "countries": sorted(countries.values(), key=lambda c: c["code"]),
    }

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"manifest نهایی -> {a.out}  ({len(countries)} کشور)")
    for c in manifest["countries"]:
        print(f"  {c['code']}  {c['name_fa']}  {c['total_size']/1e6:.1f} MB")


if __name__ == "__main__":
    main()
