// مدل‌های داده برای manifest.json چند-کشوره‌ی abtin-maps
// آدرس منبع: https://github.com/abtin123/abtin-maps/releases/download/<tag>/manifest.json

class CountryFile {
  final String name;
  final int size;
  final String sha256;

  CountryFile({required this.name, required this.size, required this.sha256});

  factory CountryFile.fromJson(Map<String, dynamic> j) => CountryFile(
        name: j['name'] as String,
        size: j['size'] as int,
        sha256: j['sha256'] as String,
      );
}

class CountryMapEntry {
  final String code; // مثل "IR"
  final String nameFa; // ایران
  final String nameEn; // Iran
  final bool enabled;
  final String format; // "ABTINMAP/1"
  final int baseZoom;
  final List<double> bbox; // [minLon, minLat, maxLon, maxLat]
  final List<CountryFile> files; // ممکن است چند تکه (part0, part1, ...) باشد
  final int totalSize; // بایت
  final String sha256; // هش کل فایل (پس از الحاق تکه‌ها)
  final String downloadBase; // پیشوند URL ریلیز گیت‌هاب

  CountryMapEntry({
    required this.code,
    required this.nameFa,
    required this.nameEn,
    required this.enabled,
    required this.format,
    required this.baseZoom,
    required this.bbox,
    required this.files,
    required this.totalSize,
    required this.sha256,
    required this.downloadBase,
  });

  /// آدرس‌های دانلود هر تکه، به ترتیب الحاق.
  List<String> get downloadUrls =>
      files.map((f) => '$downloadBase${f.name}').toList();

  double get totalSizeMb => totalSize / 1e6;

  factory CountryMapEntry.fromJson(Map<String, dynamic> j) => CountryMapEntry(
        code: j['code'] as String,
        nameFa: j['name_fa'] as String,
        nameEn: j['name_en'] as String,
        enabled: (j['enabled'] as bool?) ?? true,
        format: j['format'] as String? ?? 'ABTINMAP/1',
        baseZoom: (j['base_zoom'] as num).toInt(),
        bbox: (j['bbox'] as List).map((e) => (e as num).toDouble()).toList(),
        files: (j['files'] as List)
            .map((e) => CountryFile.fromJson(e as Map<String, dynamic>))
            .toList(),
        totalSize: (j['total_size'] as num).toInt(),
        sha256: j['sha256'] as String,
        downloadBase: j['download_base'] as String,
      );
}

class CountryManifest {
  final int schema;
  final String generatedAt;
  final String releaseTag;
  final List<CountryMapEntry> countries;

  CountryManifest({
    required this.schema,
    required this.generatedAt,
    required this.releaseTag,
    required this.countries,
  });

  factory CountryManifest.fromJson(Map<String, dynamic> j) => CountryManifest(
        schema: (j['schema'] as num).toInt(),
        generatedAt: j['generated_at'] as String,
        releaseTag: j['release_tag'] as String,
        countries: (j['countries'] as List)
            .map((e) => CountryMapEntry.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
