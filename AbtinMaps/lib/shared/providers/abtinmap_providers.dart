import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../abtinmap/abm_map_service.dart';
import '../../features/offline_maps/data/map_catalog.dart';
import '../../features/offline_maps/data/vector_map_service.dart';
import '../../features/offline_maps/presentation/offline_maps_providers.dart';
import '../../features/routing/data/routing_provider.dart';
import '../../features/settings/data/settings_repository.dart';
import '../../features/settings/presentation/settings_repository_provider.dart';

/// سرویس دانلود و نگهداری فایل‌های .abm
final abmMapServiceProvider = Provider<AbmMapService>((ref) {
  final service = AbmMapService();
  ref.onDispose(service.closeMap);
  return service;
});


/// نقشه‌های ساخته‌شده با ABM Builder می‌توانند همراه APK قرار بگیرند.
/// این bootstrap همان فایل `.abm` تولیدشده توسط اسکریپت را وارد مسیر واقعی
/// نصب می‌کند؛ renderer/search/routing هیچ مسیر ویژه‌ای برای asset ندارند.
final bundledMapBootstrapProvider = FutureProvider<void>((ref) async {
  try {
    final raw = await rootBundle.loadString('assets/maps/bundled_manifest.json');
    final decoded = jsonDecode(raw);
    if (decoded is! Map<String, dynamic>) return;
    final maps = decoded['maps'];
    if (maps is! List) return;
    final service = ref.read(abmMapServiceProvider);
    String? firstId;
    for (final item in maps) {
      if (item is! Map) continue;
      final id = item['id']?.toString().trim();
      final asset = item['asset']?.toString().trim();
      final version = item['version']?.toString().trim() ?? '';
      if (id == null || id.isEmpty || asset == null || asset.isEmpty) continue;
      firstId ??= id;
      await service.installBundledAsset(
        name: '$id.abm',
        assetPath: asset,
        version: version,
      );
    }
    final current = ref.read(abmActiveMapNameProvider);
    final currentId = current.replaceAll(RegExp(r'\.abm$'), '');
    final currentInstalled = currentId.isNotEmpty &&
        await service.isInstalled('$currentId.abm');
    if (!currentInstalled && firstId != null) {
      ref.read(abmActiveMapNameProvider.notifier).state = '$firstId.abm';
      ref.read(activeOfflineMapIdProvider.notifier).state = firstId;
      ref.read(routingEngineProvider.notifier).state = RoutingEngine.abtinmap;
      await ref.read(settingsRepositoryProvider).setValue(
            SettingsRepository.keyRoutingEngine,
            RoutingEngine.abtinmap.storageValue,
          );
    }
  } catch (error, stack) {
    AbmDebugLog.add('[BUNDLED ABM] bootstrap failed: $error\n$stack');
  }
});

final vectorMapServiceProvider = Provider<VectorMapService>((ref) {
  return VectorMapService();
});

/// شناسهٔ دادهٔ آفلاین انتخاب‌شده؛ شامل Vector/POI/Search/Routing در ABM است.
final activeOfflineMapIdProvider = StateProvider<String>((ref) => 'IR');

/// نام فایل نقشه‌ی فعال (فعلاً ایران).
final abmActiveMapNameProvider = StateProvider<String>((ref) => 'IR.abm');

/// موتور پیش‌فرض نصب تازه آنلاین است؛ نمایش آغازین کرهٔ زمین از همین حالت
/// استفاده می‌کند و کاربر پس از دانلود نقشه می‌تواند آفلاین را انتخاب کند.
final routingEngineProvider =
    StateProvider<RoutingEngine>((ref) => RoutingEngine.online);

