#!/usr/bin/env python3
"""Static contract checks for map-first search results and the global globe."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
search = (root / "lib/features/search/presentation/search_screen.dart").read_text(encoding="utf-8")
world = (root / "lib/features/map/presentation/world_outline_painter.dart").read_text(encoding="utf-8")

assert "_showMap = _results.isNotEmpty;" in search
assert "class _SearchMapMode" in search
assert "_showResultsListSheet" in search
assert "DraggableScrollableSheet" in search
assert "نمایش فهرست" in search
assert "widget.onFocus(result)" in search

assert "void _paintGlobe" in world
assert "RadialGradient" in world
assert "_globeProject" in world
assert "_paintGlobeLabels" in world
assert "scale <= 1.18" in world

print("search_map_results_contract_ok")
