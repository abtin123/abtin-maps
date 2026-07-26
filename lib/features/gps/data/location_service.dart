import 'dart:async';
import 'dart:io' show Platform;
import 'dart:math' as math;
import 'package:geolocator/geolocator.dart';
import 'package:sensors_plus/sensors_plus.dart';

class VehiclePosition {
  final double lat;
  final double lng;
  final double headingDeg;
  final double speedKmh;
  final double accuracyM;

  const VehiclePosition({
    required this.lat,
    required this.lng,
    required this.headingDeg,
    required this.speedKmh,
    required this.accuracyM,
  });
}

class _Kalman1D {
  double? _value;
  double _variance = -1;
  int? _lastTimestampMs;

  final double processNoisePerSecond;

  final double minMeasurementAccuracy;

  _Kalman1D({required this.processNoisePerSecond, this.minMeasurementAccuracy = 1.0});

  double get value => _value ?? 0;
  double get uncertainty => _variance < 0 ? 0 : math.sqrt(_variance);

  void reset() {
    _value = null;
    _variance = -1;
    _lastTimestampMs = null;
  }

  /// Shifts the filter's internal estimate to a new coordinate origin
  /// without touching its variance/timestamp — used when we re-center the
  /// local tangent-plane reference point so long trips don't lose precision.
  void rebase(double newValue) {
    _value = newValue;
  }

  double process(
    double measurement,
    double measurementAccuracy,
    int timestampMs, {
    double extraProcessNoise = 0,
  }) {
    final acc = math.max(measurementAccuracy, minMeasurementAccuracy);
    final measurementVariance = acc * acc;

    if (_value == null || _variance < 0) {
      _value = measurement;
      _variance = measurementVariance;
      _lastTimestampMs = timestampMs;
      return _value!;
    }

    final dtSec = math.max((timestampMs - (_lastTimestampMs ?? timestampMs)) / 1000.0, 0.0);
    _lastTimestampMs = timestampMs;

    if (dtSec > 0) {
      final totalNoise = processNoisePerSecond + extraProcessNoise;
      _variance += dtSec * totalNoise * totalNoise;
    }

    final kalmanGain = _variance / (_variance + measurementVariance);
    _value = _value! + kalmanGain * (measurement - _value!);
    _variance = (1 - kalmanGain) * _variance;
    return _value!;
  }
}

class LocationService {
  final _controller = StreamController<VehiclePosition>.broadcast();
  StreamSubscription<Position>? _sub;
  StreamSubscription<UserAccelerometerEvent>? _accelSub;

  double _accelBaseline = 0;
  double _accelJerk = 0;

  // --- Position filter -----------------------------------------------
  // Fixed before: lat/lng were fed straight into the Kalman filters in
  // *degrees*, while their accuracy (from the GPS) is in *meters* — those
  // two numbers differ by ~5 orders of magnitude, so the filter's variance
  // bookkeeping was meaningless and it ended up over-damping real movement
  // (most noticeable exactly where you'd notice it: mid-turn). We now
  // project lat/lng onto a local flat x/y plane (in meters) around a
  // reference point, run the filter there — where the measurement
  // accuracy and the filtered value share the same unit — and project
  // back. The reference is re-centered every ~5 km so the flat-earth
  // approximation never drifts on long trips.
  static const double _metersPerDegLat = 111320.0;
  static const double _rebaseThresholdM = 5000.0;

  double? _refLat;
  double? _refLng;

  final _xFilter = _Kalman1D(processNoisePerSecond: 8.0);
  final _yFilter = _Kalman1D(processNoisePerSecond: 8.0);
  final _speedFilter = _Kalman1D(processNoisePerSecond: 0.8, minMeasurementAccuracy: 2.0);

  double? _smoothHeading;
  int? _lastHeadingTsMs;

  // Time-constant based smoothing (instead of a flat per-fix alpha) so the
  // heading catches up to a real turn within a fixed amount of *time*
  // regardless of how often fixes happen to arrive.
  static const double _headingTimeConstantSec = 0.5;
  static const double _headingFreezeSpeedKmh = 2.0;

  Stream<VehiclePosition> get stream => _controller.stream;

  void start() {
    final settings = _buildLocationSettings();
    _refLat = null;
    _refLng = null;
    _xFilter.reset();
    _yFilter.reset();
    _speedFilter.reset();
    _smoothHeading = null;
    _lastHeadingTsMs = null;
    _accelBaseline = 0;
    _accelJerk = 0;
    _sub = Geolocator.getPositionStream(locationSettings: settings).listen(_onPosition);
    _accelSub = userAccelerometerEventStream(
      samplingPeriod: SensorInterval.gameInterval,
    ).listen(_onAccel, onError: (_) {
    });
  }

