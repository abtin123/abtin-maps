import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'package:http/http.dart' as http;
import 'package:maplibre_gl/maplibre_gl.dart';

class RouteInfo {
  final List<LatLng> geometry;
  final double distanceKm;
  final double durationMin;
  final List<RouteInstruction> instructions;

  const RouteInfo({
    required this.geometry,
    required this.distanceKm,
    required this.durationMin,
    required this.instructions,
  });
}

class RouteInstruction {
  final String text;
  final double distanceMeters;
  final LatLng location;
  final String type;
  final String? modifier;
  final int? exit;

  const RouteInstruction({
    required this.text,
    required this.distanceMeters,
    required this.location,
    required this.type,
    this.modifier,
    this.exit,
  });
}

class RoutingService {
  static const String _baseUrl = 'https://router.project-osrm.org';

  String? lastError;

  Future<RouteInfo?> calculateRoute({
    required LatLng origin,
    required LatLng destination,
  }) async {
    lastError = null;

    final originClean = _sanitizeCoordinate(origin);
    final destinationClean = _sanitizeCoordinate(destination);
    if (originClean == null || destinationClean == null) {
      lastError = 'مختصات نامعتبر (NaN/Infinity) برای مسیریابی دریافت شد';
      print('خطا در محاسبه مسیر: $lastError');
      return null;
    }

    try {
      final url = Uri.parse(
        '$_baseUrl/route/v1/driving/'
        '${originClean.longitude},${originClean.latitude};'
        '${destinationClean.longitude},${destinationClean.latitude}'
        '?overview=full&geometries=geojson&steps=true',
      );

      final response = await http
          .get(
            url,
            headers: const {
              'User-Agent': 'AbtinNavigator/1.0 (ir.abtin.abtin_navigator)',
              'Accept': 'application/json',
            },
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode != 200) {
        final bodySnippet = response.body.length > 160
            ? '${response.body.substring(0, 160)}…'
            : response.body;
        lastError = 'HTTP ${response.statusCode} از سرور مسیریابی — $bodySnippet';
        print('خطا در محاسبه مسیر: $lastError');
        return null;
      }

      final data = json.decode(response.body);

      if (data['code'] != 'Ok' || data['routes'] == null || data['routes'].isEmpty) {
        lastError = 'پاسخ سرور بدون مسیر معتبر بود (code: ${data['code']})';
        print('خطا در محاسبه مسیر: $lastError');
        return null;
      }

      final route = data['routes'][0];
      
      final geometryData = route['geometry']['coordinates'] as List;
      final geometry = geometryData.map((coord) {
        return LatLng((coord[1] as num).toDouble(), (coord[0] as num).toDouble());
      }).toList();

      final instructions = <RouteInstruction>[];
      final legs = route['legs'] as List;
      
      for (var leg in legs) {
        final steps = leg['steps'] as List;
        for (var step in steps) {
          final maneuver = step['maneuver'];
          final location = maneuver['location'];
          
          final exitVal = maneuver['exit'];
          instructions.add(RouteInstruction(
            text: _convertInstructionToPersian(step),
            distanceMeters: (step['distance'] as num).toDouble(),
            location: LatLng((location[1] as num).toDouble(), (location[0] as num).toDouble()),
            type: maneuver['type'] as String? ?? 'turn',
            modifier: maneuver['modifier'] as String?,
            exit: exitVal is num ? exitVal.toInt() : null,
          ));
        }
      }

      return RouteInfo(
        geometry: geometry,
        distanceKm: (route['distance'] as num).toDouble() / 1000,
        durationMin: (route['duration'] as num).toDouble() / 60,
        instructions: instructions,
      );
    } on TimeoutException {
      lastError = 'پاسخی از سرور مسیریابی در ۱۵ ثانیه نرسید (تایم‌اوت شبکه)';
      print('خطا در محاسبه مسیر: $lastError');
      return null;
    } catch (e) {
      lastError = 'خطای شبکه/اتصال: $e';
      print('خطا در محاسبه مسیر: $lastError');
      return null;
    }
  }

