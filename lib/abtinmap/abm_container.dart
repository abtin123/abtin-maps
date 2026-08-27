import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

/// یک archive PMTiles v3 استاندارد با پسوند اختصاصی `.abm`.
///
/// دادهٔ tile در ابتدای همان فایل قرار دارد. graph مسیریابی ABM و style/resourceها
/// در انتهای tile-data PMTiles ذخیره می‌شوند و offset آن‌ها در metadata JSON
/// استاندارد PMTiles، زیر کلید `abtin_container`، ثبت می‌شود. بنابراین طول فایل
/// دقیقاً با header PMTiles برابر می‌ماند و verifierهای PMTiles آن را رد نمی‌کنند.
class AbtinMapContainer {
  AbtinMapContainer._({
    required this.file,
    required this.fileLength,
    required this.pmtiles,
    required this.graph,
    required this.entries,
  });

  static const _headerSize = 127;
  static const _pmtilesMagic = <int>[0x50, 0x4D, 0x54, 0x69, 0x6C, 0x65, 0x73];
  static const _abmMagic = <int>[
    0x41,
    0x42,
    0x54,
    0x49,
    0x4E,
    0x4D,
    0x41,
    0x50
  ];

  final File file;
  final int fileLength;

  /// کل archive از byte zero قابل‌خواندن توسط MapLibre/PMTiles است.
  final AbtinMapSegment pmtiles;
  final AbtinMapSegment graph;
  final Map<String, AbtinMapSegment> entries;

  static Future<AbtinMapContainer?> tryOpen(File file) async {
    if (!await file.exists()) return null;
    final length = await file.length();
    if (length < _headerSize) return null;
    final raf = await file.open();
    try {
      final header = await raf.read(_headerSize);
      if (!_equalsPrefix(header, _pmtilesMagic) || header[7] != 3) return null;
      final values = ByteData.sublistView(Uint8List.fromList(header));
      final internalCompression = header[97];
      final metadataOffset = values.getUint64(24, Endian.little);
      final metadataLength = values.getUint64(32, Endian.little);
      final tileDataOffset = values.getUint64(56, Endian.little);
      final tileDataLength = values.getUint64(64, Endian.little);
      if (metadataLength == 0 ||
          metadataOffset > length ||
          metadataLength > length - metadataOffset ||
          tileDataOffset > length ||
          tileDataLength > length - tileDataOffset ||
          tileDataOffset + tileDataLength != length) {
        throw const AbtinMapContainerException(
          'اندازه یا offsetهای archive PMTiles نامعتبر است.',
        );
      }
      await raf.setPosition(metadataOffset);
      final rawMetadata = await raf.read(metadataLength);
      if (rawMetadata.length != metadataLength) {
        throw const AbtinMapContainerException(
            'metadata PMTiles کامل خوانده نشد.');
      }
      final metadataBytes = switch (internalCompression) {
        1 => rawMetadata,
        2 => Uint8List.fromList(gzip.decode(rawMetadata)),
        _ => throw AbtinMapContainerException(
            'compression داخلی PMTiles ($internalCompression) پشتیبانی نمی‌شود.',
          ),
      };
      final metadata = jsonDecode(utf8.decode(metadataBytes));
      if (metadata is! Map<String, dynamic>) {
        throw const AbtinMapContainerException(
            'metadata PMTiles باید JSON object باشد.');
      }
      final containerJson = metadata['abtin_container'];
      if (containerJson is! Map<String, dynamic>) return null;
      if (containerJson['version'] != 1) {
        throw const AbtinMapContainerException(
          'نسخهٔ container داخلی نقشه پشتیبانی نمی‌شود.',
        );
      }
      final graphJson = containerJson['graph'];
      if (graphJson is! Map<String, dynamic>) {
        throw const AbtinMapContainerException(
            'graph داخلی container موجود نیست.');
      }
      final graph = AbtinMapSegment.fromJson(graphJson, name: 'graph');
      final rawEntries = containerJson['entries'];
      final entries = <String, AbtinMapSegment>{};
      if (rawEntries is List) {
        for (final raw in rawEntries) {
          if (raw is! Map<String, dynamic>) continue;
          final path = raw['path'];
          if (path is! String || !_isSafeRelativePath(path)) {
            throw const AbtinMapContainerException(
              'مسیر resource در container نامعتبر است.',
            );
          }
          if (entries.containsKey(path)) {
            throw const AbtinMapContainerException(
              'resource تکراری در container نقشه وجود دارد.',
            );
          }
          entries[path] = AbtinMapSegment.fromJson(raw, name: path);
        }
      }
      final container = AbtinMapContainer._(
        file: file,
        fileLength: length,
        pmtiles: AbtinMapSegment(name: 'pmtiles', offset: 0, length: length),
        graph: graph,
        entries: Map.unmodifiable(entries),
      );
      container._validateSegments(tileDataOffset, tileDataLength);
      await container._validateGraphMagic(raf);
      return container;
    } finally {
      await raf.close();
    }
  }

