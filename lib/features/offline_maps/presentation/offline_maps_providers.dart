import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:storage_space/storage_space.dart';
import '../data/map_catalog.dart';
import '../../../shared/providers/abtinmap_providers.dart';

/// فضای واقعیِ ذخیره‌سازی دستگاه (نه حجمِ فرضیِ نقشه‌ها). واحد: مگابایت.
class DeviceStorage {
  const DeviceStorage({required this.totalMb, required this.freeMb});
  final double totalMb;
  final double freeMb;
  double get usedMb => (totalMb - freeMb).clamp(0, totalMb);
}

final deviceStorageProvider =
    FutureProvider.autoDispose<DeviceStorage?>((ref) async {
  final space = await getStorageSpace(
    lowOnSpaceThreshold: 500 * 1024 * 1024, // 500MB
    fractionDigits: 1,
  );
  const bytesPerMb = 1024 * 1024;
  return DeviceStorage(
    totalMb: space.total / bytesPerMb,
    freeMb: space.free / bytesPerMb,
  );
});

final mapCatalogServiceProvider = Provider<MapCatalogService>((ref) {
  final service = MapCatalogService();
  ref.onDispose(service.dispose);
  return service;
});

/// شمارندهٔ تازه‌سازی دستی فهرست کشورها (دکمهٔ «بررسی به‌روزرسانی»).
final catalogRefreshProvider = StateProvider<int>((ref) => 0);

/// فهرست کشورهای قابل دانلود؛ از مانیفست ریلیز، با کش آفلاین.
final mapCatalogProvider = FutureProvider<MapCatalog>((ref) async {
  final refreshCount = ref.watch(catalogRefreshProvider);
  final catalog = await ref
      .watch(mapCatalogServiceProvider)
      .load(forceRefresh: refreshCount > 0);
  return catalog;
});

/// شناسهٔ (id) بسته‌هایی که فایل .abm‌شان واقعاً روی دستگاه نصب است — همان
/// چیزی که نقشهٔ اصلی (رندر آبتین) واقعاً از آن می‌خواند.
final abmInstalledMapIdsProvider =
    FutureProvider.autoDispose<Set<String>>((ref) async {
  final service = ref.watch(abmMapServiceProvider);
  final names = await service.installedMaps();
  return names.map((n) => p.basenameWithoutExtension(n)).toSet();
});

/// نقشه‌هایی که نسخهٔ جدیدتری در مانیفست دارند (بر اساس نسخهٔ فایل .abm نصب‌شده).
final updatableMapIdsProvider =
    FutureProvider.autoDispose<Set<String>>((ref) async {
  final catalog = await ref.watch(mapCatalogProvider.future);
  final service = ref.watch(abmMapServiceProvider);
  final out = <String>{};
  for (final region in catalog.regions) {
    final installed = await service.installedVersion(region.abmFileName);
    if (installed != null && installed != region.version) {
      out.add(region.id);
    }
  }
  return out;
});
