# Online map rendering fixes

Applied fixes for the Android online-map incomplete-tile/gap issue:

1. Removed all runtime `addLineLayer` / `addCircleLayer` / `addSymbolLayer` calls that injected extra layers into the provider-owned OpenFreeMap MVT source-layers (`transportation` / `poi`).
2. Online OpenFreeMap styles are no longer mutated with the offline palette. Palette mutations remain limited to the bundled offline ABM style.
3. Added a one-time-per-process `clearAmbientCache()` for the online MapLibre renderer to evict stale/empty native ambient tiles without wiping offline regions.
4. The map retry action now clears MapLibre's ambient cache before recreating the map widget, so retry is a real tile-cache recovery instead of only rebuilding the Flutter widget.
5. Kept the existing camera zoom behavior (including overzoom) intact; source/style ownership remains with OpenFreeMap rather than forcing an artificial camera max-zoom reduction.
6. Pinned `maplibre_gl` to `0.27.0` so the resolved plugin cannot silently move to a future incompatible release.

## Build

The supplied environment did not contain the Flutter SDK, so an APK could not be compiled here. On a machine with Flutter installed:

```bash
flutter clean
flutter pub get
flutter analyze
flutter build apk --debug
```

For the first test on a device that previously showed gaps, uninstall the old APK first (or use the in-app retry after installing this build) so the new cache-recovery path is exercised.
