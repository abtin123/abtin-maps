# Offline map builder fix

- ABM graph index v3 removes the self-referential compressed-index offset calculation. Large maps no longer depend on index-size fixed-point stabilization.
- Graph tile offsets are relative to the tile-data block; the app reconstructs absolute offsets from the string-table end.
- Container zoom contract is explicitly tile pyramid z2-z16 with app overzoom to z20.
- Basemap now emits place labels and named POIs for MapLibre rendering.
- Renderer assets remain app-bundled and are not copied into country ABMs.
