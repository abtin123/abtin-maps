import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../gps/presentation/gps_providers.dart';
import '../data/weather_service.dart';

final weatherProvider = FutureProvider.autoDispose<WeatherData?>((ref) async {
  final pos = ref.watch(vehiclePositionProvider).value;
  if (pos == null) return null;
  
  // Update weather every 15 minutes or when position changes significantly
  return await WeatherService.getWeather(pos.lat, pos.lng);
});
