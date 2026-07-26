import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../../../core/permissions/location_permission_flow.dart';
import '../data/location_service.dart';
import 'last_location_providers.dart';

final locationServiceProvider = Provider<LocationService>((ref) {
  final service = LocationService();
  ref.onDispose(service.dispose);
  return service;
});

final locationLifecycleTickProvider = StateProvider<int>((ref) => 0);

final locationReadinessProvider = StreamProvider<LocationReadiness>((ref) async* {
  final locationService = ref.read(locationServiceProvider);
  bool serviceStarted = false;

  Future<LocationReadiness> reportAndMaybeStart(LocationReadiness r) async {
    if (r == LocationReadiness.ready && !serviceStarted) {
      serviceStarted = true;
      locationService.start();
    }
    return r;
  }

  yield await reportAndMaybeStart(await LocationPermissionFlow.ensureReady());

  final serviceStatusStream = Geolocator.getServiceStatusStream();

  final lifecycleStream = ref.watch(locationLifecycleTickProvider.notifier).stream;

  await for (final _ in _merge(serviceStatusStream, lifecycleStream)) {
    yield await reportAndMaybeStart(
      await LocationPermissionFlow.checkStatusAndRetryIfDenied(),
    );
  }
});

final retryLocationPermissionProvider = Provider<Future<void> Function()>((ref) {
  return () async {
    await LocationPermissionFlow.retryFromUserTap();
    ref.read(locationLifecycleTickProvider.notifier).state++;
  };
});

Stream<void> _merge(Stream<ServiceStatus> a, Stream<int> b) {
  final controller = StreamController<void>();
  final subA = a.listen((_) => controller.add(null));
  final subB = b.listen((_) => controller.add(null));
  controller.onCancel = () {
    subA.cancel();
    subB.cancel();
  };
  return controller.stream;
}

final vehiclePositionProvider = StreamProvider<VehiclePosition>((ref) {
  ref.watch(locationReadinessProvider);
  final stream = ref.watch(locationServiceProvider).stream;

  DateTime lastSaved = DateTime.fromMillisecondsSinceEpoch(0);
  final repo = ref.read(lastLocationRepositoryProvider);
  final broadcast = stream.asBroadcastStream();
  broadcast.listen((pos) {
    final now = DateTime.now();
    if (now.difference(lastSaved) >= const Duration(seconds: 5)) {
      lastSaved = now;
      repo.save(
        lat: pos.lat,
        lng: pos.lng,
        heading: pos.headingDeg,
        speedKmh: pos.speedKmh,
        accuracy: pos.accuracyM,
      );
    }
  });

  return broadcast;
});

final lastKnownLocationFromDbProvider = FutureProvider((ref) async {
  return ref.watch(lastLocationRepositoryProvider).getLast();
});
