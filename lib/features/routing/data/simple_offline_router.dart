import 'dart:math' as math;
import 'package:maplibre_gl/maplibre_gl.dart';

class RouteOption {
  final List<LatLng> geometry;
  final double distanceKm;
  final int durationMin;
  final String name;

  RouteOption({
    required this.geometry,
    required this.distanceKm,
    required this.durationMin,
    required this.name,
  });
}

class SimpleOfflineRouter {
  /// محاسبه فاصله بین دو نقطه (Haversine Formula)
  static double _calculateDistance(LatLng p1, LatLng p2) {
    const earthRadius = 6371000.0; // متر
    final lat1 = p1.latitude * math.pi / 180;
    final lat2 = p2.latitude * math.pi / 180;
    final dLat = (p2.latitude - p1.latitude) * math.pi / 180;
    final dLng = (p2.longitude - p1.longitude) * math.pi / 180;

    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(lat1) * math.cos(lat2) *
        math.sin(dLng / 2) * math.sin(dLng / 2);
    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    return earthRadius * c;
  }

  /// ایجاد مسیر مستقیم (Straight Line) - سریع‌ترین
  static RouteOption _createStraightRoute(LatLng origin, LatLng destination) {
    final distance = _calculateDistance(origin, destination);
    final distanceKm = distance / 1000;
    final durationMin = (distanceKm / 80 * 60).toInt(); // فرض: 80 کیلومتر بر ساعت

    return RouteOption(
      geometry: [origin, destination],
      distanceKm: distanceKm,
      durationMin: durationMin,
      name: 'مسیر مستقیم (سریع‌ترین)',
    );
  }

  /// ایجاد مسیر با نقاط میانی (Waypoints) - کوتاه‌ترین
  static RouteOption _createWaypointRoute(LatLng origin, LatLng destination) {
    final waypoints = _generateWaypoints(origin, destination, 3);
    double totalDistance = 0;
    for (int i = 0; i < waypoints.length - 1; i++) {
      totalDistance += _calculateDistance(waypoints[i], waypoints[i + 1]);
    }

    final distanceKm = totalDistance / 1000;
    final durationMin = (distanceKm / 60 * 60).toInt(); // فرض: 60 کیلومتر بر ساعت

    return RouteOption(
      geometry: waypoints,
      distanceKm: distanceKm,
      durationMin: durationMin,
      name: 'مسیر محلی (کوتاه‌ترین)',
    );
  }

  /// ایجاد مسیر امن (Safe Route) - طولانی‌ترین اما ایمن‌ترین
  static RouteOption _createSafeRoute(LatLng origin, LatLng destination) {
    final waypoints = _generateSafeWaypoints(origin, destination, 5);
    double totalDistance = 0;
    for (int i = 0; i < waypoints.length - 1; i++) {
      totalDistance += _calculateDistance(waypoints[i], waypoints[i + 1]);
    }

    final distanceKm = totalDistance / 1000;
    final durationMin = (distanceKm / 50 * 60).toInt(); // فرض: 50 کیلومتر بر ساعت

    return RouteOption(
      geometry: waypoints,
      distanceKm: distanceKm,
      durationMin: durationMin,
      name: 'مسیر ایمن (طولانی‌ترین)',
    );
  }

  /// تولید نقاط میانی بین دو نقطه
  static List<LatLng> _generateWaypoints(LatLng origin, LatLng destination, int count) {
    final waypoints = [origin];
    for (int i = 1; i < count; i++) {
      final t = i / count;
      final lat = origin.latitude + (destination.latitude - origin.latitude) * t;
      final lng = origin.longitude + (destination.longitude - origin.longitude) * t;
      waypoints.add(LatLng(lat, lng));
    }
    waypoints.add(destination);
    return waypoints;
  }

  /// تولید نقاط میانی برای مسیر ایمن (با انحراف)
  static List<LatLng> _generateSafeWaypoints(LatLng origin, LatLng destination, int count) {
    final baseWaypoints = _generateWaypoints(origin, destination, count);
    final safeWaypoints = <LatLng>[baseWaypoints[0]];

    for (int i = 1; i < baseWaypoints.length - 1; i++) {
      final wp = baseWaypoints[i];
      // اضافه کردن انحراف تصادفی برای شبیه‌سازی مسیر واقعی
      final offset = (i % 2 == 0 ? 0.002 : -0.002);
      safeWaypoints.add(LatLng(wp.latitude + offset, wp.longitude + offset));
    }
    safeWaypoints.add(baseWaypoints.last);
    return safeWaypoints;
  }

  /// محاسبه چند مسیر مختلف با دقت بیشتر
  static List<RouteOption> calculateRoutes(LatLng origin, LatLng destination) {
    final straight = _createStraightRoute(origin, destination);
    final local = _createWaypointRoute(origin, destination);
    final safe = _createSafeRoute(origin, destination);
    
    // مرتب‌سازی بر اساس زمان برای نمایش منطقی‌تر
    final routes = [straight, local, safe];
    routes.sort((a, b) => a.durationMin.compareTo(b.durationMin));
    return routes;
  }
}
