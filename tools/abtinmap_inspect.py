#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
abtinmap_inspect.py — اعتبارسنجی و آمار فایل .abm (خواننده‌ی مرجع فرمت)

این فایل «حقیقتِ اجرایی» فرمت است: پیاده‌سازی Dart در اپ باید بایت‌به‌بایت با این
خواننده هم‌خوان باشد.

اجرا:
  python3 abtinmap_inspect.py IR.abm                 # خلاصه + اعتبارسنجی
  python3 abtinmap_inspect.py IR.abm --tile 12/2624/1610
  python3 abtinmap_inspect.py IR.abm --route 51.42,35.73 51.38,35.70
"""
import argparse
import bisect
import heapq
import math
import struct
import sys

import zstandard as zstd

MAGIC = b"ABTINMAP"
HEADER_SIZE = 128


def read_uvarint(buf, p):
    shift = val = 0
    while True:
        b = buf[p]
        p += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, p
        shift += 7


def read_svarint(buf, p):
    v, p = read_uvarint(buf, p)
    return (v >> 1) if not (v & 1) else -((v + 1) >> 1), p


def tile_xy(lon, lat, z):
    n = 1 << z
    x = int((lon + 180.0) / 360.0 * n)
    lat = max(-85.05112878, min(85.05112878, lat))
    r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tile_origin(x, y, z):
    n = 1 << z
    return (x / n * 360.0 - 180.0,
            math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n)))))


def gkey(lon_e7, lat_e7):
    return (lat_e7 + 900_000_000) * 3_600_000_001 + (lon_e7 + 1_800_000_000)


class AbtinMap:
    def __init__(self, path):
        self.f = open(path, "rb")
        h = self.f.read(HEADER_SIZE)
        if h[:8] != MAGIC:
            raise ValueError("magic نامعتبر — این فایل ABTINMAP نیست")
        (self.version, self.flags, self.base_zoom, self.ovz_count) = \
            struct.unpack_from("<HHBB", h, 8)
        self.overview_zooms = [z for z in struct.unpack_from("<6B", h, 14) if z][:self.ovz_count]
        self.bbox = [v / 1e7 for v in struct.unpack_from("<iiii", h, 20)]
        (self.tile_count, self.index_offset, self.index_comp, self.index_raw,
         self.strings_offset, self.strings_comp, self.strings_raw,
         self.string_count, self.coord_scale, self.build_epoch, region) = \
            struct.unpack_from("<IQIIQIIIIQ16s", h, 36)
        self.region = region.rstrip(b"\0").decode()
        self.d = zstd.ZstdDecompressor()

        self.f.seek(self.strings_offset)
        raw = self.d.decompress(self.f.read(self.strings_comp),
                                max_output_size=self.strings_raw)
        self.strings = []
        n, p = read_uvarint(raw, 0)
        for _ in range(n):
            ln, p = read_uvarint(raw, p)
            self.strings.append(raw[p:p + ln].decode("utf-8", "replace"))
            p += ln

        self.f.seek(self.index_offset)
        raw = self.d.decompress(self.f.read(self.index_comp),
                                max_output_size=self.index_raw)
        self.ids, self.recs = [], []
        tid = end = p = 0
        for _ in range(self.tile_count):
            dt, p = read_uvarint(raw, p)
            do, p = read_uvarint(raw, p)
            cl, p = read_uvarint(raw, p)
            rl, p = read_uvarint(raw, p)
            mk, p = read_uvarint(raw, p)
            tid += dt
            off = end + do
            end = off + cl
            self.ids.append(tid)
            self.recs.append((off, cl, rl, mk))
        self._cache = {}

    def name(self, i):
        return self.strings[i] if 0 <= i < len(self.strings) else ""

    def tile(self, z, x, y):
        tid = (z << 44) | (x << 22) | y
        if tid in self._cache:
            return self._cache[tid]
        i = bisect.bisect_left(self.ids, tid)
        if i >= len(self.ids) or self.ids[i] != tid:
            return None
        off, cl, rl, _ = self.recs[i]
        self.f.seek(off)
        body = self.d.decompress(self.f.read(cl), max_output_size=rl)
        t = self._parse_tile(body, z, x, y)
        if len(self._cache) > 256:
            self._cache.clear()
        self._cache[tid] = t
        return t

    def _parse_tile(self, body, z, x, y):
        olon, olat = tile_origin(x, y, z)
        t = {"z": z, "x": x, "y": y, "origin": (olon, olat),
             "nodes": [], "ways": [], "edges": [], "areas": [], "pois": [], "border": {}}
        n, p = read_uvarint(body, 0)
        for _ in range(n):
            stype, p = read_uvarint(body, p)
            slen, p = read_uvarint(body, p)
            self._parse_section(t, stype, body, p, p + slen)
            p += slen
        return t

    def _parse_section(self, t, stype, b, p, end):
        s = self.coord_scale
        olon, olat = t["origin"]
        if stype == 1:
            n, p = read_uvarint(b, p)
            lo = la = 0
            for _ in range(n):
                d1, p = read_svarint(b, p)
                d2, p = read_svarint(b, p)
                lo += d1
                la += d2
                t["nodes"].append((olon + lo / s, olat + la / s))
        elif stype == 2:
            n, p = read_uvarint(b, p)
            for _ in range(n):
                klass, p = read_uvarint(b, p)
                attr, p = read_uvarint(b, p)
                mz, p = read_uvarint(b, p)
                nid, p = read_uvarint(b, p)
                sp, p = read_uvarint(b, p)
                cnt, p = read_uvarint(b, p)
                refs = []
                prev = 0
                for i in range(cnt):
                    if i == 0:
                        prev, p = read_uvarint(b, p)
                    else:
                        d, p = read_svarint(b, p)
                        prev += d
                    refs.append(prev)
                t["ways"].append({"klass": klass, "attr": attr, "min_zoom": mz,
                                  "name": self.name(nid), "speed_code": sp, "refs": refs})
        elif stype == 3:
            n, p = read_uvarint(b, p)
            wi = 0
            for _ in range(n):
                d, p = read_uvarint(b, p)
                wi += d
                a, p = read_uvarint(b, p)
                bb, p = read_uvarint(b, p)
                fw, p = read_uvarint(b, p)
                bw, p = read_uvarint(b, p)
                t["edges"].append((wi, a, bb, fw, bw))
        elif stype == 4:
            n, p = read_uvarint(b, p)
            for _ in range(n):
                klass, p = read_uvarint(b, p)
                attr, p = read_uvarint(b, p)
                mz, p = read_uvarint(b, p)
                nid, p = read_uvarint(b, p)
                rings, p = read_uvarint(b, p)
                out = []
                for _r in range(rings):
                    cnt, p = read_uvarint(b, p)
                    lo = la = 0
                    ring = []
                    for _q in range(cnt):
                        d1, p = read_svarint(b, p)
                        d2, p = read_svarint(b, p)
                        lo += d1
                        la += d2
                        ring.append((olon + lo / s, olat + la / s))
                    out.append(ring)
                t["areas"].append({"klass": klass, "attr": attr, "min_zoom": mz,
                                   "name": self.name(nid), "rings": out})
        elif stype == 5:
            n, p = read_uvarint(b, p)
            lo = la = 0
            for _ in range(n):
                d1, p = read_svarint(b, p)
                d2, p = read_svarint(b, p)
                lo += d1
                la += d2
                klass, p = read_uvarint(b, p)
                mz, p = read_uvarint(b, p)
                nid, p = read_uvarint(b, p)
                t["pois"].append({"lon": olon + lo / s, "lat": olat + la / s,
                                  "klass": klass, "min_zoom": mz, "name": self.name(nid)})
        elif stype == 6:
            n, p = read_uvarint(b, p)
            for _ in range(n):
                ni, p = read_uvarint(b, p)
                gk, p = read_uvarint(b, p)
                t["border"][ni] = gk

    # ------------------------------------------------------------ routing ----
    def _graph_key(self, t, ni):
        lon, lat = t["nodes"][ni]
        return gkey(round(lon * self.coord_scale), round(lat * self.coord_scale))

    def route(self, start, goal, max_tiles=4096):
        """A* روی همان کاشی‌های نمایشی — اثبات این‌که گراف و نقشه یکی هستند."""
        z = self.base_zoom
        loaded = {}

        def load(x, y):
            if (x, y) not in loaded:
                loaded[(x, y)] = self.tile(z, x, y)
            return loaded[(x, y)]

        def neighbors(key, pos):
            x, y = tile_xy(pos[0], pos[1], z)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    t = load(x + dx, y + dy)
                    if not t:
                        continue
                    for wi, a, b, fw, bw in t["edges"]:
                        w = t["ways"][wi]
                        ka = self._graph_key(t, w["refs"][a])
                        kb = self._graph_key(t, w["refs"][b])
                        if ka == key and fw:
                            yield kb, fw / 10.0, t["nodes"][w["refs"][b]], w
                        elif kb == key and bw:
                            yield ka, bw / 10.0, t["nodes"][w["refs"][a]], w

        def snap(pt):
            x, y = tile_xy(pt[0], pt[1], z)
            best = None
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    t = load(x + dx, y + dy)
                    if not t:
                        continue
                    for wi, a, b, fw, bw in t["edges"]:
                        w = t["ways"][wi]
                        for idx in (a, b):
                            n = t["nodes"][w["refs"][idx]]
                            d = (n[0] - pt[0]) ** 2 + (n[1] - pt[1]) ** 2
                            if best is None or d < best[0]:
                                best = (d, self._graph_key(t, w["refs"][idx]), n, w)
            return best

        s = snap(start)
        g = snap(goal)
        if not s or not g:
            return None
        skey, spos = s[1], s[2]
        gkey_, gpos = g[1], g[2]

        def hcost(pos):
            dx = (pos[0] - gpos[0]) * 88_000
            dy = (pos[1] - gpos[1]) * 111_000
            return math.hypot(dx, dy) / 33.0  # 120km/h سقف خوش‌بینانه

        openq = [(hcost(spos), 0.0, skey, spos, None)]
        came, best_g = {}, {skey: 0.0}
        visited = 0
        while openq:
            _f, gc, key, pos, prev = heapq.heappop(openq)
            if key in came and came[key][1] <= gc:
                pass
            came.setdefault(key, (prev, gc, pos))
            visited += 1
            if visited > max_tiles * 64:
                return None
            if key == gkey_:
                path, k = [], key
                while k is not None:
                    prev_k, _gc, p_pos = came[k]
                    path.append(p_pos)
                    k = prev_k
                return {"seconds": gc, "points": list(reversed(path)),
                        "expanded": visited}
            for nk, cost, npos, w in neighbors(key, pos):
                ng = gc + cost
                if ng < best_g.get(nk, float("inf")) - 1e-9:
                    best_g[nk] = ng
                    came[nk] = (key, ng, npos)
                    heapq.heappush(openq, (ng + hcost(npos), ng, nk, npos, key))
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--tile")
    ap.add_argument("--route", nargs=2, metavar=("lon,lat", "lon,lat"))
    a = ap.parse_args()
    m = AbtinMap(a.file)
    print(f"region={m.region} version={m.version} base_zoom={m.base_zoom} "
          f"overview={m.overview_zooms}")
    print(f"bbox={['%.4f' % v for v in m.bbox]}")
    print(f"tiles={m.tile_count:,} strings={m.string_count:,}")
    per_z, raw_total, comp_total = {}, 0, 0
    for tid, (off, cl, rl, mk) in zip(m.ids, m.recs):
        z = tid >> 44
        d = per_z.setdefault(z, [0, 0, 0])
        d[0] += 1
        d[1] += cl
        d[2] += rl
        raw_total += rl
        comp_total += cl
    for z in sorted(per_z):
        c, cl, rl = per_z[z]
        print(f"  z{z}: {c:,} tiles  {cl/1e6:.1f}MB comp / {rl/1e6:.1f}MB raw")
    if comp_total:
        print(f"  نسبت فشرده‌سازی: {raw_total/comp_total:.2f}x")

    if a.tile:
        z, x, y = (int(v) for v in a.tile.split("/"))
        t = m.tile(z, x, y)
        if not t:
            print("کاشی موجود نیست")
        else:
            print(f"\ntile {z}/{x}/{y}: nodes={len(t['nodes']):,} ways={len(t['ways']):,} "
                  f"edges={len(t['edges']):,} areas={len(t['areas']):,} "
                  f"pois={len(t['pois']):,} border={len(t['border']):,}")
            for w in t["ways"][:5]:
                sp = w["speed_code"]
                kmh = sp * 5 if 1 <= sp <= 40 else ("شهری" if sp == 200 else
                                                    ("آزادراهی" if sp == 201 else "-"))
                print(f"  way klass={w['klass']} maxspeed={kmh} "
                      f"explicit={'y' if w['attr'] & (1 << 11) else 'n'} "
                      f"pts={len(w['refs'])} name={w['name']!r}")

    if a.route:
        p1 = tuple(float(v) for v in a.route[0].split(","))
        p2 = tuple(float(v) for v in a.route[1].split(","))
        r = m.route(p1, p2)
        if r:
            print(f"\nمسیر: {r['seconds']/60:.1f} دقیقه، {len(r['points'])} نقطه، "
                  f"{r['expanded']} گره بازشده — کاملاً از همین فایل")
        else:
            print("\nمسیر پیدا نشد")
    return 0


if __name__ == "__main__":
    sys.exit(main())
