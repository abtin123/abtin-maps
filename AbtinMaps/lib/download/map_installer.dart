import 'dart:io';
import '../map_engine/abm_reader.dart';
import '../map_engine/cache_manager.dart';

class MapInstaller {
  final MapCacheManager cache = MapCacheManager();
  Future<AbmReader> prepare({required File abm, required String country, void Function(double)? onProgress}) async {
    onProgress?.call(.15);
    final dir = await cache.country(country);
    onProgress?.call(.55);
    final reader = await AbmReader.open(abm, dir);
    onProgress?.call(.8);
    await File('${dir.path}/search.ready').writeAsString('1');
    await File('${dir.path}/spatial.ready').writeAsString('1');
    await File('${dir.path}/routing.ready').writeAsString('1');
    await File('${dir.path}/render.ready').writeAsString('1');
    onProgress?.call(1);
    return reader;
  }
}
