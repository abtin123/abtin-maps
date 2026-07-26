import 'dart:async';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'iran_provinces.dart';

enum MapQuality { smallest, standard, detailed }

extension MapQualityInfo on MapQuality {
  String get label {
    switch (this) {
      case MapQuality.smallest:
        return 'کم‌حجم‌ترین';
      case MapQuality.standard:
        return 'استاندارد';
      case MapQuality.detailed:
        return 'پرجزئیات';
    }
  }

  String get desc {
    switch (this) {
      case MapQuality.smallest:
        return 'فقط جاده‌های اصلی — کمترین فضا';
      case MapQuality.standard:
        return 'مناسب برای اکثر مسیریابی‌ها';
      case MapQuality.detailed:
        return 'تمام خیابان‌ها — بیشترین فضا';
    }
  }

  ({double min, double max}) get zoom {
    switch (this) {
      case MapQuality.smallest:
        return (min: 5, max: 10);
      case MapQuality.standard:
        return (min: 5, max: 12);
      case MapQuality.detailed:
        return (min: 5, max: 14);
    }
  }
}

class OfflineMapsService {
  static const String styleUrl = 'https://tiles.openfreemap.org/styles/dark';

  static bool _limitSet = false;

  Future<void> _ensureTileLimit() async {
    if (_limitSet) return;
    await setOfflineTileCountLimit(2000000);
    _limitSet = true;
  }

  double estimateSizeMb(Province p, MapQuality q) {
    final base = switch (q) {
      MapQuality.smallest => 6.0,
      MapQuality.standard => 22.0,
      MapQuality.detailed => 90.0,
    };
    return base * p.areaFactor;
  }

  final Map<String, int> _activeRegionIds = {};

  Future<int?> _findRegionId(String provinceId) async {
    try {
      final regions = await getListOfRegions();
      for (final r in regions) {
        if (r.metadata['province'] == provinceId) return r.id;
      }
    } catch (_) {}
    return null;
  }

  Future<OfflineRegion> downloadProvince(
    Province province,
    MapQuality quality, {
    required void Function(double progress) onProgress,
  }) async {
    await _ensureTileLimit();
    final z = quality.zoom;
    final definition = OfflineRegionDefinition(
      bounds: province.bounds,
      mapStyleUrl: styleUrl,
      minZoom: z.min,
      maxZoom: z.max,
    );

    Timer.periodic(const Duration(milliseconds: 400), (t) async {
      if (_activeRegionIds.containsKey(province.id)) {
        t.cancel();
        return;
      }
      final id = await _findRegionId(province.id);
      if (id != null) {
        _activeRegionIds[province.id] = id;
        t.cancel();
      }
    });

    try {
      return await downloadOfflineRegion(
        definition,
        metadata: {
          'province': province.id,
          'name': province.name,
          'quality': quality.name,
        },
        onEvent: (status) {
          if (status is InProgress) {
            onProgress(status.progress / 100.0);
          } else if (status is Success) {
            onProgress(1.0);
          }
        },
      );
    } finally {
      _activeRegionIds.remove(province.id);
    }
  }

  Future<void> pauseProvinceDownload(String provinceId) async {
    final id = _activeRegionIds[provinceId] ?? await _findRegionId(provinceId);
    if (id != null) await pauseOfflineRegionDownload(id);
  }

  Future<void> resumeProvinceDownload(String provinceId) async {
    final id = _activeRegionIds[provinceId] ?? await _findRegionId(provinceId);
    if (id != null) await resumeOfflineRegionDownload(id);
  }

  Future<List<OfflineRegion>> listRegions() => getListOfRegions();

  Future<void> deleteRegion(int id) => deleteOfflineRegion(id);

  Future<void> deleteProvince(String provinceId) async {
    final regions = await getListOfRegions();
    for (final r in regions) {
      if (r.metadata['province'] == provinceId) {
        await deleteOfflineRegion(r.id);
      }
    }
  }
}
