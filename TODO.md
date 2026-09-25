# Abtin Maps — final validation TODO

- [x] ABM runtime extracts exactly `map.mbtiles` and `map.sqlite`.
- [x] `map.mbtiles` is the offline cartographic basemap consumed by MapLibre.
- [x] `map.sqlite` remains the direct query store for search, POI, road metadata and routing.
- [x] No whole-`map.sqlite` application cache or rebuild is used during viewport/search/routing queries.
- [x] Only targeted query results are materialized for the visible viewport.
- [x] Local MBTiles URI uses `mbtiles://file://...` for MapLibre Native compatibility.
- [x] Existing ABM extraction is reused only when the source archive signature matches; it is not a data-query cache.
- [ ] Run `flutter analyze` and `flutter test` in an environment with the Flutter SDK installed.
- [ ] Run a real Android offline-map smoke test with a downloaded `.abm` and verify the MBTiles source reaches `onStyleLoaded` and renders tiles.

# POI / sprite rendering
- [ ] Device check after rebuild: `adb logcat | grep -i -E "mbgl|maplibre"` must show no "Error setting filter", "Failed to load sprite", "Missing image".
- [ ] Armenian (AM) and `№` labels: Vazirmatn glyph ranges 1280-1535 / 8448-8703 are not bundled, those characters are not drawn.
- [ ] Rebuild IR/AM abm (see builder repo) - POI/search work, routing graph does not until rebuilt.

# Route guidance card
- [ ] Verify on device against the reference screenshot (886x304 design px, scale = width/886). Saved appearance settings override the new defaults (arrow #40F538, bg #01173D, border #91BCF2, radius .45, opacity .97): reset them once.
- [ ] Stat icons are Material (schedule/pin_drop/timer outlined), not the exact reference glyphs.


## ABM v2 routing partition contract
- [x] Geographic routing cells (0.25°) with per-node/per-segment cell IDs and indexed lookup.
- [x] Node spatial R-tree for nearest-road/map-matching candidate lookup.
- [x] Compressed way geometry separated from graph records (delta + ZigZag + Varint, 1e-5°).
- [x] Road metadata includes speed, lanes, access, one-way, bridge/tunnel/toll/ferry flags.
- [x] Hierarchy levels are materialized for local/primary/trunk/motorway routing.
- [x] Roundabout metadata table is materialized; exit count can be completed by runtime using the selected entry/exit context.
- [x] ABM metadata advertises schema 7 / graph 2 and the routing partition contract.
