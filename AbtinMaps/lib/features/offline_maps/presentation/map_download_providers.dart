import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/abm_debug_log.dart';
import '../../../abtinmap/abm_map_service.dart';
import '../../../shared/providers/abtinmap_providers.dart';
import '../../../shared/providers/map_style_providers.dart';
import '../data/map_catalog.dart';
import '../data/vector_map_service.dart';
import '../../routing/data/routing_provider.dart';

/// وضعیت دانلود مستقل هر کشور (برخلاف [AbmDownloadController] که فقط یک
/// نقشه‌ی «فعال» را مدیریت می‌کند، اینجا هر [MapRegion] وضعیت جدای خودش را
/// دارد تا چند کارت هم‌زمان بتوانند در حال دانلود/توقف/نصب باشند).
class RegionDownloadState {
  const RegionDownloadState({
    this.downloading = false,
    this.received = 0,
    this.total,
    this.error,
  });

  final bool downloading;
  final int received;
  final int? total;
  final String? error;

  double? get fraction =>
      (total == null || total == 0) ? null : (received / total!).clamp(0, 1);

  RegionDownloadState copyWith({
    bool? downloading,
    int? received,
    int? total,
    String? error,
  }) =>
      RegionDownloadState(
        downloading: downloading ?? this.downloading,
        received: received ?? this.received,
        total: total ?? this.total,
        error: error,
      );
}

class RegionDownloadController extends StateNotifier<RegionDownloadState> {
  RegionDownloadController(this._ref, this._region)
      : super(const RegionDownloadState());

  final Ref _ref;
  final MapRegion _region;
  bool _cancelled = false;

  /// این پروایدر `autoDispose` است: با خروج از صفحهٔ دانلود (مثلاً برگشتن به
  /// تنظیمات)، به‌محض این‌که هیچ ویجتی دیگر آن را `watch` نکند، ریوِرپاد
  /// بلافاصله `StateNotifier` را `dispose` می‌کند. اما دانلود شبکه‌ای در پس‌زمینه
  /// (داخل `AbmMapService`, که خودش `autoDispose` نیست) هم‌چنان ادامه دارد و
  /// در هر chunk سعی می‌کند `state` را به‌روزرسانی کند؛ نوشتن روی یک
  /// StateNotifier از بین‌رفته خطا پرتاب می‌کند و کل دانلود را وسط راه با
  /// استثنا متوقف می‌کند — همان چیزی که باعث می‌شد کاربر با برگشتن به صفحه
  /// دوباره «نصب‌نشده» ببیند و مجبور به دانلود از نو شود.
  ///
  /// راه‌حل: تا پایان دانلود (موفق/خطا/لغو) با `ref.keepAlive()` از حذف
  /// زودهنگام این پروایدر جلوگیری می‌کنیم؛ و برای اطمینان بیشتر پیش از هر
  /// تغییر state هم [mounted] را چک می‌کنیم.
  KeepAliveLink? _keepAliveLink;

