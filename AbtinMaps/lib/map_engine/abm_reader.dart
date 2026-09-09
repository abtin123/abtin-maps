import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:archive/archive.dart';

class AbmFeature {
  const AbmFeature({required this.id, required this.geometry, required this.tags, this.layer=''});
  final int id;
  final List<List<double>> geometry; // [lon,lat]
  final Map<String, dynamic> tags;
  final String layer;
}

class AbmReader {
  AbmReader._(this.file, this.root, this.metadata);

  final File file;
  final Directory root;
  final Map<String, dynamic> metadata;
  final Map<String, List<AbmFeature>> _cache = {};

  static Future<AbmReader> open(File file, Directory cacheRoot) async {
    if (!await file.exists()) throw const FormatException('ABM file not found');
    final work = Directory('${cacheRoot.path}/${_safeName(file.path)}');
    if (!await work.exists()) await work.create(recursive: true);
    final marker = File('${work.path}/.extracted');
    final signature = '${await file.length()}:${(await file.lastModified()).millisecondsSinceEpoch}';
    if (!await marker.exists() || (await marker.readAsString()) != signature) {
      if (await work.exists()) { for (final e in work.listSync()) { if (e is File) await e.delete(); else if (e is Directory) await e.delete(recursive: true); } }
      await _extract(file, work);
      await marker.writeAsString(signature, flush: true);
    }
    final metadataFile = File('${work.path}/metadata.json');
    if (!await metadataFile.exists()) throw const FormatException('metadata.json missing from ABM');
    final decoded = jsonDecode(await metadataFile.readAsString());
    if (decoded is! Map<String, dynamic> || decoded['format'] != 'ABM' || decoded['tiles'] != false) {
      throw const FormatException('Unsupported ABM format: expected tile-free ABM');
    }
    return AbmReader._(file, work, decoded);
  }

  static String _safeName(String path) => path.split(Platform.pathSeparator).last.replaceAll(RegExp(r'[^A-Za-z0-9_.-]'), '_');

  static Future<void> _extract(File source, Directory destination) async {
    await Isolate.run(() => _extractSync(source.path, destination.path));
  }

  static void _extractSync(String sourcePath, String destinationPath) {
    final input = InputFileStream(sourcePath);
    try {
      final archive = ZipDecoder().decodeStream(input);
      for (final entry in archive) {
        final name = entry.name.replaceAll('\\', '/');
        if (name.startsWith('/') || name.contains('../') || name.split('/').contains('.')) {
          throw const FormatException('Unsafe ABM entry path');
        }
        if (!entry.isFile) continue;
        final outPath = '$destinationPath/$name';
        final out = OutputFileStream(outPath);
        try { entry.writeContent(out); } finally { out.closeSync(); }
      }
    } finally { input.closeSync(); }
  }

  Directory get vectorDirectory => Directory('${root.path}/vector');
  File get searchDatabase => File('${root.path}/search/search.sqlite');
  File get poiDatabase => File('${root.path}/poi/poi.sqlite');
  File get routingGraph => File('${root.path}/routing/graph.bin');

  Future<List<AbmFeature>> readLayer(String layer) async {
    final cached = _cache[layer];
    if (cached != null) return cached;
    final file = File('${vectorDirectory.path}/$layer.bin');
    if (!await file.exists()) return const [];
    final features = await Isolate.run(() => _readRecords(file.path, layer));
    _cache[layer] = features;
    return features;
  }

  Future<List<AbmFeature>> readAllFeatures() async {
    final layers = <String>['roads', 'buildings', 'landuse', 'water', 'boundaries', 'places'];
    final result = <AbmFeature>[];
    for (final layer in layers) result.addAll(await readLayer(layer));
    return result;
  }

  static List<AbmFeature> _readRecords(String path, String layer) {
    final bytes = File(path).readAsBytesSync();
    if (bytes.length < 6 || utf8.decode(bytes.sublist(0, 6), allowMalformed: true) != 'ABMV1\n') {
      throw FormatException('Invalid ABM vector stream: $path');
    }
    var offset = 6;
    final out = <AbmFeature>[];
    while (offset + 4 <= bytes.length) {
      final size = (bytes[offset] << 24) | (bytes[offset + 1] << 16) | (bytes[offset + 2] << 8) | bytes[offset + 3];
      offset += 4;
      if (size < 0 || offset + size > bytes.length) throw FormatException('Truncated ABM record: $path');
      final value = jsonDecode(utf8.decode(bytes.sublist(offset, offset + size)));
      offset += size;
      if (value is! Map<String, dynamic>) continue;
      final geometry = <List<double>>[];
      final rawGeometry = value['geometry'];
      if (rawGeometry is List) {
        for (final point in rawGeometry) {
          if (point is List && point.length >= 2 && point[0] is num && point[1] is num) {
            geometry.add([(point[0] as num).toDouble(), (point[1] as num).toDouble()]);
          }
        }
      }
      out.add(AbmFeature(
        id: (value['id'] as num?)?.toInt() ?? 0,
        geometry: geometry,
        tags: value['tags'] is Map ? Map<String, dynamic>.from(value['tags'] as Map) : const {}, layer: layer,
      ));
    }
    return out;
  }
}
