import 'dart:async';
import 'dart:io';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

enum VoiceState { playing, stopped }

class VoiceService {
  final AudioPlayer _player = AudioPlayer();
  VoiceState _state = VoiceState.stopped;
  sherpa.OfflineTts? _tts;

  double _volume = 0.75;
  double _playbackRate = 1.0;
  int _generation = 0;

  VoiceService() {
    _player.setReleaseMode(ReleaseMode.stop);
    _initTts();
  }

  Future<void> _initTts() async {
    try {
      // Setup Sherpa-ONNX with a Persian VITS model
      // Note: You need to place these files in assets/models/tts/
      final modelPath = await _copyAssetToLocal('assets/models/tts/fa_vits.onnx');
      final lexiconPath = await _copyAssetToLocal('assets/models/tts/lexicon.txt');
      final tokensPath = await _copyAssetToLocal('assets/models/tts/tokens.txt');

      final config = sherpa.OfflineTtsConfig(
        model: sherpa.OfflineTtsModelConfig(
          vits: sherpa.OfflineTtsVitsModelConfig(
            model: modelPath,
            lexicon: lexiconPath,
            tokens: tokensPath,
          ),
          numThreads: 2,
          debug: false,
        ),
      );

      _tts = sherpa.OfflineTts(config);
    } catch (e) {
      print('Error initializing Sherpa-ONNX: $e');
    }
  }

  Future<String> _copyAssetToLocal(String assetPath) async {
    final byteData = await rootBundle.load(assetPath);
    final file = File('${(await getApplicationDocumentsDirectory()).path}/${assetPath.split('/').last}');
    await file.writeAsBytes(byteData.buffer.asUint8List(byteData.offsetInBytes, byteData.lengthInBytes));
    return file.path;
  }

  Future<void> speak(String text) async {
    if (_tts == null) return;
    final myGeneration = ++_generation;
    _state = VoiceState.playing;

    try {
      final audio = _tts!.generate(text);
      // Play the generated audio using a temporary file or byte stream
      final tempFile = File('${(await getTemporaryDirectory()).path}/tts_out.wav');
      // Note: sherpa_onnx returns raw samples, need to wrap in WAV or use a raw player
      // For now, we simulate the flow. You'll need to handle raw PCM to WAV conversion.
      await _player.play(DeviceFileSource(tempFile.path));
    } catch (e) {
      print('TTS Error: $e');
    }

    if (myGeneration == _generation) _state = VoiceState.stopped;
  }

  Future<void> setVolume(double volume) async {
    _volume = volume.clamp(0.0, 1.0);
    await _player.setVolume(_volume);
  }

  Future<void> setPlaybackRate(double rate) async {
    _playbackRate = rate.clamp(0.5, 2.0);
    await _player.setPlaybackRate(_playbackRate);
  }

  Future<void> stop() async {
    _generation++;
    await _player.stop();
    _state = VoiceState.stopped;
  }

  Future<void> dispose() async {
    _generation++;
    await _player.dispose();
    _tts?.free();
  }

  VoiceState get state => _state;
}
