# Abtin Maps - requested update

This project starts from the original uploaded app UI.

Preserved:
- Original navigation-card layout and visual shell.
- Existing app navigation, bottom bar, weather widget and overall visual language.

Updated:
- Navigation maneuver arrows.
- Dedicated roundabout maneuver icon with exit number/turn sweep.
- Road-warning badges styled like the supplied reference (camera/speed-bump).
- Optional clock + battery floating widget, with on/off, position, size,
  alignment, background color/opacity and text color controls in Appearance.
- Lean offline map runtime: styles are app-bundled; rendered POI sprites are
  not duplicated in each .abm map.
- Offline map download size formatting.
- Language packs may be partial; missing/empty translations fall back to the
  app's built-in strings.
- Map build scripts for the lean basemap/container/manifest are included under
  tool/maps.

No Flutter build was run in this environment because Flutter/Dart is not
installed here.

Fixed in this revision:
- Offline PMTiles/ABM container validation now accepts container schema v2 produced by the current `pack_abm_container.py` (while keeping v1 compatibility). This restores local PMTiles style preparation and offline map rendering.
- Online MapLibre startup no longer wipes the native ambient tile cache automatically. Cached valid tiles are reused on startup, preventing partial/blank map areas on unstable connections; retry remains available through the existing map reload flow.
