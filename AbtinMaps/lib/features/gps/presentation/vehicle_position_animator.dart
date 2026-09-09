import 'dart:async';
import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/scheduler.dart';

import '../../../core/geo/geo_types.dart';

import '../data/location_service.dart';
import 'gps_providers.dart';

/// Turns discrete location fixes into one continuous visual stream.
///
/// There is deliberately only one speed integrator here.  A new GPS speed is
/// a TARGET, never a value that is assigned directly to the UI.  This prevents
/// 10 -> 40 -> 70 km/h jumps and, importantly, gives braking its own continuous
/// path all the way to zero.
class VehiclePositionAnimator {
  // GPS is an anchor/validator, never the animation clock. In navigation
  // the marker advances along the calculated route at 60fps; GPS only updates
  // speed targets and is validated by the navigation layer.
  static const double _maxAccelerationKmhPerSec = 18.0;
  static const double _maxBrakingKmhPerSec = 28.0;
  static const double _maxSpeedKmh = 240.0;

  // Positional correction is deliberately slow. A normal GNSS fix can move
  // several metres from one sample to the next even when the car is perfectly
  // stable. Applying it immediately is the source of the visible "jump".
  static const double _realCorrectionMps = 4.5;
  static const double _estimatedCorrectionMps = 1.5;
  static const double _maxCorrectionPerFixM = 12.0;

  double? _lat;
  double? _lng;
  double _headingDeg = 0;
  double _targetHeadingDeg = 0;
  double _renderedSpeedKmh = 0;
  double _targetSpeedKmh = 0;
  double _accuracyM = 50;

  // GPS correction expressed in local metres relative to the current
  // predicted position. It is consumed gradually by _tick().
  double _correctionEastM = 0;
  double _correctionNorthM = 0;
  bool _correctionIsEstimated = false;

  // When navigation is active the route is the visual track. GPS never moves
  // the marker; it only updates speed/heading targets and is validated by the
  // navigation layer for off-route/re-route decisions.
  List<({double lat, double lng})>? _routePoints;
  List<double>? _routeCumulativeM;
  double? _routeProgressM;
  bool _routeDriven = false;

  DateTime? _lastTick;
  DateTime? _lastFixAt;

  final _controller = StreamController<VehiclePosition>.broadcast();
  Ticker? _ticker;
  Duration? _lastTickerElapsed;
  bool _disposed = false;

  Stream<VehiclePosition> get stream => _controller.stream;

  bool get isRouteDriven => _routeDriven;

  /// Attach the currently active navigation route. The marker is then
  /// advanced by speed along this polyline at 60fps. GPS fixes do not pull it
  /// backwards; GPS is used only by the validator and as a bounded speed
  /// target, never as a position/progress command.
  void setRoute(List<LatLng> geometry, {VehiclePosition? anchor}) {
    if (_disposed || geometry.length < 2) {
      _routeDriven = false;
      _routePoints = null;
      _routeCumulativeM = null;
      _routeProgressM = null;
        return;
    }
    _routePoints = [
      for (final p in geometry) (lat: p.latitude, lng: p.longitude),
    ];
    _routeCumulativeM = _buildRouteCumulative(_routePoints!);
    _routeDriven = true;

    // Keep the currently rendered vehicle position as the visual anchor.
    // Never snap the marker/camera back to the newest GPS fix when a route is
    // attached or replaced. Only the route progress is anchored to the
    // current visual position; the first rendered frame therefore stays where
    // the driver already sees the car.
    final anchorLat = _lat ?? anchor?.lat;
    final anchorLng = _lng ?? anchor?.lng;
    if (anchorLat != null && anchorLng != null) {
      final nearest = _nearestRouteProgress(
        anchorLat,
        anchorLng,
        _routePoints!,
        _routeCumulativeM!,
      );
      if (nearest != null) {
        _routeProgressM = nearest;
        final sample = _sampleRoute(_routePoints!, _routeCumulativeM!, nearest);
        if (sample != null) {
          _targetHeadingDeg = sample.$3;
          if (_headingDeg.isNaN || !_headingDeg.isFinite) {
            _headingDeg = sample.$3;
          }
        }
      } else {
        _routeProgressM = 0;
      }
    } else {
        _routeProgressM = 0;
    }
    _correctionEastM = 0;
    _correctionNorthM = 0;
    _correctionIsEstimated = false;
    _lastTickerElapsed = null;
    _startTicker();
  }

