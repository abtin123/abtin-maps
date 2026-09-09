# Offline vector rendering

Offline maps are rendered directly from the installed ABM vector streams.

- `AbmReader` extracts and reads the six vector layers.
- Search uses `search/search.sqlite`.
- POI data uses `poi/poi.sqlite`.
- Routing uses `routing/graph.bin`.
- App styles live under `assets/styles/`.
- No PMTiles/MBTiles/raster tiles are used by the offline renderer.
- At low zoom the offline view shows the bundled world overview instead of an empty single-country canvas.
