#!/usr/bin/env python3
"""Creates a self-contained, server-rendered raster tile package from OSM PBF.

The output ZIP contains WebP tiles and a style template. Flutter never reads
geometry from it: it downloads, extracts and displays these completed pixels.
"""
import argparse
import concurrent.futures
import hashlib
import json
import math
import shutil
import sys
import tempfile
import zipfile
from collections import OrderedDict
from pathlib import Path

try:
    import osmium
    from PIL import Image, ImageDraw
except ImportError as error:
    raise SystemExit("Install server dependencies: pip install osmium Pillow") from error


TILE_SIZE = 512
MAX_OPEN_TILES = 96
ROAD_STYLE = {
    "motorway": ("#F2A65A", 10), "trunk": ("#F4C96A", 8),
    "primary": ("#F3F5F7", 7), "secondary": ("#D9E0E8", 6),
    "tertiary": ("#BAC5D0", 5), "residential": ("#99A6B5", 4),
    "service": ("#7E8C9B", 3), "unclassified": ("#8794A2", 3),
}
POI_STYLE = {
    "fuel": (50, "#F6A623"), "parking": (51, "#71B7FF"),
    "hospital": (52, "#FF6B6B"), "pharmacy": (53, "#78E08F"),
    "police": (54, "#71B7FF"), "school": (55, "#B8E986"),
    "restaurant": (56, "#E0A458"), "cafe": (57, "#C98B4B"),
    "bank": (58, "#63D0FF"), "hotel": (59, "#C5A4FF"),
    "supermarket": (60, "#5ED39B"), "mosque": (61, "#78D6D1"),
    "toilets": (62, "#B4C7E7"), "bus_station": (63, "#F4D35E"),
    "airport": (64, "#B9C9FF"), "attraction": (65, "#E6A4FF"),
    "park": (66, "#5FC77B"), "pitch": (67, "#80D398"),
    "place": (68, "#D6DEE8"), "speed_camera": (70, "#FF5C61"),
    "traffic_calming": (71, "#FFD166"), "traffic_signals": (72, "#4ADE80"),
}


def _encode_webp(job):
    """کارگر مستقلِ تبدیل PNG موقت به WebP؛ باید در سطح ماژول باشد تا قابل
    ارسال به ProcessPool باشد."""
    raw_path, quality, method = job
    png = Path(raw_path)
    webp = png.with_suffix(".webp")
    with Image.open(png) as image:
        image.save(webp, "WEBP", quality=quality, method=method)
    png.unlink()
    return str(webp)


