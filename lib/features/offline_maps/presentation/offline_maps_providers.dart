import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../data/offline_maps_service.dart';
import '../data/graphhopper_download_service.dart';

final offlineMapsServiceProvider = Provider<OfflineMapsService>((ref) {
  return OfflineMapsService();
});

final graphHopperDownloadServiceProvider = Provider<GraphHopperDownloadService>((ref) {
  return GraphHopperDownloadService();
});

final selectedMapQualityProvider = StateProvider<MapQuality>((ref) {
  return MapQuality.standard;
});

final offlineRegionsProvider = FutureProvider.autoDispose<List<OfflineRegion>>((ref) async {
  final service = ref.watch(offlineMapsServiceProvider);
  return service.listRegions();
});

// Refresh providers after download/delete operations
final graphDownloadRefreshProvider = StateProvider<int>((ref) => 0);

final downloadedGraphIdsRefreshProvider = FutureProvider.autoDispose<Set<String>>((ref) async {
  // Watch the refresh trigger
  ref.watch(graphDownloadRefreshProvider);
  final service = ref.watch(graphHopperDownloadServiceProvider);
  return service.listDownloadedGraphs();
});

final downloadedGraphIdsProvider = FutureProvider.autoDispose<Set<String>>((ref) async {
  final service = ref.watch(graphHopperDownloadServiceProvider);
  return service.listDownloadedGraphs();
});
