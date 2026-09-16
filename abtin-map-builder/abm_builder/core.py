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
    """Write a versioned length-prefixed ABM vector stream."""
    count = 0
    with path.open("wb") as f:
        f.write(b"ABMV1\n")
        for record in records:
            payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()
            f.write(struct.pack("!I", len(payload)))
            f.write(payload)
            count += 1
    return count


def feature_bbox(record: dict[str, Any]) -> tuple[float, float, float, float] | None:
    geom = record.get("geometry") or []
    points = []
    for pt in geom:
        try:
            if len(pt) >= 2:
                points.append((float(pt[0]), float(pt[1])))
        except (TypeError, ValueError):
            continue
    return geometry_bbox(points) if points else None


def write_spatial_chunks(
    directory: Path,
    layer: str,
    records: Iterable[dict[str, Any]],
    chunk_size: int = 768,
) -> dict[str, Any]:
    """Write localized spatial chunks with bounded memory.

    Records are assigned to fixed geographic cells and flushed as soon as a
    cell reaches ``chunk_size`` features.  The previous implementation kept
    every feature of every cell in RAM until the complete layer was consumed;
    that was unnecessarily expensive for country-sized PBF builds.
    """
    out_dir = directory / layer
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks: list[dict[str, Any]] = []
    cell_batches: dict[tuple[int, int], list[tuple[tuple[float, float, float, float], dict[str, Any]]]] = {}
    chunk_index = 0
    total = 0

    def cell_key(b: tuple[float, float, float, float]) -> tuple[int, int]:
        cx = (b[0] + b[2]) * 0.5
        cy = (b[1] + b[3]) * 0.5
        gx = max(0, min(255, int(math.floor((cx + 180.0) / 360.0 * 256.0))))
        gy = max(0, min(127, int(math.floor((cy + 90.0) / 180.0 * 128.0))))
        return gx, gy

    def flush(cell: tuple[int, int]) -> None:
        nonlocal chunk_index
        batch = cell_batches.pop(cell, None)
        if not batch:
            return
        batch.sort(key=lambda item: (item[0][1], item[0][0], item[0][3], item[0][2]))
        name = f"{chunk_index:06d}.bin"
        chunk_index += 1
        path = out_dir / name
        write_records(path, (rec for _, rec in batch))
        bboxes = [b for b, _ in batch]
        bbox = (
            min(b[0] for b in bboxes), min(b[1] for b in bboxes),
            max(b[2] for b in bboxes), max(b[3] for b in bboxes),
        )
        chunks.append({
            "path": f"vector/{layer}/{name}",
            "bbox": list(bbox),
            "count": len(batch),
            "cell": [cell[0], cell[1]],
        })

    limit = max(1, chunk_size)
    for rec in records:
        bbox = feature_bbox(rec)
        if bbox is None:
            continue
        total += 1
        cell = cell_key(bbox)
        batch = cell_batches.setdefault(cell, [])
        batch.append((bbox, rec))
        if len(batch) >= limit:
            flush(cell)

    for cell in sorted(cell_batches):
        flush(cell)

    if not chunks:
        name = "000000.bin"
        write_records(out_dir / name, [])
        chunks.append({
            "path": f"vector/{layer}/{name}",
            "bbox": [180.0, 90.0, -180.0, -90.0],
            "count": 0,
            "cell": [-1, -1],
        })

    return {
        "version": 2,
        "layer": layer,
        "count": total,
        "chunk_size": limit,
        "chunks": chunks,
    }

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