  Future<void> start() async {
    if (state.downloading) return;
    _cancelled = false;
    state = const RegionDownloadState(downloading: true);
    _keepAliveLink ??= _ref.keepAlive();
    final service = _ref.read(abmMapServiceProvider);
    final vector = _region.vectorMap;
    final vectorService = _ref.read(vectorMapServiceProvider);
    try {
      final onProgress = (AbmDownloadProgress p) {
        if (_cancelled || !mounted) return;
        state = state.copyWith(
          received: p.received,
          total: _region.totalSizeBytes > 0 ? _region.totalSizeBytes : p.total,
        );
      };
      if (_region.isBundledAsset) {
        await service.installBundledAsset(
          name: _region.abmFileName,
          assetPath: _region.bundledAsset,
          version: _region.version,
          onProgress: onProgress,
        );
      } else {
        await service.downloadRegion(
          id: _region.id,
          files: _region.effectiveFiles,
          patch: _region.patch,
          downloadBase: _region.effectiveDownloadBase,
          totalSizeBytes: _region.totalSizeBytes,
          expectedSha256: _region.version,
          onProgress: onProgress,
          isCancelled: () => _cancelled,
        );
      }
      if (_cancelled) throw const AbmDownloadCancelled();
      final containerFile = await service.localFile(_region.abmFileName);
      await vectorService.prepare(containerFile: containerFile, id: _region.id, onProgress: (v) {
        if (!mounted || _cancelled) return;
        state = state.copyWith(received: (_region.totalSizeBytes * v).round(), total: _region.totalSizeBytes);
      });
      if (!await vectorService.isInstalled(containerFile: containerFile)) {
        throw const VectorMapInstallException(
          'فایل ABM دانلودشده با معماری Vector ABM سازگار نیست.',
        );
      }
      if (!mounted) return;
      if (_cancelled) {
        state = const RegionDownloadState();
        return;
      }
      state = const RegionDownloadState();
      // فعال‌سازی فقط پس از اعتبارسنجی Vector/Search/POI/Routing در ABM.
      _ref.read(abmActiveMapNameProvider.notifier).state = _region.abmFileName;
      _ref.read(activeOfflineMapIdProvider.notifier).state = _region.id;
      _ref.invalidate(abmInstalledMapIdsProviderFamily(_region.id));
      _ref.invalidate(abmInstalledProvider);
      _ref.invalidate(abmInstalledVersionProvider);
      _ref.invalidate(offlineAtlasReadyProvider);
      _ref.invalidate(resolvedMapStyleProvider);
    } on AbmDownloadCancelled {
      if (mounted) state = const RegionDownloadState();
    } catch (error, stack) {
      AbmDebugLog.add(
        '[MAP DOWNLOAD] region=${_region.id} name=${_region.abmFileName} '
        'base=${_region.effectiveDownloadBase} failed: $error\n$stack',
      );
      if (mounted) state = RegionDownloadState(error: '$error');
    } finally {
      _keepAliveLink?.close();
      _keepAliveLink = null;
    }
  }

  /// دانلودِ در حال اجرا را بلافاصله (وسط دریافت chunk فعلی) لغو می‌کند.
  /// چون بخشِ نیمه‌دانلودشده روی دیسک (`*.part`) نگه داشته می‌شود و سرور از
  /// هدر `Range` پشتیبانی می‌کند، دفعه‌ی بعد که «شروع» زده شود دانلود از همان
  /// نقطه ادامه پیدا می‌کند — نه از صفر؛ در عمل همان تجربه‌ی «مکث و ادامه».
  void pause() {
    _cancelled = true;
  }

  Future<void> delete() async {
    final service = _ref.read(abmMapServiceProvider);
    await service.deleteMap(_region.abmFileName);
    await _ref.read(vectorMapServiceProvider).delete(_region.id);
    state = const RegionDownloadState();
    _ref.invalidate(abmInstalledMapIdsProviderFamily(_region.id));
    _ref.invalidate(abmInstalledProvider);
    _ref.invalidate(abmInstalledVersionProvider);
    // اگر همین نقشه فعال بود، providerهای داده نیز باید invalidate شوند تا
    // routing و search به فایل حذف‌شده اشاره نکنند.
    if (_ref.read(abmActiveMapNameProvider) == _region.abmFileName) {
      _ref.read(abmActiveMapNameProvider.notifier).state = '__none__.abm';
      _ref.read(activeOfflineMapIdProvider.notifier).state = '';
      await setRoutingEngine(_ref, RoutingEngine.online);
    }
    _ref.invalidate(offlineAtlasReadyProvider);
    _ref.invalidate(resolvedMapStyleProvider);
  }
}

final regionDownloadControllerProvider = StateNotifierProvider.family
    .autoDispose<RegionDownloadController, RegionDownloadState, MapRegion>(
        (ref, region) => RegionDownloadController(ref, region));

/// آیا نقشه‌ی این کشور مشخص روی دستگاه نصب است؟ (خانواده‌ی سبک برای
/// invalidation دقیق به‌جای رفرش کل لیست).
final abmInstalledMapIdsProviderFamily =
    FutureProvider.family.autoDispose<bool, String>((ref, regionId) async {
  final service = ref.watch(abmMapServiceProvider);
  return service.isInstalled('$regionId.abm');
});
