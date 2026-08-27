import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../../../abtinmap/abm_container.dart';
import 'map_catalog.dart';

class VectorMapInstallException implements Exception {
  const VectorMapInstallException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// آماده‌سازی نمایش برداری از container تک‌فایلی `CC.abm`.
///
/// PMTiles در ابتدای همان فایل است و MapLibre از URI همان archive می‌خواند.
/// graph ABM، styleهای روز/شب و resourceها نیز در segmentهای داخلی آن هستند.
/// این سرویس فقط resourceهای لازم style را در cache محلی استخراج می‌کند؛ هیچ
/// map archive یا graph جداگانه‌ای دانلود یا نگه‌داری نمی‌شود.
class VectorMapService {
  VectorMapService({Directory? rootDirectory}) : _root = rootDirectory;

  Directory? _root;

  Future<Directory> _rootDirectory() async {
    final existing = _root;
    if (existing != null) return existing;
    final support = await getApplicationSupportDirectory();
    final dir = Directory(p.join(support.path, 'abtinmap_vector_cache'));
    if (!await dir.exists()) await dir.create(recursive: true);
    return _root = dir;
  }

  Future<Directory> regionDirectory(String id) async {
    final dir =
        Directory(p.join((await _rootDirectory()).path, id.toUpperCase()));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<File> resolvedStyleFile(String id, {required bool isDark}) async =>
      File(p.join(
        (await regionDirectory(id)).path,
        isDark ? 'style.night.resolved.json' : 'style.day.resolved.json',
      ));

  /// بررسی می‌کند که یک archive واحد هم PMTiles و هم graph ABM و entryهای
  /// لازم برای styleهای این package را داشته باشد.
  Future<bool> isInstalled({
    required VectorMapPackage bundle,
    required File containerFile,
  }) async {
    if (!bundle.isUsable) return false;
    try {
      final container = await AbtinMapContainer.tryOpen(containerFile);
      if (container == null) return false;
      return bundle.entryPaths.every(container.entries.containsKey);
    } on AbtinMapContainerException {
      return false;
    } on FileSystemException {
      return false;
    }
  }

  /// resourceهای داخلی را extract و style انتخابی را برای URI محلی archive
  /// resolve می‌کند. خروجی، مسیر absolute JSON قابل‌خواندن توسط MapLibre است.
  Future<File?> styleFileFor({
    required VectorMapPackage? bundle,
    required String id,
    required File containerFile,
    required bool isDark,
  }) async {
    if (bundle == null || !bundle.isUsable) return null;
    final container = await _openValidatedContainer(containerFile, bundle);
    if (container == null) return null;
    final directory = await regionDirectory(id);
    try {
      for (final path in bundle.resources) {
        await container.extractEntry(path, File(p.join(directory.path, path)));
      }
      final stylePath = isDark ? bundle.nightStylePath : bundle.dayStylePath;
      final template = await container.readTextEntry(stylePath);
      final resolved = resolveStyleTemplate(
        template,
        archive: containerFile,
        directory: directory,
        styleName: stylePath,
      );
      final destination = await resolvedStyleFile(id, isDark: isDark);
      await destination.writeAsString(resolved, flush: true);
      return destination;
    } on AbtinMapContainerException catch (error) {
      throw VectorMapInstallException(error.message);
    } on FileSystemException catch (error) {
      throw VectorMapInstallException(
          'آماده‌سازی style آفلاین ناموفق بود: $error');
    }
  }

  Future<AbtinMapContainer?> _openValidatedContainer(
    File containerFile,
    VectorMapPackage bundle,
  ) async {
    try {
      final container = await AbtinMapContainer.tryOpen(containerFile);
      if (container == null ||
          !bundle.entryPaths.every(container.entries.containsKey)) {
        return null;
      }
      return container;
    } on AbtinMapContainerException {
      return null;
    } on FileSystemException {
      return null;
    }
  }

  /// جای‌گذاری tokenهای style با URIهای محلیِ قابل‌خواندن توسط MapLibre.
  static String resolveStyleTemplate(
    String template, {
    required File archive,
    required Directory directory,
    String styleName = 'style.json',
  }) {
    if (!template.contains('__ABTIN_PMTILES_URI__')) {
      throw VectorMapInstallException(
        'style برداری «$styleName» token PMTiles محلی ندارد.',
      );
    }
    final pmtilesUri = 'pmtiles://${Uri.file(archive.path)}';
    final rootUri = Uri.directory(directory.path).toString();
    final resolved = template
        .replaceAll('__ABTIN_PMTILES_URI__', pmtilesUri)
        .replaceAll('__ABTIN_VECTOR_ROOT_URI__', rootUri);
    if (!resolved.contains('pmtiles://file:')) {
      throw const VectorMapInstallException(
          'URI محلی PMTiles در style معتبر نیست.');
    }
    return resolved;
  }

  /// حذف cache استخراج‌شده؛ archive اصلی `CC.abm` توسط سرویس نقشه پاک می‌شود.
  Future<void> delete(String id) async {
    final dir =
        Directory(p.join((await _rootDirectory()).path, id.toUpperCase()));
    if (await dir.exists()) await dir.delete(recursive: true);
  }
}
