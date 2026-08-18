import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import 'country_models.dart';

/// ⚠️ همینجا با تگ واقعی ریلیزتان هماهنگ کنید (همان TAG در ورک‌فلوی build-abtin-map.yml)
const _releaseTag = 'maps-v1';
const _repo = 'abtin123/abtin-maps';
const _manifestUrl =
    'https://github.com/$_repo/releases/download/$_releaseTag/manifest.json';

/// میررهای جایگزین برای زمانی که GitHub در ایران فیلتر/کند است
/// (همان الگوی fallback که در دانلود گراف‌های GraphHopper استفاده شده).
List<String> _mirrorUrls(String originalUrl) {
  final ghProxy = 'https://gh-proxy.com/$originalUrl';
  return [originalUrl, ghProxy];
}

final dioProvider = Provider<Dio>((ref) {
  return Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 20),
    receiveTimeout: const Duration(minutes: 10),
  ));
});

/// دریافت manifest.json (لیست همه‌ی کشورهای قابل‌دانلود)
final countryManifestProvider = FutureProvider<CountryManifest>((ref) async {
  final dio = ref.watch(dioProvider);
  Object? lastError;
  for (final url in _mirrorUrls(_manifestUrl)) {
    try {
      final res = await dio.get<String>(
        url,
        options: Options(responseType: ResponseType.plain),
      );
      final jsonMap = jsonDecode(res.data!) as Map<String, dynamic>;
      return CountryManifest.fromJson(jsonMap);
    } catch (e) {
      lastError = e;
      continue;
    }
  }
  throw Exception('دریافت لیست کشورها ناموفق بود: $lastError');
});

enum CountryDownloadStatus { notDownloaded, downloading, paused, installed, failed }

class CountryDownloadState {
  final CountryDownloadStatus status;
  final double progress; // 0..1
  final String? error;

  const CountryDownloadState({
    this.status = CountryDownloadStatus.notDownloaded,
    this.progress = 0,
    this.error,
  });

  CountryDownloadState copyWith({
    CountryDownloadStatus? status,
    double? progress,
    String? error,
  }) =>
      CountryDownloadState(
        status: status ?? this.status,
        progress: progress ?? this.progress,
        error: error,
      );
}

/// پوشه‌ای که فایل‌های .abm نصب‌شده‌ی هر کشور در آن ذخیره می‌شوند
Future<Directory> countryMapsDir() async {
  final base = await getApplicationSupportDirectory();
  final dir = Directory('${base.path}/country_maps');
  if (!await dir.exists()) await dir.create(recursive: true);
  return dir;
}

Future<File> installedFilePath(String code) async {
  final dir = await countryMapsDir();
  return File('${dir.path}/$code.abm');
}

/// مدیریت دانلود/نصب/حذف نقشه‌ی هر کشور، به‌صورت مستقل به‌ازای هر کد کشور.
class CountryDownloadNotifier extends StateNotifier<CountryDownloadState> {
  final Ref ref;
  final CountryMapEntry entry;
  CancelToken? _cancelToken;

  CountryDownloadNotifier(this.ref, this.entry)
      : super(const CountryDownloadState()) {
    _checkInstalled();
  }

  Future<void> _checkInstalled() async {
    final f = await installedFilePath(entry.code);
    if (await f.exists() && await f.length() == entry.totalSize) {
      state = state.copyWith(status: CountryDownloadStatus.installed, progress: 1);
    }
  }

  Future<void> download() async {
    if (state.status == CountryDownloadStatus.downloading) return;
    state = state.copyWith(status: CountryDownloadStatus.downloading, progress: 0, error: null);
    _cancelToken = CancelToken();
    final dio = ref.read(dioProvider);

    try {
      final dir = await countryMapsDir();
      final tmp = File('${dir.path}/${entry.code}.abm.download');
      if (await tmp.exists()) await tmp.delete();

      final sink = tmp.openWrite();
      int totalWritten = 0;

      // فایل ممکن است چند تکه (part0, part1, ...) باشد؛ به ترتیب دانلود و الحاق می‌شود.
      for (final url in entry.downloadUrls) {
        final mirrors = _mirrorUrls(url);
        Object? lastErr;
        var done = false;
        for (final mUrl in mirrors) {
          try {
            final res = await dio.get<ResponseBody>(
              mUrl,
              cancelToken: _cancelToken,
              options: Options(responseType: ResponseType.stream),
            );
            await for (final chunk in res.data!.stream) {
              sink.add(chunk);
              totalWritten += chunk.length;
              state = state.copyWith(
                progress: (totalWritten / entry.totalSize).clamp(0, 1),
              );
            }
            done = true;
            break;
          } catch (e) {
            lastErr = e;
            continue; // میرور بعدی را امتحان کن
          }
        }
        if (!done) throw Exception('دانلود ناموفق: $lastErr');
      }

      await sink.close();

      // اعتبارسنجی حجم قبل از جایگزینی نهایی
      final finalSize = await tmp.length();
      if (finalSize != entry.totalSize) {
        await tmp.delete();
        throw Exception('حجم فایل مطابقت ندارد (انتظار ${entry.totalSize}, دریافت $finalSize)');
      }

      final dest = await installedFilePath(entry.code);
      if (await dest.exists()) await dest.delete();
      await tmp.rename(dest.path);

      state = state.copyWith(status: CountryDownloadStatus.installed, progress: 1);
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) {
        state = state.copyWith(status: CountryDownloadStatus.paused);
      } else {
        state = state.copyWith(status: CountryDownloadStatus.failed, error: e.message);
      }
    } catch (e) {
      state = state.copyWith(status: CountryDownloadStatus.failed, error: e.toString());
    }
  }

  void cancelDownload() {
    _cancelToken?.cancel('لغو توسط کاربر');
    state = state.copyWith(status: CountryDownloadStatus.paused);
  }

  Future<void> delete() async {
    final f = await installedFilePath(entry.code);
    if (await f.exists()) await f.delete();
    state = const CountryDownloadState();
  }
}

final countryDownloadProvider = StateNotifierProvider.family<
    CountryDownloadNotifier, CountryDownloadState, CountryMapEntry>(
  (ref, entry) => CountryDownloadNotifier(ref, entry),
);