  RouteInfo straightLineFallback(LatLng origin, LatLng destination) {
    final distanceM = _haversine(origin, destination);
    return RouteInfo(
      geometry: [origin, destination],
      distanceKm: distanceM / 1000,
      durationMin: (distanceM / 1000) / 45 * 60,
      instructions: [
        RouteInstruction(
          text: 'به سمت مقصد حرکت کنید (مسیر آفلاین تقریبی)',
          distanceMeters: distanceM,
          location: origin,
          type: 'depart',
        ),
        RouteInstruction(
          text: 'به مقصد رسیدید',
          distanceMeters: 0,
          location: destination,
          type: 'arrive',
        ),
      ],
    );
  }

  LatLng? _sanitizeCoordinate(LatLng coord) {
    final lat = coord.latitude;
    final lng = coord.longitude;
    if (lat.isNaN || lat.isInfinite || lng.isNaN || lng.isInfinite) {
      return null;
    }
    double round6(double v) => (v * 1000000).round() / 1000000;
    return LatLng(round6(lat), round6(lng));
  }

  double _haversine(LatLng a, LatLng b) {
    const r = 6371000.0;
    final dLat = (b.latitude - a.latitude) * math.pi / 180;
    final dLng = (b.longitude - a.longitude) * math.pi / 180;
    final la1 = a.latitude * math.pi / 180;
    final la2 = b.latitude * math.pi / 180;
    final h = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(la1) * math.cos(la2) * math.sin(dLng / 2) * math.sin(dLng / 2);
    return r * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h));
  }

  String _convertInstructionToPersian(Map<String, dynamic> step) {
    final maneuver = step['maneuver'];
    final type = maneuver['type'] as String? ?? '';
    final modifier = maneuver['modifier'] as String? ?? '';
    final name = step['name'] as String? ?? '';
    final exit = maneuver['exit'];

    if (type == 'depart') {
      return 'حرکت کنید${name.isNotEmpty ? ' در $name' : ''}';
    }
    if (type == 'arrive') {
      return name.isNotEmpty ? 'به مقصد رسیدید ($name)' : 'به مقصد رسیدید';
    }

    if (type == 'roundabout' || type == 'rotary') {
      final exitText = (exit is num) ? ' و از خروجی ${_ordinalFa(exit.toInt())} خارج شوید' : '';
      final nameText = name.isNotEmpty ? ' به $name' : '';
      return 'وارد میدان شوید$exitText$nameText'.trim();
    }

    String direction = '';
    if (modifier.contains('sharp right')) {
      direction = 'کاملاً به راست';
    } else if (modifier.contains('sharp left')) {
      direction = 'کاملاً به چپ';
    } else if (modifier.contains('slight right')) {
      direction = 'کمی به راست';
    } else if (modifier.contains('slight left')) {
      direction = 'کمی به چپ';
    } else if (modifier.contains('uturn')) {
      direction = 'دور بزنید';
    } else if (modifier.contains('right')) {
      direction = 'به راست';
    } else if (modifier.contains('left')) {
      direction = 'به چپ';
    } else if (modifier.contains('straight')) {
      direction = 'مستقیم';
    }

    String action = '';
    if (type == 'turn') {
      action = 'بپیچید';
    } else if (type == 'new name' || type == 'continue') {
      action = 'ادامه دهید';
    } else if (type == 'merge') {
      action = 'ادغام شوید';
    } else if (type == 'on ramp' || type == 'off ramp') {
      action = 'وارد شوید';
    } else if (type == 'fork') {
      action = 'مسیر را انتخاب کنید';
    } else if (type == 'end of road') {
      action = 'در انتهای خیابان بپیچید';
    }
    if (action.isEmpty) action = 'ادامه دهید';

    final nameText = name.isNotEmpty ? ' به $name' : '';
    return '$action $direction$nameText'.trim();
  }

  String _ordinalFa(int n) {
    const words = ['', 'اول', 'دوم', 'سوم', 'چهارم', 'پنجم', 'ششم', 'هفتم', 'هشتم'];
    return (n >= 1 && n < words.length) ? words[n] : '$n';
  }
}
