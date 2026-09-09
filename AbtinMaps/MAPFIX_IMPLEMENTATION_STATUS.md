# Abtin Maps map-fix status

## Route-driven vehicle animation

The vehicle marker and heading are emitted from one `VehiclePositionAnimator` stream. When a route is active, the animator integrates the smoothed vehicle speed at ticker cadence, samples the active route polyline by cumulative distance, and emits the sampled point and tangent bearing. The map widget uses that same position for the car, arrow, and follow camera.

GPS fixes do not assign latitude/longitude or route progress in navigation mode. They update the bounded speed/heading targets and are consumed by navigation validation. The prior GPS phase-lock path, which advanced route progress from a projected GPS fix, has been removed because it could make a noisy fix select a different point on a parallel road or jump across a turn.

On confirmed off-route detection, the old route clock is abandoned, the current fix is used as a temporary anchor while rerouting, and the new route is attached as the only animation track. The reroute anchor no longer overwrites the rendered speed, so rerouting cannot cause an instantaneous speed jump.

## Important remaining compatibility issue

The supplied project still contains a legacy `PMTiles`/tile-index ABM reader in `lib/abtinmap/abm_file.dart` and `lib/abtinmap/abm_container.dart`. It cannot read the data-only `country.abm` produced by the standalone Python ABM builder (which contains `metadata.json`, raw vector streams, SQLite databases, and `graph.bin`). A complete product release requires replacing that reader and the MapLibre tile source with a data-only ABM reader/renderer integration; this is a larger migration than the animation fix and must not be hidden behind a version label.

## Release build

A workflow is included at `.github/workflows/release-apk.yml`. It uses Flutter 3.35.1, runs `flutter analyze` and `flutter test`, builds `flutter build apk --release`, writes a SHA-256 file, and zips the APK. The current sandbox does not contain the Flutter SDK, so a local APK could not be produced here.