  void _validateSegments(int tileDataOffset, int tileDataLength) {
    final tileDataEnd = tileDataOffset + tileDataLength;
    for (final segment in <AbtinMapSegment>[graph, ...entries.values]) {
      if (segment.offset < tileDataOffset ||
          segment.length <= 0 ||
          segment.offset >= tileDataEnd ||
          segment.length > tileDataEnd - segment.offset) {
        throw AbtinMapContainerException(
          'offset segment «${segment.name}» در PMTiles نامعتبر است.',
        );
      }
    }
  }

  Future<void> _validateGraphMagic(RandomAccessFile raf) async {
    await raf.setPosition(graph.offset);
    final bytes = await raf.read(_abmMagic.length);
    if (!_equalsPrefix(bytes, _abmMagic)) {
      throw const AbtinMapContainerException('segment graph ABM معتبر نیست.');
    }
  }

  AbtinMapSegment entry(String path) {
    final found = entries[path];
    if (found == null) {
      throw AbtinMapContainerException(
        'resource «$path» در container نقشه موجود نیست.',
      );
    }
    return found;
  }

  Future<String> readTextEntry(String path) async {
    final data = await _readSegment(entry(path));
    return utf8.decode(data);
  }

  Future<void> extractEntry(String path, File destination) async {
    final data = await _readSegment(entry(path));
    await destination.parent.create(recursive: true);
    await destination.writeAsBytes(data, flush: true);
  }

  Future<Uint8List> _readSegment(AbtinMapSegment segment) async {
    final raf = await file.open();
    try {
      await raf.setPosition(segment.offset);
      final data = await raf.read(segment.length);
      if (data.length != segment.length) {
        throw AbtinMapContainerException(
          'segment «${segment.name}» کامل خوانده نشد.',
        );
      }
      return Uint8List.fromList(data);
    } finally {
      await raf.close();
    }
  }

  static bool _equalsPrefix(List<int> actual, List<int> expected) {
    if (actual.length < expected.length) return false;
    for (var index = 0; index < expected.length; index++) {
      if (actual[index] != expected[index]) return false;
    }
    return true;
  }

  static bool _isSafeRelativePath(String value) {
    final normalized = value.replaceAll('\\', '/');
    return value.trim().isNotEmpty &&
        !normalized.startsWith('/') &&
        !normalized.contains('../') &&
        !normalized.split('/').any((part) => part.isEmpty || part == '.');
  }
}

class AbtinMapSegment {
  const AbtinMapSegment({
    required this.name,
    required this.offset,
    required this.length,
  });

  final String name;
  final int offset;
  final int length;

  factory AbtinMapSegment.fromJson(Map<String, dynamic> json,
      {required String name}) {
    final offset = json['offset'];
    final length = json['length'];
    if (offset is! num || length is! num) {
      throw AbtinMapContainerException('segment «$name» metadata معتبر ندارد.');
    }
    return AbtinMapSegment(
      name: name,
      offset: offset.toInt(),
      length: length.toInt(),
    );
  }
}

class AbtinMapContainerException implements Exception {
  const AbtinMapContainerException(this.message);

  final String message;

  @override
  String toString() => message;
}
