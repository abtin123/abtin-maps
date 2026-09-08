# Abtin Maps vector renderer configuration

- Vector map data range: z2–z16 in PMTiles.
- Client renderer overzooms the z16 vector data to z18.
- POI target visibility: z12+
- Buildings target visibility: z14+
- Major road labels: z8+
- Local road labels: z14+
- The `.abm` archive stores only vector map data, routing graph and offline search data.
- Day/night styles, glyphs and POI sprites are bundled once with the app and are rendered by MapLibre Native.

The vehicle/location marker is controlled by the client and is not part of the map build.
