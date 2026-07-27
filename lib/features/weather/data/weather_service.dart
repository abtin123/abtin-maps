import 'dart:convert';
import 'package:http/http.dart' as http;

class WeatherData {
  final double temp;
  final String condition;
  final String iconCode;

  WeatherData({required this.temp, required this.condition, required this.iconCode});
}

class WeatherService {
  // Using Open-Meteo (Free, no API key required for basic use)
  static Future<WeatherData?> getWeather(double lat, double lng) async {
    try {
      final url = Uri.parse('https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lng&current_weather=true');
      final response = await http.get(url);
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final current = data['current_weather'];
        return WeatherData(
          temp: current['temperature'].toDouble(),
          condition: _getConditionText(current['weathercode']),
          iconCode: current['weathercode'].toString(),
        );
      }
    } catch (e) {
      print('Weather Error: $e');
    }
    return null;
  }

  static String _getConditionText(int code) {
    if (code == 0) return 'صاف';
    if (code <= 3) return 'نیمه ابری';
    if (code <= 48) return 'مه‌آلود';
    if (code <= 55) return 'باران ریز';
    if (code <= 65) return 'بارانی';
    if (code <= 75) return 'برفی';
    if (code <= 82) return 'رگبار';
    if (code <= 99) return 'طوفانی';
    return 'نامشخص';
  }
}
