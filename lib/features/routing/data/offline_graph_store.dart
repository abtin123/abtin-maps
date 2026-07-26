import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'package:http/http.dart' as http;
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:path_provider/path_provider.dart';
import '../../offline_maps/data/iran_provinces.dart';
import 'road_graph.dart';
import 'road_graph_builder.dart';

class OfflineGraphStore {
  static const List<String> _overpassMirrors = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.openstreetmap.ru/api/interpreter',
  ];

  static const double _initialCellSizeDeg = 0.3;
  static const double _minCellSizeDeg = 0.02;
  static const int _maxSplitDepth = 4;

  final Map<String, RoadGraph> _cache = {};

  final Map<String, Completer<void>?> _pauseGates = {};

  bool isPaused(String provinceId) => _pauseGates[provinceId] != null;

  void pauseProvinceDownload(String provinceId) {
    _pauseGates.putIfAbsent(provinceId, () => Completer<void>());
  }

  void resumeProvinceDownload(String provinceId) {
    _pauseGates.remove(provinceId)?.complete();
  }

  Future<void> _waitIfPaused(String provinceId) async {
    final gate = _pauseGates[provinceId];
    if (gate != null) await gate.future;
  }

  Future<Directory> _graphsDir() async {
    final base = await getApplicationDocumentsDirectory();
    final dir = Directory('${base.path}/routing_graphs');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  Future<File> _fileFor(String provinceId) async {
    final dir = await _graphsDir();
    return File('${dir.path}/$provinceId.aog');
  }

  Future<bool> isDownloaded(String provinceId) async {
    final f = await _fileFor(provinceId);
    return f.exists();
  }

  Future<void> downloadProvince(
    Province province, {
    void Function(double progress)? onProgress,
  }) async {
    onProgress?.call(0);
    final b = province.bounds;
    final cells = _splitIntoCells(b, _initialCellSizeDeg);

    final merged = <String, Map<String, dynamic>>{};
    var completed = 0;
    Object? firstError;

    for (final cell in cells) {
      await _waitIfPaused(province.id);
      try {
        await _downloadCellRecursive(cell, merged, depth: 0);
      } catch (e) {
        firstError ??= e;
      }
      completed++;
      onProgress?.call(completed / cells.length);
    }

    _pauseGates.remove(province.id);

    if (merged.isEmpty) {
      throw Exception(
        firstError != null
            ? 'دانلود گراف ناموفق بود: $firstError'
            : 'دانلود گراف ناموفق بود: هیچ داده‌ای از Overpass دریافت نشد.',
      );
    }

    final graph = RoadGraphBuilder.build({'elements': merged.values.toList()});

    final file = await _fileFor(province.id);
    await file.writeAsBytes(graph.encode(), flush: true);
    _cache[province.id] = graph;
    onProgress?.call(1);
  }

  Future<void> _downloadCellRecursive(
    LatLngBounds cell,
    Map<String, Map<String, dynamic>> sink, {
    required int depth,
  }) async {
    try {
      final json = await _queryCellWithRetry(cell);
      final elements = (json['elements'] as List?) ?? const [];
      for (final el in elements) {
        final map = el as Map<String, dynamic>;
        final key = '${map['type']}_${map['id']}';
        sink[key] = map;
      }
    } catch (e) {
      final latSpan = cell.northeast.latitude - cell.southwest.latitude;
      final lngSpan = cell.northeast.longitude - cell.southwest.longitude;
      final tooSmall = latSpan <= _minCellSizeDeg || lngSpan <= _minCellSizeDeg;
      if (depth >= _maxSplitDepth || tooSmall) {
        rethrow;
      }
      for (final quadrant in _splitInFour(cell)) {
        await _downloadCellRecursive(quadrant, sink, depth: depth + 1);
      }
    }
  }

  Future<Map<String, dynamic>> _queryCellWithRetry(LatLngBounds cell) async {
    final query = RoadGraphBuilder.overpassQuery(
      south: cell.southwest.latitude,
      west: cell.southwest.longitude,
      north: cell.northeast.latitude,
      east: cell.northeast.longitude,
      timeoutSec: 55,
    );

    Object lastError = Exception('اتصال به سرورهای Overpass ممکن نشد');

    for (final mirror in _overpassMirrors) {
      for (var attempt = 0; attempt < 2; attempt++) {
        try {
          final response = await http
              .post(
                Uri.parse(mirror),
                headers: const {
                  'Accept': 'application/json',
                  'User-Agent': 'AbtinGpsNavigator/1.0 (offline-routing-graph)',
                  'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: {'data': query},
              )
              .timeout(const Duration(seconds: 65));

          if (response.statusCode == 200) {
            return jsonDecode(response.body) as Map<String, dynamic>;
          }

          final snippet = response.body.length > 150
              ? response.body.substring(0, 150)
              : response.body;
          lastError = Exception('HTTP ${response.statusCode} — $snippet');

          final retryable = response.statusCode == 429 ||
              (response.statusCode >= 500 && response.statusCode < 600);
          if (!retryable) break;
        } catch (e) {
          lastError = e;
        }
        await Future.delayed(Duration(seconds: 2 + attempt * 3));
      }
    }

    throw lastError;
  }

  List<LatLngBounds> _splitIntoCells(LatLngBounds b, double cellSizeDeg) {
    final cells = <LatLngBounds>[];
    var lat = b.southwest.latitude;
    while (lat < b.northeast.latitude) {
      final latEnd = math.min(lat + cellSizeDeg, b.northeast.latitude);
      var lng = b.southwest.longitude;
      while (lng < b.northeast.longitude) {
        final lngEnd = math.min(lng + cellSizeDeg, b.northeast.longitude);
        cells.add(LatLngBounds(
          southwest: LatLng(lat, lng),
          northeast: LatLng(latEnd, lngEnd),
        ));
        lng = lngEnd;
      }
      lat = latEnd;
    }
    return cells;
  }

  List<LatLngBounds> _splitInFour(LatLngBounds b) {
    final midLat = (b.southwest.latitude + b.northeast.latitude) / 2;
    final midLng = (b.southwest.longitude + b.northeast.longitude) / 2;
    return [
      LatLngBounds(
        southwest: LatLng(b.southwest.latitude, b.southwest.longitude),
        northeast: LatLng(midLat, midLng),
      ),
      LatLngBounds(
        southwest: LatLng(b.southwest.latitude, midLng),
        northeast: LatLng(midLat, b.northeast.longitude),
      ),
      LatLngBounds(
        southwest: LatLng(midLat, b.southwest.longitude),
        northeast: LatLng(b.northeast.latitude, midLng),
      ),
      LatLngBounds(
        southwest: LatLng(midLat, midLng),
        northeast: LatLng(b.northeast.latitude, b.northeast.longitude),
      ),
    ];
  }

  Future<RoadGraph?> loadProvince(String provinceId) async {
    final cached = _cache[provinceId];
    if (cached != null) return cached;

    final file = await _fileFor(provinceId);
    if (!await file.exists()) return null;

    final bytes = await file.readAsBytes();
    final graph = RoadGraph.decode(bytes);
    _cache[provinceId] = graph;
    return graph;
  }

  Province? provinceContaining(double lat, double lng) {
    for (final p in kIranProvinces) {
      final b = p.bounds;
      if (lat >= b.southwest.latitude &&
          lat <= b.northeast.latitude &&
          lng >= b.southwest.longitude &&
          lng <= b.northeast.longitude) {
        return p;
      }
    }
    return null;
  }

  Future<void> deleteProvince(String provinceId) async {
    _cache.remove(provinceId);
    final f = await _fileFor(provinceId);
    if (await f.exists()) await f.delete();
  }
}