  /// Immediately abandon route-driven animation and adopt a confirmed GPS
  /// position as the visual anchor. This is used the instant the driver takes
  /// a different road; keeping the old planned route as the animation clock
  /// would otherwise make the car continue around the planned turn while a
  /// reroute is being calculated.
  void adoptGpsAnchor(VehiclePosition pos) {
    if (_disposed || !pos.lat.isFinite || !pos.lng.isFinite) return;
    _routeDriven = false;
    _routePoints = null;
    _routeCumulativeM = null;
    _routeProgressM = null;
    _correctionEastM = 0;
    _correctionNorthM = 0;
    _correctionIsEstimated = false;
    _lat = pos.lat;
    _lng = pos.lng;
    // This is an exceptional off-route re-anchor, not a new animation clock.
    // Keep the existing rendered velocity and let the normal acceleration /
    // braking limiter converge to the GPS speed. Assigning the GPS speed to
    // _renderedSpeedKmh here caused a visible velocity jump exactly when a
    // reroute was requested.
    _targetSpeedKmh = _sanitizeSpeed(pos.speedKmh);
    _accuracyM = _safeAccuracy(pos.accuracyM);
    if (_validHeading(pos.headingDeg)) {
      _headingDeg = pos.headingDeg;
      _targetHeadingDeg = pos.headingDeg;
    }
    _lastFixAt = DateTime.now();
    _lastTick = DateTime.now();
    _lastTickerElapsed = null;
    _startTicker();
    _emit(VehiclePosition(
      lat: _lat!,
      lng: _lng!,
      headingDeg: _headingDeg,
      speedKmh: _renderedSpeedKmh,
      accuracyM: _accuracyM,
      isEstimated: pos.isEstimated,
    ));
  }

  void clearRoute() {
    _routeDriven = false;
    _routePoints = null;
    _routeCumulativeM = null;
    _routeProgressM = null;
    _correctionEastM = 0;
    _correctionNorthM = 0;
  }

  void onRawFix(VehiclePosition pos) {
    if (_disposed) return;
    final now = DateTime.now();

    final lat = pos.lat;
    final lng = pos.lng;
    if (!lat.isFinite || !lng.isFinite) return;

    if (_lat == null || _lng == null) {
      _lat = lat;
      _lng = lng;
      _headingDeg = _validHeading(pos.headingDeg) ? pos.headingDeg : 0;
      _targetHeadingDeg = _headingDeg;
      _targetSpeedKmh = _sanitizeSpeed(pos.speedKmh);
      _renderedSpeedKmh = pos.isEstimated ? 0 : _targetSpeedKmh;
      _accuracyM = _safeAccuracy(pos.accuracyM);
      _lastFixAt = now;
      _lastTick = now;
      _startTicker();
      return;
    }

    // GPS is a measurement of where we are, not an instruction to move the
    // marker there immediately. First update the velocity/heading targets.
    _targetSpeedKmh = _sanitizeSpeed(pos.speedKmh);
    if (_validHeading(pos.headingDeg)) {
      _targetHeadingDeg = pos.headingDeg;
    }
    _accuracyM = _safeAccuracy(pos.accuracyM);

    if (_routeDriven &&
        _routePoints != null &&
        _routeCumulativeM != null &&
        _routeProgressM != null &&
        !pos.isEstimated &&
        pos.accuracyM <= 35.0) {
      // GPS is not allowed to move or advance the marker. It is consumed by
      // the navigation validator, while the route clock below is integrated
      // from the smoothed vehicle speed. This prevents a noisy GPS sample
      // from selecting a different point on a parallel road or jumping across
      // a turn.
      final projected = _nearestRouteProgressNear(
        pos.lat,
        pos.lng,
        _routePoints!,
        _routeCumulativeM!,
        _routeProgressM!,
      );
      // Deliberately validation-only: do not copy projected into route
      // progress. The controller owns off-route decisions; the animator owns
      // continuous movement on the active route.
      if (projected == null) {
        _accuracyM = math.max(_accuracyM, pos.accuracyM);
      }
    }

    if (!_routeDriven) {
      // Outside navigation, keep the old gentle positional correction so the
      // normal map marker can converge to the latest GPS anchor.
      final eastNorth = _toLocalMeters(_lat!, _lng!, lat, lng);
      var east = eastNorth.$1;
      var north = eastNorth.$2;
      final error = math.sqrt(east * east + north * north);
      if (error < 0.75) {
        east = 0;
        north = 0;
      }
      final cap = pos.isEstimated
          ? _maxCorrectionPerFixM * 0.5
          : _maxCorrectionPerFixM;
      final scale = error > cap && error > 0 ? cap / error : 1.0;
      final newEast = east * scale;
      final newNorth = north * scale;
      final blend = pos.isEstimated ? 0.20 : 0.35;
      _correctionEastM = _correctionEastM * (1 - blend) + newEast * blend;
      _correctionNorthM = _correctionNorthM * (1 - blend) + newNorth * blend;
      _correctionIsEstimated = pos.isEstimated;
    } else {
      // Navigation mode: NEVER create a correction vector from GPS. A delayed
      // or noisy fix is allowed to differ from the rendered marker; the route
      // validator decides whether that difference means a reroute is needed.
      _correctionEastM = 0;
      _correctionNorthM = 0;
    }
    _lastFixAt = now;
    _startTicker();
  }

