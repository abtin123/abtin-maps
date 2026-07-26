import 'dart:math';
import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../../../core/theme/app_colors.dart';
import 'vehicle_provider.dart';

class VehicleMarker extends StatefulWidget {
  final MapLibreMapController? mapController;
  final LatLng position;
  final double headingDeg;
  final VehicleType vehicle;

  final bool followsCamera;

  const VehicleMarker({
    super.key,
    required this.mapController,
    required this.position,
    required this.headingDeg,
    required this.vehicle,
    this.followsCamera = false,
  });

  @override
  State<VehicleMarker> createState() => _VehicleMarkerState();
}

class _VehicleMarkerState extends State<VehicleMarker> {
  Point<num>? _screen;

  double _rotationTurns = 0;

  @override
  void initState() {
    super.initState();
    _rotationTurns = widget.headingDeg / 360.0;
    _syncFollowMode();
  }

  @override
  void didUpdateWidget(covariant VehicleMarker oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.followsCamera != oldWidget.followsCamera) {
      _syncFollowMode();
    } else if (!widget.followsCamera) {
      _updateScreenLocation();
    }
    if (!widget.followsCamera) {
      _advanceRotation(widget.headingDeg);
    }
  }

  void _syncFollowMode() {
    if (widget.followsCamera) {
      _rotationTurns = _rotationTurns.roundToDouble();
      return;
    }
    _updateScreenLocation();
  }

  void _advanceRotation(double newHeadingDeg) {
    final newTurnsRaw = newHeadingDeg / 360.0;
    final currentFraction = _rotationTurns - _rotationTurns.floorToDouble();
    var delta = newTurnsRaw - currentFraction;
    delta -= delta.roundToDouble();
    _rotationTurns += delta;
  }

  Future<void> _updateScreenLocation() async {
    final controller = widget.mapController;
    if (controller == null) return;
    try {
      final s = await controller.toScreenLocation(widget.position);
      if (!mounted) return;
      final x = s.x.toDouble();
      final y = s.y.toDouble();
      if (x.isFinite && y.isFinite) {
        setState(() => _screen = s);
      }
    } catch (_) {
    }
  }

  @override
  Widget build(BuildContext context) {
    const markerSize = 52.0;
    final screenSize = MediaQuery.of(context).size;

    double left;
    double top;
    if (widget.followsCamera) {
      left = screenSize.width / 2 - markerSize / 2;
      top = screenSize.height / 2 - markerSize / 2;
    } else {
      final s = _screen;
      left = s != null
          ? s.x.toDouble() - markerSize / 2
          : screenSize.width / 2 - markerSize / 2;
      top = s != null
          ? s.y.toDouble() - markerSize / 2
          : screenSize.height / 2 - markerSize / 2;
    }
    return Positioned(
      left: left,
      top: top,
      child: IgnorePointer(
        child: AnimatedRotation(
          turns: _rotationTurns,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
          child: widget.vehicle == VehicleType.arrow
              ? Image.asset(
                  'assets/images/nav_arrow.png',
                  width: markerSize,
                  height: markerSize,
                  fit: BoxFit.contain,
                )
              : const _CarIcon(),
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
