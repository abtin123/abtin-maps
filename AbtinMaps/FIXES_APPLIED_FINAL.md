# Abtin Maps — Final navigation/map fixes

## Navigation
- GPS Android update interval reduced from 1s to 250ms for navigation-grade position updates.
- Vehicle animation is frame-synchronised with Flutter `Ticker` instead of a 16ms wall-clock timer.
- Route progress is integrated from smoothed vehicle speed and sampled from the active route geometry; GPS is validation/speed input only and cannot advance the marker.
- Route projection look-ahead increased to tolerate one delayed GPS sample without snapping.
- Movement bearing is calculated before off-route validation, so the first fix after a missed turn can trigger rerouting.
- Off-route corridor tightened and high-confidence wrong-direction detection made faster.
- Confirmed off-route immediately abandons the old route animation and anchors the vehicle to the validated GPS position before rerouting, without overwriting rendered speed.

## External location/deep links
- `geo:` and `geo:0,0?q=lat,lng` are parsed safely.
- `geo:0,0` without a real destination is ignored instead of becoming Null Island.
- GoRouter redirects external navigation URIs to `/` and has a Home fallback, preventing the `GoException: no routes for location` page.

## Offline vector map
- The standalone Python builder now emits a data-only ABM contract; this Flutter project still contains a legacy PMTiles reader and requires the reader/renderer migration before it can consume that new archive directly.
- Day/night styles, glyphs and POI sprites are app-bundled renderer assets and are not duplicated in every country archive.
- Offline styles are local-only; no HTTP/HTTPS resource is allowed by the runtime guard.
- Offline day/night styles use the same MapLibre vector-rendering model and include POI symbol rendering.
- The map schema now actually emits a `pois` vector layer, matching the offline styles.
- PMTiles remains vector/PBF data; the mobile MapLibre renderer draws fills, lines, labels and symbols at runtime.
- New data-only containers use ABTINMAP container version 4; the app still reads older v1-v3 installed maps.
