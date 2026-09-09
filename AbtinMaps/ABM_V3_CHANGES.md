# ABM v3 contract

The app and builder are synchronized on a ZIP-based, tile-free ABM archive.

Required entries:
- `metadata.json`
- `vector/roads.bin`
- `vector/buildings.bin`
- `vector/landuse.bin`
- `vector/water.bin`
- `vector/boundaries.bin`
- `vector/places.bin`
- `poi/poi.sqlite`
- `search/search.sqlite`
- `routing/graph.bin`

The ABM contains data only. Styles stay in the app. There is no PMTiles, MBTiles, raster tile provider, `terrain.bin`, `style.json`, or render cache inside the ABM.

At low offline zoom (`<= 4.25`) the app switches to its bundled world overview renderer. At closer zoom it renders the installed ABM vector data.
