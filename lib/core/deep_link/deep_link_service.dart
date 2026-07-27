import 'dart:async';
import 'package:app_links/app_links.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class DeepLinkDestination {
  final double lat;
  final double lng;
  final String? label;

  const DeepLinkDestination({required this.lat, required this.lng, this.label});
}

class DeepLinkService {
  final _appLinks = AppLinks();
  StreamSubscription<Uri>? _sub;
  final _controller = StreamController<DeepLinkDestination>.broadcast();

  Stream<DeepLinkDestination> get destinations => _controller.stream;

  Future<void> init() async {
    final initial = await _appLinks.getInitialLink();
    if (initial != null) _handle(initial);

    _sub = _appLinks.uriLinkStream.listen(_handle);
  }

  void _handle(Uri uri) {
    if (uri.scheme != 'abtin' || uri.host != 'navigate') return;
    final lat = double.tryParse(uri.queryParameters['lat'] ?? '');
    final lng = double.tryParse(uri.queryParameters['lng'] ?? '');
    if (lat == null || lng == null) return;
    _controller.add(DeepLinkDestination(
      lat: lat,
      lng: lng,
      label: uri.queryParameters['label'],
    ));
  }

  void dispose() {
    _sub?.cancel();
    _controller.close();
  }
}

final deepLinkServiceProvider = Provider<DeepLinkService>((ref) {
  final service = DeepLinkService();
  service.init();
  ref.onDispose(service.dispose);
  return service;
});

final deepLinkDestinationProvider = StreamProvider<DeepLinkDestination>((ref) {
  return ref.watch(deepLinkServiceProvider).destinations;
});
