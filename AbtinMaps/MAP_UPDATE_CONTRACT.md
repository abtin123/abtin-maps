# Abtin Maps — map update contract

- GitHub Actions rebuilds maps weekly (Monday 03:30 UTC).
- Geofabrik `.osm.pbf.md5` is the source-change signature. Unchanged extracts are not rebuilt or re-uploaded.
- A changed single-file ABM gets an optional `ABTINMAP-CHUNK-PATCH/1` delta made of 4 MiB blocks. The patch is published only when smaller than the full ABM.
- The Android app checks the map manifest at most once every 7 days (unless the user manually refreshes).
- The app updates only ABMs that are already installed on the device. It does not download maps for countries the user has never installed.
- If a compatible delta patch exists, only changed blocks are downloaded. The app reconstructs the new ABM locally and verifies SHA-256 before replacing the installed map.
- If no usable/smaller patch exists, the app falls back to a resumable full-map download.
- Map data remains data-only: vector tiles + routing graph + offline search; styles/glyphs/sprites stay bundled with the app renderer.
