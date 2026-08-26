"""Build one compact pre-rendered multi-zoom map file.

The .amap output is SQLite containing only server-rendered WebP pixels. The
mobile application reads the required image blobs by viewport and never parses
or draws OSM geometry for map display.
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from raster_primitives import RenderHandler, TileStore
from PIL import Image


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zoom_of(path, root):
    parts = path.relative_to(root).parts
    return int(parts[1] if parts[0] == "tiles" else parts[2])


def select_max_zoom(root, minimum, maximum, budget):
    by_zoom = {zoom: 0 for zoom in range(minimum, maximum + 1)}
    for path in root.rglob("*.webp"):
        if path.relative_to(root).parts[0] not in {"tiles", "poi"}:
            continue
        zoom = zoom_of(path, root)
        if zoom in by_zoom:
            by_zoom[zoom] += path.stat().st_size
    used, selected = 0, minimum
    for zoom in range(minimum, maximum + 1):
        next_size = by_zoom[zoom]
        if zoom > minimum and used + next_size > int(budget * 0.94):
            break
        used += next_size
        selected = zoom
    return selected, used


def build_preview(root, output, zoom):
    paths = list((root / "tiles" / str(zoom)).glob("*/*.webp"))
    if not paths:
        return None
    coordinates = [(int(path.parent.name), int(path.stem), path) for path in paths]
    min_x, max_x = min(x for x, _, _ in coordinates), max(x for x, _, _ in coordinates)
    min_y, max_y = min(y for _, y, _ in coordinates), max(y for _, y, _ in coordinates)
    cols, rows = max_x - min_x + 1, max_y - min_y + 1
    cell_w, cell_h = max(1, 512 // cols), max(1, 512 // rows)
    preview = Image.new("RGB", (cols * cell_w, rows * cell_h), "#10171f")
    for x, y, path in coordinates:
        with Image.open(path) as image:
            preview.paste(image.convert("RGB").resize((cell_w, cell_h)), ((x - min_x) * cell_w, (y - min_y) * cell_h))
    preview.save(output, "WEBP", quality=58, method=6)
    return output


def build_atlas(root, output, code, minimum, maximum, bounds, target_mb):
    max_zoom, raw_size = select_max_zoom(root, minimum, maximum, target_mb * 1024 * 1024)
    db = sqlite3.connect(output)
    db.executescript("""
      PRAGMA page_size=4096; PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
      CREATE TABLE metadata (name TEXT PRIMARY KEY, value TEXT);
      CREATE TABLE tiles (z INTEGER, x INTEGER, y INTEGER, data BLOB, PRIMARY KEY(z,x,y));
      CREATE TABLE poi_tiles (klass INTEGER, z INTEGER, x INTEGER, y INTEGER, data BLOB, PRIMARY KEY(klass,z,x,y));
    """)
    base, pois = [], []
    for path in root.rglob("*.webp"):
        parts = path.relative_to(root).parts
        if parts[0] == "tiles":
            _, z, x, filename = parts
            klass = None
        elif parts[0] == "poi":
            _, klass, z, x, filename = parts
            klass = int(klass)
        else:
            continue
        z = int(z)
        if z > max_zoom:
            continue
        item = (z, int(x), int(Path(filename).stem), path.read_bytes())
        if klass is None:
            base.append(item)
        else:
            pois.append((klass, *item))
    db.executemany("INSERT INTO tiles VALUES (?,?,?,?)", base)
    db.executemany("INSERT INTO poi_tiles VALUES (?,?,?,?,?)", pois)
    db.executemany("INSERT INTO metadata VALUES (?,?)", {
        "format": "ABTIN_RENDERED_ATLAS/1",
        "code": code,
        "tile_size": "512",
        "minzoom": str(minimum),
        "maxzoom": str(max_zoom),
        "overzoom_max": str(min(max_zoom + 5, 19)),
        "bounds": json.dumps(bounds),
        "rendered_on_server": "true",
    }.items())
    db.commit()
    db.execute("VACUUM")
    db.close()
    return max_zoom, len(base), len(pois), raw_size


def merge_shard_dirs(shard_dirs, dest):
    """کاشی‌های WebP از چند دایرکتوریِ شارد (هرکدام خروجیِ --shard-out یک تکه‌ی
    جغرافیایی) را در یک درخت واحد ادغام می‌کند. تکه‌ها ممکن است در کاشی‌های
    مرزی هم‌پوشانی داشته باشند (به‌عمد، برای جلوگیری از شکاف در لبه‌ی برش)؛
    محتوای آن کاشی‌ها از یک منبع OSM یکسان است، پس هر کدام که اول کپی شود کافی
    است — آخری در صورت تفاوت جزئی رونویسی می‌کند که بی‌ضرر است."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    merged = 0
    for shard_dir in shard_dirs:
        shard_root = Path(shard_dir)
        for path in shard_root.rglob("*.webp"):
            rel = path.relative_to(shard_root)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            merged += 1
    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pbf", nargs="?",
                        help="در حالت --merge-shards نیازی نیست")
    parser.add_argument("--code", required=True)
    parser.add_argument("--shard-out",
                        help="به‌جای ساختِ atlas نهایی، فقط کاشی‌های رندرشده‌ی "
                             "همین اجرا (معمولاً محدود به bbox یک تکه) را در "
                             "این دایرکتوری می‌گذارد؛ برای اجرای موازیِ چند "
                             "تکه‌ی جغرافیایی روی یک کشورِ بزرگ")
    parser.add_argument("--merge-shards", nargs="+",
                         help="به‌جای رندر از یک pbf، خروجیِ چند اجرای "
                              "--shard-out قبلی را ادغام کرده و atlas نهایی را "
                              "می‌سازد")
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--min-zoom", type=int, default=2)
    parser.add_argument("--max-zoom", type=int, default=14)
    parser.add_argument("--target-mb", type=int, default=260)
    parser.add_argument("--webp-quality", type=int, default=64)
    parser.add_argument("--webp-method", type=int, default=3,
                        help="سرعت/فشرده‌سازی WebP بین 0 تا 6؛ 3 برای ساخت سرور سریع‌تر است")
    parser.add_argument("--workers", type=int, default=0,
                        help="تعداد پردازش‌های تبدیل WebP؛ صفر یعنی تشخیص خودکار")
    parser.add_argument("--max-open-tiles", type=int, default=4096,
                        help="سقف کاشی‌های موقت در حافظه برای کاهش I/O دیسک؛ "
                             "برای کشورهای بزرگ (ایران و مشابه) مقدار پایین "
                             "باعث flush/reload مکرر همان کاشی‌ها و کندی چندبرابری "
                             "می‌شود")
    parser.add_argument("--bounds", nargs=4, type=float)
    parser.add_argument("--include-poi-tiles", action="store_true",
                        help="POIها پیش‌فرض دادهٔ اپ هستند، نه پیکسل نقشه")
    parser.add_argument("--include-buildings", action="store_true",
                        help="ساختمان‌ها پیش‌فرض در نقشهٔ پایه نیستند")
    args = parser.parse_args()
    if not 0 <= args.min_zoom <= args.max_zoom <= 18:
        raise SystemExit("invalid zoom range")
    if not 0 <= args.webp_method <= 6:
        raise SystemExit("invalid webp method")
    if args.max_open_tiles < 32:
        raise SystemExit("max-open-tiles must be at least 32")
    if args.merge_shards and args.shard_out:
        raise SystemExit("--merge-shards و --shard-out هم‌زمان قابل استفاده نیستند")
    if not args.merge_shards and not args.pbf:
        raise SystemExit("pbf لازم است (مگر در حالت --merge-shards)")
    workers = args.workers if args.workers > 0 else min(4, os.cpu_count() or 1)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.merge_shards:
        work = Path(tempfile.mkdtemp(prefix=f"abtin-atlas-merge-{args.code}-"))
        try:
            merged = merge_shard_dirs(args.merge_shards, work)
            print(f"ادغام {merged:,} کاشی از {len(args.merge_shards)} تکه", flush=True)
            bounds = args.bounds or [-180.0, -85.051129, 180.0, 85.051129]
            atlas = out / f"{args.code}.amap"
            preview = build_preview(work, out / f"{args.code}.preview.webp", args.min_zoom)
            max_zoom, base_count, poi_count, raw_size = build_atlas(
                work, atlas, args.code, args.min_zoom, args.max_zoom, bounds, args.target_mb)
            metadata = {
                "format": "ABTIN_RENDERED_ATLAS/1",
                "file": atlas.name,
                "archive": atlas.name,
                "preview": preview.name if preview else None,
                "size": atlas.stat().st_size,
                "sha256": sha256_file(atlas),
                "tile_size": 512,
                "minzoom": args.min_zoom,
                "maxzoom": max_zoom,
                "overzoom_max": min(max_zoom + 5, 19),
                "bounds": bounds,
                "base_tile_count": base_count,
                "poi_tile_count": poi_count,
                "rendered_tile_count": merged,
                "render_workers": workers,
                "target_mb": args.target_mb,
                "poi_tiles_embedded": args.include_poi_tiles,
                "buildings_embedded": args.include_buildings,
                "shards_merged": len(args.merge_shards),
            }
            (out / f"rendered-{args.code}.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(metadata, ensure_ascii=False))
        finally:
            shutil.rmtree(work, ignore_errors=True)
        return

    work = Path(tempfile.mkdtemp(prefix=f"abtin-atlas-{args.code}-"))
    try:
        store = TileStore(work, args.min_zoom, args.max_zoom, args.max_open_tiles)
        source = str(Path(args.pbf))
        RenderHandler(
            store,
            include_poi_tiles=args.include_poi_tiles,
            include_buildings=args.include_buildings,
        ).apply_file(source, locations=True)
        rendered_count = store.finalize_webp(
            quality=args.webp_quality, method=args.webp_method, workers=workers)

        if args.shard_out:
            shard_dest = Path(args.shard_out)
            if shard_dest.exists():
                shutil.rmtree(shard_dest)
            shutil.move(str(work), str(shard_dest))
            print(f"شارد {args.code} -> {shard_dest} ({rendered_count:,} کاشی)", flush=True)
            return

        bounds = args.bounds or [-180.0, -85.051129, 180.0, 85.051129]
        atlas = out / f"{args.code}.amap"
        preview = build_preview(work, out / f"{args.code}.preview.webp", args.min_zoom)
        max_zoom, base_count, poi_count, raw_size = build_atlas(
            work, atlas, args.code, args.min_zoom, args.max_zoom, bounds, args.target_mb)
        metadata = {
            "format": "ABTIN_RENDERED_ATLAS/1",
            "file": atlas.name,
            "archive": atlas.name,
            "preview": preview.name if preview else None,
            "size": atlas.stat().st_size,
            "sha256": sha256_file(atlas),
            "tile_size": 512,
            "minzoom": args.min_zoom,
            "maxzoom": max_zoom,
            "overzoom_max": min(max_zoom + 5, 19),
            "bounds": bounds,
            "base_tile_count": base_count,
            "poi_tile_count": poi_count,
            "rendered_tile_count": rendered_count,
            "render_workers": workers,
            "target_mb": args.target_mb,
            "poi_tiles_embedded": args.include_poi_tiles,
            "buildings_embedded": args.include_buildings,
        }
        (out / f"rendered-{args.code}.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(metadata, ensure_ascii=False))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