/// آفلاین فقط وقتی فعال است که ABM جدیدِ Vector/POI/Search/Routing همان
/// منطقه نصب شده باشند. Atlas raster قدیمی دیگر شرط نمایش نقشه نیست.
Future<MapRegion?> _activeRegion(Ref ref) async {
  final id = ref.read(activeOfflineMapIdProvider);
  final catalog = await ref.read(mapCatalogProvider.future);
  return catalog.byId(id) ?? catalog.byId(id.toUpperCase());
}

Future<bool> hasActiveOfflineAtlas(Ref ref) async {
  final mapName = ref.read(abmActiveMapNameProvider);
  final mapService = ref.read(abmMapServiceProvider);
  if (!await mapService.isInstalled(mapName)) return false;
  // نصب بودن ABM و معتبر بودن محتوای آن منبع حقیقتِ حالت آفلاین است.
  // برای نقشهٔ ساخته‌شده با اسکریپت، وجود catalog شبکه‌ای نباید مانع رندر
  // شدن فایل محلی شود.
  final file = await mapService.localFile(mapName);
  return ref.read(vectorMapServiceProvider).isInstalled(containerFile: file);
}

final offlineAtlasReadyProvider = FutureProvider<bool>((ref) {
  ref.watch(abmActiveMapNameProvider);
  ref.watch(activeOfflineMapIdProvider);
  ref.watch(mapCatalogProvider);
  return hasActiveOfflineAtlas(ref);
});

final activeOfflineMapFileProvider = FutureProvider<File?>((ref) async {
  final ready = await ref.watch(offlineAtlasReadyProvider.future).catchError((_) => false);
  if (!ready) return null;
  return ref.read(abmMapServiceProvider).localFile(ref.read(abmActiveMapNameProvider));
});

/// مسیر style محلی آماده برای MapLibre. نبود آن یعنی دادهٔ آفلاین هنوز کامل
/// نشده و نباید به renderer raster قدیمی برگردیم.
final routingEngineInitProvider = FutureProvider<void>((ref) async {
  final repo = ref.watch(settingsRepositoryProvider);
  final saved = await repo.getValue(SettingsRepository.keyRoutingEngine);
  final requested = RoutingEngineX.parse(saved);
  final engine =
      requested == RoutingEngine.abtinmap && !await hasActiveOfflineAtlas(ref)
          ? RoutingEngine.online
          : requested;
  ref.read(routingEngineProvider.notifier).state = engine;
  if (engine != requested) {
    await repo.setValue(
        SettingsRepository.keyRoutingEngine, engine.storageValue);
  }
});

/// تغییر و ذخیرهٔ موتور مسیریابی؛ آفلاین بدون نقشهٔ دانلودشده پذیرفته نمی‌شود.
Future<void> setRoutingEngine(Ref ref, RoutingEngine engine) async {
  final resolved =
      engine == RoutingEngine.abtinmap && !await hasActiveOfflineAtlas(ref)
          ? RoutingEngine.online
          : engine;
  ref.read(routingEngineProvider.notifier).state = resolved;
  await ref
      .read(settingsRepositoryProvider)
      .setValue(SettingsRepository.keyRoutingEngine, resolved.storageValue);
}

/// نسخهٔ مصرفی از ویجت‌ها (WidgetRef).
Future<void> setRoutingEngineFromWidget(
    WidgetRef ref, RoutingEngine engine) async {
  final resolved = engine == RoutingEngine.abtinmap &&
          !await ref.read(offlineAtlasReadyProvider.future)
      ? RoutingEngine.online
      : engine;
  ref.read(routingEngineProvider.notifier).state = resolved;
  await ref
      .read(settingsRepositoryProvider)
      .setValue(SettingsRepository.keyRoutingEngine, resolved.storageValue);
}

/// آیا نقشه‌ی .abm فعال روی دستگاه نصب است؟
final abmInstalledProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(abmMapServiceProvider);
  return service.isInstalled(ref.watch(abmActiveMapNameProvider));
});