  void _startTicker() {
    final ticker = _ticker ??= Ticker((elapsed) => _tick(elapsed));
    if (!ticker.isActive) {
      _lastTickerElapsed = null;
      ticker.start();
    }
  }

  void _tick(Duration elapsed) {
    if (_disposed || _lat == null || _lng == null) return;
    final now = DateTime.now();
    final previousElapsed = _lastTickerElapsed ?? elapsed;
    final dt = ((elapsed - previousElapsed).inMicroseconds / 1e6).clamp(0.001, 0.050);
    _lastTickerElapsed = elapsed;

    // Speed is also a target. This keeps the visual velocity continuous even
    // when GNSS reports 13 -> 31 -> 18 km/h on successive fixes.
    final speedDelta = _targetSpeedKmh - _renderedSpeedKmh;
    final maxSpeedStep =
        (speedDelta >= 0 ? _maxAccelerationKmhPerSec : _maxBrakingKmhPerSec) * dt;
    if (speedDelta.abs() <= maxSpeedStep) {
      _renderedSpeedKmh = _targetSpeedKmh;
    } else {
      _renderedSpeedKmh += speedDelta.sign * maxSpeedStep;
    }

    if (_routeDriven && _routePoints != null && _routeCumulativeM != null && _routeProgressM != null) {
      final sample = _sampleRoute(_routePoints!, _routeCumulativeM!, _routeProgressM!);
      if (sample != null) _targetHeadingDeg = sample.$3;
    }

    // Heading follows the latest measurement continuously. At walking/very
    // low speed heading can be garbage, so retain the previous heading.
    final headingDiff = _shortAngle(_targetHeadingDeg - _headingDeg);
    final maxHeadingStep = (45.0 + _renderedSpeedKmh * 1.2) * dt;
    if (headingDiff.abs() <= maxHeadingStep) {
      _headingDeg = _targetHeadingDeg;
    } else {
      _headingDeg = (_headingDeg + headingDiff.sign * maxHeadingStep) % 360;
      if (_headingDeg < 0) _headingDeg += 360;
    }

    // The active route is the animation clock. We advance by the rendered
    // speed and sample the exact route polyline, so turns/roundabouts are
    // followed continuously instead of waiting for the next GPS fix.
    final distanceM = (_renderedSpeedKmh / 3.6) * dt;
    if (_routeDriven &&
        _routePoints != null &&
        _routeCumulativeM != null &&
        _routeProgressM != null) {
      final total = _routeCumulativeM!.last;
      _routeProgressM = math.min(total, _routeProgressM! + distanceM);

      final sample = _sampleRoute(
        _routePoints!,
        _routeCumulativeM!,
        _routeProgressM!,
      );
      if (sample != null) {
        _lat = sample.$1;
        _lng = sample.$2;
        _targetHeadingDeg = sample.$3;
      }
    } else {
      final move = _offsetFromHeading(_lat!, _lng!, _headingDeg, distanceM);
      _lat = move.$1;
      _lng = move.$2;

      final correctionSpeed = (_correctionIsEstimated
          ? _estimatedCorrectionMps
          : _realCorrectionMps);
      final correctionStep = correctionSpeed * dt;
      final correctionMagnitude = math.sqrt(
        _correctionEastM * _correctionEastM +
            _correctionNorthM * _correctionNorthM,
      );
      if (correctionMagnitude > 0.001) {
        final amount = math.min(correctionStep, correctionMagnitude);
        final ratio = amount / correctionMagnitude;
        final corrected = _offsetFromMeters(
          _lat!,
          _lng!,
          _correctionEastM * ratio,
          _correctionNorthM * ratio,
        );
        _lat = corrected.$1;
        _lng = corrected.$2;
        _correctionEastM -= _correctionEastM * ratio;
        _correctionNorthM -= _correctionNorthM * ratio;
      }
    }

    // During a prolonged GPS gap, gradually coast down instead of extrapolating
    // at the last reported speed forever. The route layer can continue to
    // project this smooth estimate onto the active route.
    final gap = _lastFixAt == null
        ? 0.0
        : now.difference(_lastFixAt!).inMilliseconds / 1000.0;
    if (gap > 2.5) {
      final coastTarget = math.max(0.0, _targetSpeedKmh - (gap - 2.5) * 8.0);
      if (_targetSpeedKmh > coastTarget) _targetSpeedKmh = coastTarget;
    }

    _emit(VehiclePosition(
      lat: _lat!,
      lng: _lng!,
      headingDeg: _headingDeg,
      speedKmh: _renderedSpeedKmh.clamp(0.0, _maxSpeedKmh).toDouble(),
      accuracyM: _accuracyM,
      // Every rendered frame is the predicted/route-driven visual state.
      // Raw GPS is consumed separately as the validation signal.
      isEstimated: true,
    ));
  }

