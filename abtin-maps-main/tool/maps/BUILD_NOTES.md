# ABM build/update notes

- The country artifact remains one `CC.abm` file. PMTiles, routing graph, styles, glyphs, sprites and the offline SQLite FTS5 search index are embedded as independent ABM segments.
- Vector tiles are generated through Planetiler with `maxzoom: 16`.
- Major road labels start at zoom 8; local road labels and buildings are visible from zoom 14; POI features are present/rendered from zoom 12.
- The world overview (country boundaries at low zoom) is an app-level world basemap; a country `.abm` is not expected to contain the entire planet.
- `build_all_maps.py` compares the upstream PBF revision (ETag/Last-Modified/Content-Length when available) with the previous release. Unchanged countries are not rebuilt.
- When a country changes, the updated ABM is built and `build_abm_delta.py` produces an `ABTINMAP-CHUNK-PATCH/1` patch if it is smaller than the full archive. The Flutter app can apply that patch only when its installed ABM SHA-256 matches the patch base SHA-256.
- `weekly_update.sh` can maintain a local PBF by applying OSM replication diffs with `pyosmium-up-to-date`; Planetiler itself is a full-import tool, so the tile renderer still imports the updated PBF. This avoids pretending Planetiler supports partial imports while still making the data-refresh and mobile-download paths incremental.
- GitHub Actions runs the release workflow weekly and can also be started manually.
