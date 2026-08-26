"""Static contract checks for simultaneous online/offline route alternatives."""

from pathlib import Path


root = Path(__file__).resolve().parents[2]
canvas = (root / "lib/abtinmap/abm_canvas_map_view.dart").read_text(encoding="utf-8")
router = (root / "lib/abtinmap/abm_router.dart").read_text(encoding="utf-8")
service = (root / "lib/features/routing/data/routing_service.dart").read_text(encoding="utf-8")
providers = (root / "lib/features/routing/presentation/routing_providers.dart").read_text(encoding="utf-8")
screen = (root / "lib/features/routes/presentation/routes_screen.dart").read_text(encoding="utf-8")

assert "class AbmRouteOverlay" in canvas
assert "this.routeOverlays = const []" in canvas
assert "final List<AbmRouteOverlay> routeOverlays;" in canvas
assert "routeOverlays: widget.routeOverlays" in canvas
assert "routeOverlays.where((item) => !item.selected)" in canvas
assert "routeOverlays.where((item) => item.selected)" in canvas

assert "routeAlternatives(" in router
assert "calculateRoutes(" in service
assert "alternatives=true" in service
assert "calculateRoutesProvider" in providers

assert "ref.watch(calculateRoutesProvider)" in screen
assert "class _AlternativeRouteCards" in screen
assert "routeOverlays:" in screen
assert "onSelectRoute: (index) => setState" in screen
assert "_startNavigation(routes[selectedIndex])" in screen

print("multi_route_contract_ok")
