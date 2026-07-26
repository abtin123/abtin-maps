import 'package:drift/drift.dart';
import '../../../core/database/app_database.dart';

class SettingsRepository {
  final AppDatabase db;
  const SettingsRepository(this.db);

  static const keyVoiceGender = 'voice_gender';
  static const keyVoiceEnabled = 'voice_enabled';
  static const keyVoiceVolume = 'voice_volume';
  static const keyVoiceRate = 'voice_rate';
  static const keyThemeMode = 'theme_mode';
  static const keyMapStyle = 'map_style';

  Future<String?> getValue(String key) async {
    final row = await (db.select(db.appSettings)..where((t) => t.key.equals(key))).getSingleOrNull();
    return row?.value;
  }

  Future<void> setValue(String key, String value) async {
    await db.into(db.appSettings).insertOnConflictUpdate(
          AppSettingsCompanion.insert(key: key, value: value),
        );
  }

  Future<bool> getBool(String key, {required bool fallback}) async {
    final v = await getValue(key);
    if (v == null) return fallback;
    return v == 'true';
  }

  Future<void> setBool(String key, bool value) => setValue(key, value.toString());

  Future<double> getDouble(String key, {required double fallback}) async {
    final v = await getValue(key);
    if (v == null) return fallback;
    return double.tryParse(v) ?? fallback;
  }

  Future<void> setDouble(String key, double value) => setValue(key, value.toString());
}