  List<double> _buildRouteCumulative(List<({double lat, double lng})> points) {
    final cumulative = <double>[0];
    for (var i = 1; i < points.length; i++) {
      cumulative.add(cumulative.last + _distanceM(
            points[i - 1].lat,
            points[i - 1].lng,
            points[i].lat,
            points[i].lng,
          ));
    }
    return cumulative;
  }

  double? _nearestRouteProgress(
    double lat,
    double lng,
    List<({double lat, double lng})> points,
    List<double> cumulative,
  ) {
    var best = double.infinity;
    double? progress;
    for (var i = 0; i < points.length - 1; i++) {
      final a = points[i];
      final b = points[i + 1];
      final latRad = ((a.lat + b.lat) * 0.5) * math.pi / 180.0;
      final mx = 111320.0 * math.cos(latRad);
      final my = 110540.0;
      final ax = a.lng * mx, ay = a.lat * my;
      final bx = b.lng * mx, by = b.lat * my;
      final px = lng * mx, py = lat * my;
      final dx = bx - ax, dy = by - ay;
      final len2 = dx * dx + dy * dy;
      final t = len2 <= 1e-6 ? 0.0 : ((px - ax) * dx + (py - ay) * dy) / len2;
      final clamped = t.clamp(0.0, 1.0).toDouble();
      final qx = ax + dx * clamped, qy = ay + dy * clamped;
      final d = math.sqrt((px - qx) * (px - qx) + (py - qy) * (py - qy));
      if (d < best) {
        best = d;
        progress = cumulative[i] + math.sqrt(len2) * clamped;
      }
    }
    return progress;
  }

  double? _nearestRouteProgressNear(
    double lat,
    double lng,
    List<({double lat, double lng})> points,
    List<double> cumulative,
    double currentProgress,
  ) {
    if (points.length < 2) return null;
    const backWindowM = 35.0;
    const aheadWindowM = 300.0;
    final lo = math.max(0.0, currentProgress - backWindowM);
    final hi = math.min(cumulative.last, currentProgress + aheadWindowM);
    var start = 0;
    while (start < cumulative.length - 2 && cumulative[start + 1] < lo) {
      start++;
    }
    var end = start;
    while (end < points.length - 2 && cumulative[end] < hi) {
      end++;
    }

    final latRad = lat * math.pi / 180.0;
    final mx = 111320.0 * math.cos(latRad);
    const my = 110540.0;
    var bestDistance = double.infinity;
    double? bestProgress;
    for (var i = start; i <= end; i++) {
      final a = points[i];
      final b = points[i + 1];
      final ax = a.lng * mx, ay = a.lat * my;
      final bx = b.lng * mx, by = b.lat * my;
      final px = lng * mx, py = lat * my;
      final dx = bx - ax, dy = by - ay;
      final len2 = dx * dx + dy * dy;
      if (len2 <= 1e-6) continue;
      final t = (((px - ax) * dx + (py - ay) * dy) / len2)
          .clamp(0.0, 1.0)
          .toDouble();
      final qx = ax + dx * t, qy = ay + dy * t;
      final ex = px - qx, ey = py - qy;
      final distance = math.sqrt(ex * ex + ey * ey);
      final progress = cumulative[i] + math.sqrt(len2) * t;
      if (progress < lo - 1.0 || progress > hi + 1.0) continue;
      if (distance < bestDistance) {
        bestDistance = distance;
        bestProgress = progress;
      }
    }
    return bestDistance <= 35.0 ? bestProgress : null;
  }

