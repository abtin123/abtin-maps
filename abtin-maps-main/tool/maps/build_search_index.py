#!/usr/bin/env python3
"""Build the offline SQLite FTS5 search index embedded in an ABM container.

The index deliberately contains named places/POIs and named roads from the same
PBF used by Planetiler and the routing graph, so offline search never depends on
an external geocoder.  It is a compact read-only database once embedded.
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
from pathlib import Path

import osmium


class SearchCollector(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str, str, float, float, str]] = []
        self._seen: set[tuple[str, int, int, str]] = set()

    @staticmethod
    def _name(tags: object) -> str:
        return str(tags.get("name:fa") or tags.get("name") or "").strip()

    @staticmethod
    def _region(tags: object) -> str:
        for key in ("addr:city", "addr:town", "addr:district", "is_in", "place"):
            value = str(tags.get(key) or "").strip()
            if value:
                return value
        return ""

    def _add(self, name: str, region: str, lon: float, lat: float, kind: str) -> None:
        if not name or not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return
        key = (name.casefold(), round(lat, 5), round(lon, 5), kind)
        if key in self._seen:
            return
        self._seen.add(key)
        self.rows.append((name, region, float(lat), float(lon), kind))

    def node(self, node: object) -> None:
        tags = node.tags
        name = self._name(tags)
        if not name:
            return
        if tags.get("place") or tags.get("amenity") or tags.get("tourism") or tags.get("shop") or tags.get("highway") or tags.get("public_transport"):
            self._add(name, self._region(tags), node.location.lon, node.location.lat, "place")

    def way(self, way: object) -> None:
        tags = way.tags
        name = self._name(tags)
        highway = str(tags.get("highway") or "").strip().lower()
        if not name or highway not in {
            "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
            "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified",
            "residential", "living_street", "service", "track",
        }:
            return
        points = [(n.lon, n.lat) for n in way.nodes if n.location.valid()]
        if not points:
            return
        lon = sum(p[0] for p in points) / len(points)
        lat = sum(p[1] for p in points) / len(points)
        self._add(name, self._region(tags), lon, lat, "road")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build(pbf: Path, output: Path) -> None:
    collector = SearchCollector()
    collector.apply_file(str(pbf), locations=True, idx="flex_mem")
    rows = sorted(collector.rows, key=lambda r: (r[0].casefold(), r[1].casefold(), r[2], r[3]))
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    db = sqlite3.connect(tmp)
    try:
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA synchronous=OFF")
        db.execute("PRAGMA page_size=4096")
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("CREATE VIRTUAL TABLE places_fts USING fts5(name, region, latitude UNINDEXED, longitude UNINDEXED, kind UNINDEXED, tokenize='unicode61 remove_diacritics 2')")
        db.executemany("INSERT INTO places_fts(name,region,latitude,longitude,kind) VALUES(?,?,?,?,?)", rows)
        db.executemany("INSERT INTO meta(key,value) VALUES(?,?)", [
            ("schema", "abtin-search/1"),
            ("source_sha256", sha256(pbf)),
            ("rows", str(len(rows))),
        ])
        db.commit()
        db.execute("VACUUM")
        db.commit()
    finally:
        db.close()
    tmp.replace(output)
    print(f"Search index created: {output} rows={len(rows)} sha256={sha256(output)}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pbf", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if not a.pbf.is_file():
        raise SystemExit(f"PBF not found: {a.pbf}")
    build(a.pbf, a.output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
