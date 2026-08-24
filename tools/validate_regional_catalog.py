#!/usr/bin/env python3
"""Structural checks for regional large-country map packages."""

import json
from pathlib import Path


root = Path(__file__).resolve().parents[1]
data = json.loads((root / "tools/countries.json").read_text(encoding="utf-8"))
items = data["countries"]
codes = [item["code"] for item in items]
assert len(codes) == len(set(codes)), "regional package codes must be unique"

for parent, expected in {
    "US": {"US-NE", "US-MW", "US-SO", "US-WE", "US-PA"},
    "RU": {"RU-CTR", "RU-FE", "RU-SIB", "RU-VOL"},
    "CA": {"CA-AB", "CA-BC", "CA-ON", "CA-QC", "CA-NU"},
    "BR": {"BR-CO", "BR-NE", "BR-NO", "BR-SE", "BR-SO"},
}.items():
    actual = {item["code"] for item in items if item.get("country_code") == parent}
    assert expected.issubset(actual), f"missing regional packages for {parent}"
    assert parent not in actual
    for item in (item for item in items if item.get("country_code") == parent):
        assert item["country_name_fa"]
        assert item["region_name_fa"]
        assert item["pbf_url"].endswith(".osm.pbf")

manifest = (root / "tools/make_manifest.py").read_text(encoding="utf-8")
assert "--country-code" in manifest
assert '"country_code"' in manifest
workflow = (root / ".github/workflows/build-abtin-map.yml").read_text(encoding="utf-8")
assert "matrix.country_code" in workflow
assert '"max_zoom": c.get("render_max_zoom", 14)' in workflow
assert "cache-dependency-path: requirements-renderer.txt" in workflow
assert "cache-dependency-path: server_map_builder/requirements-renderer.txt" not in workflow
assert "--only-binary=:all: -r requirements-renderer.txt" in workflow
assert "needs.build.result == 'success'" in workflow
deps = (root / "requirements-renderer.txt").read_text(encoding="utf-8").splitlines()
assert deps[:3] == ["osmium", "zstandard", "Pillow"]
print(f"regional_catalog_ok packages={len(items)}")
