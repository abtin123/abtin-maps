#!/usr/bin/env python3
"""Static contracts for stable server-side ABM zoom rendering and road LOD."""

from pathlib import Path


root = Path(__file__).resolve().parents[1]
source = (root / "tools/raster_primitives.py").read_text(encoding="utf-8")
builder = (root / "tools/rendered_tile_builder.py").read_text(encoding="utf-8")

assert "WIDTH_ZOOM_REFERENCE = 14" in source
assert "WIDTH_ZOOM_BASE = 1.32" in source
assert "MIN_POLYGON_PIXELS = 2.5" in source
assert "max(1, round(width * (WIDTH_ZOOM_BASE ** (z - WIDTH_ZOOM_REFERENCE))))" in source
assert '"motorway": 3' in source
assert '"residential": 12' in source
assert '"service": 13' in source
assert "overzoom_max" in source and "overzoom_max" in builder
print("map_lod_source_contract_ok")
