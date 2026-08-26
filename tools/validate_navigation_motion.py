"""Static contract checks for the Flutter navigation-motion pipeline."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
home = (root / "lib/features/map/presentation/home_screen.dart").read_text(encoding="utf-8")
canvas = (root / "lib/abtinmap/abm_canvas_map_view.dart").read_text(encoding="utf-8")
settings = (root / "lib/features/settings/domain/appearance_settings.dart").read_text(encoding="utf-8")
providers = (root / "lib/features/settings/presentation/appearance_settings_providers.dart").read_text(encoding="utf-8")
marker_page = (root / "lib/features/settings/presentation/appearance/pages/marker_page.dart").read_text(encoding="utf-8")
marker = (root / "lib/features/vehicle/presentation/vehicle_marker.dart").read_text(encoding="utf-8")
kalman = (root / "lib/features/gps/data/joint_kalman_filter_2d.dart").read_text(encoding="utf-8")

assert "ref.watch(navigationPositionProvider)" in home
assert "ref.listen<AsyncValue<VehiclePosition>>(navigationPositionProvider" in home
assert "controller.animateCamera(" in home
assert "duration: _cameraFollowDuration" in home
assert "_filterFollowBearing" in home
assert "if (mounted && !_cameraFollowsVehicle) setState(() {});" in home
assert "ref.read(navigationCameraTiltProvider)" in home
assert "bearing = isNavigating ? _filterFollowBearing(pos.headingDeg)" in home
assert "ref.read(mapTiltProvider)" in home
assert "navigationCameraTiltProvider) / 90.0 * 60.0" in home

assert "void animateTo(AbmCamera target" in canvas
assert "Timer.periodic(const Duration(milliseconds: 16)" in canvas
assert "_shortestBearingDelta" in canvas

assert "navigationCameraTiltDegrees" in settings
assert "carDisplayAngleDegrees" not in settings
assert "navigationCameraTiltProvider" in providers
assert "carDisplayAngleProvider" not in providers
assert "نمای عمودی دوربین ناوبری" in marker_page
assert "از بالا" in marker_page and "پشت خودرو" in marker_page
assert "max: 90" in marker_page
assert "settings.copyWith(vehicleModelIndex: next)" in marker_page
assert "settings.copyWith(carBodyColor: c)" in marker_page
assert "_syncTargetRotation();" in marker
assert "double _lastBearingDeg = 0;" in kalman
assert "fallbackBearingDeg ?? _lastBearingDeg" in kalman
sample_body = kalman.split("KalmanLocationSample _sampleFromState", 1)[1].split("/// یک مرحله", 1)[0]
assert "raw.bearingDeg" not in sample_body
print("navigation_motion_contract_ok")
