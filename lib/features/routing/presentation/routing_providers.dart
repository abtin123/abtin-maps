import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../data/routing_service.dart';
import '../data/offline_graph_store.dart';
import '../data/offline_routing_service.dart';
import '../../map/presentation/destination_provider.dart';
import '../../gps/presentation/gps_providers.dart';

final routingServiceProvider = Provider<RoutingService>((ref) {
  return RoutingService();
});

final offlineGraphStoreProvider = Provider<OfflineGraphStore>((ref) {
  return OfflineGraphStore();
});

final offlineRoutingServiceProvider = Provider<OfflineRoutingService>((ref) {
  return OfflineRoutingService();
});

enum NavigationState {
  idle,
  calculating,
  navigating,
  error,
}

class ActiveNavigation {
  final RouteInfo route;
  final NavigationState state;
  final int currentInstructionIndex;
  final double remainingDistanceKm;
  final double distanceToNextManeuverM;
  final String? errorMessage;

  const ActiveNavigation({
    required this.route,
    this.state = NavigationState.navigating,
    this.currentInstructionIndex = 0,
    required this.remainingDistanceKm,
    this.distanceToNextManeuverM = 0,
    this.errorMessage,
  });

  ActiveNavigation copyWith({
    RouteInfo? route,
    NavigationState? state,
    int? currentInstructionIndex,
    double? remainingDistanceKm,
    double? distanceToNextManeuverM,
    String? errorMessage,
  }) {
    return ActiveNavigation(
      route: route ?? this.route,
      state: state ?? this.state,
      currentInstructionIndex: currentInstructionIndex ?? this.currentInstructionIndex,
      remainingDistanceKm: remainingDistanceKm ?? this.remainingDistanceKm,
      distanceToNextManeuverM: distanceToNextManeuverM ?? this.distanceToNextManeuverM,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }

  RouteInstruction get currentInstruction {
    if (currentInstructionIndex < route.instructions.length) {
      return route.instructions[currentInstructionIndex];
    }
    return route.instructions.last;
  }

  bool get hasArrived => currentInstructionIndex >= route.instructions.length - 1;
}

class ActiveNavigationNotifier extends StateNotifier<ActiveNavigation?> {
  ActiveNavigationNotifier() : super(null);

  void setNavigation(ActiveNavigation nav) {
    state = nav;
  }

  void updateProgress(int instructionIndex, double remainingDistance,
      {double? distanceToNextManeuverM}) {
    if (state != null) {
      state = state!.copyWith(
        currentInstructionIndex: instructionIndex,
        remainingDistanceKm: remainingDistance,
        distanceToNextManeuverM: distanceToNextManeuverM,
      );
    }
  }

  void clear() {
    state = null;
  }
}

final activeNavigationProvider = StateNotifierProvider<ActiveNavigationNotifier, ActiveNavigation?>((ref) {
  return ActiveNavigationNotifier();
});

final calculateRouteProvider = FutureProvider.autoDispose<RouteInfo?>((ref) async {
  final destination = ref.watch(selectedDestinationProvider);
  final vehiclePosition = ref.watch(vehiclePositionProvider).value;
  
  if (destination == null || vehiclePosition == null) {
    return null;
  }

  final routingService = ref.read(routingServiceProvider);
  
  return await routingService.calculateRoute(
    origin: LatLng(vehiclePosition.lat, vehiclePosition.lng),
    destination: destination.point,
  );
});
