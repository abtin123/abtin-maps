import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class MapStyle {
  const MapStyle({required this.background, required this.road, required this.motorway, required this.building, required this.water, required this.landuse, required this.boundary, required this.label});
  final Color background, road, motorway, building, water, landuse, boundary, label;
}

class StyleManager {
  static Future<MapStyle> load({required String name, bool dark = false}) async {
    final path = 'assets/styles/$name.json';
    try {
      final raw = jsonDecode(await rootBundle.loadString(path));
      if (raw is Map<String, dynamic>) {
        Color color(String key, Color fallback) {
          final value = raw[key];
          if (value is String) {
            final v = value.replaceFirst('#', '');
            final n = int.tryParse(v.length == 6 ? 'FF$v' : v, radix: 16);
            if (n != null) return Color(n);
          }
          return fallback;
        }
        return MapStyle(background: color('background', dark ? const Color(0xFF11151A) : const Color(0xFFF4F1E8)), road: color('road', dark ? const Color(0xFF89939C) : const Color(0xFF8D8D8D)), motorway: color('motorway', dark ? const Color(0xFFE2A15C) : const Color(0xFFD46A45)), building: color('building', dark ? const Color(0xFF343A40) : const Color(0xFFD9D4CA)), water: color('water', dark ? const Color(0xFF1E4C63) : const Color(0xFF9BCBE0)), landuse: color('landuse', dark ? const Color(0xFF273A2B) : const Color(0xFFD9E4CF)), boundary: color('boundary', dark ? const Color(0xFF66717A) : const Color(0xFF8E8E8E)), label: color('label', dark ? Colors.white : const Color(0xFF303030)));
      }
    } catch (_) {}
    return MapStyle(background: dark ? const Color(0xFF11151A) : const Color(0xFFF4F1E8), road: dark ? const Color(0xFF89939C) : const Color(0xFF8D8D8D), motorway: dark ? const Color(0xFFE2A15C) : const Color(0xFFD46A45), building: dark ? const Color(0xFF343A40) : const Color(0xFFD9D4CA), water: dark ? const Color(0xFF1E4C63) : const Color(0xFF9BCBE0), landuse: dark ? const Color(0xFF273A2B) : const Color(0xFFD9E4CF), boundary: dark ? const Color(0xFF66717A) : const Color(0xFF8E8E8E), label: dark ? Colors.white : const Color(0xFF303030));
  }
}
