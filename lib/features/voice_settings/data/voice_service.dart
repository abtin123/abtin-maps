import 'package:audioplayers/audioplayers.dart';
import 'voice_pack_fa.dart';

enum VoiceState { playing, stopped }

class VoiceService {
  final AudioPlayer _player = AudioPlayer();
  VoiceState _state = VoiceState.stopped;

  double _volume = 0.75;
  double _playbackRate = 1.0;

  int _generation = 0;

  VoiceService() {
    _player.setReleaseMode(ReleaseMode.stop);
  }

  Future<void> setVolume(double volume) async {
    _volume = volume.clamp(0.0, 1.0);
    await _player.setVolume(_volume);
  }

  Future<void> setPlaybackRate(double rate) async {
    _playbackRate = rate.clamp(0.5, 2.0);
    try {
      await _player.setPlaybackRate(_playbackRate);
    } catch (_) {
    }
  }

  Future<void> playSequence(List<String> files) async {
    if (files.isEmpty) return;
    final myGeneration = ++_generation;
    await _player.stop();
    _state = VoiceState.playing;

    for (final file in files) {
      if (myGeneration != _generation) return;
      try {
        await _player.play(AssetSource('${VoicePackFa.assetFolder}/$file'));
        await _player.onPlayerComplete.first.timeout(
          const Duration(seconds: 6),
          onTimeout: () => null,
        );
      } catch (_) {
        continue;
      }
    }

    if (myGeneration == _generation) _state = VoiceState.stopped;
  }

  Future<void> stop() async {
    _generation++;
    await _player.stop();
    _state = VoiceState.stopped;
  }

  Future<void> dispose() async {
    _generation++;
    await _player.dispose();
  }

  VoiceState get state => _state;
  double get volume => _volume;
  double get playbackRate => _playbackRate;
}
