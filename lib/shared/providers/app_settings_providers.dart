import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/database/app_database.dart';

final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.dark);
final languageProvider = StateProvider<String>((ref) => 'fa');

class AppSettingsNotifier extends StateNotifier<Map<String, String>> {
  final AppDatabase db;
  AppSettingsNotifier(this.db) : super({});

  Future<void> loadSettings() async {
    final settings = await db.select(db.appSettings).get();
    final map = {for (var s in settings) s.key: s.value};
    state = map;
  }

  Future<void> updateSetting(String key, String value) async {
    await db.into(db.appSettings).insertOnConflictUpdate(
      AppSettingsCompanion.insert(key: key, value: value),
    );
    state = {...state, key: value};
  }
}
