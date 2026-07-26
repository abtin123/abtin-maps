import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/voice_service.dart';
import '../data/voice_pack_fa.dart';
import '../../settings/presentation/settings_repository_provider.dart';
import '../../settings/data/settings_repository.dart';

final ttsServiceProvider = Provider<VoiceService>((ref) {
  final service = VoiceService();
  ref.onDispose(service.dispose);
  return service;
});

final ttsStateProvider = StateProvider<VoiceState>((ref) {
  return VoiceState.stopped;
});

final ttsGenderProvider = StateNotifierProvider<TtsGenderNotifier, VoiceGender>((ref) {
  return TtsGenderNotifier(ref.watch(settingsRepositoryProvider));
});

class TtsGenderNotifier extends StateNotifier<VoiceGender> {
  final SettingsRepository repo;
  TtsGenderNotifier(this.repo) : super(VoiceGender.female) {
    _load();
  }

  Future<void> _load() async {
    final v = await repo.getValue(SettingsRepository.keyVoiceGender);
    final gender = v == 'male' ? VoiceGender.male : VoiceGender.female;
    VoicePackFa.setGender(gender);
    state = gender;
  }

  Future<void> set(VoiceGender gender) async {
    state = gender;
    VoicePackFa.setGender(gender);
    await repo.setValue(SettingsRepository.keyVoiceGender, gender == VoiceGender.male ? 'male' : 'female');
  }
}

final ttsRateProvider = StateNotifierProvider<_DoubleSettingNotifier, double>((ref) {
  return _DoubleSettingNotifier(
    ref.watch(settingsRepositoryProvider),
    SettingsRepository.keyVoiceRate,
    1.0,
  );
});

final ttsVolumeProvider = StateNotifierProvider<_DoubleSettingNotifier, double>((ref) {
  return _DoubleSettingNotifier(
    ref.watch(settingsRepositoryProvider),
    SettingsRepository.keyVoiceVolume,
    0.75,
  );
});

final ttsEngineProvider = StateNotifierProvider<TtsEngineNotifier, VoiceEngine>((ref) {
  return TtsEngineNotifier(
    ref.watch(settingsRepositoryProvider),
    ref.watch(ttsServiceProvider),
  );
});

class TtsEngineNotifier extends StateNotifier<VoiceEngine> {
  final SettingsRepository repo;
  final VoiceService service;
  static const key = 'voice_engine';

  TtsEngineNotifier(this.repo, this.service) : super(VoiceEngine.assets) {
    _load();
  }

  Future<void> _load() async {
    final v = await repo.getValue(key);
    final engine = v == 'tts' ? VoiceEngine.tts : VoiceEngine.assets;
    service.setEngine(engine);
    state = engine;
  }

  Future<void> set(VoiceEngine engine) async {
    state = engine;
    service.setEngine(engine);
    await repo.setValue(key, engine == VoiceEngine.tts ? 'tts' : 'assets');
  }
}

class _DoubleSettingNotifier extends StateNotifier<double> {
  final SettingsRepository repo;
  final String key;
  _DoubleSettingNotifier(this.repo, this.key, double fallback) : super(fallback) {
    _load(fallback);
  }

  Future<void> _load(double fallback) async {
    state = await repo.getDouble(key, fallback: fallback);
  }

  Future<void> set(double value) async {
    state = value;
    await repo.setDouble(key, value);
  }
}

final ttEnabledProvider = StateNotifierProvider<_BoolSettingNotifier, bool>((ref) {
  return _BoolSettingNotifier(
    ref.watch(settingsRepositoryProvider),
    SettingsRepository.keyVoiceEnabled,
    true,
  );
});

class _BoolSettingNotifier extends StateNotifier<bool> {
  final SettingsRepository repo;
  final String key;
  _BoolSettingNotifier(this.repo, this.key, bool fallback) : super(fallback) {
    _load(fallback);
  }

  Future<void> _load(bool fallback) async {
    state = await repo.getBool(key, fallback: fallback);
  }

  Future<void> set(bool value) async {
    state = value;
    await repo.setBool(key, value);
  }
}
