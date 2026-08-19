import gzip
import json
from pathlib import Path


root = Path(__file__).resolve().parents[2]
asset = root / "assets/world/world_boundaries.v1.json.gz"
with gzip.open(asset, "rb") as stream:
    payload = json.load(stream)
assert payload["v"] == 1
assert payload["s"] == 10000
assert len(payload["b"]) >= 170
assert all(len(ring) >= 4 for country in payload["b"] for ring in country)
builder = (root / "server_map_builder/tools/abtinmap_build.py").read_text(encoding="utf-8")
assert '"traffic_signals": 72' in builder
assert "resolve_building_height_dm" in builder
rendered_builder = (root / "server_map_builder/tools/rendered_tile_builder.py").read_text(encoding="utf-8")
assert '"format": "ABTIN_RENDERED_ATLAS/1"' in rendered_builder
assert "CREATE TABLE tiles" in rendered_builder
assert "CREATE TABLE poi_tiles" in rendered_builder
manifest_builder = (root / "server_map_builder/tools/make_manifest.py").read_text(encoding="utf-8")
assert "--rendered-meta" in manifest_builder
embedder = (root / "server_map_builder/tools/embed_rendered_atlas.py").read_text(encoding="utf-8")
assert 'MAGIC = b"ABTATLS2"' in embedder
workflow = (root / "server_map_builder/.github/workflows/build-abtin-map.yml").read_text(encoding="utf-8")
assert "embed_rendered_atlas.py" in workflow
assert 'rm -f "out/${{ matrix.code }}.amap"' in workflow
world_view = (root / "lib/features/map/presentation/world_outline_painter.dart").read_text(encoding="utf-8")
assert "world_boundaries.v1.json.gz" in world_view
assert "GZipDecoder" in world_view
assert "details.rotation" in world_view
renderer = (root / "lib/abtinmap/abm_renderer.dart").read_text(encoding="utf-8")
assert "'height': area.buildingHeightMeters" in renderer
assert "poiTrafficLight" in renderer
assert "assets/world/" in (root / "pubspec.yaml").read_text(encoding="utf-8")
tile_service = (root / "lib/features/offline_maps/data/rendered_tile_map_service.dart").read_text(encoding="utf-8")
assert "localAtlasFile" in tile_service
assert "installFromAbm" in tile_service
assert "installPreviewFromAbm" in tile_service
home = (root / "lib/features/map/presentation/home_screen.dart").read_text(encoding="utf-8")
assert "showRenderedAtlas" in home
assert "RenderedAtlasMapView" in home
assert "showRenderedPreview" in home
print(f"world_asset_ok countries={len(payload['b'])} bytes={asset.stat().st_size}")
