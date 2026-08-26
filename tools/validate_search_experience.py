"""Structural checks for the map-first POI search experience."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
screen = (root / "lib/features/search/presentation/search_screen.dart").read_text(encoding="utf-8")

for token in (
    "class _SearchMapPoiBadge",
    "class _PoiDetailsSheet",
    "class _PoiGlyph",
    "_camera.project(AbmPoint(result.lng, result.lat))",
    "widget.results.take(14)",
    "SharePlus.instance.share",
    "savedPlacesRepositoryProvider",
    "مسیریابی",
    "نمایش ${widget.results.length} نتیجه در فهرست",
    "bool samePlace(SearchResult other)",
):
    assert token in screen, f"missing search experience contract: {token}"

assert "Icons.local_gas_station_rounded" in screen
assert "Icons.local_hospital_rounded" in screen
print("search_experience_contract_ok")
