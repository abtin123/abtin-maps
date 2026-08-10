#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
abtinmap_build.py — تبدیل .osm.pbf به فرمت باینری یکپارچه ABTINMAP v1

یک پاس شمارش تقاطع + یک پاس استخراج. خروجی: یک فایل .abm که هم هندسه‌ی نمایشی،
هم گراف مسیریابی، هم POI و هم محدودیت سرعت را دارد.

نیازمندی:  pip install osmium zstandard
اجرا:      python3 abtinmap_build.py iran-latest.osm.pbf -o out/IR.abm --region IR
"""

import argparse
import json
import math
import os
import pickle
import struct
import sys
import tempfile
import time
from collections import defaultdict

import osmium
import zstandard as zstd

MAGIC = b"ABTINMAP"
# v2: به هر way یک فیلد جدید width_dm (عرض به دسی‌متر) بعد از speed_code
# اضافه شد. خواننده‌ی Dart باید هم‌زمان با این نسخه به‌روز باشد وگرنه
# بایت‌ها اشتباه parse می‌شوند (فایل‌های v1 قدیمی دیگر با این اسکریپت
# سازگار نیستند — باید دوباره ساخته شوند).
VERSION = 2
COORD_SCALE = 10_000_000
HEADER_SIZE = 128
SHARD_COUNT = 256

# ---------------------------------------------------------------- classes ----
ROAD_CLASSES = {
    "motorway": (1, 5, 120), "motorway_link": (1, 11, 80),
    "trunk": (2, 6, 100), "trunk_link": (2, 11, 70),
    "primary": (3, 7, 90), "primary_link": (3, 12, 60),
    "secondary": (4, 9, 80), "secondary_link": (4, 12, 50),
    "tertiary": (5, 11, 70), "tertiary_link": (5, 13, 50),
    "residential": (6, 13, 50), "living_street": (6, 14, 30),
    "service": (7, 15, 20), "unclassified": (8, 13, 50),
    "track": (9, 14, 30), "footway": (10, 15, 5), "path": (10, 15, 5),
    "pedestrian": (10, 15, 5), "cycleway": (11, 15, 15), "steps": (12, 16, 2),
}
KLASS_RAILWAY, KLASS_WATER_AREA, KLASS_WATERWAY = 20, 30, 31
KLASS_GREEN, KLASS_URBAN, KLASS_BUILDING, KLASS_BOUNDARY = 32, 33, 34, 40

# عرضِ پیش‌فرض هر کلاس جاده (متر) — فقط وقتی از OSM (تگ width یا lanes)
# چیزی استخراج نشود استفاده می‌شود. باید دقیقاً با AbmWidthEstimate در
# lib/abtinmap/abm_models.dart (سمت Dart) هم‌ارز بماند.
DEFAULT_WIDTH_M = {
    1: 15.0, 2: 12.0, 3: 9.0, 4: 7.5, 5: 6.5, 6: 6.0,
    7: 3.5, 8: 5.0, 9: 2.5, 10: 2.0, 11: 2.0, 12: 1.2,
}

POI_CLASSES = {
    "fuel": 50, "charging_station": 50, "parking": 51, "hospital": 52,
    "pharmacy": 53, "police": 54, "fire_station": 54, "school": 55,
    "university": 55, "restaurant": 56, "fast_food": 56, "cafe": 57,
    "bank": 58, "atm": 58, "hotel": 59, "supermarket": 60, "bakery": 60,
    "mosque": 61, "place_of_worship": 61, "toilets": 62, "bus_station": 63,
    "airport": 64, "aerodrome": 64, "attraction": 65, "museum": 65,
    "viewpoint": 65, "park": 66, "pitch": 67, "stadium": 67,
    "speed_camera": 70,
}

# مقادیر تگ traffic_calming که در OSM به معنای سرعت‌گیر فیزیکی‌اند.
TRAFFIC_CALMING_VALUES = {
    "bump", "hump", "table", "cushion", "rumble_strip", "chicane", "choker",
}
POI_SPEED_BUMP = 71
PLACE_MIN_ZOOM = {
    # برای این‌که در زوم‌های خیلی دور هم نمای سراسریِ کشور قابل‌فهم بماند،
    # چند سطحِ مهم کمی زودتر ظاهر می‌شوند.
    "country": 3, "state": 4, "province": 4, "city": 6, "town": 9,
    "village": 11, "suburb": 12, "neighbourhood": 14, "hamlet": 13,
}

GREEN_LANDUSE = {"forest", "grass", "meadow", "park", "recreation_ground",
                 "village_green", "cemetery", "orchard", "farmland", "scrub"}
URBAN_LANDUSE = {"residential", "industrial", "commercial", "retail",
                 "construction", "military", "quarry"}

# feature kinds inside shards
K_WAY, K_AREA, K_POI = 1, 2, 3

# ------------------------------------------------------------- primitives ----
def w_uvarint(buf: bytearray, v: int) -> None:
    if v < 0:
        raise ValueError(f"negative uvarint: {v}")
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            buf.append(b | 0x80)
        else:
            buf.append(b)
            return


def w_svarint(buf: bytearray, v: int) -> None:
    w_uvarint(buf, (v << 1) ^ (v >> 63) if v >= 0 else ((-v) << 1) - 1)


def tile_xy(lon: float, lat: float, z: int):
    n = 1 << z
    x = int((lon + 180.0) / 360.0 * n)
    lat = max(-85.05112878, min(85.05112878, lat))
    r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(r) + 1.0 / math.cos(r)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tile_origin(x: int, y: int, z: int):
    n = 1 << z
    lon = x / n * 360.0 - 180.0
    ry = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    return lon, math.degrees(ry)


def tile_id(z: int, x: int, y: int) -> int:
    return (z << 44) | (x << 22) | y


def gkey(lon_e7: int, lat_e7: int) -> int:
    return (lat_e7 + 900_000_000) * 3_600_000_001 + (lon_e7 + 1_800_000_000)


def haversine(a, b) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12_742_000.0 * math.asin(min(1.0, math.sqrt(h)))


def simplify(points, tol_m: float):
    """Douglas-Peucker با تلورانس متری (تقریب صفحه‌ای، کافی برای رندر)."""
    if tol_m <= 0 or len(points) < 3:
        return points
    tol = tol_m / 111_320.0
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = points[i]
        bx, by = points[j]
        dx, dy = bx - ax, by - ay
        den = dx * dx + dy * dy
        best, best_d = -1, 0.0
        for k in range(i + 1, j):
            px, py = points[k]
            if den == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / den))
                d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > best_d:
                best_d, best = d, k
        if best_d > tol:
            keep[best] = True
            stack.append((i, best))
            stack.append((best, j))
    return [p for p, k in zip(points, keep) if k]


class HashBitset:
    """بیت‌ست هش‌محور با حافظه‌ی ثابت. مثبت کاذب فقط یک تقاطع اضافی می‌سازد."""

    def __init__(self, bits: int):
        self.mask = bits - 1
        self.buf = bytearray(bits >> 3)

    def _i(self, key: int) -> int:
        return ((key * 0x9E3779B97F4A7C15) >> 17) & self.mask

    def test_set(self, key: int) -> bool:
        i = self._i(key)
        byte, bit = i >> 3, 1 << (i & 7)
        if self.buf[byte] & bit:
            return True
        self.buf[byte] |= bit
        return False

    def test(self, key: int) -> bool:
        i = self._i(key)
        return bool(self.buf[i >> 3] & (1 << (i & 7)))


# ---------------------------------------------------------- speed encoding ---
def encode_maxspeed(raw, klass, default_kmh):
    """(code, explicit) — جدول ۵ مستند فرمت."""
    if raw:
        s = raw.strip().lower()
        if s in ("none", "unlimited"):
            return 255, True
        if s.startswith("ir:urban") or s == "urban":
            return 200, False
        if s.startswith("ir:rural") or s.startswith("ir:motorway"):
            return 201, False
        mult = 1.60934 if "mph" in s else 1.0
        num = "".join(ch for ch in s if ch.isdigit())
        if num:
            kmh = int(int(num) * mult)
            if 5 <= kmh <= 200:
                return max(1, min(40, round(kmh / 5))), True
    if default_kmh and default_kmh >= 5:
        return 200 if klass >= 6 else 201, False
    return 0, False


# ------------------------------------------------------------ width encoding --
def parse_width_m(raw):
    """تگ width اُاس‌ام را به متر تبدیل می‌کند. فرمت‌های رایج: "5", "5.5",
    "5 m", "16'" (فوت)، "16'6\"" (فوت و اینچ). خروجی None یعنی قابل‌پارس نبود."""
    if not raw:
        return None
    s = raw.strip().lower()
    try:
        if s.endswith("m"):
            return float(s[:-1].strip())
        if "'" in s:
            parts = s.replace('"', "").split("'")
            feet = float(parts[0])
            inches = float(parts[1]) if len(parts) > 1 and parts[1].strip() else 0.0
            return (feet * 12.0 + inches) * 0.0254
        return float(s)
    except (ValueError, IndexError):
        return None


def width_from_lanes(raw, klass):
    """اگر width نبود، از تعداد لِین تخمین می‌زنیم (هر لِین ~۳ تا ۳.۵ متر)."""
    if not raw:
        return None
    try:
        lanes = float(raw.split(";")[0])
    except ValueError:
        return None
    if lanes <= 0:
        return None
    lane_width = 3.5 if klass <= 4 else 3.0
    return lanes * lane_width


def resolve_width_m(tags, klass):
    """عرض نهایی: تگ width > تخمین از lanes > مقدار پیش‌فرض کلاس."""
    w = parse_width_m(tags.get("width"))
    if w is None:
        w = width_from_lanes(tags.get("lanes"), klass)
    if w is None:
        w = DEFAULT_WIDTH_M.get(klass, 3.0)
    # محدوده‌ی معقول — از دادهٔ خراب/غلط OSM (مثلاً width=0 یا width=500)
    # جلوگیری می‌کند.
    return max(0.5, min(40.0, w))


# کشورهایی که رانندگی در آن‌ها از سمت چپ است (بقیه پیش‌فرض راست‌رانی‌اند،
# مثل ایران). کد ISO 3166-1 alpha-2. این فقط برای تعیینِ «جهت» است — مثلاً
# جهتِ چرخش در میدان (در راست‌رانی پادساعت‌گرد، در چپ‌رانی ساعت‌گرد) — و در
# بیتِ ۳ از فیلد flags هدر ذخیره می‌شود تا اپ حین مسیریابی/رندر از آن
# استفاده کند.
LEFT_HAND_TRAFFIC_COUNTRIES = {
    "AG", "AU", "BS", "BD", "BB", "BT", "BW", "BN", "CY", "DM", "TL", "FJ",
    "GD", "GY", "HK", "IN", "ID", "IE", "JM", "JP", "KE", "KI", "LS", "MO",
    "MW", "MY", "MV", "MT", "MU", "MZ", "NA", "NR", "NP", "NZ", "NU", "PK",
    "PG", "KN", "LC", "VC", "WS", "SC", "SG", "SB", "ZA", "LK", "SR", "SZ",
    "TZ", "TH", "TO", "TT", "TV", "UG", "GB", "ZM", "ZW", "JE", "GG", "IM",
    "BM", "KY", "FK", "AI", "VG", "MS", "TC",
}


def resolve_driving_side(value, region_code):
    """right/left/auto -> 'right' یا 'left'. در حالت auto بر اساس کدِ
    کشور (مثلاً از --region) تشخیص داده می‌شود؛ اگر کد ناشناس بود، راست‌رانی
    (رایج‌ترین حالت، مطابقِ ایران) پیش‌فرض است."""
    if value in ("right", "left"):
        return value
    code = (region_code or "").strip().upper()
    return "left" if code in LEFT_HAND_TRAFFIC_COUNTRIES else "right"


# ------------------------------------------------------------- pass 1 ---------
class JunctionCounter(osmium.SimpleHandler):
    def __init__(self, bits: int):
        super().__init__()
        self.seen1 = HashBitset(bits)
        self.seen2 = HashBitset(bits)
        self.ways = 0

    def way(self, w):
        hw = w.tags.get("highway")
        if hw not in ROAD_CLASSES:
            return
        self.ways += 1
        refs = [n.ref for n in w.nodes]
        if not refs:
            return
        for r in (refs[0], refs[-1]):
            self.seen2.test_set(r)
        for r in refs[1:-1]:
            if self.seen1.test_set(r):
                self.seen2.test_set(r)


# ------------------------------------------------------------- pass 2 ---------
class Extractor(osmium.SimpleHandler):
    def __init__(self, opts, junctions: HashBitset, sink):
        super().__init__()
        self.o = opts
        self.j = junctions
        self.sink = sink
        self.stats = defaultdict(int)

    # --- POIs ------------------------------------------------------------
    def node(self, n):
        t = n.tags
        klass = None
        min_zoom = self.o.poi_min_zoom
        for k in ("amenity", "shop", "tourism", "leisure", "aeroway", "highway"):
            v = t.get(k)
            if v and v in POI_CLASSES:
                klass = POI_CLASSES[v]
                break
        if klass is None and t.get("enforcement") in ("maxspeed", "average_speed"):
            klass = POI_CLASSES["speed_camera"]
        if klass is None and (t.get("traffic_calming") in TRAFFIC_CALMING_VALUES
                              or t.get("traffic_calming") == "yes"):
            klass = POI_SPEED_BUMP
        if klass is None:
            place = t.get("place")
            if place in PLACE_MIN_ZOOM:
                klass, min_zoom = 68, PLACE_MIN_ZOOM[place]
        if klass is None:
            return
        try:
            lon, lat = n.location.lon, n.location.lat
        except Exception:
            return
        name = t.get("name:fa") or t.get("name") or ""
        self.stats["pois"] += 1
        self.sink.emit_point(lon, lat, klass, min_zoom, name)

    # --- ways ------------------------------------------------------------
    def way(self, w):
        t = w.tags
        try:
            pts = [(n.lon, n.lat) for n in w.nodes if n.location.valid()]
            refs = [n.ref for n in w.nodes if n.location.valid()]
        except Exception:
            return
        if len(pts) < 2:
            return
        name = t.get("name:fa") or t.get("name") or ""

        hw = t.get("highway")
        if hw in ROAD_CLASSES:
            klass, min_zoom, default_kmh = ROAD_CLASSES[hw]
            # ---------------------------------------------------------------
            # مهم: این بیت‌ها باید دقیقاً با AbmAttr در lib/abtinmap/abm_models.dart
            # یکی باشند — قبلاً جابه‌جا بودند (پل/تونل برعکس، roundabout هرگز
            # درست نمی‌شد، و بدتر از همه bit9 که Dart آن را noAccess می‌خواند
            # این‌جا برای رمپ/لینک استفاده می‌شد؛ یعنی همه‌ی رمپ‌های بزرگراهی
            # کلاً از گراف مسیریابی حذف می‌شدند). اگر این جدول را تغییر دادی،
            # AbmAttr در Dart را هم همزمان عوض کن.
            #   bit0 onewayForward   bit1 onewayBackward  bit2 bridge
            #   bit3 tunnel          bit4 roundabout       bit5 link
            #   bit6 toll            bit7 surfaceUnpaved   bit9 noAccess
            #   bit11 explicitMaxspeed
            attr = 0
            oneway = (t.get("oneway") or "").lower()
            if oneway in ("yes", "true", "1"):
                attr |= 1 << 0
            elif oneway == "-1":
                attr |= 1 << 1
            if t.get("junction") == "roundabout":
                attr |= (1 << 0) | (1 << 4)
            if t.get("bridge"):
                attr |= 1 << 2
            if t.get("tunnel"):
                attr |= 1 << 3
            if "_link" in hw:
                attr |= 1 << 5
            if t.get("toll") == "yes":
                attr |= 1 << 6
            if (t.get("surface") or "") in ("unpaved", "gravel", "dirt", "ground", "sand"):
                attr |= 1 << 7

            # دسترسی واقعی — قبلاً اصلاً خوانده نمی‌شد، یعنی جاده‌های خصوصی
            # واقعی هم وارد گراف مسیریابی می‌شدند.
            access = (t.get("access") or "").lower()
            motor_vehicle = (t.get("motor_vehicle") or t.get("motorcar") or "").lower()
            no_access = access in ("private", "no") or (
                klass <= 9 and motor_vehicle in ("private", "no")
            )
            if no_access:
                attr |= 1 << 9

            # این سه‌تا فعلاً سمت Dart خوانده نمی‌شوند؛ روی بیت‌های آزاد
            # (۱۲+) نگه داشته می‌شوند تا با فیلدهای واقعی تداخل نکنند.
            if hw in ("footway", "path", "pedestrian", "steps", "cycleway"):
                attr |= 1 << 12
            if t.get("foot") == "no":
                attr |= 1 << 13
            if t.get("bicycle") == "no":
                attr |= 1 << 14

            code, explicit = encode_maxspeed(t.get("maxspeed"), klass, default_kmh)
            if explicit:
                attr |= 1 << 11
            speed = (code * 5) if 1 <= code <= 40 else (
                50 if code == 200 else (100 if code == 201 else default_kmh))
            width_dm = round(resolve_width_m(t, klass) * 10)
            junc = [i for i, r in enumerate(refs)
                    if i in (0, len(refs) - 1) or self.j.test(r)]
            self.stats["roads"] += 1
            self.sink.emit_line(pts, klass, attr, min_zoom, name, code,
                                routable=True, junction_idx=junc, speed_kmh=speed,
                                width_dm=width_dm)
            return

        if t.get("railway") in ("rail", "subway", "light_rail", "tram"):
            self.sink.emit_line(pts, KLASS_RAILWAY, 0, 10, name, 0, False, None, 0, 0)
            return

        closed = refs[0] == refs[-1] and len(pts) >= 4
        area_klass, area_zoom = None, 15
        if t.get("natural") in ("water", "bay") or t.get("waterway") == "riverbank" \
                or t.get("landuse") == "reservoir":
            area_klass, area_zoom = KLASS_WATER_AREA, 6
        elif t.get("leisure") in ("park", "garden", "pitch") or \
                (t.get("landuse") or "") in GREEN_LANDUSE or t.get("natural") == "wood":
            area_klass, area_zoom = KLASS_GREEN, 10
        elif (t.get("landuse") or "") in URBAN_LANDUSE:
            area_klass, area_zoom = KLASS_URBAN, 11
        elif t.get("building") and not self.o.drop_buildings:
            area_klass, area_zoom = KLASS_BUILDING, 15
        if area_klass is not None and closed:
            self.stats["areas"] += 1
            self.sink.emit_area(pts, area_klass, 0, area_zoom, name)
            return

        wt = t.get("waterway")
        if wt in ("river", "stream", "canal", "drain"):
            self.sink.emit_line(pts, KLASS_WATERWAY, 0,
                                9 if wt == "river" else 13, name, 0, False, None, 0, 0)


# ------------------------------------------------------------ shard sink -----
class ShardSink:
    """قطعه‌بندی هر عارضه بر مرز کاشی و ریختن رکوردها در shard های موقت."""

    def __init__(self, opts, tmpdir):
        self.o = opts
        self.files = [open(os.path.join(tmpdir, f"s{i:03d}.bin"), "wb")
                      for i in range(SHARD_COUNT)]
        self.tile_ids = set()
        self.bbox = [180.0, 90.0, -180.0, -90.0]

    def close(self):
        for f in self.files:
            f.close()

    def _track(self, lon, lat):
        b = self.bbox
        if lon < b[0]:
            b[0] = lon
        if lat < b[1]:
            b[1] = lat
        if lon > b[2]:
            b[2] = lon
        if lat > b[3]:
            b[3] = lat

    def _write(self, tid, kind, payload):
        blob = pickle.dumps(payload, protocol=4)
        hdr = bytearray()
        w_uvarint(hdr, tid)
        w_uvarint(hdr, kind)
        w_uvarint(hdr, len(blob))
        f = self.files[(tid * 0x2545F49) % SHARD_COUNT]
        f.write(hdr)
        f.write(blob)
        self.tile_ids.add(tid)

    # ---- point ----
    def emit_point(self, lon, lat, klass, min_zoom, name):
        self._track(lon, lat)
        if min_zoom > self.o.base_zoom:
            min_zoom = self.o.base_zoom
        x, y = tile_xy(lon, lat, self.o.base_zoom)
        self._write(tile_id(self.o.base_zoom, x, y), K_POI,
                    (lon, lat, klass, min_zoom, name))
        for z in self.o.overview_zooms:
            if min_zoom <= z:
                ox, oy = tile_xy(lon, lat, z)
                self._write(tile_id(z, ox, oy), K_POI,
                            (lon, lat, klass, min_zoom, name))

    # ---- line ----
    def emit_line(self, pts, klass, attr, min_zoom, name, speed_code,
                  routable, junction_idx, speed_kmh, width_dm=0):
        for lon, lat in pts:
            self._track(lon, lat)
        junc = set(junction_idx or ())
        for z, tol in [(self.o.base_zoom, self.o.base_tol)] + \
                      [(zz, self.o.overview_tol[i]) for i, zz in enumerate(self.o.overview_zooms)]:
            if min_zoom > z and z != self.o.base_zoom:
                continue
            base = z == self.o.base_zoom
            geom = pts if base else simplify(pts, tol)
            if len(geom) < 2:
                continue
            keep_junc = junc if base else set()
            for seg, seg_junc in self._split_by_tile(geom, z, keep_junc, base, pts):
                if len(seg) < 2:
                    continue
                x, y = tile_xy(seg[0][0], seg[0][1], z)
                self._write(tile_id(z, x, y), K_WAY,
                            (seg, klass, attr, min_zoom, name, speed_code,
                             routable and base, sorted(seg_junc), speed_kmh, width_dm))

    def _split_by_tile(self, geom, z, junc_idx, base, orig):
        """برش خط روی مرز کاشی؛ نقطه‌ی مرزی در هر دو قطعه می‌آید (اتصال گراف)."""
        out = []
        cur, cur_junc = [geom[0]], set()
        if base and 0 in junc_idx:
            cur_junc.add(0)
        cur_tile = tile_xy(geom[0][0], geom[0][1], z)
        for i in range(1, len(geom)):
            p = geom[i]
            t = tile_xy(p[0], p[1], z)
            if t != cur_tile:
                cur.append(p)
                cur_junc.add(len(cur) - 1)
                out.append((cur, cur_junc))
                cur, cur_junc, cur_tile = [p], {0}, t
            else:
                cur.append(p)
                if base and i in junc_idx:
                    cur_junc.add(len(cur) - 1)
        cur_junc.add(len(cur) - 1)
        out.append((cur, cur_junc))
        return out

    # ---- area ----
    def emit_area(self, pts, klass, attr, min_zoom, name):
        for lon, lat in pts:
            self._track(lon, lat)
        for z, tol in [(self.o.base_zoom, self.o.base_tol)] + \
                      [(zz, self.o.overview_tol[i]) for i, zz in enumerate(self.o.overview_zooms)]:
            if min_zoom > z and z != self.o.base_zoom:
                continue
            ring = pts if z == self.o.base_zoom else simplify(pts, tol)
            if len(ring) < 4:
                continue
            x, y = tile_xy(ring[0][0], ring[0][1], z)
            self._write(tile_id(z, x, y), K_AREA, (ring, klass, attr, min_zoom, name))


# ------------------------------------------------------------- encoding ------
class StringPool:
    """رشته‌های (نام‌ها) با شماره‌گذاریِ append-only.

    اگر state_path داده شود، شماره‌ی هر رشته از اجرای قبلی حفظ می‌شود (فقط
    رشته‌های جدید به انتهای لیست اضافه می‌شوند، هیچ ایندکس قدیمی هرگز عوض
    نمی‌شود). این پایداری پیش‌نیازِ درستیِ پچ‌های افزایشی است: کاشی‌هایی که
    بین دو build عوض نشده‌اند، بایتِ خامِ خودشان (شاملِ nameId های قدیمی)
    بدونِ رمزگشایی مجدد در فایلِ نهایی استفاده می‌شود؛ اگر شماره‌ی رشته‌ها هر
    بار از صفر بازتولید می‌شد، آن nameId ها در فایلِ جدید به رشته‌ی غلط
    اشاره می‌کردند.
    """

    def __init__(self, state_path=None):
        self.state_path = state_path
        self.ids = {"": 0}
        self.list = [""]
        if state_path and os.path.exists(state_path):
            with open(state_path, encoding="utf-8") as f:
                saved = json.load(f)
            self.list = saved["strings"]
            self.ids = {s: i for i, s in enumerate(self.list)}

    def get(self, s: str) -> int:
        if not s:
            return 0
        i = self.ids.get(s)
        if i is None:
            i = len(self.list)
            self.ids[s] = i
            self.list.append(s)
        return i

    def encode(self) -> bytes:
        buf = bytearray()
        w_uvarint(buf, len(self.list))
        for s in self.list:
            b = s.encode("utf-8")
            w_uvarint(buf, len(b))
            buf += b
        return bytes(buf)

    def save_state(self):
        if not self.state_path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.state_path)) or ".", exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump({"strings": self.list}, f, ensure_ascii=False)


def encode_tile(tid, records, pool, opts):
    z = tid >> 44
    x = (tid >> 22) & 0x3FFFFF
    y = tid & 0x3FFFFF
    olon, olat = tile_origin(x, y, z)

    nodes, node_ix = [], {}
    ways, edges, areas, pois = [], [], [], []
    border = {}

    def node_of(lon, lat):
        key = (round((lon - olon) * COORD_SCALE), round((lat - olat) * COORD_SCALE))
        i = node_ix.get(key)
        if i is None:
            i = len(nodes)
            node_ix[key] = i
            nodes.append(key)
        return i

    for kind, payload in records:
        if kind == K_WAY:
            seg, klass, attr, min_zoom, name, speed_code, routable, junc, speed, width_dm = payload
            refs = [node_of(lon, lat) for lon, lat in seg]
            wi = len(ways)
            ways.append((klass, attr, min_zoom, pool.get(name), speed_code, width_dm, refs))
            if routable and speed > 0 and len(junc) >= 2:
                for a, b in zip(junc, junc[1:]):
                    dist = sum(haversine(seg[k], seg[k + 1]) for k in range(a, b))
                    if dist <= 0:
                        continue
                    sec10 = max(1, int(dist / (speed / 3.6) * 10))
                    # مهم: a همیشه اندیسِ کوچک‌تر در refs است (زودتر در جهتِ
                    # رسمِ way) و b اندیسِ بزرگ‌تر — یعنی a→b همان جهتِ
                    # «forward»ی است که سمتِ Dart با edge.forward10 می‌سازد
                    # (نگاه کنید به AbmGraph.ensureTile: forward10>0 → یال از
                    # ka به kb). پس:
                    #   oneway=yes (bit0) یعنی فقط جهتِ رسمِ way مجاز است
                    #     → a→b (فوروارد) باز، b→a (بکوارد) بسته.
                    #   oneway=-1  (bit1) یعنی فقط عکسِ جهتِ رسم مجاز است
                    #     → a→b (فوروارد) بسته، b→a (بکوارد) باز.
                    # نسخه‌ی قبلی این دو شرط را برعکس نوشته بود (fwd را با
                    # بیتِ oneway=yes صفر می‌کرد، bwd را با oneway=-1) که
                    # دقیقاً جهتِ مجاز را می‌بست و جهتِ ممنوع را باز می‌گذاشت —
                    # همان چیزی که در اپ به‌صورت «مسیریابی کاملاً برعکسِ
                    # جهتِ واقعیِ خیابان» دیده می‌شد.
                    fwd = 0 if (attr & 2) else sec10   # بسته فقط اگر oneway=-1
                    bwd = 0 if (attr & 1) else sec10   # بسته فقط اگر oneway=yes
                    if fwd or bwd:
                        edges.append((wi, a, b, fwd, bwd))
                for j in (junc[0], junc[-1]):
                    ni = refs[j]
                    lon, lat = seg[j]
                    border[ni] = gkey(round(lon * COORD_SCALE), round(lat * COORD_SCALE))
        elif kind == K_AREA:
            ring, klass, attr, min_zoom, name = payload
            areas.append((klass, attr, min_zoom, pool.get(name), ring, olon, olat))
        else:
            lon, lat, klass, min_zoom, name = payload
            pois.append((round((lon - olon) * COORD_SCALE),
                         round((lat - olat) * COORD_SCALE),
                         klass, min_zoom, pool.get(name)))

    sections = []

    nb = bytearray()
    w_uvarint(nb, len(nodes))
    plon = plat = 0
    for lo, la in nodes:
        w_svarint(nb, lo - plon)
        w_svarint(nb, la - plat)
        plon, plat = lo, la
    sections.append((1, nb))

    wb = bytearray()
    w_uvarint(wb, len(ways))
    for klass, attr, min_zoom, name_id, speed_code, width_dm, refs in ways:
        w_uvarint(wb, klass)
        w_uvarint(wb, attr)
        w_uvarint(wb, min_zoom)
        w_uvarint(wb, name_id)
        w_uvarint(wb, speed_code)
        w_uvarint(wb, width_dm)
        w_uvarint(wb, len(refs))
        prev = 0
        for i, r in enumerate(refs):
            if i == 0:
                w_uvarint(wb, r)
            else:
                w_svarint(wb, r - prev)
            prev = r
    sections.append((2, wb))

    if edges:
        eb = bytearray()
        w_uvarint(eb, len(edges))
        prev_wi = 0
        for wi, a, b, fwd, bwd in edges:
            w_uvarint(eb, wi - prev_wi)
            prev_wi = wi
            w_uvarint(eb, a)
            w_uvarint(eb, b)
            w_uvarint(eb, fwd)
            w_uvarint(eb, bwd)
        sections.append((3, eb))

    if areas:
        ab = bytearray()
        w_uvarint(ab, len(areas))
        for klass, attr, min_zoom, name_id, ring, olo, ola in areas:
            w_uvarint(ab, klass)
            w_uvarint(ab, attr)
            w_uvarint(ab, min_zoom)
            w_uvarint(ab, name_id)
            w_uvarint(ab, 1)
            w_uvarint(ab, len(ring))
            plo = pla = 0
            for lon, lat in ring:
                lo = round((lon - olo) * COORD_SCALE)
                la = round((lat - ola) * COORD_SCALE)
                w_svarint(ab, lo - plo)
                w_svarint(ab, la - pla)
                plo, pla = lo, la
        sections.append((4, ab))

    if pois:
        pb = bytearray()
        w_uvarint(pb, len(pois))
        plo = pla = 0
        for lo, la, klass, min_zoom, name_id in pois:
            w_svarint(pb, lo - plo)
            w_svarint(pb, la - pla)
            plo, pla = lo, la
            w_uvarint(pb, klass)
            w_uvarint(pb, min_zoom)
            w_uvarint(pb, name_id)
        sections.append((5, pb))

    if border:
        bb = bytearray()
        w_uvarint(bb, len(border))
        for ni in sorted(border):
            w_uvarint(bb, ni)
            w_uvarint(bb, border[ni])
        sections.append((6, bb))

    body = bytearray()
    w_uvarint(body, len(sections))
    for stype, sbuf in sections:
        w_uvarint(body, stype)
        w_uvarint(body, len(sbuf))
        body += sbuf

    mask = 0
    if ways:
        mask |= 1
    if areas:
        mask |= 2
    if pois:
        mask |= 4
    if edges:
        mask |= 8
    return bytes(body), mask


# ---------------------------------------------------------------- driver -----
def build(opts):
    t0 = time.time()
    print(f"[1/4] شمارش تقاطع‌ها از {opts.input} ...", flush=True)
    jc = JunctionCounter(opts.junction_bits)
    jc.apply_file(opts.input)
    print(f"      راه‌های قابل مسیریابی: {jc.ways:,}  ({time.time()-t0:.0f}s)", flush=True)

    with tempfile.TemporaryDirectory(dir=opts.tmpdir) as tmp:
        sink = ShardSink(opts, tmp)
        ex = Extractor(opts, jc.seen2, sink)
        print("[2/4] استخراج هندسه + گراف (یک پاس) ...", flush=True)
        ex.apply_file(opts.input, locations=True,
                      idx=f"sparse_file_array,{os.path.join(tmp, 'nodes.cache')}")
        sink.close()
        del jc, ex
        print(f"      کاشی‌ها: {len(sink.tile_ids):,}  ({time.time()-t0:.0f}s)", flush=True)

        pool = StringPool(state_path=opts.string_state)
        cctx = zstd.ZstdCompressor(level=opts.zstd_level)
        index = []
        tiles_path = os.path.join(tmp, "tiles.bin")
        print("[3/4] کدگذاری و فشرده‌سازی کاشی‌ها ...", flush=True)
        with open(tiles_path, "wb") as tf:
            for si in range(SHARD_COUNT):
                path = os.path.join(tmp, f"s{si:03d}.bin")
                groups = defaultdict(list)
                with open(path, "rb") as f:
                    data = f.read()
                os.remove(path)
                p = 0
                n = len(data)
                while p < n:
                    tid, p = read_uvarint(data, p)
                    kind, p = read_uvarint(data, p)
                    ln, p = read_uvarint(data, p)
                    groups[tid].append((kind, pickle.loads(data[p:p + ln])))
                    p += ln
                del data
                for tid, recs in groups.items():
                    body, mask = encode_tile(tid, recs, pool, opts)
                    comp = cctx.compress(body)
                    index.append((tid, tf.tell(), len(comp), len(body), mask))
                    tf.write(comp)
                if si % 32 == 0:
                    print(f"      shard {si}/{SHARD_COUNT} ({time.time()-t0:.0f}s)", flush=True)

        # کاشی‌ها به ترتیب tile_id مرتب می‌شوند تا آفست‌ها صعودی و
        # خواندن کاشی‌های مجاور در اپ متوالی (locality) باشد.
        index.sort()
        strings_raw = pool.encode()
        strings_comp = cctx.compress(strings_raw)

        tiles_size = sum(r[2] for r in index)
        strings_offset = HEADER_SIZE
        tiles_offset = strings_offset + len(strings_comp)
        index_offset = tiles_offset + tiles_size

        ib = bytearray()
        prev_tid = 0
        prev_end = 0   # اولین delta_offset = آفست مطلق از ابتدای فایل
        final = []
        cursor = tiles_offset
        for tid, tmp_off, clen, rlen, mask in index:
            w_uvarint(ib, tid - prev_tid)
            w_uvarint(ib, cursor - prev_end)
            w_uvarint(ib, clen)
            w_uvarint(ib, rlen)
            w_uvarint(ib, mask)
            prev_tid, prev_end = tid, cursor + clen
            final.append((tmp_off, clen))
            cursor += clen
        index_comp = cctx.compress(bytes(ib))

        print("[4/4] نوشتن فایل نهایی ...", flush=True)
        os.makedirs(os.path.dirname(os.path.abspath(opts.output)), exist_ok=True)

        header = bytearray(HEADER_SIZE)
        ovz = list(opts.overview_zooms) + [0] * (6 - len(opts.overview_zooms))
        driving_side = resolve_driving_side(opts.driving_side, opts.region)
        flags = 0b111
        if driving_side == "left":
            flags |= 0x08  # بیت ۳ = چپ‌رانی (مثل انگلیس)؛ صفر یعنی راست‌رانی (مثل ایران)
        print(f"      driving_side={driving_side} (region={opts.region})", flush=True)
        struct.pack_into("<8sHHBB6B", header, 0, MAGIC, VERSION,
                         flags, opts.base_zoom, len(opts.overview_zooms), *ovz)
        b = sink.bbox
        struct.pack_into("<iiii", header, 20,
                         round(b[0] * COORD_SCALE), round(b[1] * COORD_SCALE),
                         round(b[2] * COORD_SCALE), round(b[3] * COORD_SCALE))
        struct.pack_into("<IQIIQIIIIQ16s", header, 36,
                         len(index), index_offset, len(index_comp), len(ib),
                         strings_offset, len(strings_comp), len(strings_raw),
                         len(pool.list), COORD_SCALE, int(time.time()),
                         opts.region.encode()[:16])

        with open(opts.output, "wb") as out:
            out.write(header)
            out.write(strings_comp)
            with open(tiles_path, "rb") as tf:
                for tmp_off, clen in final:
                    tf.seek(tmp_off)
                    out.write(tf.read(clen))
            assert out.tell() == index_offset, (out.tell(), index_offset)
            out.write(index_comp)

        pool.save_state()


    size = os.path.getsize(opts.output)
    print(f"\n✅ {opts.output}  =  {size/1e6:.1f} MB   کاشی: {len(index):,}   "
          f"رشته: {len(pool.list):,}   زمان: {time.time()-t0:.0f}s")
    return size


def read_uvarint(buf, p):
    shift = 0
    val = 0
    while True:
        b = buf[p]
        p += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, p
        shift += 7


def main(argv=None):
    ap = argparse.ArgumentParser(description="OSM PBF -> ABTINMAP v1")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--region", default="IR")
    # base-zoom قبلاً ۱۲ بود: هر کاشی ~۹.۵×۹.۵ کیلومتر، یعنی حتی موقع
    # زوم خیابانی (۱۶-۱۸) همون کاشی بزرگ decode می‌شد — کندی اصلی از همینجا
    # بود. با ۱۴، هر کاشی ~۲.۴×۲.۴ کیلومتره (۱۶ برابر کوچیک‌تر).
    ap.add_argument("--base-zoom", type=int, default=14)
    # وجود زوم ۴ باعث می‌شود بشود تقریباً کل ایران را یک‌جا دید.
    ap.add_argument("--overview-zooms", default="4,6,8,11")
    ap.add_argument("--zstd-level", type=int, default=19)
    ap.add_argument("--poi-min-zoom", type=int, default=14)
    ap.add_argument("--drop-buildings", action="store_true")
    ap.add_argument("--junction-bits", type=int, default=1 << 30)
    ap.add_argument("--tmpdir", default=None)
    ap.add_argument("--string-state", default=None,
                    help="فایل JSON برای حفظِ شماره‌ی رشته‌ها بین اجراهای "
                         "متوالیِ همین کشور (پیش‌نیازِ پچ‌های افزایشی؛ اگر "
                         "داده نشود، رفتار قبلی بدون تغییر است).")
    ap.add_argument("--driving-side", choices=["auto", "right", "left"],
                    default="auto",
                    help="جهتِ رانندگی برای این نقشه — right (مثل ایران)، "
                         "left (مثل انگلیس)، یا auto (تشخیصِ خودکار از روی "
                         "--region). در بیتِ ۳ از flags هدرِ فایل ذخیره "
                         "می‌شود.")
    o = ap.parse_args(argv)
    o.overview_zooms = [int(z) for z in o.overview_zooms.split(",") if z.strip()]
    o.overview_tol = [
        2500.0 if z <= 4 else (700.0 if z <= 6 else 120.0)
        for z in o.overview_zooms
    ]
    o.base_tol = 3.0
    build(o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
