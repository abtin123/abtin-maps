# TODO

- [x] 1. Fix distance-to-maneuver counting up instead of down (route-progress based)
- [x] 2. Fix route polyline loop/kink artifact at curves (shape-aware snap/reroute)
- [x] 3. Fix warning signs (camera/speed-bump/etc) not showing during navigation
- [x] 4. Fix online map incomplete tile rendering (gaps) — one-time ambient tile
      cache invalidation on the online style's first load (online_map_view.dart),
      so any corrupted/incomplete tiles left over from a previous interrupted
      session are re-fetched instead of reused as-is.
- [x] 5. Battery icon -> vertical orientation, configurable size/color
      (system_info_widget.dart, appearance_settings.dart, Appearance settings
      screen). Defaults unchanged (horizontal, 100%, uses text color).
- [x] 6. Font settings: size/color/weight controls (no default appearance change)
      (new "تنظیمات فونت" card in Appearance settings; app_theme.dart + main.dart
      apply the overrides). Defaults (100%, transparent=off, "as designed") leave
      the app's current look untouched.
- [x] 7. Final: zip whole project, present to user

## This pass (road-label-halo-fix session)
- [x] 8. Curve-sticking bug (car leaving road on turns) — root cause was
      `_navigationCameraTarget` in online_map_view.dart projecting a
      straight-line heading chord instead of following route.geometry. In
      driving mode the vehicle marker's screen position is pinned
      (_refreshScreenPositions/fixedVehicle) so only the camera target
      decides visual alignment with the road — a straight chord through a
      curve pulled the pinned marker off the drawn road. Fixed by walking
      forward along the actual route polyline (windowed/cached projection).
- [x] 9. Fake "AI alert" icon in hud_display_screen.dart — was a hardcoded
      Icon shown purely from a boolean setting, no real data. Replaced with
      nearestAheadRouteAlert() sourced from nav.route.alerts (same
      distance/heading-cone logic as the home screen's alert badge).
- [x] 10. Speed-limit sign — now only shown (both HUD and main map) when
      current speed is within 10 km/h of the limit or over it; hidden
      otherwise. No color/warning styling added — plain sign as before,
      just gated on proximity.
- [ ] Re-test the curve fix against a real drive/recording — this was
      fixed from frame analysis of the two provided screen recordings, not
      a live rebuild (no Flutter SDK in this environment to build/analyze).
- [ ] Run `flutter analyze` / a real build before shipping — edits were
      reviewed by hand only.
