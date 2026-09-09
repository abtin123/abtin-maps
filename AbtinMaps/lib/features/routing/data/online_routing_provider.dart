import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/geo/geo_types.dart';
import 'routing_instruction_localizer.dart';
import '../../../core/localization/app_localizations.dart';
import 'routing_provider.dart';
import 'routing_service.dart';

/// پیاده‌سازی مسیریابی برخط بر پایهٔ API سازگار با OSRM.
///
/// endpoint به‌صورت constructor injection است تا نسخهٔ عملیاتی بتواند به
/// سرویس اختصاصی/قراردادی منتقل شود؛ endpoint عمومی پیش‌فرض فقط برای توسعه و
/// استفادهٔ سبک تعاملی مناسب است. هیچ مختصات مکانی در حافظه ذخیره نمی‌شود و
/// درخواست فقط پس از انتخاب صریح مقصد توسط کاربر ارسال می‌شود.
class OnlineRoutingProvider implements RoutingProvider {
  OnlineRoutingProvider({
    http.Client? client,
    this.endpoint = defaultEndpoint,
    this.requestTimeout = const Duration(seconds: 12),
    this.languageCode = _defaultLanguageCode,
  })  : _client = client ?? http.Client(),
        _ownsClient = client == null;

  /// endpoint پیش‌فرضِ قابل جایگزینی. برای تولید پرترافیک باید OSRM اختصاصی
  /// یا سرویس دارای قرارداد جایگزین شود.
  static const String defaultEndpoint = 'https://router.project-osrm.org';
  static String _defaultLanguageCode() => 'fa';

  final http.Client _client;
  final bool _ownsClient;
  final String endpoint;
  final Duration requestTimeout;
  final String Function() languageCode;

  @override
  RoutingEngine get engine => RoutingEngine.online;

  @override
  String get displayName => 'نقشه و مسیریابی آنلاین';

  @override
  bool get isOffline => false;

  @override
  String? lastError;

  @override
  Future<bool> isReady() async => true;

  @override
  Future<RouteInfo?> calculateRoute({
    required LatLng origin,
    required LatLng destination,
    bool offlineOnly = false,
  }) async {
    final routes = await calculateRoutes(
      origin: origin,
      destination: destination,
      offlineOnly: offlineOnly,
    );
    return routes.isEmpty ? null : routes.first;
  }

