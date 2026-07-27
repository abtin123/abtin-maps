import 'dart:async';
import 'dart:math' as math;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/location_service.dart';
import 'gps_providers.dart';

class _Fix {
  final double lat;
  final double lng;
  final double headingDeg;
  final double speedKmh;
  final double accuracyM;
  final DateTime receivedAt;

  _Fix({
    required this.lat,
    required this.lng,
    required this.headingDeg,
    required this.speedKmh,
    required this.accuracyM,
    required this.receivedAt,
  });
}

/// Takes the raw, discrete GPS fixes (which normally arrive roughly once
/// every 1-2 seconds) and turns them into a continuous ~60fps stream by
/// interpolating between the last two fixes, and — if the next fix is late
/// — extrapolating forward from the last known speed/heading (dead
/// reckoning) so the vehicle never visibly stops or jumps.
class VehiclePositionAnimator {
  _Fix? _prev;
  _Fix? _curr;
  
  // Smooth interpolated state
  double? _sLat;
  double? _sLng;
  double? _sHeading;

  int _estimatedIntervalMs = 1000;
  final _controller = StreamController<VehiclePosition>.broadcast();
  Timer? _ticker;

  Stream<VehiclePosition> get stream => _controller.stream;

  void onRawFix(VehiclePosition pos) {
    final now = DateTime.now();

    if (_curr != null) {
      final gapMs = now.difference(_curr!.receivedAt).inMilliseconds;
      if (gapMs > 100 && gapMs < 5000) {
        _estimatedIntervalMs = ((_estimatedIntervalMs * 0.7) + (gapMs * 0.3)).round();
      }
    }

    _prev = _curr;
    _curr = _Fix(
      lat: pos.lat,
      lng: pos.lng,
      headingDeg: pos.headingDeg,
      speedKmh: pos.speedKmh,
      accuracyM: pos.accuracyM,
      receivedAt: now,
    );

    _ticker ??= Timer.periodic(const Duration(milliseconds: 16), (_) => _tick());
  }

  void _tick() {
    final curr = _curr;
    if (curr == null) return;

    final now = DateTime.now();
    final elapsedMs = now.difference(curr.receivedAt).inMilliseconds;
    final intervalMs = _estimatedIntervalMs.clamp(500, 3000);

    double targetLat;
    double targetLng;
    double targetHeading;

    final prev = _prev;
    if (prev == null) {
      targetLat = curr.lat;
      targetLng = curr.lng;
      targetHeading = curr.headingDeg;
    } else if (elapsedMs < intervalMs) {
      // Linear interpolation between fixes
      final t = (elapsedMs / intervalMs).clamp(0.0, 1.0);
      targetLat = _lerp(prev.lat, curr.lat, t);
      targetLng = _lerp(prev.lng, curr.lng, t);
      targetHeading = _lerpAngle(prev.headingDeg, curr.headingDeg, t);
    } else {
      // Extrapolation (Dead Reckoning)
      final extraMs = math.min(elapsedMs - intervalMs, 2000);
      final metersPerSecond = curr.speedKmh / 3.6;
      final distanceM = metersPerSecond * (extraMs / 1000.0);
      final headingRad = curr.headingDeg * math.pi / 180;
      final dLat = (distanceM * math.cos(headingRad)) / 111320.0;
      final dLng = (distanceM * math.sin(headingRad)) /
          (111320.0 * math.cos(curr.lat * math.pi / 180));
      targetLat = curr.lat + dLat;
      targetLng = curr.lng + dLng;
      targetHeading = curr.headingDeg;
    }

    // Apply secondary smoothing (Exponential Smoothing) 
    // This is what Google Maps uses to remove micro-stutters.
    const double smoothingFactor = 0.12; // 0.1 to 0.2 is the sweet spot
    
    _sLat = _sLat == null ? targetLat : _lerp(_sLat!, targetLat, smoothingFactor);
    _sLng = _sLng == null ? targetLng : _lerp(_sLng!, targetLng, smoothingFactor);
    _sHeading = _sHeading == null ? targetHeading : _lerpAngle(_sHeading!, targetHeading, 0.1);

    _controller.add(VehiclePosition(
      lat: _sLat!,
      lng: _sLng!,
      headingDeg: _sHeading!,
      speedKmh: curr.speedKmh,
      accuracyM: curr.accuracyM,
    ));
  }

  double _lerp(double a, double b, double t) => a + (b - a) * t;

  double _lerpAngle(double a, double b, double t) {
    final diff = (b - a + 540) % 360 - 180;
    return (a + diff * t + 360) % 360;
  }

  void dispose() {
    _ticker?.cancel();
    _controller.close();
  }
}

/// Smooth, ~60fps version of [vehiclePositionProvider] — use this for
/// anything visual (camera, vehicle marker, speedometer, compass). Keep
/// using [vehiclePositionProvider] directly only for one-shot reads (e.g.
/// "where am I right now" when starting a route) where animation doesn't
/// matter.
final animatedVehiclePositionProvider = StreamProvider<VehiclePosition>((ref) {
  final animator = VehiclePositionAnimator();
  ref.onDispose(animator.dispose);

  final sub = ref.watch(vehiclePositionProvider.stream).listen(
        animator.onRawFix,
        onError: (_, __) {},
      );
  ref.onDispose(sub.cancel);

  return animator.stream;
});