/// نسخه‌ی نصب‌شده‌ی نقشه (از فایل کنار .abm).
final abmInstalledVersionProvider = FutureProvider<String?>((ref) async {
  final service = ref.watch(abmMapServiceProvider);
  return service.installedVersion(ref.watch(abmActiveMapNameProvider));
});


/// وضعیت دانلود نقشه‌ی .abm
class AbmDownloadState {
  const AbmDownloadState({
    this.busy = false,
    this.received = 0,
    this.total,
    this.error,
    this.done = false,
  });

  final bool busy;
  final int received;
  final int? total;
  final String? error;
  final bool done;

  double? get fraction =>
      (total == null || total == 0) ? null : received / total!;

  AbmDownloadState copyWith({
    bool? busy,
    int? received,
    int? total,
    String? error,
    bool? done,
  }) =>
      AbmDownloadState(
        busy: busy ?? this.busy,
        received: received ?? this.received,
        total: total ?? this.total,
        error: error,
        done: done ?? this.done,
      );
}

class AbmDownloadController extends StateNotifier<AbmDownloadState> {
  AbmDownloadController(this._ref) : super(const AbmDownloadState());

  final Ref _ref;

  Future<File?> download({bool force = false}) async {
    final service = _ref.read(abmMapServiceProvider);
    final name = _ref.read(abmActiveMapNameProvider);
    final id = name.toLowerCase().endsWith('.abm')
        ? name.substring(0, name.length - 4)
        : name;
    state = const AbmDownloadState(busy: true);
    try {
      final catalog = await _ref.read(mapCatalogServiceProvider).load();
      final region = catalog.byId(id) ?? catalog.byId(id.toUpperCase());
      final File file;
      if (region != null) {
        file = await service.downloadRegion(
          id: region.id,
          files: region.effectiveFiles,
          downloadBase: region.effectiveDownloadBase,
          totalSizeBytes: region.totalSizeBytes,
          expectedSha256: region.version,
          force: force,
          onProgress: (p) {
            state = state.copyWith(received: p.received, total: p.total);
          },
        );
      } else {
        // مانیفست در دسترس نبود؛ تلاش برای دانلود مستقیم با آدرس پیش‌فرض.
        file = await service.download(
          name,
          force: force,
          onProgress: (p) {
            state = state.copyWith(received: p.received, total: p.total);
          },
        );
      }
      state = state.copyWith(busy: false, done: true);
      _ref.invalidate(abmInstalledProvider);
      _ref.invalidate(abmInstalledVersionProvider);
      return file;
    } catch (error) {
      state = AbmDownloadState(
          busy: false, error: 'دانلود نقشه ناموفق بود: $error');
      return null;
    }
  }

  Future<void> delete() async {
    final service = _ref.read(abmMapServiceProvider);
    await service.deleteMap(_ref.read(abmActiveMapNameProvider));
    state = const AbmDownloadState();
    _ref.invalidate(abmInstalledProvider);
    _ref.invalidate(abmInstalledVersionProvider);
  }
}

final abmDownloadControllerProvider =
    StateNotifierProvider<AbmDownloadController, AbmDownloadState>(
        (ref) => AbmDownloadController(ref));

/// آیا نسخه‌ی جدیدتری از نقشه در manifest هست؟
final abmUpdateAvailableProvider = FutureProvider<bool>((ref) async {
  final name = ref.watch(abmActiveMapNameProvider);
  final id = name.toLowerCase().endsWith('.abm')
      ? name.substring(0, name.length - 4)
      : name;
  final service = ref.watch(abmMapServiceProvider);
  if (!await service.isInstalled(name)) return false;

  MapCatalog catalog;
  try {
    catalog = await ref.watch(mapCatalogServiceProvider).load();
  } catch (_) {
    return false;
  }
  final region = catalog.byId(id) ?? catalog.byId(id.toUpperCase());
  if (region == null || region.version.isEmpty) return false;
  final installed = await service.installedVersion(name);
  return installed != null && installed != region.version;
});
