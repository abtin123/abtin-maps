import 'dart:io';

import 'package:flutter/services.dart' show rootBundle;
import 'package:path_provider/path_provider.dart';

/// آماده‌سازی گلیف‌های فونتِ آفلاین برای برچسب‌های فارسی/لاتین.
///
/// MapLibre نمی‌تواند این‌ها را مستقیم از asset باندل فلاتر بخواند، بنابراین یک
/// بار روی حافظه‌ی داخلی اپ کپی می‌شوند و آدرس آن‌ها به‌صورت `file://` داخل
/// استایل تزریق می‌شود. هیچ درخواست شبکه‌ای انجام نمی‌شود.
class AbmStyleAssets {
  AbmStyleAssets._();

  static final AbmStyleAssets instance = AbmStyleAssets._();

  // Bump this whenever bundled style/sprite assets change so an installed app
  // does not keep serving an older copy from Application Support.
  static const String _assetRevision = 'vector-renderer-v4';

  static const List<String> _fontstacks = ['Vazirmatn', 'VazirmatnBold'];
  static const List<String> _ranges = [
    '0-255',
    '256-511',
    '1536-1791',
    '1792-2047',
    '8192-8447',
    '64256-64511',
    '64512-64767',
    '65024-65279',
    '65280-65535',
  ];

  Directory? _root;
  final Map<String, String> _styleCache = {};

  Future<Directory> _ensureRoot() async {
    if (_root != null) return _root!;
    final base = await getApplicationSupportDirectory();
    final root = Directory('${base.path}/abm_style/$_assetRevision');
    await root.create(recursive: true);
    for (final stack in _fontstacks) {
      final dir = Directory('${root.path}/glyphs/$stack');
      await dir.create(recursive: true);
      for (final range in _ranges) {
        await _copyAsset(
          'assets/glyphs/$stack/$range.pbf',
          File('${dir.path}/$range.pbf'),
        );
      }
    }
    final spriteDir = Directory('${root.path}/sprites');
    await spriteDir.create(recursive: true);
    for (final assetName in const ['abtin.json', 'abtin.png', 'abtin@2x.json', 'abtin@2x.png']) {
      await _copyAsset('assets/sprites/$assetName', File('${spriteDir.path}/$assetName'));
    }
    _root = root;
    return root;
  }

  Future<void> _copyAsset(String assetPath, File target) async {
    if (await target.exists()) return;
    final data = await rootBundle.load(assetPath);
    await target.writeAsBytes(
      data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
      flush: true,
    );
  }

  /// آیا این استایل، استایل آفلاینِ خودمان است؟ (استایل آنلاین OSM دست‌نخورده می‌ماند)
  bool isOfflineStyle(String assetPath) =>
      assetPath.startsWith('assets/styles/') &&
      !assetPath.contains('osm_online');

  /// مسیر نهاییِ قابل‌استفاده در `MapLibreMap.styleString`.
  /// برای استایل آفلاین یک فایل `file://` با گلیف/اسپریت لوکال برمی‌گرداند.
  Future<String> resolveStyle(String assetPath) async {
    if (!isOfflineStyle(assetPath)) return assetPath;
    final cached = _styleCache[assetPath];
    if (cached != null) return cached;

    final root = await _ensureRoot();
    final raw = await rootBundle.loadString(assetPath);
    final glyphs = 'file://${root.path}/glyphs/{fontstack}/{range}.pbf';
    final sprite = 'file://${root.path}/sprites/abtin';
    final patched = raw
        .replaceAll('{ABM_GLYPHS}', glyphs)
        .replaceAll('{ABM_SPRITE}', sprite);

    final name = assetPath.split('/').last;
    final out = File('${root.path}/$name');
    await out.writeAsString(patched, flush: true);
    final url = 'file://${out.path}';
    _styleCache[assetPath] = url;
    return url;
  }
}
