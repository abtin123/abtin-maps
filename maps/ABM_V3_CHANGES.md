# ABM v3 / Offline map loading changes

- Each country remains one `CC.abm` file. No map ZIP/part files are required by the app.
- PMTiles v3 stays at the beginning of the same `.abm` file, so MapLibre can read vector tiles directly with HTTP/file range access.
- Routing graph remains a directly seekable ABTINMAP segment.
- Offline `search/places.sqlite` is compressed inside the ABM (zstd when the build environment has it; otherwise deterministic gzip level 9) and is transparently decompressed only when offline search is first used.
- Container metadata records segment offsets, compressed/raw sizes, codec and hashes.
- The previous segment-bound validation bug was fixed: graph/search are after PMTiles tile data, not inside the PMTiles tile-data range.
- Offline POIs are now rendered from OSM in a dedicated `pois` vector layer from zoom 12, with names from zoom 14. The complete searchable POI database remains intact in the ABM search segment.
- App map zoom is locked consistently to 2..16 for online/offline rendering and navigation.
- Search cache filenames include the ABM search-segment hash so a country update cannot reuse an old POI/search database.
