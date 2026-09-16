# TODO

## Fixed this delivery
- `lib/routing/routing_engine.dart` `_routeSqliteDetailed`: Dijkstra only read
  `edges WHERE start=?`; `oneway` column was selected but never checked, so any
  two-way road was only traversable in whichever direction the graph builder
  happened to store it — most of the network was effectively unreachable,
  causing "مسیری روی نقشهٔ آفلاین پیدا نشد" even on a correctly rendered map.
  Added a `WHERE end=?` reverse-edge query, excluded only when the row is
  actually oneway.
- `lib/map_engine/abm_reader.dart` replaced with the fixed version (was still
  the pre-fix file in this zip): `_workerBudget` 900ms → 18s (was cutting
  legitimate chunks mid-read and returning `partial=true`), added persistent
  chunk LRU cache, layer-priority + nearest-first chunk ordering, and an
  index-empty recovery probe.
- `abm_reader.dart` `_loadVectorIndex`: added `_normalizeLayerKey()` alias
  table (building→buildings, land_use/land→landuse, poi/place→places,
  boundary/admin→boundaries, highway→roads) so a build-pipeline index.json
  using a slightly different layer key no longer gets silently dropped from
  `byLayer` (which would otherwise leave that whole layer permanently empty
  offline, with no error). Still worth checking the real `.abm`'s
  `vector/index.json` keys directly if any layer is still empty after this.
- `abm_reader.dart` `maxCachedChunks` 16 → 64 (a real viewport in testing
  selected 29 chunks/52 road features alone; 16 was evicting chunks the very
  next pan re-requested).

## Investigated, not a bug
- `_mapReloadKey` (home_screen.dart) only increments from `_retryMapLoad`,
  itself only triggered by the 20s "still not loaded" watchdog — not a
  frequent/spurious remount source. The back-to-back "[OFFLINE MAP] active=…
  ready=true" log lines were most likely two call sites logging one real
  cold start, not repeated remounts. Not touched.

## Still open — needs device/runtime, not fixable from source alone here
- `ZONE CRASH ... MAP_NOT_READY` from `AnnotationManager.initialize` is
  raised inside the `maplibre_gl` package's own `MapLibreMapController`
  constructor (stack trace confirms), not app code. Grep confirms this app
  never uses `SymbolManager`/`CircleManager`/`FillManager`/annotation APIs
  (everything is style layers), so the failing annotation manager is pure
  plugin overhead the app doesn't need but can't disable. It's already
  caught by the zone handler and only logged, not fatal. No source-level fix
  available without upgrading `maplibre_gl` (pinned `^0.27.1`) or patching
  it — no network access here to check for a newer release.

## Runtime test still required
No Flutter SDK / real `.abm` / device in this environment. Rebuild + full
reinstall (not overlay) and retest offline rendering (all zooms/areas) and
offline routing (several origin/destination pairs, including roads only
reachable "the other direction").
