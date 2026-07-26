import 'dart:async';
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

  final _latFilter = _Kalman1D(processNoisePerSecond: 20);
  final _lngFilter = _Kalman1D(processNoisePerSecond: 20);
  final _speedFilter = _Kalman1D(processNoisePerSecond: 0.8, minMeasurementAccuracy: 2.0);
  double? _lastRawSpeedMs;
  int? _lastRawSpeedTsMs;

  double? _smoothHeading;

  static const double _headingAlpha = 0.25;
  static const double _headingFreezeSpeedKmh = 2.0;

  Stream<VehiclePosition> get stream => _controller.stream;

  void start() {
    const settings = LocationSettings(
      accuracy: LocationAccuracy.bestForNavigation,
      distanceFilter: 1,
    );
    _latFilter.reset();
    _lngFilter.reset();
    _speedFilter.reset();
    _smoothHeading = null;
    _accelBaseline = 0;
    _accelJerk = 0;
    _sub = Geolocator.getPositionStream(locationSettings: settings).listen(_onPosition);
    _accelSub = userAccelerometerEventStream(
      samplingPeriod: SensorInterval.gameInterval,
    ).listen(_onAccel, onError: (_) {
    });
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

    final filteredLat = _latFilter.process(p.latitude, posAccuracy, tsMs);
    final filteredLng = _lngFilter.process(p.longitude, posAccuracy, tsMs);

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
      _smoothHeading = _lerpAngle(_smoothHeading, p.heading, _headingAlpha);
    } else {
      _smoothHeading ??= (p.heading >= 0 && p.heading.isFinite) ? p.heading : 0;
    }

    final accuracyM = math.sqrt(
      _latFilter.uncertainty * _latFilter.uncertainty + _lngFilter.uncertainty * _lngFilter.uncertainty,
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
