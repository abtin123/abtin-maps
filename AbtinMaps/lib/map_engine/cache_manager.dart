import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

class MapCacheManager {
  Future<Directory> country(String country) async {
    final base = await getApplicationSupportDirectory();
    final dir = Directory(p.join(base.path, 'AbtinMaps', 'cache', country.toUpperCase()));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }
  Future<Directory> render(String country) async => Directory(p.join((await countryDirectory(country)).path, 'render'));
  Future<Directory> countryDirectory(String country) => country(country);
  Future<File> marker(String country) async => File(p.join((await country(country)).path, '.ready'));
}
