import 'dart:math';
import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import '../../../core/theme/app_colors.dart';
import 'vehicle_provider.dart';

class VehicleMarker extends StatefulWidget {
  final MapLibreMapController? mapController;
  final LatLng position;
  final double headingDeg;
  final double accuracyM;
  final VehicleType vehicle;
  final bool followsCamera;
  final bool drivingMode;

  const VehicleMarker({
    super.key,
    required this.mapController,
    required this.position,
    required this.headingDeg,
    required this.accuracyM,
    required this.vehicle,
    this.followsCamera = false,
    this.drivingMode = false,
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
    // در حالت رانندگی، موقعیت ثابت است
    if (widget.drivingMode) {
      final screenSize = MediaQuery.of(context).size;
      // افقی: وسط صفحه
      // عمودی: 60% ارتفاع (کمی پایین‌تر از وسط)
      final centerX = screenSize.width / 2;
      final centerY = screenSize.height * 0.60;
      
      if (mounted) {
        setState(() {
          _screen = Point(centerX, centerY);
          _pixelsPerMeter = 1.0; // در حالت رانندگی نیازی به محاسبه نیست
        });
      }
      return;
    }

    // در حالت عادی، موقعیت بر اساس GPS محاسبه می‌شود
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

    // در صورتی که از نشانگر نیتیو استفاده می‌کنیم، نشانگر دستی را در حالت رانندگی مخفی می‌کنیم
    if (widget.drivingMode) return const SizedBox.shrink();

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
              
              // Vehicle Arrow/Icon or 3D Model
              widget.vehicle == VehicleType.arrow
                  ? AnimatedRotation(
                      turns: _rotationTurns,
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.linear,
                      child: Image.asset(
                        'assets/images/nav_arrow.png',
                        width: markerSize,
                        height: markerSize,
                        fit: BoxFit.contain,
                      ),
                    )
                  : _ThreeDVehicle(headingDeg: widget.headingDeg),
            ],
          ),
        ),
      ),
    );
  }
}

class _ThreeDVehicle extends StatefulWidget {
  final double headingDeg;
  const _ThreeDVehicle({required this.headingDeg});

  @override
  State<_ThreeDVehicle> createState() => _ThreeDVehicleState();
}

class _ThreeDVehicleState extends State<_ThreeDVehicle> with SingleTickerProviderStateMixin {
  late AnimationController _rotationController;
  double _previousHeading = 0;
  double _smoothHeading = 0;

  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _previousHeading = widget.headingDeg;
    _smoothHeading = widget.headingDeg;
  }

  @override
  void didUpdateWidget(_ThreeDVehicle oldWidget) {
    super.didUpdateWidget(oldWidget);
    if ((widget.headingDeg - _previousHeading).abs() > 1) {
      _previousHeading = widget.headingDeg;
      _smoothHeading = widget.headingDeg;
      setState(() {});
    }
  }

  @override
  void dispose() {
    _rotationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 80,
      height: 80,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // 3D Model with smooth rotation
          ModelViewer(
            src: 'assets/models/bmw_i8.glb',
            alt: 'BMW i8 3D Model',
            autoRotate: false,
            cameraControls: false,
            disableZoom: true,
            // Top-down isometric view with dynamic rotation
            cameraOrbit: '${_smoothHeading}deg 85deg 3.5m',
            cameraTarget: '0m 0m 0m',
            fieldOfView: '25deg',
            backgroundColor: Colors.transparent,
          ),
          // Subtle shadow under the vehicle
          Positioned(
            bottom: 5,
            child: Container(
              width: 60,
              height: 8,
              decoration: BoxDecoration(
                shape: BoxShape.ellipse,
                color: Colors.black.withOpacity(0.2),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 8,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
