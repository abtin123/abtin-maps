#!/usr/bin/env python3
"""Static contract checks for the Flutter navigation-motion pipeline."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
home = (root / "lib/features/map/presentation/home_screen.dart").read_text(encoding="utf-8")
canvas = (root / "lib/abtinmap/abm_canvas_map_view.dart").read_text(encoding="utf-8")
settings = (root / "lib/features/settings/domain/appearance_settings.dart").read_text(encoding="utf-8")
providers = (root / "lib/features/settings/presentation/appearance_settings_providers.dart").read_text(encoding="utf-8")
marker_page = (root / "lib/features/settings/presentation/appearance/pages/marker_page.dart").read_text(encoding="utf-8")

assert "ref.watch(animatedVehiclePositionProvider)" in home
assert "ref.listen<AsyncValue<VehiclePosition>>(animatedVehiclePositionProvider" in home
assert "controller.animateCamera(" in home
assert "duration: _cameraFollowDuration" in home
assert "_filterFollowBearing" in home
assert "if (mounted && !_cameraFollowsVehicle) setState(() {});" in home
assert "ref.read(navigationCameraTiltProvider)" in home
assert "bearing = isNavigating ? _filterFollowBearing(pos.headingDeg)" in home

assert "void animateTo(AbmCamera target" in canvas
assert "Timer.periodic(const Duration(milliseconds: 16)" in canvas
assert "_shortestBearingDelta" in canvas

assert "navigationCameraTiltDegrees" in settings
assert "carDisplayAngleDegrees" not in settings
assert "navigationCameraTiltProvider" in providers
assert "carDisplayAngleProvider" not in providers
assert "نمای عمودی دوربین ناوبری" in marker_page
assert "از بالا" in marker_page and "پشت خودرو" in marker_page
print("navigation_motion_contract_ok")
