import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../data/offline_maps_service.dart';
import '../data/iran_provinces.dart';
import '../../routing/presentation/routing_providers.dart';

final offlineMapsServiceProvider = Provider<OfflineMapsService>((ref) {
  return OfflineMapsService();
});

final selectedMapQualityProvider =
    StateProvider<MapQuality>((ref) => MapQuality.standard);

final offlineRegionsProvider =
    FutureProvider.autoDispose<List<OfflineRegion>>((ref) async {
  return ref.watch(offlineMapsServiceProvider).listRegions();
});

final downloadedGraphsProvider =
    FutureProvider.autoDispose<List<String>>((ref) async {
  final graphStore = ref.watch(offlineGraphStoreProvider);
  final graphs = <String>[];
  for (final p in kIranProvinces) {
    final isDownloaded = await graphStore.isDownloaded(p.id);
    if (isDownloaded) graphs.add(p.id);
  }
  return graphs;
});
