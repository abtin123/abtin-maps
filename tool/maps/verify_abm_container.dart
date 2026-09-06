import 'dart:io';

import 'package:abtin_navigator/abtinmap/abm_container.dart';

Future<void> main(List<String> arguments) async {
  if (arguments.length != 1) {
    stderr
        .writeln('Usage: dart run tool/maps/verify_abm_container.dart CC.abm');
    exitCode = 64;
    return;
  }
  final file = File(arguments.single);
  final container = await AbtinMapContainer.tryOpen(file);
  if (container == null) {
    stderr.writeln('Not a valid one-file ABM/PMTiles container: ${file.path}');
    exitCode = 1;
    return;
  }
  const requiredEntries = <String>[
    'styles/day.json',
    'styles/night.json',
    'sprites/abtin.json',
    'sprites/abtin.png',
    'sprites/abtin@2x.json',
    'sprites/abtin@2x.png',
    'glyphs/Vazirmatn/0-255.pbf',
    'glyphs/Vazirmatn/256-511.pbf',
    'glyphs/Vazirmatn/1536-1791.pbf',
    'glyphs/Vazirmatn/1792-2047.pbf',
    'glyphs/Vazirmatn/8192-8447.pbf',
    'glyphs/Vazirmatn/64256-64511.pbf',
    'glyphs/Vazirmatn/64512-64767.pbf',
    'glyphs/Vazirmatn/65024-65279.pbf',
    'glyphs/Vazirmatn/65280-65535.pbf',
  ];
  for (final required in requiredEntries) {
    container.entry(required);
  }
  stdout.writeln(
    'Container verified: ${file.path} | graph=${container.graph.length} bytes | '
    'entries=${container.entries.length}',
  );
}
