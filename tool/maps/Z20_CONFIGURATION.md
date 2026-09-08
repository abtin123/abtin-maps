# Abtin Maps Z20 configuration

- Vector map zoom range: 2–20 (client-facing, declared in the app-bundled offline styles)
- Planetiler tile-pyramid maxzoom: 16 (hard cap in Planetiler 0.10.2; z17-20 are
  reached by MapLibre overzooming the z16 tiles, not by generating extra data)
- POI target visibility: z12+
- Buildings target visibility: z14+
- Major road labels: z8+
- Local road labels: z14+

The app location puck is controlled by the client and is not part of the map build.


### ABM graph index v3
The graph index stores tile offsets relative to the tile-data block. This removes the self-referential compressed-index offset calculation and prevents large-map fixed-point failures. The app adds `strings_offset + strings_compressed_length` at read time.
