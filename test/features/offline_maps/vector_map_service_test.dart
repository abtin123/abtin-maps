import 'dart:io';

import 'package:abtin_navigator/features/offline_maps/data/map_catalog.dart';
import 'package:abtin_navigator/features/offline_maps/data/vector_map_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('VectorMapPackage in one ABM container', () {
    test('parses embedded style entries without a second map archive', () {
      final bundle = VectorMapPackage.fromJson(<String, dynamic>{
        'embedded': true,
        'day_style': 'styles/day.json',
        'night_style': <String, dynamic>{'path': 'styles/night.json'},
        'resources': <String>[
          'sprites/sprite.png',
          'sprites/sprite.json',
        ],
      });

      expect(bundle.isUsable, isTrue);
      expect(bundle.entryPaths, <String>[
        'styles/day.json',
        'styles/night.json',
        'sprites/sprite.png',
        'sprites/sprite.json',
      ]);
    });

    test('requires explicit embedded metadata and safe unique entry paths', () {
      expect(
        const VectorMapPackage(
          embedded: false,
          dayStylePath: 'styles/day.json',
          nightStylePath: 'styles/night.json',
        ).isUsable,
        isFalse,
      );
      expect(
        const VectorMapPackage(
          dayStylePath: '../day.json',
          nightStylePath: 'styles/night.json',
        ).isUsable,
        isFalse,
      );
      expect(
        const VectorMapPackage(
          dayStylePath: 'styles/day.json',
          nightStylePath: 'styles/day.json',
        ).isUsable,
        isFalse,
      );
    });
  });

  group('VectorMapService', () {
    late Directory root;
    late VectorMapService service;

    setUp(() async {
      root = await Directory.systemTemp.createTemp('abtin_vector_style_test_');
      service = VectorMapService(rootDirectory: root);
    });

    tearDown(() async {
      if (await root.exists()) await root.delete(recursive: true);
    });

    test('resolves both local PMTiles and resource URI tokens', () async {
      final archive = File('${root.path}/IR.abm');
      final styleCache = await service.regionDirectory('IR');
      final resolved = VectorMapService.resolveStyleTemplate(
        '{"sources":{"map":{"url":"__ABTIN_PMTILES_URI__"}},'
        '"sprite":"__ABTIN_VECTOR_ROOT_URI__sprites/sprite"}',
        archive: archive,
        directory: styleCache,
        styleName: 'styles/day.json',
      );

      expect(resolved, contains('pmtiles://file:'));
      expect(resolved, contains('IR.abm'));
      expect(resolved, contains(Uri.directory(styleCache.path).toString()));
    });

    test('rejects a style without the PMTiles token', () {
      expect(
        () => VectorMapService.resolveStyleTemplate(
          '{"version":8}',
          archive: File('${root.path}/IR.abm'),
          directory: root,
          styleName: 'styles/day.json',
        ),
        throwsA(isA<VectorMapInstallException>()),
      );
    });
  });
}