  /// Real GPS chips report fixes at 1–10 Hz at best — nothing updates
  /// "every microsecond". What we *can* do is stop the OS from throttling
  /// updates to distance-only delivery and ask for the fastest sane
  /// interval, then lean on [VehiclePositionAnimator] (already interpolating
  /// at 60fps) to make the motion between those fixes look continuous.
  LocationSettings _buildLocationSettings() {
    if (Platform.isAndroid) {
      return AndroidSettings(
        accuracy: LocationAccuracy.bestForNavigation,
        distanceFilter: 0,
        intervalDuration: const Duration(milliseconds: 500),
      );
    }
    if (Platform.isIOS || Platform.isMacOS) {
      return AppleSettings(
        accuracy: LocationAccuracy.bestForNavigation,
        activityType: ActivityType.automotiveNavigation,
        distanceFilter: 0,
        pauseLocationUpdatesAutomatically: false,
      );
    }
    return const LocationSettings(
      accuracy: LocationAccuracy.bestForNavigation,
      distanceFilter: 0,
    );
  }

  void _onAccel(UserAccelerometerEvent e) {
    final mag = math.sqrt(e.x * e.x + e.y * e.y + e.z * e.z);
    _accelBaseline += (mag - _accelBaseline) * 0.01;
    final instantJerk = (mag - _accelBaseline).abs();
    _accelJerk += (instantJerk - _accelJerk) * 0.25;
  }

  void _onPosition(Position p) {
    final tsMs = p.timestamp.millisecondsSinceEpoch;
    final posAccuracy = p.accuracy.isFinite && p.accuracy > 0 ? p.accuracy : 15.0;

    _refLat ??= p.latitude;
    _refLng ??= p.longitude;
    final metersPerDegLng = _metersPerDegLat * math.cos(degToRad(_refLat!));

    final xMeasurement = (p.longitude - _refLng!) * metersPerDegLng;
    final yMeasurement = (p.latitude - _refLat!) * _metersPerDegLat;

    final filteredX = _xFilter.process(xMeasurement, posAccuracy, tsMs);
    final filteredY = _yFilter.process(yMeasurement, posAccuracy, tsMs);

    var filteredLat = _refLat! + filteredY / _metersPerDegLat;
    var filteredLng = _refLng! + filteredX / metersPerDegLng;

    if (filteredX.abs() > _rebaseThresholdM || filteredY.abs() > _rebaseThresholdM) {
      _refLat = filteredLat;
      _refLng = filteredLng;
      _xFilter.rebase(0);
      _yFilter.rebase(0);
    }

    final rawSpeedMs = p.speed.isFinite && p.speed >= 0 ? p.speed : 0.0;
    final speedAccuracy = p.speedAccuracy.isFinite && p.speedAccuracy > 0 ? p.speedAccuracy : 1.5;

    final accelExtraNoise = math.min(_accelJerk * 2.5, 6.0);

    final adaptiveNoise = (_accelJerk > 1.5) ? 2.2 : 0.0;

    final filteredSpeedMs = _speedFilter.process(
      rawSpeedMs,
      speedAccuracy,
      tsMs,
      extraProcessNoise: accelExtraNoise + adaptiveNoise,
    );
    final speedKmh = math.max(filteredSpeedMs, 0) * 3.6;

    if (speedKmh >= _headingFreezeSpeedKmh && p.heading >= 0 && p.heading.isFinite) {
      final dtSec = _lastHeadingTsMs == null
          ? 1.0
          : math.max((tsMs - _lastHeadingTsMs!) / 1000.0, 0.0);
      final alpha = 1 - math.exp(-dtSec / _headingTimeConstantSec);
      _smoothHeading = _lerpAngle(_smoothHeading, p.heading, alpha);
      _lastHeadingTsMs = tsMs;
    } else {
      _smoothHeading ??= (p.heading >= 0 && p.heading.isFinite) ? p.heading : 0;
    }

    final accuracyM = math.sqrt(
      _xFilter.uncertainty * _xFilter.uncertainty + _yFilter.uncertainty * _yFilter.uncertainty,
    );

    _controller.add(VehiclePosition(
      lat: filteredLat,
      lng: filteredLng,
      headingDeg: _smoothHeading!,
      speedKmh: speedKmh,
      accuracyM: accuracyM,
    ));
  }

  double _lerpAngle(double? current, double target, double alpha) {
    if (current == null) return target;
    var diff = (target - current + 540) % 360 - 180;
    return (current + diff * alpha + 360) % 360;
  }

  void dispose() {
    _sub?.cancel();
    _accelSub?.cancel();
    _controller.close();
  }
}

double degToRad(double deg) => deg * math.pi / 180;
