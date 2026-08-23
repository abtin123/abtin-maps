#!/usr/bin/env python3
"""Static contracts for stable ABM zoom rendering and road-detail levels."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
canvas = (root / "lib/abtinmap/abm_canvas_map_view.dart").read_text(encoding="utf-8")
renderer = (root / "lib/abtinmap/abm_renderer.dart").read_text(encoding="utf-8")

assert "includePois: camera.zoom >= 15.0" in canvas
assert "includeAreas: camera.zoom >= 15.0" in canvas
assert "result.tileCount > 0 || _rendered == null" in canvas
assert "final maxKlass = camera.zoom < 7.5" in canvas
assert "? AbmKlass.trunk" in canvas and "? AbmKlass.secondary" in canvas
assert "if (klass > maxKlass) continue;" in canvas

assert "int? storageZoom" in renderer
assert "storageZoom ?? pickZoom(cameraZoom)" in renderer
assert "render fallback: requested z=$z was empty" in renderer
assert "candidate < z" in renderer
print("map_lod_contract_ok")
