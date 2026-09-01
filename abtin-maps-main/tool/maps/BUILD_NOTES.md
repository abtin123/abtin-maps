# ABTINMAP build pipeline

## Output contract

Each Geofabrik country or regional extract is built as its own `XX.abm` container. The regional partition is **not** changed by this pipeline: if Geofabrik exposes north/east/west/etc. children, those children remain separate ABMs.

Each ABM contains, in one random-access PMTiles v3 file:

- vector PMTiles (`land`, `water`, `boundaries`, `roads`, `buildings`, `pois`)
- the unified routing graph for that extract, including border-node data for routing across the extract
- day/night styles
- glyphs and POI sprites
- `search/places.sqlite` (SQLite FTS5 offline search index)

The PMTiles payload remains the first declared tile-data region; ABM segments are appended inside that declared region and are referenced from `metadata.abtin_container`. The mobile reader therefore continues to use one `.abm` file.

## Zoom contract

- country boundaries/world overview are supplied by the app's world layer
- major road labels: zoom 8
- local road labels: zoom 14
- buildings: zoom 14
- POI: zoom 12
- vector source maximum zoom: 16

## Update behavior

The weekly GitHub Actions workflow checks the Geofabrik PBF `.md5` sidecar for every catalog entry. If the source signature is unchanged from the published manifest, the map is **not rebuilt**.

If the source changed, Planetiler is run for that affected extract. Planetiler is a snapshot builder and does not expose a supported incremental tile-rebuild API, so the changed extract is regenerated from its new PBF; the important incremental behavior for the application is that unchanged extracts are untouched and the phone receives a block-level delta when a new ABM is published.

The server-side delta format is `ABTINMAP-CHUNK-PATCH/1`, with 4 MiB blocks. A patch is published only when it is smaller than the full target file.

## Reliability

The workflow:

1. discovers the complete Geofabrik catalog once;
2. expands countries into their existing regional children where applicable;
3. divides the catalog across 64 build jobs;
4. retries an individual failed map up to three times;
5. validates PMTiles, graph, styles, POI layer and offline search index;
6. refuses to publish if any expected catalog entry is missing or stale;
7. keeps previous release maps for entries whose source signature did not change;
8. publishes only after the complete catalog has been proven.

Large ABMs are split into byte-identical concatenable `XX.abm.partN` files below the GitHub Release per-asset limit. The manifest SHA-256 is the SHA-256 of the concatenated original ABM, so the Flutter client can reassemble and validate the map.

## Important source

Geofabrik publishes `.osm.pbf.md5` checksum sidecars for its extracts; the builder verifies the downloaded PBF against that checksum before doing the expensive build.
