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

  int _estimatedIntervalMs = 1000;

  final _controller = StreamController<VehiclePosition>.broadcast();
  Timer? _ticker;

  Stream<VehiclePosition> get stream => _controller.stream;

  void onRawFix(VehiclePosition pos) {
    final now = DateTime.now();

    if (_curr != null) {
      final gapMs = now.difference(_curr!.receivedAt).inMilliseconds;
      if (gapMs > 100 && gapMs < 8000) {
        _estimatedIntervalMs = ((_estimatedIntervalMs * 0.5) + (gapMs * 0.5)).round();
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
    final intervalMs = _estimatedIntervalMs.clamp(300, 3000);

    double lat;
    double lng;
    double heading;

    final prev = _prev;
    if (prev == null) {
      lat = curr.lat;
      lng = curr.lng;
      heading = curr.headingDeg;
    } else if (elapsedMs < intervalMs) {
      final t = (elapsedMs / intervalMs).clamp(0.0, 1.0);
      lat = _lerp(prev.lat, curr.lat, t);
      lng = _lerp(prev.lng, curr.lng, t);
      heading = _lerpAngle(prev.headingDeg, curr.headingDeg, t);
    } else {
      // next fix is late — keep moving using the last known speed/heading
      // instead of freezing, capped so a long GPS gap doesn't cause drift
      final extraMs = math.min(elapsedMs - intervalMs, 2000);
      final metersPerSecond = curr.speedKmh / 3.6;
      final distanceM = metersPerSecond * (extraMs / 1000.0);
      final headingRad = curr.headingDeg * math.pi / 180;
      final dLat = (distanceM * math.cos(headingRad)) / 111320.0;
      final dLng = (distanceM * math.sin(headingRad)) /
          (111320.0 * math.cos(curr.lat * math.pi / 180));
      lat = curr.lat + dLat;
      lng = curr.lng + dLng;
      heading = curr.headingDeg;
    }

    _controller.add(VehiclePosition(
      lat: lat,
      lng: lng,
      headingDeg: heading,
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
