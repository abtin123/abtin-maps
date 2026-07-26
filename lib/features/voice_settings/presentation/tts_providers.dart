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
