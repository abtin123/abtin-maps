import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/database/app_database.dart';
import '../../features/settings/data/settings_repository.dart';
import '../../features/settings/presentation/settings_repository_provider.dart';
import '../../features/settings/presentation/appearance_settings_providers.dart';
import '../../features/settings/domain/appearance_settings.dart';
import '../../features/dashcam/presentation/dashcam_settings_providers.dart';
import '../../features/hud/presentation/hud_settings_providers.dart';
import 'map_style_providers.dart';
import 'abtinmap_providers.dart';
import 'abm_poi_visibility_providers.dart';
import '../../features/routing/data/routing_provider.dart';
import '../../features/language_settings/presentation/language_pack_providers.dart';
import 'app_notice_provider.dart';

export '../../features/settings/domain/appearance_settings.dart'
    show MapPerspective;

// رنگ برند طبق طراحی مرجع HTML: --purple-2:#8a3fd0
const defaultAppPrimaryColor = Color(0xFF8A3FD0);

/// رنگ‌های پیشنهادی که در صفحهٔ ظاهر نمایش داده می‌شوند — هشت‌تایی، طبق
/// طراحیِ مرجعِ صفحهٔ تنظیمات ظاهری.
const appColorPresets = <Color>[
  defaultAppPrimaryColor,
  Color(0xFF7C4DFF),
  Color(0xFF2F6FE0),
  Color(0xFF3FD0E0),
  Color(0xFF52C24C),
  Color(0xFFE0D23F),
  Color(0xFFE0973F),
  Color(0xFFE0523F),
];

final languageProvider = StateProvider<String>((ref) => 'fa');

/// حالتِ تیره/روشن/سیستم — مشتق از [appearanceSettingsProvider]، برای
/// سازگاری با main.dart که مستقیماً این Provider را می‌خواند.
final themeModeProvider = Provider<ThemeMode>(
    (ref) => ref.watch(appearanceSettingsProvider).themeMode);

/// رنگ اصلیِ UI — مشتق از [appearanceSettingsProvider].
final primaryColorProvider = Provider<Color>(
    (ref) => ref.watch(appearanceSettingsProvider).primaryColor);

/// زاویهٔ نمایش نقشه (۲بعدی/۳بعدی) — مشتق از [appearanceSettingsProvider].
final mapPerspectiveProvider = Provider<MapPerspective>(
    (ref) => ref.watch(appearanceSettingsProvider).mapPerspective);

/// یک رنگ را با آلفای کامل برای کاربرد به‌عنوان رنگ اصلی UI نرمال می‌کند.
/// رنگ‌های ذخیره‌شده در نسخه‌های قبل ممکن است کانال آلفای نادرست داشته باشند.
Color normalizeAppPrimaryColor(Color color) {
  return Color(0xFF000000 | (color.value & 0x00FFFFFF));
}

/// Loads persisted app-level settings once at startup.
final appSettingsInitProvider = FutureProvider<void>((ref) async {
  final repo = ref.watch(settingsRepositoryProvider);

  // خواندن کلیدهای مستقل دیسک را موازی شروع می‌کنیم؛ قبلاً این عملیات پشت‌سرهم
  // بود و هر read یک تأخیر جدا به cold start اضافه می‌کرد.
  final savedEngineFuture = repo.getValue(SettingsRepository.keyRoutingEngine);
  final savedLangFuture = repo.getValue(SettingsRepository.keyLanguage);
  final savedActiveMapFuture =
      repo.getValue(SettingsRepository.keyActiveMapName);
  final savedMapDisplayModeFuture =
      repo.getValue(SettingsRepository.keyMapDisplayMode);
  final downloadedLanguagesFuture =
      ref.read(downloadedLanguagesProvider.notifier).loadFromDiskAndReturn();

  final downloadedLanguages = await downloadedLanguagesFuture;
  final savedEngine = await savedEngineFuture;
  ref.read(routingEngineProvider.notifier).state =
      RoutingEngineX.parse(savedEngine);

  // زبان باید بعد از خواندن فهرست بسته‌های دانلودشده اعمال شود.
  final savedLang = await savedLangFuture;
  if (savedLang == 'en' ||
      savedLang == 'fa' ||
      (savedLang != null && downloadedLanguages.contains(savedLang))) {
    ref.read(languageProvider.notifier).state = savedLang!;
  }

  final savedActiveMap = await savedActiveMapFuture;
  if (savedActiveMap != null && savedActiveMap.isNotEmpty) {
    ref.read(abmActiveMapNameProvider.notifier).state = savedActiveMap;
  }

  // تنظیمات مستقل را هم‌زمان می‌خوانیم؛ ترتیب آن‌ها به یکدیگر وابسته نیست.
  await Future.wait<void>([
    ref.read(appearanceSettingsProvider.notifier).load(),
    ref.read(appNoticeProvider.notifier).load(),
    ref.read(offlineLightPaletteProvider.notifier).load(),
    ref.read(offlineDarkPaletteProvider.notifier).load(),
    ref.read(abmPoiVisibilityProvider.notifier).load(),
    ref.read(dashCamSettingsProvider.notifier).load(),
    ref.read(hudSettingsProvider.notifier).load(),
  ]);

  final savedMapDisplayMode = await savedMapDisplayModeFuture;
  final savedThemeIsLight =
      ref.read(appearanceSettingsProvider).themeMode == ThemeMode.light;
  if (savedMapDisplayMode == MapStyleMode.day.name) {
    ref.read(mapStyleModeProvider.notifier).state = MapStyleMode.day;
  } else if (savedMapDisplayMode == MapStyleMode.night.name) {
    ref.read(mapStyleModeProvider.notifier).state = MapStyleMode.night;
  } else if (savedThemeIsLight) {
    ref.read(mapStyleModeProvider.notifier).state = MapStyleMode.day;
  }
});

class AppSettingsNotifier extends StateNotifier<Map<String, String>> {
  final AppDatabase db;

  AppSettingsNotifier(this.db) : super({});

  Future<void> loadSettings() async {
    final settings = await db.select(db.appSettings).get();
    state = {for (final setting in settings) setting.key: setting.value};
  }

  Future<void> updateSetting(String key, String value) async {
    await db.into(db.appSettings).insertOnConflictUpdate(
          AppSettingsCompanion.insert(key: key, value: value),
        );
    state = {...state, key: value};
  }
}
