"""Core types and utilities for the tile-free ABM builder."""
from __future__ import annotations

import json
import logging
import math
import re
import struct
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Iterator

LOG = logging.getLogger("abm_builder")


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def norm_fa(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    value = value.replace("\u200c", " ").replace("\u200f", " ")
    return re.sub(r"\s+", " ", value).strip().lower()


def tags_get(tags: Any, key: str, default: str = "") -> str:
    try:
        return str(tags.get(key, default) or default)
    except AttributeError:
        return default


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.asin(math.sqrt(h))


def geometry_bbox(coords: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    lons = [c[0] for c in coords]; lats = [c[1] for c in coords]
    return min(lons), min(lats), max(lons), max(lats)


def records_bbox(record_lists: Iterable[Iterable[dict[str, Any]]]) -> tuple[float, float, float, float] | None:
    """Union bbox (minlon, minlat, maxlon, maxlat) across many feature-record lists.

    Returns None when there is no geometry at all (e.g. an empty test fixture),
    so callers can decide how to handle that instead of writing a bogus [0,0,0,0].
    """
    minlon = minlat = math.inf
    maxlon = maxlat = -math.inf
    found = False
    for records in record_lists:
        for rec in records:
            geom = rec.get("geometry") or []
            for pt in geom:
                if not pt or len(pt) < 2:
                    continue
                lon, lat = float(pt[0]), float(pt[1])
                found = True
                if lon < minlon: minlon = lon
                if lon > maxlon: maxlon = lon
                if lat < minlat: minlat = lat
                if lat > maxlat: maxlat = lat
    if not found:
        return None
    return (minlon, minlat, maxlon, maxlat)


def bbox_intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def write_records(path: Path, records: Iterable[dict[str, Any]]) -> int:
    """Write a versioned length-prefixed JSON-lines binary stream, stable and streamable."""
    count = 0
    with path.open("wb") as f:
        f.write(b"ABMV1\n")
        for record in records:
            payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()
            f.write(struct.pack("!I", len(payload))); f.write(payload); count += 1
    return count


def read_records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("rb") as f:
        if f.read(6) != b"ABMV1\n":
            raise ValueError(f"Invalid ABM vector stream header: {path}")
        while True:
            raw = f.read(4)
            if not raw: break
            if len(raw) != 4: raise ValueError(f"Truncated record length in {path}")
            size = struct.unpack("!I", raw)[0]
            payload = f.read(size)
            if len(payload) != size: raise ValueError(f"Truncated record in {path}")
            yield json.loads(payload)


def way_geometry(way: Any) -> list[tuple[float, float]]:
    nodes = getattr(way, "nodes", way.get("geometry", []) if isinstance(way, dict) else [])
    out = []
    for n in nodes:
        if isinstance(n, dict):
            if n.get("lon") is not None and n.get("lat") is not None: out.append((float(n["lon"]), float(n["lat"])))
        elif getattr(n, "lon", None) is not None and getattr(n, "lat", None) is not None: out.append((float(n.lon), float(n.lat)))
        elif isinstance(n, (list, tuple)) and len(n) >= 2: out.append((float(n[0]), float(n[1])))
    return out


def tags_dict(obj: Any) -> dict[str, str]:
    tags = getattr(obj, "tags", obj.get("tags", {}) if isinstance(obj, dict) else {})
    try: return {str(k): str(v) for k, v in tags.items()}
    except AttributeError: return {}


def entity_id(obj: Any) -> int:
    return int(getattr(obj, "id", obj.get("id", 0) if isinstance(obj, dict) else 0))


@dataclass
class Feature:
    id: int
    geometry: list[tuple[float, float]]
    tags: dict[str, str]

    def record(self) -> dict[str, Any]:
        return {"id": self.id, "geometry": self.geometry, "tags": self.tags}
