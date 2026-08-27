import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:abtin_navigator/abtinmap/abm_container.dart';
import 'package:flutter_test/flutter_test.dart';

const _pmtilesMagic = <int>[0x50, 0x4D, 0x54, 0x69, 0x6C, 0x65, 0x73];
const _graphMagic = <int>[0x41, 0x42, 0x54, 0x49, 0x4E, 0x4D, 0x41, 0x50];

Future<File> _createContainer(
  Directory directory, {
  required bool gzipMetadata,
}) async {
  final rootDirectory = Uint8List.fromList(<int>[0]);
  final graph = Uint8List(128)..setRange(0, _graphMagic.length, _graphMagic);
  final day =
      utf8.encode('{"sources":{"map":{"url":"__ABTIN_PMTILES_URI__"}}}');
  final night =
      utf8.encode('{"sources":{"map":{"url":"__ABTIN_PMTILES_URI__"}}}');
  final payload = <int>[...graph, ...day, ...night];

  Map<String, dynamic> metadata = <String, dynamic>{};
  var previousTileOffset = -1;
  for (var attempt = 0; attempt < 12; attempt++) {
    final raw = utf8.encode(jsonEncode(metadata));
    final encoded = gzipMetadata ? gzip.encode(raw) : raw;
    final tileOffset = 127 + rootDirectory.length + encoded.length;
    final next = <String, dynamic>{
      'vector_layers': <dynamic>[],
      'abtin_container': <String, dynamic>{
        'version': 1,
        'region': 'IR',
        'graph': <String, int>{'offset': tileOffset, 'length': graph.length},
        'entries': <Map<String, dynamic>>[
          <String, dynamic>{
            'path': 'styles/day.json',
            'offset': tileOffset + graph.length,
            'length': day.length,
          },
          <String, dynamic>{
            'path': 'styles/night.json',
            'offset': tileOffset + graph.length + day.length,
            'length': night.length,
          },
        ],
      },
    };
    metadata = next;
    if (tileOffset == previousTileOffset) break;
    previousTileOffset = tileOffset;
  }
  final rawMetadata = utf8.encode(jsonEncode(metadata));
  final encodedMetadata = gzipMetadata ? gzip.encode(rawMetadata) : rawMetadata;
  final tileOffset = 127 + rootDirectory.length + encodedMetadata.length;
  final header = Uint8List(127)
    ..setRange(0, _pmtilesMagic.length, _pmtilesMagic);
  header[7] = 3;
  header[97] = gzipMetadata ? 2 : 1;
  final bytes = ByteData.sublistView(header);
  bytes.setUint64(8, 127, Endian.little);
  bytes.setUint64(16, rootDirectory.length, Endian.little);
  bytes.setUint64(24, 127 + rootDirectory.length, Endian.little);
  bytes.setUint64(32, encodedMetadata.length, Endian.little);
  bytes.setUint64(40, tileOffset, Endian.little);
  bytes.setUint64(48, 0, Endian.little);
  bytes.setUint64(56, tileOffset, Endian.little);
  bytes.setUint64(64, payload.length, Endian.little);

  final target = File('${directory.path}/IR.abm');
  await target.writeAsBytes(<int>[
    ...header,
    ...rootDirectory,
    ...encodedMetadata,
    ...payload,
  ]);
  return target;
}

void main() {
  group('AbtinMapContainer', () {
    late Directory directory;

    setUp(() async {
      directory =
          await Directory.systemTemp.createTemp('abtin_container_test_');
    });

    tearDown(() async {
      if (await directory.exists()) await directory.delete(recursive: true);
    });

    test('opens one uncompressed PMTiles archive named .abm', () async {
      final file = await _createContainer(directory, gzipMetadata: false);
      final container = await AbtinMapContainer.tryOpen(file);

      expect(container, isNotNull);
      expect(container!.pmtiles.offset, 0);
      expect(container.graph.offset, greaterThanOrEqualTo(127));
      expect(
        container.entries.keys,
        containsAll(<String>['styles/day.json', 'styles/night.json']),
      );
    });

    test('rejects a normal old graph-only ABM as a map container', () async {
      final oldGraph = File('${directory.path}/old.abm');
      await oldGraph.writeAsBytes(
        <int>[..._graphMagic, ...List<int>.filled(160, 0)],
      );
      expect(await AbtinMapContainer.tryOpen(oldGraph), isNull);
    });
  });
}
