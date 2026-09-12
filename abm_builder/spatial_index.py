"""Compact spatial index for tile-free ABM vector streams.

The index is deliberately an internal ABM member, not a new map format.  The
vector stream remains ABMV1; the index only records byte ranges for records
that intersect fixed geographic cells.  New builders write vector members as
ZIP_STORED so the app can seek directly to those byte ranges without
materializing the whole vector member.
"""
from __future__ import annotations

import math
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

MAGIC = b"ABMIDX1\n"
CELL_DEGREES = 0.5
_HEADER = struct.Struct("!dIII")  # cell degrees, cells, records, flags
_CELL = struct.Struct("!iiI")
_ENTRY = struct.Struct("!QI")  # absolute member offset, record byte length


def _bbox(record: dict[str, Any]) -> tuple[float, float, float, float] | None:
    geom = record.get("geometry") or []
    min_lon = min_lat = math.inf
    max_lon = max_lat = -math.inf
    found = False
    for p in geom:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        try:
            lon, lat = float(p[0]), float(p[1])
        except (TypeError, ValueError):
            continue
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue
        found = True
        min_lon = min(min_lon, lon); max_lon = max(max_lon, lon)
        min_lat = min(min_lat, lat); max_lat = max(max_lat, lat)
    return (min_lon, min_lat, max_lon, max_lat) if found else None


def _cell_range(bbox: tuple[float, float, float, float]):
    min_lon, min_lat, max_lon, max_lat = bbox
    x0 = math.floor(min_lon / CELL_DEGREES)
    x1 = math.floor(max_lon / CELL_DEGREES)
    y0 = math.floor(min_lat / CELL_DEGREES)
    y1 = math.floor(max_lat / CELL_DEGREES)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            yield x, y


def write_index(index_path: Path, records: Iterable[dict[str, Any]], record_offsets: list[tuple[int, int]]) -> dict[str, int | float]:
    """Write ABMIDX1 for records in the same order as record_offsets.

    record_offsets contains (offset_of_4_byte_length_prefix, full_record_bytes)
    where full_record_bytes includes the 4-byte length prefix.  The index can
    therefore read one record with exactly two seeks/reads from a stored ZIP
    member.
    """
    cells: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    count = 0
    for record, (offset, size) in zip(records, record_offsets):
        bbox = _bbox(record)
        if bbox is None or size <= 4:
            continue
        for cell in _cell_range(bbox):
            cells[cell].append((offset, size))
        count += 1

    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("wb") as f:
        f.write(MAGIC)
        f.write(_HEADER.pack(CELL_DEGREES, len(cells), count, 0))
        for (x, y) in sorted(cells):
            entries = cells[(x, y)]
            f.write(_CELL.pack(x, y, len(entries)))
            for offset, size in entries:
                f.write(_ENTRY.pack(offset, size))
    return {"cells": len(cells), "indexed_records": count, "cell_degrees": CELL_DEGREES}
