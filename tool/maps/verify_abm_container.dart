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
  for (final required in <String>['styles/day.json', 'styles/night.json']) {
    container.entry(required);
  }
  stdout.writeln(
    'Container verified: ${file.path} | graph=${container.graph.length} bytes | '
    'entries=${container.entries.length}',
  );
}
