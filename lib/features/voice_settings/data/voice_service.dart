import 'dart:async';
import 'dart:io';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;
import 'voice_pack_fa.dart';

enum VoiceState { playing, stopped }
enum VoiceEngine { assets, tts }

class VoiceService {
  final AudioPlayer _player = AudioPlayer();
  VoiceState _state = VoiceState.stopped;
  VoiceEngine _engine = VoiceEngine.assets;
  sherpa.OfflineTts? _tts;

  double _volume = 0.75;
  double _playbackRate = 1.0;
  int _generation = 0;

  VoiceService() {
    _player.setReleaseMode(ReleaseMode.stop);
    _player.onPlayerStateChanged.listen((s) {
      if (s == PlayerState.completed || s == PlayerState.stopped) {
        _state = VoiceState.stopped;
      }
    });
    _initTts();
  }

  Future<void> _initTts() async {
    try {
      final appDocDir = await getApplicationDocumentsDirectory();
      final ttsDir = Directory('${appDocDir.path}/models/tts');
      if (!await ttsDir.exists()) {
        await ttsDir.create(recursive: true);
      }

      // We expect the models to be in assets/models/tts/
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
    try {
      final byteData = await rootBundle.load(assetPath);
      final file = File('${(await getApplicationDocumentsDirectory()).path}/${assetPath.split('/').last}');
      await file.writeAsBytes(byteData.buffer.asUint8List(byteData.offsetInBytes, byteData.lengthInBytes));
      return file.path;
    } catch (e) {
      print('Error copying asset $assetPath: $e');
      return '';
    }
  }

  void setEngine(VoiceEngine engine) {
    _engine = engine;
  }

  Future<void> playSequence(List<String> assetFiles) async {
    if (_engine == VoiceEngine.tts && _tts != null) {
      // For TTS, we should ideally convert the sequence to text.
      // For now, let's implement a simple mapper or just play assets if it's a specific sequence.
      // But the user wants "Dynamic TTS", so we'll likely use speak() for instructions.
      // If playSequence is called, we'll fall back to assets for now or handle it.
      await _playAssetSequence(assetFiles);
    } else {
      await _playAssetSequence(assetFiles);
    }
  }

  Future<void> _playAssetSequence(List<String> assetFiles) async {
    final myGeneration = ++_generation;
    _state = VoiceState.playing;

    for (final file in assetFiles) {
      if (myGeneration != _generation) break;
      final path = 'assets/${VoicePackFa.assetFolder}/$file';
      try {
        await _player.play(AssetSource(path.replaceFirst('assets/', '')));
        // Wait for current clip to finish
        await _player.onPlayerStateChanged.firstWhere((s) => s == PlayerState.completed || myGeneration != _generation);
      } catch (e) {
        print('Error playing asset $path: $e');
      }
    }

    if (myGeneration == _generation) _state = VoiceState.stopped;
  }

  Future<void> speak(String text) async {
    if (_tts == null) {
      print('TTS not initialized');
      return;
    }
    
    final myGeneration = ++_generation;
    _state = VoiceState.playing;

    try {
      final generatedAudio = _tts!.generate(text);
      final samples = generatedAudio.samples;
      final sampleRate = generatedAudio.sampleRate;

      // Create a WAV file from raw PCM samples
      final tempDir = await getTemporaryDirectory();
      final tempFile = File('${tempDir.path}/tts_out.wav');
      
      final wavBytes = _createWavHeader(samples, sampleRate);
      await tempFile.writeAsBytes(wavBytes);

      await _player.play(DeviceFileSource(tempFile.path));
      await _player.onPlayerStateChanged.firstWhere((s) => s == PlayerState.completed || myGeneration != _generation);
    } catch (e) {
      print('TTS Error: $e');
    }

    if (myGeneration == _generation) _state = VoiceState.stopped;
  }

  Uint8List _createWavHeader(Float32List samples, int sampleRate) {
    final int numSamples = samples.length;
    final int numChannels = 1;
    final int bitsPerSample = 16;
    final int byteRate = sampleRate * numChannels * bitsPerSample ~/ 8;
    final int blockAlign = numChannels * bitsPerSample ~/ 8;
    final int dataSize = numSamples * numChannels * bitsPerSample ~/ 8;
    final int fileSize = 36 + dataSize;

    final ByteData header = ByteData(44);
    header.setUint8(0, 0x52); // R
    header.setUint8(1, 0x49); // I
    header.setUint8(2, 0x46); // F
    header.setUint8(3, 0x46); // F
    header.setUint32(4, fileSize, Endian.little);
    header.setUint8(8, 0x57); // W
    header.setUint8(9, 0x41); // A
    header.setUint8(10, 0x56); // V
    header.setUint8(11, 0x45); // E
    
    header.setUint8(12, 0x66); // f
    header.setUint8(13, 0x6d); // m
    header.setUint8(14, 0x74); // t
    header.setUint8(15, 0x20); // ' '
    header.setUint32(16, 16, Endian.little); // Subchunk1Size
    header.setUint16(20, 1, Endian.little); // AudioFormat (PCM)
    header.setUint16(22, numChannels, Endian.little);
    header.setUint32(24, sampleRate, Endian.little);
    header.setUint32(28, byteRate, Endian.little);
    header.setUint16(32, blockAlign, Endian.little);
    header.setUint16(34, bitsPerSample, Endian.little);

    header.setUint8(36, 0x64); // d
    header.setUint8(37, 0x61); // a
    header.setUint8(38, 0x74); // t
    header.setUint8(39, 0x61); // a
    header.setUint32(40, dataSize, Endian.little);

    final Uint8List wavBytes = Uint8List(44 + dataSize);
    wavBytes.setAll(0, header.buffer.asUint8List());

    final int offset = 44;
    for (int i = 0; i < numSamples; i++) {
      // Clamp and convert float to 16-bit PCM
      int sample = (samples[i] * 32767).toInt();
      if (sample > 32767) sample = 32767;
      if (sample < -32768) sample = -32768;
      
      final int byteOffset = offset + (i * 2);
      wavBytes[byteOffset] = sample & 0xFF;
      wavBytes[byteOffset + 1] = (sample >> 8) & 0xFF;
    }

    return wavBytes;
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
  VoiceEngine get engine => _engine;
}
