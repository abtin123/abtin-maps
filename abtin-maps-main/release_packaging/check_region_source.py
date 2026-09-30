#!/usr/bin/env python3
"""Fingerprint OSM source data independently for each configured region.

The fingerprint is intentionally based on the region's published/routing bbox,
so roads crossing an admin boundary and routing continuity data are included.
A changed country PBF therefore does not imply every province changed.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path


def region_fingerprints(pbf: Path, config: Path) -> dict[str, dict]:
    try:
        import osmium
    except ImportError as exc:
        raise SystemExit('pyosmium is required for regional source fingerprints') from exc
    cfg = json.loads(config.read_text(encoding='utf-8'))
    regions = cfg.get('regions') or []
    out = {}
    for r in regions:
        code = str(r['code']).strip().upper()
        bbox = tuple(float(x) for x in r['bbox'])
        out[code] = _fingerprint_one(pbf, code, bbox, osmium)
    return out


def _fingerprint_one(pbf: Path, code: str, bbox, osmium) -> dict:
    minlon, minlat, maxlon, maxlat = bbox
    h = hashlib.sha256()
    way_ids: set[int] = set()
    count = 0

    def add(kind: str, obj):
        nonlocal count
        tags = sorted((str(k), str(v)) for k, v in obj.tags)
        payload = [kind, str(obj.id), str(getattr(obj, 'version', '')), tags]
        h.update(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode())
        h.update(b'\n')
        count += 1

    class Handler(osmium.SimpleHandler):
        def node(self, n):
            lon, lat = float(n.location.lon), float(n.location.lat)
            if minlon <= lon <= maxlon and minlat <= lat <= maxlat:
                add('node', n)

        def way(self, w):
            coords = []
            for n in w.nodes:
                if n.location.valid():
                    coords.append((float(n.location.lon), float(n.location.lat)))
            if not coords:
                return
            bx0 = min(x for x, _ in coords); by0 = min(y for _, y in coords)
            bx1 = max(x for x, _ in coords); by1 = max(y for _, y in coords)
            if bx1 >= minlon and bx0 <= maxlon and by1 >= minlat and by0 <= maxlat:
                way_ids.add(int(w.id))
                add('way', w)

        def relation(self, rel):
            members = {int(m.ref) for m in rel.members if str(m.type) == 'w'}
            if members & way_ids:
                add('relation', rel)

    hnd = Handler()
    hnd.apply_file(str(pbf), locations=True, idx='flex_mem')
    return {'sha256': h.hexdigest(), 'objects': count, 'bbox': list(bbox)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('pbf', type=Path)
    ap.add_argument('--regions-config', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = region_fingerprints(args.pbf, args.regions_config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for code, item in result.items():
        print(f'{code} {item["sha256"]} objects={item["objects"]}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