def mercator(lon, lat, zoom):
    lat = max(-85.05112878, min(85.05112878, lat))
    scale = TILE_SIZE * (1 << zoom)
    x = (lon + 180.0) / 360.0 * scale
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * scale
    return x, y


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TileStore:
    def __init__(self, root, min_zoom, max_zoom, max_open_tiles=256):
        self.root = Path(root)
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.max_open_tiles = max_open_tiles
        self.open = OrderedDict()

    def _png_path(self, z, x, y, layer="tiles"):
        return self.root / layer / str(z) / str(x) / f"{y}.png"

    def image(self, z, x, y, layer="tiles"):
        key = (z, x, y, layer)
        image = self.open.pop(key, None)
        if image is not None:
            self.open[key] = image
            return image
        path = self._png_path(z, x, y, layer)
        if path.exists():
            image = Image.open(path).convert("RGBA")
        else:
            image = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
        self.open[key] = image
        if len(self.open) > self.max_open_tiles:
            old_key, old_image = self.open.popitem(last=False)
            self._write_png(old_key, old_image)
        return image

    def _write_png(self, key, image):
        path = self._png_path(*key[:3], layer=key[3])
        path.parent.mkdir(parents=True, exist_ok=True)
        # PNG فقط یک فایلِ موقت است و بعد از آن به WebP تبدیل می‌شود؛ فشرده‌سازی
        # سنگین PNG در این مرحله زمان ساخت کشور را چند برابر می‌کرد، در حالی که
        # هیچ اثری بر حجم ABM نهایی ندارد.
        image.save(path, "PNG", optimize=False, compress_level=1)

    def flush(self):
        for key, image in self.open.items():
            self._write_png(key, image)
        self.open.clear()

    def draw_line(self, coordinates, color, width, min_zoom=None):
        if len(coordinates) < 2:
            return
        first_zoom = max(self.min_zoom, min_zoom if min_zoom is not None else self.min_zoom)
        for z in range(first_zoom, self.max_zoom + 1):
            points = [mercator(lon, lat, z) for lon, lat in coordinates]
            min_x = max(0, int(min(x for x, _ in points) // TILE_SIZE))
            max_x = min((1 << z) - 1, int(max(x for x, _ in points) // TILE_SIZE))
            min_y = max(0, int(min(y for _, y in points) // TILE_SIZE))
            max_y = min((1 << z) - 1, int(max(y for _, y in points) // TILE_SIZE))
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    local = [(px - x * TILE_SIZE, py - y * TILE_SIZE) for px, py in points]
                    ImageDraw.Draw(self.image(z, x, y)).line(local, fill=color, width=width, joint="curve")

    def draw_polygon(self, coordinates, fill, outline=None, extrusion=0):
        if len(coordinates) < 3:
            return
        for z in range(self.min_zoom, self.max_zoom + 1):
            points = [mercator(lon, lat, z) for lon, lat in coordinates]
            min_x = max(0, int(min(x for x, _ in points) // TILE_SIZE))
            max_x = min((1 << z) - 1, int(max(x for x, _ in points) // TILE_SIZE))
            min_y = max(0, int(min(y for _, y in points) // TILE_SIZE))
            max_y = min((1 << z) - 1, int(max(y for _, y in points) // TILE_SIZE))
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    local = [(px - x * TILE_SIZE, py - y * TILE_SIZE) for px, py in points]
                    draw = ImageDraw.Draw(self.image(z, x, y))
                    if extrusion:
                        side = [(px + extrusion, py + extrusion) for px, py in local]
                        draw.polygon(side, fill="#17202A")
                    draw.polygon(local, fill=fill, outline=outline)

    def draw_poi(self, lon, lat, poi_klass, color):
        for z in range(max(11, self.min_zoom), self.max_zoom + 1):
            px, py = mercator(lon, lat, z)
            x, y = int(px // TILE_SIZE), int(py // TILE_SIZE)
            r = max(3, min(7, 2 + z // 4))
            local_x, local_y = px - x * TILE_SIZE, py - y * TILE_SIZE
            draw = ImageDraw.Draw(self.image(z, x, y, f"poi/{poi_klass}"))
            draw.ellipse((local_x-r-1, local_y-r-1, local_x+r+1, local_y+r+1), fill="#101419")
            draw.ellipse((local_x-r, local_y-r, local_x+r, local_y+r), fill=color)

    def finalize_webp(self, quality=64, method=3, workers=1):
        self.flush()
        jobs = [(str(png), quality, method) for png in self.root.rglob("*.png")]
        if not jobs:
            return 0
        if workers <= 1:
            for job in jobs:
                _encode_webp(job)
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                list(executor.map(_encode_webp, jobs, chunksize=16))
        return len(jobs)


def way_coordinates(way):
    try:
        return [(node.location.lon, node.location.lat) for node in way.nodes if node.location.valid()]
    except osmium.InvalidLocationError:
        return []


class AreaHandler(osmium.SimpleHandler):
    def __init__(self, store):
        super().__init__()
        self.store = store

    def way(self, way):
        tags = way.tags
        coords = way_coordinates(way)
        if len(coords) < 3:
            return
        if "building" in tags:
            height = float(tags.get("height", "8").split(" ")[0]) if tags.get("height", "").split(" ")[0].replace(".", "", 1).isdigit() else 8
            self.store.draw_polygon(coords, "#384552", "#566372", min(10, max(2, int(height / 3))))
        elif tags.get("natural") == "water" or tags.get("waterway"):
            self.store.draw_polygon(coords, "#183B5A")
        elif tags.get("landuse") in ("forest", "grass", "meadow", "residential") or tags.get("leisure") == "park":
            self.store.draw_polygon(coords, "#1E3B32")


class RoadHandler(osmium.SimpleHandler):
    def __init__(self, store):
        super().__init__()
        self.store = store

    def way(self, way):
        kind = way.tags.get("highway")
        if kind not in ROAD_STYLE:
            return
        coords = way_coordinates(way)
        if len(coords) > 1:
            color, width = ROAD_STYLE[kind]
            min_zoom = {
                "motorway": 5, "trunk": 5, "primary": 6,
                "secondary": 7, "tertiary": 9, "residential": 13,
                "unclassified": 13, "service": 14,
            }.get(kind, 14)
            self.store.draw_line(coords, "#1C2530", width + 2, min_zoom)
            self.store.draw_line(coords, color, width, min_zoom)


class PoiHandler(osmium.SimpleHandler):
    def __init__(self, store):
        super().__init__()
        self.store = store

    def node(self, node):
        if not node.location.valid():
            return
        tags = node.tags
        key = self._key(tags)
        if key in POI_STYLE:
            poi_klass, color = POI_STYLE[key]
            self.store.draw_poi(node.location.lon, node.location.lat, poi_klass, color)

    @staticmethod
    def _key(tags):
        if "traffic_calming" in tags:
            return "traffic_calming"
        if tags.get("shop") == "supermarket":
            return "supermarket"
        if tags.get("tourism") in ("hotel", "attraction"):
            return tags.get("tourism")
        if tags.get("aeroway") == "aerodrome":
            return "airport"
        if tags.get("amenity") == "place_of_worship" and tags.get("religion") == "muslim":
            return "mosque"
        if tags.get("leisure") in ("park", "pitch"):
            return tags.get("leisure")
        if tags.get("place"):
            return "place"
        return tags.get("amenity") or tags.get("highway")


class RenderHandler(osmium.SimpleHandler):
    """یک بارخوانی PBF برای ساختمان، راه و POI.

    اجرای قبلی فایل بزرگ PBF را سه بار کامل می‌خواند. این handler همان منطق
    لایه‌ها را در یک عبور انجام می‌دهد تا زمان CPU و I/O ساخت کشور به‌شکل
    محسوسی کمتر شود.
    """

    def __init__(self, store, include_poi_tiles=False, include_buildings=False):
        super().__init__()
        self.store = store
        self.include_poi_tiles = include_poi_tiles
        self.include_buildings = include_buildings

    def way(self, way):
        tags = way.tags
        coords = way_coordinates(way)
        if len(coords) < 2:
            return
        if len(coords) >= 3:
            if "building" in tags and self.include_buildings:
                height_value = tags.get("height", "8").split(" ")[0]
                height = float(height_value) if height_value.replace(".", "", 1).isdigit() else 8
                self.store.draw_polygon(coords, "#384552", "#566372", min(10, max(2, int(height / 3))))
            elif tags.get("natural") == "water" or tags.get("waterway"):
                self.store.draw_polygon(coords, "#183B5A")
            elif tags.get("landuse") in ("forest", "grass", "meadow", "residential") or tags.get("leisure") == "park":
                self.store.draw_polygon(coords, "#1E3B32")
        kind = tags.get("highway")
        if kind in ROAD_STYLE:
            color, width = ROAD_STYLE[kind]
            min_zoom = {
                "motorway": 5, "trunk": 5, "primary": 6,
                "secondary": 7, "tertiary": 9, "residential": 13,
                "unclassified": 13, "service": 14,
            }.get(kind, 14)
            self.store.draw_line(coords, "#1C2530", width + 2, min_zoom)
            self.store.draw_line(coords, color, width, min_zoom)

    def node(self, node):
        if not self.include_poi_tiles:
            return
        if not node.location.valid():
            return
        key = PoiHandler._key(node.tags)
        if key in POI_STYLE:
            poi_klass, color = POI_STYLE[key]
            self.store.draw_poi(node.location.lon, node.location.lat, poi_klass, color)


def write_style(path, bounds, min_zoom, max_zoom):
    style = {
        "version": 8,
        "name": "Abtin rendered offline",
        "sources": {"abtin-rendered": {
            "type": "raster", "tiles": ["__ABTIN_PACKAGE_ROOT__/tiles/{z}/{x}/{y}.webp"],
            "tileSize": TILE_SIZE, "minzoom": min_zoom, "maxzoom": max_zoom,
            "bounds": bounds,
        }},
        "layers": [
            {"id": "background", "type": "background", "paint": {"background-color": "#0F1419"}},
            {"id": "abtin-rendered", "type": "raster", "source": "abtin-rendered",
             "paint": {"raster-fade-duration": 0, "raster-resampling": "linear"}},
        ],
    }
    for _, (klass, _) in POI_STYLE.items():
        source = f"abtin-poi-{klass}"
        style["sources"][source] = {
            "type": "raster",
            "tiles": [f"__ABTIN_PACKAGE_ROOT__/poi/{klass}/{{z}}/{{x}}/{{y}}.webp"],
            "tileSize": TILE_SIZE, "minzoom": max(11, min_zoom), "maxzoom": max_zoom,
            "bounds": bounds,
        }
        style["layers"].append({
            "id": source, "type": "raster", "source": source,
            "metadata": {"abtin_poi_klass": klass},
            "paint": {"raster-fade-duration": 0, "raster-resampling": "linear"},
        })
    Path(path).write_text(json.dumps(style, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pbf")
    parser.add_argument("--code", required=True)
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--min-zoom", type=int, default=6)
    # سطح ۱۶، نمایش خیابان و تقاطع را ممکن می‌کند؛ با تقسیم منطقه‌ای کشورها
    # حجم دانلود همچنان کنترل‌شده می‌ماند.
    parser.add_argument("--max-zoom", type=int, default=16)
    parser.add_argument("--bounds", nargs=4, type=float, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"))
    args = parser.parse_args()
    if not 0 <= args.min_zoom <= args.max_zoom <= 18:
        raise SystemExit("Invalid zoom range")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"abtin-rendered-{args.code}-"))
    try:
        store = TileStore(work, args.min_zoom, args.max_zoom)
        source = str(Path(args.pbf))
        AreaHandler(store).apply_file(source, locations=True)
        RoadHandler(store).apply_file(source, locations=True)
        PoiHandler(store).apply_file(source, locations=True)
        tile_count = store.finalize_webp()
        if tile_count == 0:
            raise SystemExit("No rendered tiles were produced")
        bounds = args.bounds or [-180.0, -85.051129, 180.0, 85.051129]
        write_style(work / "style.template.json", bounds, args.min_zoom, args.max_zoom)
        archive_name = f"{args.code}.rendered.zip"
        archive_path = out / archive_name
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for file in work.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(work).as_posix())
        metadata = {
            "format": "ABTIN_RENDERED_RASTER/1", "archive": archive_name,
            "size": archive_path.stat().st_size, "sha256": sha256_file(archive_path),
            "tile_size": TILE_SIZE, "minzoom": args.min_zoom, "maxzoom": args.max_zoom,
            "bounds": bounds, "style_template": "style.template.json", "tile_count": tile_count,
        }
        meta_path = out / f"rendered-{args.code}.json"
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(metadata, ensure_ascii=False))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
