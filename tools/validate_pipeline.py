from pathlib import Path


root = Path(__file__).resolve().parents[1]

# This repository is the source package for the map builder.  Older copies of
# this validator assumed it was checked out next to the Flutter application and
# therefore looked two directories above this file (for /assets, /lib and
# /server_map_builder).  In CI and in the source ZIP requested by users, the
# builder itself is the repository root, so validate the files that are actually
# in this project.
builder = (root / "tools/abtinmap_build.py").read_text(encoding="utf-8")
assert '"traffic_signals": 72' in builder
assert "resolve_building_height_dm" in builder
rendered_builder = (root / "tools/rendered_tile_builder.py").read_text(encoding="utf-8")
assert '"format": "ABTIN_RENDERED_ATLAS/1"' in rendered_builder
assert "CREATE TABLE tiles" in rendered_builder
assert "CREATE TABLE poi_tiles" in rendered_builder
manifest_builder = (root / "tools/make_manifest.py").read_text(encoding="utf-8")
assert "--rendered-meta" in manifest_builder
assert "--patch-json" in manifest_builder
patch_builder = (root / "tools/abtinmap_diff.py").read_text(encoding="utf-8")
assert 'SCHEMA = "ABTINMAP-CHUNK-PATCH/1"' in patch_builder
assert "target_size" in patch_builder
embedder = (root / "tools/embed_rendered_atlas.py").read_text(encoding="utf-8")
assert 'MAGIC = b"ABTATLS2"' in embedder
workflow = (root / ".github/workflows/build-abtin-map.yml").read_text(encoding="utf-8")
country_builder = (root / "tools/build_country_package.py").read_text(encoding="utf-8")
assert "rendered_tile_builder.py" in country_builder
assert "embed_rendered_atlas.py" in country_builder
assert "temporary.unlink" in country_builder
assert "--max-open-tiles" in country_builder
assert "--webp-quality" in country_builder
assert "--webp-method" in country_builder
assert "build_country_package.py" in workflow
print("pipeline_source_ok")
