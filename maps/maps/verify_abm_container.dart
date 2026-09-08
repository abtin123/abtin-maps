import 'dart:io';

import 'package:abtin_maps/abtinmap/abm_container.dart';

Future<void> main(List<String> arguments) async {
  if (arguments.length != 1) {
    stderr.writeln('Usage: dart run tool/maps/verify_abm_container.dart CC.abm');
    exitCode = 64;
    return;
  }
  final file = File(arguments.single);
  final container = await AbtinMapContainer.tryOpen(file);
  if (container == null) {
    stderr.writeln('Not a valid ABTINMAP data container: ${file.path}');
    exitCode = 1;
    return;
  }
  try {
    container.entry('search/places.sqlite');
  } catch (_) {
    stderr.writeln('Missing offline search data in ${file.path}');
    exitCode = 1;
    return;
  }
  stdout.writeln(
    'Container verified: ${file.path} | graph=${container.graph.length} bytes | '
    'entries=${container.entries.length} | renderer-assets=app-bundled',
  );
}
