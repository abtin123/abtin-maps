library;

import '../../../core/localization/locale_flags.dart';

/// Manifest and language packs are remote assets published by the language
/// builder. Nothing except the app's built-in Persian/English UI is bundled.
const String kLangPacksManifestUrl =
    'https://github.com/abtin123/Make-langueg/releases/download/langpacks-latest/manifest.json';

class LanguagePack {
  const LanguagePack({
    required this.code,
    required this.name,
    required this.flag,
    required this.downloadUrl,
    this.direction = 'ltr',
    this.stringCount = 0,
    this.sizeBytes = 0,
    this.sha256 = '',
    this.version = '',
  });

  final String code;
  final String name;
  final String flag;
  final String downloadUrl;
  final String direction;
  final int stringCount;
  final int sizeBytes;
  final String sha256;
  final String version;

  String get localFileName => 'lang_$code.abl';

  factory LanguagePack.fromManifestJson(Map<String, dynamic> json) {
    final rawCode = json['language_code'] ?? json['code'] ?? json['locale'];
    if (rawCode is! String || rawCode.trim().isEmpty) {
      throw const FormatException('رکورد زبان کد معتبر ندارد.');
    }
    final code = rawCode.trim().toLowerCase();
    final rawName = json['language'] ?? json['name'] ?? json['language_name'];
    final rawDirection = json['direction'];
    final rawUrl = json['download_url'];
    if (rawUrl is! String || rawUrl.trim().isEmpty) {
      throw const FormatException('رکورد زبان لینک دانلود ندارد.');
    }
    return LanguagePack(
      code: code,
      name: rawName is String && rawName.trim().isNotEmpty
          ? cleanLocalizedLabel(rawName)
          : code,
      flag: flagAssetForLanguageCode(code),
      downloadUrl: rawUrl.trim(),
      direction: rawDirection == 'rtl' ? 'rtl' : 'ltr',
      stringCount: (json['string_count'] ?? json['strings']) is num
          ? ((json['string_count'] ?? json['strings']) as num).toInt()
          : 0,
      sizeBytes: json['size'] is num ? (json['size'] as num).toInt() : 0,
      sha256: json['sha256']?.toString() ?? '',
      version: json['version']?.toString() ?? '',
    );
  }
}

/// Persian and English remain part of the executable UI. Every other
/// language is downloaded from the remote release manifest.
final List<LanguagePack> builtInLanguages = [
  LanguagePack(
    code: 'fa',
    name: 'فارسی',
    flag: flagAssetForLanguageCode('fa'),
    downloadUrl: '',
    direction: 'rtl',
  ),
  LanguagePack(
    code: 'en',
    name: 'English',
    flag: flagAssetForLanguageCode('en'),
    downloadUrl: '',
  ),
];