  Future<List<RouteInfo>> calculateRoutes({
    required LatLng origin,
    required LatLng destination,
    bool offlineOnly = false,
  }) async {
    lastError = null;
    if (offlineOnly) {
      lastError = AppStrings.getForLanguage(languageCode(), 'route_error_offline_unavailable');
      return const [];
    }
    if (!_isValidCoordinate(origin) || !_isValidCoordinate(destination)) {
      lastError = AppStrings.getForLanguage(languageCode(), 'route_error_invalid_coordinates');
      return const [];
    }

    final coordinates =
        '${origin.longitude.toStringAsFixed(6)},${origin.latitude.toStringAsFixed(6)};'
        '${destination.longitude.toStringAsFixed(6)},${destination.latitude.toStringAsFixed(6)}';
    final base = endpoint.endsWith('/')
        ? endpoint.substring(0, endpoint.length - 1)
        : endpoint;
    final uri = Uri.parse('$base/route/v1/driving/$coordinates').replace(
      queryParameters: const {
        'alternatives': 'true',
        'steps': 'true',
        'geometries': 'geojson',
        'overview': 'full',
      },
    );

    try {
      final response = await _client.get(
        uri,
        headers: const {
          // شناسهٔ شفاف برای سرویس‌های مبتنی بر OSM؛ از جعل User-Agent
          // مرورگر اجتناب شده است.
          'User-Agent': 'AbtinMaps/0.1 (online-routing)',
          'Accept': 'application/json',
        },
      ).timeout(requestTimeout);
      if (response.statusCode != 200) {
        lastError = AppStrings.getForLanguage(languageCode(), 'route_error_http')
            .replaceAll('{code}', '${response.statusCode}');
        return const [];
      }
      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        lastError = AppStrings.getForLanguage(languageCode(), 'route_error_unreadable_response');
        return const [];
      }
      if (decoded['code'] != 'Ok') {
        lastError = _osrmErrorMessage(decoded['code']?.toString(), languageCode());
        return const [];
      }
      final routesJson = decoded['routes'];
      if (routesJson is! List || routesJson.isEmpty) {
        lastError = AppStrings.getForLanguage(languageCode(), 'route_error_online_not_found');
        return const [];
      }

      final routes = <RouteInfo>[];
      for (final routeJson in routesJson) {
        if (routeJson is! Map) continue;
        final route = _parseRoute(Map<String, dynamic>.from(routeJson));
        if (route != null) routes.add(route);
      }
      if (routes.isEmpty) {
        lastError = AppStrings.getForLanguage(languageCode(), 'route_error_invalid_geometry');
      }
      return routes;
    } on TimeoutException {
      lastError = AppStrings.getForLanguage(languageCode(), 'route_error_timeout');
      return const [];
    } on FormatException {
      lastError = AppStrings.getForLanguage(languageCode(), 'route_error_invalid_response');
      return const [];
    } on http.ClientException {
      lastError = AppStrings.getForLanguage(languageCode(), 'route_error_connection');
      return const [];
    } catch (_) {
      lastError = AppStrings.getForLanguage(languageCode(), 'route_error_unexpected');
      return const [];
    }
  }

  RouteInfo? _parseRoute(Map<String, dynamic> route) {
    final geometry = route['geometry'];
    if (geometry is! Map) return null;
    final coordinates = geometry['coordinates'];
    if (coordinates is! List) return null;

    final points = <LatLng>[];
    for (final coordinate in coordinates) {
      if (coordinate is! List || coordinate.length < 2) continue;
      final lng = _asDouble(coordinate[0]);
      final lat = _asDouble(coordinate[1]);
      if (lat == null || lng == null || !lat.isFinite || !lng.isFinite)
        continue;
      points.add(LatLng(lat, lng));
    }
    if (points.length < 2) return null;

    final distanceM = _asDouble(route['distance']) ?? 0;
    final durationS = _asDouble(route['duration']) ?? 0;
    return RouteInfo(
      geometry: points,
      distanceKm: distanceM / 1000,
      durationMin: durationS / 60,
      instructions: _parseInstructions(route['legs'], languageCode()),
    );
  }

  List<RouteInstruction> _parseInstructions(Object? legsJson, String languageCode) {
    if (legsJson is! List) return const [];
    final instructions = <RouteInstruction>[];
    for (final legJson in legsJson) {
      if (legJson is! Map) continue;
      final stepsJson = legJson['steps'];
      if (stepsJson is! List) continue;
      for (final stepJson in stepsJson) {
        if (stepJson is! Map) continue;
        final step = Map<String, dynamic>.from(stepJson);
        final maneuver = step['maneuver'];
        if (maneuver is! Map) continue;
        final maneuverMap = Map<String, dynamic>.from(maneuver);
        final location = maneuverMap['location'];
        if (location is! List || location.length < 2) continue;
        final lng = _asDouble(location[0]);
        final lat = _asDouble(location[1]);
        if (lat == null || lng == null || !lat.isFinite || !lng.isFinite)
          continue;
        final type = maneuverMap['type']?.toString() ?? 'turn';
        final modifier = maneuverMap['modifier']?.toString();
        final exit = maneuverMap['exit'] is num
            ? (maneuverMap['exit'] as num).toInt()
            : null;
        final roadName = step['name']?.toString().trim();
        instructions.add(
          RouteInstruction(
            text: _instructionText(
              type: type,
              modifier: modifier,
              roadName: roadName?.isEmpty ?? true ? null : roadName,
              exit: exit,
              languageCode: languageCode,
            ),
            distanceMeters: _asDouble(step['distance']) ?? 0,
            location: LatLng(lat, lng),
            type: type,
            modifier: modifier,
            exit: exit,
          ),
        );
      }
    }
    return instructions;
  }

  String _instructionText({
    required String type,
    required String? modifier,
    required String? roadName,
    required int? exit,
    required String languageCode,
  }) => RoutingInstructionLocalizer.text(
        languageCode: languageCode,
        type: type,
        modifier: modifier,
        roadName: roadName,
        exit: exit,
      );

  String _osrmErrorMessage(String? code, String languageCode) => switch (code) {
        'NoRoute' => AppStrings.getForLanguage(languageCode, 'route_error_online_not_found'),
        'NoSegment' =>
          AppStrings.getForLanguage(languageCode, 'route_error_no_segment'),
        'TooBig' => AppStrings.getForLanguage(languageCode, 'route_error_too_big'),
        _ => AppStrings.getForLanguage(languageCode, 'route_error_online_failed'),
      };

  bool _isValidCoordinate(LatLng point) =>
      point.latitude.isFinite &&
      point.longitude.isFinite &&
      point.latitude.abs() <= 90 &&
      point.longitude.abs() <= 180;

  double? _asDouble(Object? value) => value is num ? value.toDouble() : null;

  void dispose() {
    if (_ownsClient) _client.close();
  }
}
