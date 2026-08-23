# TODO

## Done this session
- Atlas zoom domain: z2–z14 default everywhere (`rendered_tile_builder.py`, `raster_primitives.py`, `build_country_package.py`, `countries.json`, `sync_geofabrik_catalog.py`, `.github/workflows/build-abtin-map.yml`). Removed IR's z16 override — no country exception.
- Road width now scales on absolute zoom: `width * 1.32^(zoom-14)`, floor 1px, reference z14 (`raster_primitives.py` `WIDTH_ZOOM_REFERENCE`/`WIDTH_ZOOM_BASE`).
- Road LOD staircase updated: motorway z3, trunk z5, primary z7, secondary z9, tertiary z10, residential/unclassified z12, service z13 (both `RoadHandler.way` and `RenderHandler.way`).
- Polygons under `MIN_POLYGON_PIXELS` (2.5px) bbox at a given zoom are skipped (`draw_polygon`) — cuts sub-pixel draw/blur noise at distant zooms.
- `overzoom_max = min(maxzoom+5, 19)` written to atlas sqlite metadata, `rendered-{code}.json`, and `raster_primitives.py`'s own metadata — flows into `manifest-{code}.json` via `make_manifest.py`'s existing `entry["rendered"]` passthrough (no manifest code change needed).
- `validate_rendered_atlas.py` assertions updated to new numbers (12/13, default=14, overzoom_max present) — ran the atlas + width/polygon-skip logic directly (osmium+Pillow installed in sandbox) as a smoke test; sqlite metadata confirmed `maxzoom=14`, `overzoom_max=19`.

## Open / not touched (out of scope — not in this zip)
- `lib/features/map/presentation/rendered_atlas_map_view.dart` and `lib/abtinmap/abm_canvas_map_view.dart` (Flutter app repo, separate zip) — these are where `overzoom_max` actually needs to be read to clamp/upscale camera zoom client-side; `validate_rendered_atlas.py` already expects `_maxInteractiveZoom`, `nearestBaseTile`, `.clamp(2.0, 20.0)`, `camera.zoom >= 16.0` there. Not present in `abtin-maps-main-fixed.zip`, so unchanged.
- Not build/CI-run end-to-end (no `osmium`/network access to real Geofabrik PBFs here) — only unit-level smoke tests on the changed functions.
