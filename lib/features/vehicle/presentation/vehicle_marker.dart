import 'dart:math';
import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../../../core/theme/app_colors.dart';
import 'vehicle_provider.dart';

class VehicleMarker extends StatefulWidget {
  final MapLibreMapController? mapController;
  final LatLng position;
  final double headingDeg;
  final double accuracyM;
  final VehicleType vehicle;
  final bool followsCamera;

  const VehicleMarker({
    super.key,
    required this.mapController,
    required this.position,
    required this.headingDeg,
    required this.accuracyM,
    required this.vehicle,
    this.followsCamera = false,
  });

  @override
  State<VehicleMarker> createState() => _VehicleMarkerState();
}

class _VehicleMarkerState extends State<VehicleMarker> {
  Point<num>? _screen;
  double _rotationTurns = 0;
  double _pixelsPerMeter = 0;

  @override
  void initState() {
    super.initState();
    _rotationTurns = widget.headingDeg / 360.0;
    _updateLocation();
  }

  @override
  void didUpdateWidget(covariant VehicleMarker oldWidget) {
    super.didUpdateWidget(oldWidget);
    _advanceRotation(widget.headingDeg);
    _updateLocation();
  }

  void _advanceRotation(double newHeadingDeg) {
    final newTurnsRaw = newHeadingDeg / 360.0;
    final currentFraction = _rotationTurns - _rotationTurns.floorToDouble();
    var delta = newTurnsRaw - currentFraction;
    delta -= delta.roundToDouble();
    _rotationTurns += delta;
  }

  Future<void> _updateLocation() async {
    final controller = widget.mapController;
    if (controller == null) return;
    try {
      final s = await controller.toScreenLocation(widget.position);
      
      // Calculate pixels per meter for the accuracy circle
      // We take a point 100m away to get a stable scale
      const double testDistM = 100.0;
      final double latOffset = testDistM / 111320.0;
      final testPos = LatLng(widget.position.latitude + latOffset, widget.position.longitude);
      final s2 = await controller.toScreenLocation(testPos);
      
      if (!mounted) return;
      
      final double dx = (s.x - s2.x).toDouble();
      final double dy = (s.y - s2.y).toDouble();
      final double distPx = sqrt(dx * dx + dy * dy);
      
      setState(() {
        _screen = s;
        _pixelsPerMeter = distPx / testDistM;
      });
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final s = _screen;
    if (s == null) return const SizedBox.shrink();

    const markerSize = 52.0;
    final accuracyRadiusPx = widget.accuracyM * _pixelsPerMeter;

    return Positioned(
      left: s.x.toDouble() - max(markerSize / 2, accuracyRadiusPx),
      top: s.y.toDouble() - max(markerSize / 2, accuracyRadiusPx),
      child: IgnorePointer(
        child: SizedBox(
          width: max(markerSize, accuracyRadiusPx * 2),
          height: max(markerSize, accuracyRadiusPx * 2),
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Accuracy Circle
              if (widget.accuracyM > 0)
                Container(
                  width: accuracyRadiusPx * 2,
                  height: accuracyRadiusPx * 2,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.blue.withOpacity(0.15),
                    border: Border.all(
                      color: Colors.blue.withOpacity(0.3),
                      width: 1,
                    ),
                  ),
                ),
              
              // Vehicle Arrow/Icon
              AnimatedRotation(
                turns: _rotationTurns,
                duration: const Duration(milliseconds: 200),
                curve: Curves.linear,
                child: widget.vehicle == VehicleType.arrow
                    ? Image.asset(
                        'assets/images/nav_arrow.png',
                        width: markerSize,
                        height: markerSize,
                        fit: BoxFit.contain,
                      )
                    : const _CarIcon(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CarIcon extends StatelessWidget {
  const _CarIcon();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.homeAccent.withOpacity(.18),
        border: Border.all(color: AppColors.homeAccent, width: 2),
      ),
      child: const Icon(Icons.directions_car_rounded, color: AppColors.homeAccent, size: 26),
    );
  }
}