  (double, double, double)? _sampleRoute(
    List<({double lat, double lng})> points,
    List<double> cumulative,
    double progress,
  ) {
    if (points.length < 2) return null;
    final target = progress.clamp(0.0, cumulative.last).toDouble();
    var i = 0;
    while (i < cumulative.length - 2 && cumulative[i + 1] < target) i++;
    final a = points[i], b = points[i + 1];
    final len = cumulative[i + 1] - cumulative[i];
    final t = len <= 0.001 ? 0.0 : ((target - cumulative[i]) / len).clamp(0.0, 1.0);
    final lat = a.lat + (b.lat - a.lat) * t;
    final lng = a.lng + (b.lng - a.lng) * t;

    // Use a short tangent around the current progress instead of the raw
    // segment bearing. This removes the visible heading snap when a route
    // polyline has sparse points at a bend and makes the car rotate into the
    // turn continuously rather than one segment at a time.
    final lookBack = math.max(0.0, target - 2.5);
    final lookAhead = math.min(cumulative.last, target + 7.0);
    final back = _pointAtProgress(points, cumulative, lookBack) ?? (lat: lat, lng: lng);
    final ahead = _pointAtProgress(points, cumulative, lookAhead) ?? (lat: b.lat, lng: b.lng);
    final heading = _bearingBetween(back.lat, back.lng, ahead.lat, ahead.lng);
    return (lat, lng, heading);
  }

  ({double lat, double lng})? _pointAtProgress(
    List<({double lat, double lng})> points,
    List<double> cumulative,
    double progress,
  ) {
    if (points.isEmpty || cumulative.isEmpty) return null;
    final target = progress.clamp(0.0, cumulative.last).toDouble();
    var i = 0;
    while (i < cumulative.length - 2 && cumulative[i + 1] < target) i++;
    final a = points[i];
    final b = points[i + 1];
    final len = cumulative[i + 1] - cumulative[i];
    final t = len <= 0.001
        ? 0.0
        : ((target - cumulative[i]) / len).clamp(0.0, 1.0).toDouble();
    return (
      lat: a.lat + (b.lat - a.lat) * t,
      lng: a.lng + (b.lng - a.lng) * t,
    );
  }

  double _bearingBetween(double lat1, double lng1, double lat2, double lng2) {
    final y = (lng2 - lng1) *
        math.cos((lat1 + lat2) * math.pi / 360.0);
    final x = lat2 - lat1;
    return (math.atan2(y, x) * 180.0 / math.pi + 360.0) % 360.0;
  }

  double _distanceM(double lat1, double lng1, double lat2, double lng2) {
    final latRad = ((lat1 + lat2) * 0.5) * math.pi / 180.0;
    final mx = 111320.0 * math.cos(latRad);
    const my = 110540.0;
    final dx = (lng2 - lng1) * mx;
    final dy = (lat2 - lat1) * my;
    return math.sqrt(dx * dx + dy * dy);
  }

  (double, double) _toLocalMeters(
      double fromLat, double fromLng, double toLat, double toLng) {
    final cosLat = math.cos(fromLat * math.pi / 180.0).abs().clamp(0.2, 1.0);
    final east = (toLng - fromLng) * 111320.0 * cosLat;
    final north = (toLat - fromLat) * 111320.0;
    return (east, north);
  }

  (double, double) _offsetFromHeading(
      double lat, double lng, double headingDeg, double meters) {
    final rad = headingDeg * math.pi / 180.0;
    return _offsetFromMeters(lat, lng, math.sin(rad) * meters, math.cos(rad) * meters);
  }

  (double, double) _offsetFromMeters(
      double lat, double lng, double eastM, double northM) {
    final dLat = northM / 111320.0;
    final cosLat = math.cos(lat * math.pi / 180.0).abs().clamp(0.2, 1.0);
    final dLng = eastM / (111320.0 * cosLat);
    return (lat + dLat, lng + dLng);
  }

  double _sanitizeSpeed(double value) {
    if (!value.isFinite) return 0;
    return value.clamp(0.0, _maxSpeedKmh).toDouble();
  }

  double _safeAccuracy(double value) {
    if (!value.isFinite || value <= 0) return 50;
    return value.clamp(1.0, 500.0).toDouble();
  }

  bool _validHeading(double value) => value.isFinite && value >= 0 && value < 360;

  double _shortAngle(double value) => (value + 540) % 360 - 180;

  void _emit(VehiclePosition value) {
    if (_disposed || _controller.isClosed) return;
    _controller.add(value);
  }

  void dispose() {
    if (_disposed) return;
    _disposed = true;
    _ticker?.stop();
    _ticker?.dispose();
    _ticker = null;
    _controller.close();
  }
}

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
