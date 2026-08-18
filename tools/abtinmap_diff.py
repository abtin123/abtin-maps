#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
abtinmap_diff.py — ساخت پچِ افزایشی بین دو build از یک کشور.

فقط کاشی‌هایی که واقعاً محتوایشان عوض شده (نه فقط شماره‌ی داخلیِ رشته‌ها یا
ترتیبِ نودها) در پچ قرار می‌گیرند؛ بقیه از فایلِ قدیمیِ نصب‌شده روی گوشیِ
کاربر کپی می‌شوند. این یعنی به‌روزرسانیِ نقشه فقط همان بخش‌های تغییرکرده را
دانلود می‌کند، نه کل فایل را.

⚠️ پیش‌نیاز: هر دو build باید با یک --string-state مشترک ساخته شده باشند
(نگاه کنید به abtinmap_build.py)؛ وگرنه شماره‌ی رشته‌ها بین دو build جابه‌جا
می‌شود و کاشی‌های «بدون تغییر» کپی‌شده به نامِ غلط اشاره می‌کنند.

اجرا:
  python3 abtinmap_diff.py old/IR.abm new/IR.abm --code IR --out-dir out
"""
import argparse
import bisect
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abtinmap_inspect as insp  # noqa: E402


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _q(lon, lat, scale):
    return (round(lon * scale), round(lat * scale))


def canonical_tile(t, scale):
    """نمایشِ محتوامحورِ یک کاشی — مستقل از شماره‌ی داخلیِ رشته‌ها/نودها، تا
    مقایسه‌ی دو build فقط تغییرِ *واقعی* را تشخیص دهد."""
    nodes = t["nodes"]
    ways = []
    for w in t["ways"]:
        coords = tuple(_q(*nodes[r], scale) for r in w["refs"])
        ways.append((w["klass"], w["attr"], w["min_zoom"], w["name"],
                    w["speed_code"], round(w["width_m"] * 10), coords))
    ways.sort()
    areas = []
    for a in t["areas"]:
        rings = tuple(tuple(_q(*pt, scale) for pt in ring) for ring in a["rings"])
        areas.append((a["klass"], a["attr"], a["min_zoom"], a["name"], rings))
    areas.sort()
    pois = []
    for poi in t["pois"]:
        lon, lat = _q(poi["lon"], poi["lat"], scale)
        pois.append((lon, lat, poi["klass"], poi["min_zoom"], poi["name"]))
    pois.sort()
    border = sorted(set(t["border"].values()))
    return {"ways": ways, "areas": areas, "pois": pois, "border": border}


def tile_hash(m, tid):
    idx = bisect.bisect_left(m.ids, tid)
    off, cl, rl, mask = m.recs[idx]
    m.f.seek(off)
    body = m.d.decompress(m.f.read(cl), max_output_size=rl)
    z, x, y = tid >> 44, (tid >> 22) & 0x3FFFFF, tid & 0x3FFFFF
    t = m._parse_tile(body, z, x, y)
    canon = canonical_tile(t, m.coord_scale)
    digest = hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()
    return digest, off, cl, rl, mask


def diff(old_path, new_path, out_dir, code):
    old = insp.AbtinMap(old_path)
    new = insp.AbtinMap(new_path)

    old_ids = set(old.ids)
    new_ids = set(new.ids)
    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    common = sorted(new_ids & old_ids)

    changed = []
    unchanged = 0
    for tid in common:
        h_old, *_ = tile_hash(old, tid)
        h_new, *_ = tile_hash(new, tid)
        if h_old != h_new:
            changed.append(tid)
        else:
            unchanged += 1

    touched = sorted(set(added) | set(changed))

    os.makedirs(out_dir, exist_ok=True)
    patch_path = os.path.join(out_dir, f"{code}.abmpatch")
    with open(new_path, "rb") as nf, open(patch_path, "wb") as out:
        nf.seek(new.strings_offset)
        strings_bytes = nf.read(new.strings_comp)
        out.write(strings_bytes)
        cursor = len(strings_bytes)

        ops = []
        for tid in touched:
            idx = bisect.bisect_left(new.ids, tid)
            off, cl, rl, mask = new.recs[idx]
            nf.seek(off)
            out.write(nf.read(cl))
            ops.append({"tile_id": tid, "offset": cursor, "clen": cl,
                       "rlen": rl, "mask": mask})
            cursor += cl

    with open(new_path, "rb") as nf:
        header_prefix = nf.read(36).hex()  # magic..bbox — بقیه‌ی هدر بازساخته می‌شود

    manifest = {
        "code": code,
        "base_sha256": sha256_file(old_path),
        "target_sha256": sha256_file(new_path),
        "header_prefix_hex": header_prefix,
        "base_zoom": new.base_zoom,
        "coord_scale": new.coord_scale,
        "build_epoch": new.build_epoch,
        "strings": {"clen": len(strings_bytes), "rlen": new.strings_raw,
                    "count": new.string_count},
        "ops": ops,
        "removed_tile_ids": removed,
        "kept_tile_count": unchanged,
        "target_tile_count": new.tile_count,
        "patch_size": os.path.getsize(patch_path),
        "patch_sha256": sha256_file(patch_path),
    }
    manifest_path = os.path.join(out_dir, f"patch-{code}.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    full_size = os.path.getsize(new_path)
    patch_size = manifest["patch_size"]
    print(f"{code}: {len(touched):,} کاشیِ تغییرکرده/جدید، "
          f"{len(removed):,} حذف‌شده، {unchanged:,} بدون تغییر")
    print(f"  فایلِ کامل: {full_size/1e6:.1f} MB   "
          f"پچ: {patch_size/1e6:.1f} MB   "
          f"({100*patch_size/full_size:.1f}٪ از حجمِ کامل)")
    print(f"  -> {patch_path}")
    print(f"  -> {manifest_path}")
    return manifest_path, patch_path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("old_abm")
    ap.add_argument("new_abm")
    ap.add_argument("--code", required=True)
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    diff(a.old_abm, a.new_abm, a.out_dir, a.code)


if __name__ == "__main__":
    main()
