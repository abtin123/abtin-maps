import '../../../abtinmap/abm_map_service.dart';
import '../../../core/abm_debug_log.dart';
import '../../../core/database/app_database.dart';
import 'map_catalog.dart';

class WeeklyMapUpdateService {
  WeeklyMapUpdateService(this._maps, this._catalog, this._db);
  final AbmMapService _maps;
  final MapCatalogService _catalog;
  final AppDatabase _db;
  static const _key = 'weekly_map_update_check';
  Future<void> checkAndUpdate() async {
    try {
      final row = await (_db.select(_db.appSettings)..where((t) => t.key.equals(_key))).getSingleOrNull();
      final last = row == null ? null : DateTime.tryParse(row.value);
      if (last != null && DateTime.now().difference(last) < const Duration(days: 7)) return;
      final catalog = await _catalog.load(forceRefresh: true);
      for (final region in catalog.regions) {
        if (!await _maps.isInstalled(region.abmFileName)) continue;
        await _maps.downloadRegion(id: region.id, files: region.effectiveFiles, patch: region.patch, downloadBase: region.effectiveDownloadBase, totalSizeBytes: region.totalSizeBytes, expectedSha256: region.version);
      }
      await _db.into(_db.appSettings).insertOnConflictUpdate(AppSettingsCompanion.insert(key: _key, value: DateTime.now().toIso8601String()));
    } catch (e, st) { AbmDebugLog.add('[WEEKLY MAP UPDATE] failed: $e\n$st'); }
  }
}
