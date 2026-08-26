"""Static contract checks for route-constrained long-tunnel navigation."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
home = (root / "lib/features/map/presentation/home_screen.dart").read_text(encoding="utf-8")

assert "_longTunnelWatchTimer" in home
assert "_maxLongTunnelEstimate = Duration(seconds: 120)" in home
assert "_advanceLongTunnelEstimate" in home
assert "_projectRouteProgressMeters" in home
assert "_routeSampleAtMeters" in home
assert "_tunnelEstimatedPosition ?? liveVehiclePosition" in home
assert "_updateNavigationProgress(estimated, nav, estimated: true)" in home
assert "isEstimated: true" in home
assert "_EstimatedLocationBanner" in home
assert "موقعیت تخمینی است؛ در انتظار بازگشت GPS" in home
assert "if (!estimated && nav.state == NavigationState.navigating" in home
assert "_longTunnelWatchTimer?.cancel();" in home
assert "_clearLongTunnelEstimate();" in home
assert "سرعت را به‌آرامی کم می‌کنیم" in home
print("long_tunnel_navigation_contract_ok")
